# -*- coding: utf-8 -*-
"""
StockRouter - 多源路由 + 熔断降级 + 数据聚合

核心逻辑：
1. 按数据类型选择可用数据源列表
2. 并发请求所有源（asyncio），取最快成功返回
3. 多源都成功时，实时数据取 Sina（延迟最低）；
              K线数据取 AkShare（覆盖最全）
4. 某源失败达到阈值 → 熔断（跳过该源）
5. 全源失败 → 返回缓存数据或模拟兜底
6. 所有结果记录 latency_ms，便于监控

使用示例：
    from stock_fetcher import get_router
    router = get_router()
    result = router.fetch_realtime("600036")
    print(result["price"], result["_source"])

    results = router.fetch_realtime_batch(["600036","000001","300750"])
    for r in results:
        print(r["symbol"], r.get("price"), r.get("_source"))

    klines = router.fetch_kline("600036", period="daily", limit=120)
"""

import os
import time
import json
import logging
import hashlib
from concurrent import futures
from typing import Optional, Dict, Any, List

from .base import BaseFetcher, FetchResult, SourceTag, DataType
from .akshare_fetcher import AkShareFetcher
from .sina_fetcher import SinaFetcher
from .tencent_fetcher import TencentFetcher
from .yfinance_fetcher import YFinanceFetcher

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════
#  缓存层（内存 LRU + 文件持久化兜底）
# ══════════════════════════════════════════════════════

class _Cache:
    """
    简易双层缓存：
    - L1: 进程内 dict（LRU，TTL=60s）
    - L2: 文件持久化（JSON，TTL=3600s，用于进程重启后兜底）
    """

    def __init__(self, cache_dir: str = "/tmp/quantos_cache", ttl: int = 60):
        self.ttl       = ttl
        self.cache_dir = cache_dir
        self._mem: Dict[str, tuple] = {}   # key -> (value, expire_ts)
        os.makedirs(cache_dir, exist_ok=True)

    def _key(self, data_type: str, symbol: str, **kwargs) -> str:
        extra = "".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        raw = f"{data_type}:{symbol}:{extra}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, data_type: str, symbol: str, **kwargs) -> Optional[Dict]:
        key = self._key(data_type, symbol, **kwargs)
        # L1
        if key in self._mem:
            val, exp = self._mem[key]
            if time.time() < exp:
                val["_from_cache"] = True
                return val
            del self._mem[key]
        # L2 文件
        fpath = f"{self.cache_dir}/{key}.json"
        if os.path.exists(fpath):
            try:
                mtime = os.path.getmtime(fpath)
                if time.time() - mtime < self.ttl * 60:
                    with open(fpath) as f:
                        data = json.load(f)
                    self._mem[key] = (data, time.time() + self.ttl)
                    data["_from_cache"] = True
                    return data
                else:
                    os.remove(fpath)
            except Exception:
                pass
        return None

    def set(self, data_type: str, symbol: str, data: Dict, **kwargs):
        key = self._key(data_type, symbol, **kwargs)
        self._mem[key] = (data, time.time() + self.ttl)
        fpath = f"{self.cache_dir}/{key}.json"
        try:
            with open(fpath, "w") as f:
                json.dump(data, f)
        except Exception:
            pass


# ══════════════════════════════════════════════════════
#  熔断器
# ══════════════════════════════════════════════════════

class _CircuitBreaker:
    """
    熔断器：某源连续失败 N 次后，跳过该源一段时间。

    状态机：
        CLOSED（正常）→ 失败数累加 → 达到阈值 → OPEN（熔断）
        OPEN（熔断）→ 等待冷却时间 → HALF_OPEN（试探）
        HALF_OPEN → 成功 → CLOSED；失败 → OPEN
    """

    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, fail_threshold: int = 3, recovery_timeout: float = 30.0):
        self.fail_threshold   = fail_threshold
        self.recovery_timeout = recovery_timeout
        self._state: Dict[str, str]  = {n: self.CLOSED for n in _SOURCE_NAMES}
        self._fail_cnt: Dict[str, int] = {n: 0 for n in _SOURCE_NAMES}
        self._last_fail: Dict[str, float] = {n: 0.0 for n in _SOURCE_NAMES}
        self._half_open_ok: Dict[str, bool] = {n: False for n in _SOURCE_NAMES}

    def is_available(self, name: str) -> bool:
        s = self._state[name]
        if s == self.CLOSED:
            return True
        if s == self.OPEN:
            if time.time() - self._last_fail[name] >= self.recovery_timeout:
                self._state[name] = self.HALF_OPEN
                self._half_open_ok[name] = False
                return True
            return False
        if s == self.HALF_OPEN:
            return True   # 放一个请求试探
        return True

    def record(self, name: str, success: bool):
        if success:
            self._fail_cnt[name] = 0
            if self._state[name] == self.HALF_OPEN:
                self._half_open_ok[name] = True
                self._state[name] = self.CLOSED
            elif self._state[name] == self.CLOSED:
                pass   # 保持正常
        else:
            self._fail_cnt[name] += 1
            self._last_fail[name] = time.time()
            if self._state[name] == self.HALF_OPEN:
                self._state[name] = self.OPEN
            elif self._fail_cnt[name] >= self.fail_threshold:
                self._state[name] = self.OPEN

    def status(self) -> Dict[str, Dict]:
        return {n: {"state": self._state[n], "fail_cnt": self._fail_cnt[n]}
                for n in _SOURCE_NAMES}


_SOURCE_NAMES = ["akshare", "sina", "tencent", "yfinance"]


# ══════════════════════════════════════════════════════
#  StockRouter
# ══════════════════════════════════════════════════════

class StockRouter:
    """
    多源股票数据路由

    设计原则：
    - 实时行情（A股）：Sina > Tencent > AkShare
    - K线数据（A股）：AkShare > yfinance
    - 全球市场（美/港）：yfinance
    - 熔断：某源连续失败3次后跳过，最长等待30s恢复
    - 缓存：60s 内同名请求直接返回（内存 LRU）
    - 兜底：所有源失败 → 读缓存 → 读模拟数据
    """

    def __init__(
        self,
        use_cache: bool = True,
        use_circuit_breaker: bool = True,
        cache_ttl: int = 60,
        parallel_fetch: bool = True,
    ):
        self.cache           = _Cache(ttl=cache_ttl) if use_cache else None
        self.cb              = _CircuitBreaker() if use_circuit_breaker else None
        self.parallel_fetch  = parallel_fetch

        # 初始化各 fetcher
        self.fetchers: Dict[str, BaseFetcher] = {
            "akshare":  AkShareFetcher(timeout=15.0),
            "sina":     SinaFetcher(timeout=6.0),
            "tencent":  TencentFetcher(timeout=6.0),
            "yfinance": YFinanceFetcher(timeout=12.0),
        }

        # 各数据类型偏好的数据源顺序（SourceTag 升序 = 优先级升序）
        self._realtime_sources = ["sina", "tencent", "akshare"]
        self._kline_sources    = ["akshare", "yfinance"]
        self._us_sources       = ["yfinance"]

    # ── 主入口 ─────────────────────────────────────────────

    def fetch_realtime(self, symbol: str, skip_cache: bool = False) -> Dict[str, Any]:
        """
        获取实时行情。
        优先使用 Sina；Sina 失败自动降级 Tencent → AkShare。
        所有源失败则返回缓存或模拟数据。
        """
        # 缓存命中
        if not skip_cache and self.cache:
            cached = self.cache.get("realtime", symbol)
            if cached:
                logger.debug(f"[router] cache hit for {symbol}")
                return cached

        # 选择数据源顺序
        sources = self._select_sources(symbol, "realtime")
        result  = self._try_sources(sources, symbol, "realtime")

        if result is not None:
            if self.cache:
                self.cache.set("realtime", symbol, result)
            return result

        # 全源失败 → 缓存兜底
        if self.cache:
            cached = self.cache.get("realtime", symbol)
            if cached:
                cached["_fallback"] = "cache"
                return cached

        # 最后兜底：模拟数据
        return self._mock_realtime(symbol)

    def fetch_realtime_batch(
        self,
        symbols: List[str],
        skip_cache: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        批量获取实时行情（并发）。
        返回结果顺序与输入 symbols 一致。
        """
        results = [None] * len(symbols)
        if self.parallel_fetch:
            with futures.ThreadPoolExecutor(max_workers=8) as ex:
                futs = {
                    ex.submit(self.fetch_realtime, sym, skip_cache): i
                    for i, sym in enumerate(symbols)
                }
                for fut in futures.as_completed(futs):
                    idx = futs[fut]
                    try:
                        results[idx] = fut.result()
                    except Exception as e:
                        logger.warning(f"[router] batch error at {symbols[idx]}: {e}")
                        results[idx] = self._mock_realtime(symbols[idx])
        else:
            for i, sym in enumerate(symbols):
                results[i] = self.fetch_realtime(sym, skip_cache)
        return results

    def fetch_kline(
        self,
        symbol: str,
        period: str = "daily",
        adjust: str = "qfq",
        limit: int = 60,
        skip_cache: bool = False,
    ) -> Dict[str, Any]:
        """
        获取K线数据。
        优先 AkShare（覆盖最全）；失败降级 yfinance。
        """
        cache_key = f"kline:{period}:{adjust}:{limit}"

        if not skip_cache and self.cache:
            cached = self.cache.get(cache_key, symbol)
            if cached:
                return cached

        sources = self._select_sources(symbol, "kline")
        result  = self._try_sources(sources, symbol, "kline",
                                    period=period, adjust=adjust, limit=limit)

        if result is not None:
            if self.cache:
                self.cache.set(cache_key, symbol, result,
                               period=period, adjust=adjust, limit=limit)
            return result

        # 缓存兜底
        if self.cache:
            cached = self.cache.get(cache_key, symbol)
            if cached:
                cached["_fallback"] = "cache"
                return cached

        return self._mock_kline(symbol, limit)

    def fetch_signal(self, symbol: str) -> Dict[str, Any]:
        """
        生成选股信号（整合实时 + K线 + RSI）。
        """
        quote = self.fetch_realtime(symbol)
        klines = self.fetch_kline(symbol, limit=60)

        closes = [k["close"] for k in klines.get("klines", [])]
        if len(closes) < 20:
            return self._mock_signal(symbol)

        ma5  = sum(closes[-5:]) / 5
        ma20 = sum(closes[-20:]) / 20
        ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else ma20

        # RSI（简化版）
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains  = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]
        avg_g  = sum(gains[-14:]) / 14 if gains else 0
        avg_l  = sum(losses[-14:]) / 14 if losses else 0
        rsi    = 100 - (100 / (1 + avg_g / max(avg_l, 1e-9))) if avg_l else 100

        price      = quote.get("price", 0)
        amount     = quote.get("amount", 0)
        suggestion = "HOLD"

        score   = 0
        reasons = []

        if amount > 300_000_000:
            score += 20; reasons.append("成交额>3亿")
        if 10 <= price <= 100:
            score += 15
        if 35 <= rsi <= 65:
            score += 20; reasons.append(f"RSI={rsi:.0f}")
        if ma20 > ma60:
            score += 25; reasons.append("MA20>MA60")
        if price > ma20:
            score += 20; reasons.append("价格>MA20")

        if score >= 80:
            suggestion = "BUY"
        elif rsi > 70:
            suggestion = "SELL"
        elif rsi < 30:
            suggestion = "BUY"

        return {
            "symbol":     symbol,
            "name":       quote.get("name", symbol),
            "price":      price,
            "rsi":        round(rsi, 2),
            "ma5":        round(ma5, 2),
            "ma20":       round(ma20, 2),
            "ma60":       round(ma60, 2),
            "score":      score,
            "reasons":    reasons,
            "suggestion": suggestion,
            "_source":    quote.get("_source", "unknown"),
            "_latency_ms": quote.get("_latency_ms", 0),
        }

    # ── 路由核心 ─────────────────────────────────────────

    def _select_sources(self, symbol: str, data_type: str) -> List[str]:
        """根据股票类型和数据类型选择数据源顺序"""
        if data_type == "realtime":
            # 港股/美股 → yfinance
            if self._is_foreign(symbol):
                return ["yfinance"]
            return list(self._realtime_sources)
        elif data_type == "kline":
            if self._is_foreign(symbol):
                return ["yfinance"]
            return list(self._kline_sources)
        return ["sina"]

    def _is_foreign(self, symbol: str) -> bool:
        """判断是否为港股/美股"""
        sym = symbol.lower()
        foreign_suffixes = (".hk", ".ss", ".sz", ".l", ".ax", ".to", ".vi")
        return any(sym.endswith(s) for s in foreign_suffixes) or \
               sym.isascii() and not sym.isdigit()

    def _try_sources(
        self,
        source_names: List[str],
        symbol: str,
        data_type: str,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """
        按顺序尝试各数据源，直到某个成功。
        并发 + 熔断双重保障。
        """
        # 过滤熔断中的源
        available = [
            n for n in source_names
            if self.cb is None or self.cb.is_available(n)
        ]
        if not available:
            logger.warning(f"[router] all sources circuit-opened for {symbol}")
            return None

        # 按 SourceTag 排序（优先级高的排前面）
        available.sort(key=lambda n: self.fetchers[n].source_tag.value)

        if self.parallel_fetch and len(available) > 1:
            # 并发取第一个成功
            return self._race_sources(available, symbol, data_type, **kwargs)
        else:
            # 串行降级
            return self._fallback_sources(available, symbol, data_type, **kwargs)

    def _race_sources(
        self,
        source_names: List[str],
        symbol: str,
        data_type: str,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """并发竞速：取最快返回的有效结果"""
        with futures.ThreadPoolExecutor(max_workers=len(source_names)) as ex:
            futs = {}
            for name in source_names:
                fetcher = self.fetchers[name]
                if data_type == "realtime":
                    fut = ex.submit(fetcher.fetch_realtime, symbol)
                else:
                    fut = ex.submit(fetcher.fetch_kline, symbol, **kwargs)
                futs[fut] = name

            for fut in futures.as_completed(futs, timeout=20):
                name = futs[fut]
                try:
                    result = fut.result()
                    if result.valid and result.data:
                        self._record_success(name)
                        return result.data
                    else:
                        self._record_fail(name, result.error)
                except Exception as e:
                    self._record_fail(name, str(e))

        return None

    def _fallback_sources(
        self,
        source_names: List[str],
        symbol: str,
        data_type: str,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """串行降级：按优先级依次尝试"""
        for name in source_names:
            fetcher = self.fetchers[name]
            try:
                if data_type == "realtime":
                    result = fetcher.fetch_realtime(symbol)
                else:
                    result = fetcher.fetch_kline(symbol, **kwargs)

                if result.valid and result.data:
                    self._record_success(name)
                    return result.data
                else:
                    self._record_fail(name, result.error)
            except Exception as e:
                self._record_fail(name, str(e))
        return None

    def _record_success(self, name: str):
        if self.cb:
            self.cb.record(name, True)
        logger.debug(f"[router] {name} OK")

    def _record_fail(self, name: str, err: str):
        if self.cb:
            self.cb.record(name, False)
        logger.warning(f"[router] {name} FAILED: {err}")

    # ── 模拟/兜底数据 ────────────────────────────────────

    @staticmethod
    def _mock_realtime(symbol: str) -> Dict[str, Any]:
        prices = {
            "600036": {"name": "招商银行",   "price": 35.50},
            "600900": {"name": "长江电力",   "price": 22.50},
            "601288": {"name": "农业银行",   "price": 3.20},
            "000858": {"name": "五粮液",     "price": 150.00},
            "300750": {"name": "宁德时代",   "price": 200.00},
            "601318": {"name": "中国平安",   "price": 42.00},
            "002475": {"name": "立讯精密",   "price": 28.00},
            "600519": {"name": "贵州茅台",   "price": 1600.00},
        }
        data = prices.get(symbol, {"name": symbol, "price": 20.0})
        data.update({
            "symbol":    symbol,
            "change_pct": 0.0,
            "change":     0.0,
            "open":       data["price"] * 0.99,
            "high":       data["price"] * 1.02,
            "low":        data["price"] * 0.98,
            "prev_close": data["price"],
            "volume":     1_000_000,
            "amount":     data["price"] * 1_000_000,
            "bid_vols":   [0]*5,
            "ask_vols":   [0]*5,
            "bid_prs":    [0.0]*5,
            "ask_prs":    [0.0]*5,
            "rsi":        50.0,
            "timestamp":  time.strftime("%Y-%m-%d %H:%M:%S"),
            "_source":    "mock",
            "_fallback":  "all_sources_failed",
        })
        return data

    @staticmethod
    def _mock_kline(symbol: str, limit: int = 60) -> Dict[str, Any]:
        base_prices = {
            "600036": 35.0, "600900": 22.0, "601288": 3.2,
            "000858": 150.0, "300750": 200.0, "601318": 42.0,
            "002475": 28.0, "600519": 1600.0,
        }
        import random
        base_price  = base_prices.get(symbol, 20.0)
        current     = base_price
        klines      = []
        for i in range(limit - 1, -1, -1):
            date = time.gmtime(time.time() - i * 86400)
            if date.tm_wday >= 5:
                continue
            change = (random.random() - 0.5) * 0.04
            current = current * (1 + change)
            open_   = current * (1 + (random.random() - 0.5) * 0.01)
            high    = current * (1 + random.random() * 0.02)
            low     = current * (1 - random.random() * 0.02)
            vol     = int(1_000_000 + random.random() * 500_000)
            klines.append({
                "date":    time.strftime("%Y-%m-%d", date),
                "open":    round(open_, 2),
                "high":    round(high, 2),
                "low":     round(low, 2),
                "close":   round(current, 2),
                "volume":  vol,
                "amount":  current * vol,
                "turnover": round(random.random() * 3, 2),
            })
        return {
            "klines":    klines,
            "symbol":    symbol,
            "period":    "daily",
            "adjust":    "qfq",
            "_source":   "mock",
            "_fallback": "all_sources_failed",
        }

    @staticmethod
    def _mock_signal(symbol: str) -> Dict[str, Any]:
        return {
            "symbol":     symbol,
            "name":       symbol,
            "price":      35.0,
            "rsi":        45.0,
            "ma5":        34.5,
            "ma20":       34.0,
            "ma60":       33.5,
            "score":      85,
            "reasons":    ["RSI=45", "MA20>MA60", "价格>MA20"],
            "suggestion": "BUY",
            "_source":    "mock",
        }

    # ── 诊断 ─────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """返回各数据源统计"""
        return {
            name: fetcher.stats()
            for name, fetcher in self.fetchers.items()
        }

    def circuit_status(self) -> Dict[str, Any]:
        """返回熔断器状态"""
        if self.cb is None:
            return {"enabled": False}
        return {"enabled": True, "sources": self.cb.status()}

    def health_check(self) -> Dict[str, bool]:
        """各数据源健康检查"""
        return {name: f.health_check() for name, f in self.fetchers.items()}


# ══════════════════════════════════════════════════════
#  全局单例（懒加载）
# ══════════════════════════════════════════════════════

_router: Optional[StockRouter] = None


def get_router(
    use_cache: bool = True,
    use_circuit_breaker: bool = True,
    parallel: bool = True,
) -> StockRouter:
    """获取全局 Router 单例"""
    global _router
    if _router is None:
        _router = StockRouter(
            use_cache=use_cache,
            use_circuit_breaker=use_circuit_breaker,
            parallel_fetch=parallel,
        )
    return _router


def reset_router():
    """重置全局 Router（测试用）"""
    global _router
    _router = None

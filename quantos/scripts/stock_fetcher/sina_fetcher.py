# -*- coding: utf-8 -*-
"""
新浪财经 A股实时行情获取器

API: https://hq.sinajs.cn/list={symbols}
返回格式: var hq_str_sh600036="招商银行,35.50,35.20,35.30,...;

优点：
- 无需认证
- 实时性强（交易所直连延迟 < 100ms）
- 覆盖全A股 + 基金 + 期货 + 港股

缺点：
- 返回格式原始，需要手动解析
- 无批量接口，一次最多约 100 个 symbol
- 访问频率限制（约每分钟 300 次）
"""

import re
import time
import logging
from typing import Optional, Dict, Any, List

import requests

from .base import BaseFetcher, FetchResult, SourceTag

logger = logging.getLogger(__name__)


class SinaFetcher(BaseFetcher):
    """新浪财经实时行情"""

    name       = "sina"
    source_tag = SourceTag.SINA

    # 新浪 API（支持多个交易所）
    _URL = "https://hq.sinajs.cn/list={symbols}"

    # 交易所前缀映射
    _EXCHANGE_MAP = {
        "sh": "上证",   # 沪市
        "sz": "深证",   # 深市
        "bj": "北证",   # 北交所
    }

    def __init__(self, timeout: float = 6.0, retry: int = 2):
        super().__init__(timeout, retry)
        self._session = requests.Session()
        self._session.headers.update({
            "Referer": "https://finance.sina.com.cn/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
        })

    # ── 主方法 ─────────────────────────────────────────────

    def _fetch_realtime(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取单个股票实时行情"""
        # 自动补前缀（A股标准格式）
        prefix, code = self._normalize(symbol)
        full = f"{prefix}{code}"

        raw = self._http_get(full)
        if not raw:
            return None

        return self._parse(raw, prefix, code)

    def fetch_batch(self, symbols: List[str]) -> List[FetchResult]:
        """
        批量获取实时行情（一次最多 100 个）。
        返回 FetchResult 列表。
        """
        results = []
        # 按交易所分组，最多 100 个/请求
        batch_size = 100
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]
            # 补全前缀
            full_list = []
            for s in batch:
                p, c = self._normalize(s)
                full_list.append(f"{p}{c}")

            raw_list = self._http_get(",".join(full_list))
            if not raw_list:
                for s in batch:
                    results.append(self._make_error(s, "http empty"))
                continue

            lines = raw_list.strip().split("\n")
            for s, line in zip(batch, lines):
                p, c = self._normalize(s)
                data = self._parse(line, p, c)
                if data:
                    data["_source"] = self.name
                    results.append(FetchResult(
                        source=self.name,
                        source_tag=self.source_tag,
                        data_type=1,
                        symbol=s,
                        data=data,
                        valid=True,
                    ))
                else:
                    results.append(self._make_error(s, "parse failed"))
            time.sleep(0.05)  # 避免触发频率限制
        return results

    # ── HTTP ───────────────────────────────────────────────

    def _http_get(self, symbols: str) -> Optional[str]:
        """请求新浪 API"""
        url = self._URL.format(symbols=symbols)
        try:
            resp = self._session.get(url, timeout=self.timeout)
            resp.encoding = "gbk"   # 新浪默认 GBK 编码
            if resp.status_code == 200 and resp.text:
                return resp.text
            return None
        except requests.RequestException as e:
            logger.warning(f"[sina] http error: {e}")
            return None

    # ── 解析 ───────────────────────────────────────────────

    def _parse(
        self,
        raw: str,
        prefix: str,
        code: str,
    ) -> Optional[Dict[str, Any]]:
        """
        解析新浪 hq_str 格式

        字段顺序（A 股）：
        0: 名称
        1: 今日开盘价
        2: 昨日收盘价
        3: 当前价格
        4: 今日最高价
        5: 今日最低价
        6: 买一价（即时）
        7: 卖一价（即时）
        8: 成交量（股）
        9: 成交额（元）
        10: 买1数量
        11: 买1报价
        ... 买2-5 ...
        ... 卖1-5 ...
        14: 日期
        15: 时间
        16: 状态（0=正常）
        """
        # 提取 = 后面的内容
        m = re.search(r'hq_str_[a-z]{2}(\d+)="(.+?)"', raw)
        if not m:
            return None

        fields = m.group(2).split(",")
        if len(fields) < 16:
            return None

        try:
            name      = fields[0].strip()
            open_px   = self._f(fields[1])
            prev_cls  = self._f(fields[2])
            price     = self._f(fields[3])
            high      = self._f(fields[4])
            low       = self._f(fields[5])
            bid       = self._f(fields[6])
            ask       = self._f(fields[7])
            volume    = self._i(fields[8])
            amount    = self._f(fields[9])
            timestamp = f"{fields[14]} {fields[15]}"
            change    = round(price - prev_cls, 4)
            change_pct = round(change / prev_cls * 100, 4) if prev_cls else 0.0

            # 解析买卖五档
            bid_vols, bid_prs = [], []
            ask_vols, ask_prs = [], []
            for j in range(10, 20):
                if j + 1 < len(fields):
                    bid_vols.append(self._i(fields[j]))     if j % 2 == 0 else bid_prs.append(self._f(fields[j]))
                    ask_vols.append(self._i(fields[j]))     if j % 2 == 1 else None
                    ask_prs.append(self._f(fields[j]))     if j % 2 == 0 else None
                else:
                    break

            # 整理五档
            bids = list(zip(
                bid_prs[:5] + [0.0]*5,
                bid_vols[:5] + [0]*5,
            ))[:5]
            asks = list(zip(
                ask_prs[:5] + [0.0]*5,
                ask_vols[:5] + [0]*5,
            ))[:5]

            return {
                "symbol":      code,
                "name":       name,
                "price":      price,
                "open":       open_px,
                "high":       high,
                "low":        low,
                "prev_close": prev_cls,
                "change":     change,
                "change_pct": change_pct,
                "volume":     volume,
                "amount":     amount,
                "bid":        bid,
                "ask":        ask,
                "bid_vols":   bid_vols[:5],
                "ask_vols":   ask_vols[:5],
                "bid_prs":    bid_prs[:5],
                "ask_prs":    ask_prs[:5],
                "timestamp":  timestamp,
                "_prefix":    prefix,
                "_exchange":  self._EXCHANGE_MAP.get(prefix, "未知"),
            }

        except (IndexError, ValueError, TypeError) as e:
            logger.warning(f"[sina] parse error for {prefix}{code}: {e}")
            return None

    # ── 工具 ───────────────────────────────────────────────

    @staticmethod
    def _normalize(symbol: str) -> tuple:
        """
        将各种格式的 symbol 标准化为 (prefix, code)
        例如：
            600036  -> ("sh", "600036")
            sh600036 -> ("sh", "600036")
            000001  -> ("sz", "000001")
            sz000001 -> ("sz", "000001")
            831171  -> ("bj", "831171")
            bj831171 -> ("bj", "831171")
        """
        sym = symbol.strip().lower()
        for p in ("sh", "sz", "bj"):
            if sym.startswith(p):
                return p, sym[len(p):]
        # 自动推断
        code = sym.zfill(6)
        if code.startswith("6"):
            return "sh", code
        elif code.startswith(("0", "3")):
            return "sz", code
        elif code.startswith("4") or code.startswith("8"):
            return "bj", code
        return "sh", code   # 默认沪市

    @staticmethod
    def _f(v) -> float:
        try: return float(v)
        except: return 0.0

    @staticmethod
    def _i(v) -> int:
        try: return int(float(v))
        except: return 0

    def _make_error(self, symbol: str, reason: str) -> FetchResult:
        return FetchResult(
            source=self.name,
            source_tag=self.source_tag,
            data_type=1,
            symbol=symbol,
            data=None,
            error=reason,
            valid=False,
        )

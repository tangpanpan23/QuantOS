# -*- coding: utf-8 -*-
"""
腾讯财经 A股实时行情获取器

API: https://qt.gtimg.cn/q={symbols}
返回格式: v_sh600036="49~招商银行~35.500~...;

优点：
- 延迟低（腾讯行情直连）
- 实时性强
- 无需认证

缺点：
- 返回格式特殊，需要解析
- 批量请求有限制（约 100 个/次）
"""

import re
import time
import logging
from typing import Optional, Dict, Any, List

import requests

from .base import BaseFetcher, FetchResult, SourceTag

logger = logging.getLogger(__name__)


class TencentFetcher(BaseFetcher):
    """腾讯财经实时行情"""

    name       = "tencent"
    source_tag = SourceTag.TENCENT

    _URL = "https://qt.gtimg.cn/q={symbols}"

    def __init__(self, timeout: float = 6.0, retry: int = 2):
        super().__init__(timeout, retry)
        self._session = requests.Session()
        self._session.headers.update({
            "Referer": "https://finance.qq.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
        })

    # ── 主方法 ─────────────────────────────────────────────

    def _fetch_realtime(self, symbol: str) -> Optional[Dict[str, Any]]:
        prefix, code = self._normalize(symbol)
        full = f"{prefix}{code}"

        raw = self._http_get(full)
        if not raw:
            return None

        return self._parse(raw, prefix, code)

    def fetch_batch(self, symbols: List[str]) -> List[FetchResult]:
        """批量获取（每批最多 100 个）"""
        results = []
        batch_size = 100
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            full_list = [f"{p}{c}" for p, c in (self._normalize(s) for s in batch)]
            raw = self._http_get(",".join(full_list))
            if not raw:
                for s in batch:
                    results.append(self._make_error(s, "http empty"))
                continue

            lines = raw.strip().split("\n")
            for s, line in zip(batch, lines):
                p, c = self._normalize(s)
                data = self._parse(line, p, c)
                if data:
                    data["_source"] = self.name
                    results.append(FetchResult(
                        source=self.name, source_tag=self.source_tag,
                        data_type=1, symbol=s, data=data, valid=True,
                    ))
                else:
                    results.append(self._make_error(s, "parse failed"))
            time.sleep(0.05)
        return results

    # ── HTTP ─────────────────────────────────────────────

    def _http_get(self, symbols: str) -> Optional[str]:
        url = self._URL.format(symbols=symbols)
        try:
            resp = self._session.get(url, timeout=self.timeout)
            resp.encoding = "utf-8"
            if resp.status_code == 200 and resp.text:
                return resp.text
            return None
        except requests.RequestException as e:
            logger.warning(f"[tencent] http error: {e}")
            return None

    # ── 解析 ─────────────────────────────────────────────

    def _parse(
        self,
        raw: str,
        prefix: str,
        code: str,
    ) -> Optional[Dict[str, Any]]:
        """
        腾讯 qt.gtimg 格式解析

        字段（以 ~ 分割）：
        0:  未知标志
        1:  股票名称
        2:  当前价格
        3:  昨收
        4:  今日开盘价
        5:  成交量（股）
        6:  外盘（主动买）
        7:  内盘（主动卖）
        8:  买一价
        9:  买一量（手）
        10: 买二价
        11: 买二量
        12: 买三价
        13: 买三量
        14: 买四价
        15: 买四量
        16: 买五价
        17: 买五量
        18: 卖一价
        19: 卖一量
        ... 卖二-五 ...
        27: 今日最高
        28: 今日最低
        29: 时间（YYYYMMDD HH:MM:SS）
        30: 成交额（元）
        31: 涨跌额
        32: 涨跌幅（%）
        ...
        36: 市净率
        ...
        44: 换手率（%）
        45: 总市值
        46: 流通市值
        ...
        48: 涨停价
        49: 跌停价
        ...
        """
        m = re.search(r'v_' + prefix + r'(\d+)="(.+?)"', raw)
        if not m:
            return None

        fields = m.group(2).split("~")
        if len(fields) < 50:
            return None

        try:
            name      = fields[1].strip()
            price     = self._f(fields[2])
            prev_cls  = self._f(fields[3])
            open_px   = self._f(fields[4])
            volume    = self._i(fields[5])
            high      = self._f(fields[27])
            low       = self._f(fields[28])
            amount    = self._f(fields[30])
            change    = self._f(fields[31])
            change_pct= self._f(fields[32])
            timestamp = fields[29].strip()
            pb        = self._f(fields[36])
            turnover  = self._f(fields[44])
            mkt_cap   = self._f(fields[45])
            float_cap = self._f(fields[46])
            bid_prs   = [self._f(fields[f]) for f in [8, 10, 12, 14, 16]]
            bid_vols  = [self._i(fields[f]) * 100 for f in [9, 11, 13, 15, 17]]  # 手→股
            ask_prs   = [self._f(fields[f]) for f in [18, 20, 22, 24, 26]]
            ask_vols  = [self._i(fields[f]) * 100 for f in [19, 21, 23, 25, 27]]

            return {
                "symbol":       code,
                "name":         name,
                "price":        price,
                "open":         open_px,
                "high":         high,
                "low":          low,
                "prev_close":   prev_cls,
                "change":       change,
                "change_pct":   change_pct,
                "volume":       volume,
                "amount":       amount,
                "bid":          bid_prs[0] if bid_prs else 0.0,
                "ask":          ask_prs[0] if ask_prs else 0.0,
                "bid_prs":      bid_prs,
                "bid_vols":     bid_vols,
                "ask_prs":      ask_prs,
                "ask_vols":     ask_vols,
                "timestamp":    timestamp,
                "pe_ttm":       0.0,   # 腾讯接口不直接返回，自己算或留空
                "pb":           pb,
                "turnover":     turnover,
                "market_cap":   mkt_cap,
                "float_market_cap": float_cap,
                "_prefix":      prefix,
                "_exchange":    "上证" if prefix == "sh" else "深证",
            }
        except (IndexError, ValueError) as e:
            logger.warning(f"[tencent] parse error for {prefix}{code}: {e}")
            return None

    # ── 工具 ─────────────────────────────────────────────

    @staticmethod
    def _normalize(symbol: str) -> tuple:
        """同新浪：自动补前缀"""
        sym = symbol.strip().lower()
        for p in ("sh", "sz", "bj"):
            if sym.startswith(p):
                return p, sym[len(p):]
        code = sym.zfill(6)
        if code.startswith("6"):
            return "sh", code
        elif code.startswith(("0", "3")):
            return "sz", code
        elif code.startswith(("4", "8")):
            return "bj", code
        return "sh", code

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
            source=self.name, source_tag=self.source_tag,
            data_type=1, symbol=symbol, data=None,
            error=reason, valid=False,
        )

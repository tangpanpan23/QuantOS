# -*- coding: utf-8 -*-
"""
yFinance 全球数据获取器

覆盖：
- 美股（NYSE/NASDAQ/AMEX）
- 港股（HKEX）
- 全球 ETF
- 虚拟货币
- 外汇

依赖：pip install yfinance
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from .base import BaseFetcher, FetchResult, SourceTag

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_OK = True
except ImportError:
    YFINANCE_OK = False
    yf = None


class YFinanceFetcher(BaseFetcher):
    """yfinance 全球股票数据"""

    name       = "yfinance"
    source_tag = SourceTag.YFINANCE

    # A股 symbol → yfinance 格式映射
    # 例如：600036 -> 600036.SS（上交所）
    _CN_EXCHANGE = {
        "sh": ".SS",   # 上海
        "sz": ".SZ",   # 深圳
        "hk": ".HK",   # 港股
    }

    def __init__(self, timeout: float = 12.0, retry: int = 2):
        super().__init__(timeout, retry)

    # ── 实时 ─────────────────────────────────────────────

    def _fetch_realtime(self, symbol: str) -> Optional[Dict[str, Any]]:
        if not YFINANCE_OK:
            return None
        try:
            ticker = self._to_yf_symbol(symbol)
            tk = yf.Ticker(ticker)

            # 快取实时价格（10min 内缓存）
            info = tk.fast_info
            price  = info.last_price or 0.0
            prev   = info.previous_close or 0.0
            change = price - prev
            chg_pct = (change / prev * 100) if prev else 0.0

            # 历史 K 线算成交量等
            hist = tk.history(period="5d", auto_adjust=True)
            volume = int(hist["Volume"].iloc[-1]) if not hist.empty else 0
            amount = float(hist["Volume"].iloc[-1] * price) if not hist.empty else 0.0

            return {
                "symbol":        symbol,
                "name":          ticker,
                "price":         price,
                "change":        change,
                "change_pct":    round(chg_pct, 4),
                "open":          float(info.open or prev),
                "high":          float(info.day_high or price),
                "low":           float(info.day_low or price),
                "prev_close":    prev,
                "volume":        volume,
                "amount":        amount,
                "bid":           0.0,
                "ask":           0.0,
                "bid_vols":      [0]*5,
                "ask_vols":      [0]*5,
                "bid_prs":       [0.0]*5,
                "ask_prs":       [0.0]*5,
                "market_cap":    float(info.market_cap or 0),
                "float_market_cap": float(info.market_cap or 0),
                "pe_ttm":        float(getattr(info, "trailing_pe", 0) or 0),
                "pb":            float(getattr(info, "price_to_book", 0) or 0),
                "timestamp":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "_yf_ticker":    ticker,
            }
        except Exception as e:
            logger.warning(f"[yfinance] realtime error for {symbol}: {e}")
            return None

    # ── K线 ──────────────────────────────────────────────

    def _fetch_kline(
        self,
        symbol: str,
        period: str  = "daily",
        adjust: str  = "qfq",
        limit: int   = 60,
    ) -> Optional[Dict[str, Any]]:
        if not YFINANCE_OK:
            return None
        try:
            ticker = self._to_yf_symbol(symbol)

            # yfinance period: 1d/5d/1mo/3mo/6mo/1y/2y/5y/10y/ytd/max
            # 换算 limit → period
            yf_period = self._limit_to_period(limit)

            tk = yf.Ticker(ticker)
            hist = tk.history(period=yf_period, auto_adjust=True)
            if hist.empty:
                return None

            klines = []
            for idx, row in hist.tail(limit).iterrows():
                klines.append({
                    "date":    idx.strftime("%Y-%m-%d"),
                    "open":    float(row["Open"]),
                    "high":    float(row["High"]),
                    "low":     float(row["Low"]),
                    "close":   float(row["Close"]),
                    "volume":  int(row["Volume"]),
                    "amount":  float(row["Close"] * row["Volume"]),
                })
            return {"klines": klines, "symbol": symbol, "period": period, "adjust": adjust}
        except Exception as e:
            logger.warning(f"[yfinance] kline error for {symbol}: {e}")
            return None

    # ── 批量美股快照（Bonus）───────────────────────────────

    def fetch_batch_us(self, symbols: List[str]) -> List[FetchResult]:
        """
        批量获取美股实时行情。
        传入美股代码列表，如 ["AAPL", "MSFT", "GOOG"]
        """
        if not YFINANCE_OK:
            return []
        results = []
        try:
            tickers = yf.Tickers(" ".join(symbols))
            for sym in symbols:
                try:
                    tk = tickers.tickers[sym]
                    info = tk.fast_info
                    price = info.last_price or 0.0
                    prev  = info.previous_close or 0.0
                    change = price - prev
                    chg_pct = (change / prev * 100) if prev else 0.0
                    data = {
                        "symbol":  sym,
                        "name":    sym,
                        "price":   price,
                        "change":  change,
                        "change_pct": round(chg_pct, 4),
                        "prev_close": prev,
                        "volume":  0,
                        "amount":  0.0,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    results.append(FetchResult(
                        source="yfinance", source_tag=self.source_tag,
                        data_type=1, symbol=sym, data=data, valid=True,
                    ))
                except Exception as e:
                    results.append(FetchResult(
                        source="yfinance", source_tag=self.source_tag,
                        data_type=1, symbol=sym, data=None,
                        error=str(e), valid=False,
                    ))
        except Exception as e:
            logger.warning(f"[yfinance] batch error: {e}")
        return results

    # ── 工具 ─────────────────────────────────────────────

    def _to_yf_symbol(self, symbol: str) -> str:
        """
        A股/H股 symbol → yfinance 标准格式
        600036 -> 600036.SS
        0700.HK -> 0700.HK
        AAPL   -> AAPL
        """
        sym = symbol.strip().lower()
        # 已是 yfinance 格式
        if sym.endswith((".SS", ".SZ", ".HK", ".L")):
            return symbol.upper()
        # A股：自动补后缀
        for pfx, suffix in self._CN_EXCHANGE.items():
            if sym.startswith(pfx):
                return (sym[len(pfx):] + suffix).upper()
        # 纯数字 A股
        if symbol.isdigit():
            code = symbol.zfill(6)
            if code.startswith("6"):
                return code + ".SS"
            elif code.startswith(("0", "3")):
                return code + ".SZ"
        # 美股/其他：原样返回
        return symbol.upper()

    @staticmethod
    def _limit_to_period(limit: int) -> str:
        """将 limit 条 K线换算为 yfinance period 参数"""
        if limit <= 5:
            return "5d"
        elif limit <= 30:
            return "1mo"
        elif limit <= 90:
            return "3mo"
        elif limit <= 180:
            return "6mo"
        elif limit <= 365:
            return "1y"
        elif limit <= 730:
            return "2y"
        else:
            return "5y"

    def health_check(self) -> bool:
        if not YFINANCE_OK:
            return False
        try:
            yf.Ticker("AAPL").fast_info.last_price
            return True
        except Exception:
            return False

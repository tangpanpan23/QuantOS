# -*- coding: utf-8 -*-
"""
AkShare A股数据获取器

覆盖：
- 实时行情（东方财富）
- K线历史（支持日/周/月，前复权/后复权/不复权）
- 涨停股池
- 龙虎榜

依赖：pip install akshare pandas numpy
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from .base import BaseFetcher, FetchResult, SourceTag

logger = logging.getLogger(__name__)

# 延迟导入 akshare（可选依赖）
try:
    import akshare as ak
    import pandas as pd
    AKSHARE_OK = True
except ImportError:
    AKSHARE_OK = False
    ak = None
    pd = None


class AkShareFetcher(BaseFetcher):
    """AkShare A股数据"""

    name       = "akshare"
    source_tag = SourceTag.AKSHARE

    def __init__(self, timeout: float = 15.0, retry: int = 2):
        super().__init__(timeout, retry)

    # ── 实时 ─────────────────────────────────────────────

    def _fetch_realtime(self, symbol: str) -> Optional[Dict[str, Any]]:
        if not AKSHARE_OK:
            return None
        try:
            # 拉全市场快照（东方财富），过滤目标股票
            # 注意：akshare 每次调此接口约 5-10s，极慢，不适合高频
            df = ak.stock_zh_a_spot_em()
            row = df[df["代码"] == symbol]
            if row.empty:
                return None
            r = row.iloc[0]
            return {
                "symbol":       symbol,
                "name":         str(r.get("名称", "")),
                "price":        float(r.get("最新价") or 0),
                "change_pct":   float(r.get("涨跌幅") or 0),
                "change":       float(r.get("涨跌额") or 0),
                "open":         float(r.get("今开") or 0),
                "high":         float(r.get("最高") or 0),
                "low":          float(r.get("最低") or 0),
                "prev_close":   float(r.get("昨收") or 0),
                "volume":       int(r.get("成交量") or 0),
                "amount":       float(r.get("成交额") or 0),
                "bid":          0.0,
                "ask":          0.0,
                "bid_vols":     [0]*5,
                "ask_vols":     [0]*5,
                "bid_prs":      [0.0]*5,
                "ask_prs":      [0.0]*5,
                "turnover":     float(r.get("换手率") or 0),
                "pe_ttm":       float(r.get("市盈率-动态") or 0) or 0.0,
                "pb":           float(r.get("市净率") or 0) or 0.0,
                "market_cap":   float(r.get("总市值") or 0),
                "float_market_cap": float(r.get("流通市值") or 0),
                "52w_high":     float(r.get("52周最高") or 0) or 0.0,
                "52w_low":      float(r.get("52周最低") or 0) or 0.0,
                "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            logger.warning(f"[akshare] realtime error for {symbol}: {e}")
            return None

    # ── K线 ──────────────────────────────────────────────

    def _fetch_kline(
        self,
        symbol: str,
        period: str  = "daily",
        adjust: str  = "qfq",
        limit: int   = 60,
    ) -> Optional[Dict[str, Any]]:
        if not AKSHARE_OK:
            return None
        try:
            df = ak.stock_zh_a_hist(
                symbol   = symbol,
                period   = period,
                start_date = (datetime.now() - timedelta(days=limit * 2)).strftime("%Y%m%d"),
                end_date   = datetime.now().strftime("%Y%m%d"),
                adjust    = adjust,
            )
            if df is None or df.empty:
                return None

            # 列名兼容（akshare 版本差异）
            rename_map = {
                "日期":   "date",
                "开盘":   "open",
                "收盘":   "close",
                "最高":   "high",
                "最低":   "low",
                "成交量": "volume",
                "成交额": "amount",
                "涨跌幅": "change_pct",
                "涨跌额": "change",
                "换手率": "turnover",
            }
            df = df.rename(columns=rename_map)
            needed = {"date", "open", "close", "high", "low", "volume"}
            if not needed.issubset(df.columns):
                logger.warning(f"[akshare] kline missing columns: {df.columns.tolist()}")
                return None

            klines = []
            for _, row in df.tail(limit).iterrows():
                klines.append({
                    "date":       str(row.get("date", "")),
                    "open":       float(row.get("open", 0) or 0),
                    "high":       float(row.get("high", 0) or 0),
                    "low":        float(row.get("low", 0) or 0),
                    "close":      float(row.get("close", 0) or 0),
                    "volume":     int(row.get("volume", 0) or 0),
                    "amount":     float(row.get("amount", 0) or 0),
                    "change_pct": float(row.get("change_pct", 0) or 0),
                    "turnover":   float(row.get("turnover", 0) or 0),
                })
            return {"klines": klines, "symbol": symbol, "period": period, "adjust": adjust}
        except Exception as e:
            logger.warning(f"[akshare] kline error for {symbol}: {e}")
            return None

    # ── 涨停池（Bonus）───────────────────────────────────

    def fetch_limit_up(self, trade_date: str = "") -> List[Dict[str, Any]]:
        """获取当日涨停股池"""
        if not AKSHARE_OK:
            return []
        try:
            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")
            df = ak.stock_zt_pool_em(date=trade_date)
            return df.to_dict("records")
        except Exception as e:
            logger.warning(f"[akshare] limit_up error: {e}")
            return []

    # ── 健康检查 ─────────────────────────────────────────

    def health_check(self) -> bool:
        if not AKSHARE_OK:
            return False
        try:
            ak.stock_zh_index_spot_em()   # 沪深指数快照，最轻量
            return True
        except Exception:
            return False

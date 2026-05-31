# -*- coding: utf-8 -*-
"""历史日线行情写入层"""
import logging
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional

# 清除代理环境变量，避免系统透明代理拦截 AkShare 请求
for _k in list(os.environ.keys()):
    if "proxy" in _k.lower():
        del os.environ[_k]

from sqlalchemy import and_

from .db_client import get_session
from .models import DailyKlineDB
from .technical import calc_all_indicators

logger = logging.getLogger(__name__)


def _infer_market(symbol: str) -> str:
    if symbol.startswith(("6", "9", "5", "7")):
        return "SH"
    return "SZ"


def _to_sina_symbol(symbol: str) -> str:
    """股票代码转新浪格式"""
    if symbol.startswith("6") or symbol.startswith("9"):
        return f"sh{symbol}"
    return f"sz{symbol}"


def upsert_kline(
    symbol: str,
    trade_date: str,
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: int = 0,
    amount: float = 0,
    prev_close: float = None,
    change_pct: float = None,
    turnover_rate: float = None,
    data_source: str = "akshare",
    symbol_name: str = "",
    is_adj_close: int = 1,
    klines_buffer: List[Dict] = None,
) -> DailyKlineDB:
    """插入或更新单条日线K线。"""
    trade_date_obj = datetime.strptime(trade_date, "%Y-%m-%d").date()
    market = _infer_market(symbol)

    indicators = {}
    if klines_buffer:
        buffer_with_current = klines_buffer + [{
            "open": open_price, "high": high_price,
            "low": low_price, "close": close_price,
        }]
        indicators = calc_all_indicators(buffer_with_current)

    with get_session() as db:
        existing = db.query(DailyKlineDB).filter(
            DailyKlineDB.symbol == symbol,
            DailyKlineDB.trade_date == trade_date_obj,
        ).first()

        if existing:
            existing.open_price   = open_price
            existing.high_price   = high_price
            existing.low_price    = low_price
            existing.close_price  = close_price
            existing.volume       = volume
            existing.amount       = amount
            existing.prev_close   = prev_close
            existing.change_pct   = change_pct
            existing.turnover_rate = turnover_rate
            existing.data_source  = data_source
            if symbol_name:
                existing.symbol_name = symbol_name
            for key, val in indicators.items():
                if val is not None and hasattr(existing, key):
                    setattr(existing, key, val)
            db.add(existing)
            return existing
        else:
            kline = DailyKlineDB(
                symbol=str(symbol),
                symbol_name=symbol_name or "",
                trade_date=trade_date_obj,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                prev_close=prev_close,
                change_pct=change_pct,
                volume=volume,
                amount=amount,
                turnover_rate=turnover_rate,
                market=market,
                data_source=data_source,
                is_adj_close=is_adj_close,
                ma5=indicators.get("ma5"),
                ma10=indicators.get("ma10"),
                ma20=indicators.get("ma20"),
                ma60=indicators.get("ma60"),
                rsi6=indicators.get("rsi6"),
                rsi12=indicators.get("rsi12"),
                rsi24=indicators.get("rsi24"),
                macd_dif=indicators.get("macd_dif"),
                macd_dea=indicators.get("macd_dea"),
                macd_hist=indicators.get("macd_hist"),
                boll_upper=indicators.get("boll_upper"),
                boll_mid=indicators.get("boll_mid"),
                boll_lower=indicators.get("boll_lower"),
                kdj_k=indicators.get("kdj_k"),
                kdj_d=indicators.get("kdj_d"),
                kdj_j=indicators.get("kdj_j"),
                atr=indicators.get("atr"),
            )
            db.add(kline)
            return kline


def batch_upsert_klines(
    symbol: str,
    klines: List[Dict],
    data_source: str = "akshare",
    symbol_name: str = "",
) -> Dict:
    """
    批量写入K线数据（支持增量追加）。

    参数:
        symbol: 股票代码
        klines: K线列表，每条包含 date/open/high/low/close/volume/amount/turnover/change_pct
        data_source: 数据来源标识
        symbol_name: 股票名称

    返回:
        {"inserted": N, "updated": N, "failed": [dates]}
    """
    if not klines:
        return {"inserted": 0, "updated": 0, "failed": []}

    result = {"inserted": 0, "updated": 0, "failed": []}
    market = _infer_market(symbol)

    # 预加载历史K线用于计算指标（取最近250个交易日）
    hist = get_klines(symbol, limit=250)
    closes = [k["close"] for k in hist]

    for k in klines:
        try:
            k_date = k.get("date") or k.get("trade_date")
            if not k_date:
                continue

            trade_date_obj = datetime.strptime(str(k_date), "%Y-%m-%d").date()

            # 构建 buffer 用于计算指标
            closes_with_new = closes + [k["close"]]
            klines_buffer = [
                {"open": row.get("open", row["close"]),
                 "high": row.get("high", row["close"]),
                 "low": row.get("low", row["close"]),
                 "close": row["close"]}
                for row in klines[:klines.index(k)]
            ]

            indicators = {}
            if len(closes_with_new) >= 5:
                indicators = calc_all_indicators(klines_buffer + [k])

            with get_session() as db:
                existing = db.query(DailyKlineDB).filter(
                    DailyKlineDB.symbol == symbol,
                    DailyKlineDB.trade_date == trade_date_obj,
                ).first()

                if existing:
                    existing.open_price    = float(k.get("open", 0) or 0)
                    existing.high_price   = float(k.get("high", 0) or 0)
                    existing.low_price    = float(k.get("low", 0) or 0)
                    existing.close_price  = float(k["close"])
                    existing.volume       = int(k.get("volume", 0) or 0)
                    existing.amount       = float(k.get("amount", 0) or 0)
                    existing.change_pct   = float(k.get("change_pct", 0) or 0)
                    existing.turnover_rate= float(k.get("turnover", 0) or 0)
                    existing.data_source  = data_source
                    if symbol_name:
                        existing.symbol_name = symbol_name
                    for key, val in indicators.items():
                        if val is not None and hasattr(existing, key):
                            setattr(existing, key, val)
                    result["updated"] += 1
                else:
                    kline = DailyKlineDB(
                        symbol=str(symbol),
                        symbol_name=symbol_name or "",
                        trade_date=trade_date_obj,
                        open_price=float(k.get("open", 0) or 0),
                        high_price=float(k.get("high", 0) or 0),
                        low_price=float(k.get("low", 0) or 0),
                        close_price=float(k["close"]),
                        volume=int(k.get("volume", 0) or 0),
                        amount=float(k.get("amount", 0) or 0),
                        change_pct=float(k.get("change_pct", 0) or 0),
                        turnover_rate=float(k.get("turnover", 0) or 0),
                        market=market,
                        data_source=data_source,
                        is_adj_close=1,
                        ma5=indicators.get("ma5"),
                        ma10=indicators.get("ma10"),
                        ma20=indicators.get("ma20"),
                        ma60=indicators.get("ma60"),
                        rsi6=indicators.get("rsi6"),
                        rsi12=indicators.get("rsi12"),
                        rsi24=indicators.get("rsi24"),
                        macd_dif=indicators.get("macd_dif"),
                        macd_dea=indicators.get("macd_dea"),
                        macd_hist=indicators.get("macd_hist"),
                        boll_upper=indicators.get("boll_upper"),
                        boll_mid=indicators.get("boll_mid"),
                        boll_lower=indicators.get("boll_lower"),
                        kdj_k=indicators.get("kdj_k"),
                        kdj_d=indicators.get("kdj_d"),
                        kdj_j=indicators.get("kdj_j"),
                        atr=indicators.get("atr"),
                    )
                    db.add(kline)
                    result["inserted"] += 1

                closes.append(k["close"])

        except Exception as e:
            logger.warning(f"[Kline] Failed {symbol} {k.get('date', '')}: {e}")
            result["failed"].append(str(k.get("date", "")))

    logger.info(f"[Kline] {symbol}: inserted={result['inserted']}, updated={result['updated']}, failed={len(result['failed'])}")
    return result


def fetch_from_akshare(
    symbol: str,
    start_date: str = "",
    end_date: str = "",
    period: str = "daily",
    adjust: str = "qfq",
) -> List[Dict]:
    """
    从 AkShare 新浪接口拉取日线K线（东方财富接口被代理封禁时降级用）。

    参数:
        symbol: 股票代码（如 600036）
        start_date: 起始日期 YYYYMMDD
        end_date: 截止日期 YYYYMMDD
    """
    import akshare as ak

    sina_sym = _to_sina_symbol(symbol)
    df = ak.stock_zh_a_daily(symbol=sina_sym, adjust=adjust)

    if df is None or df.empty:
        return []

    # 统一列名
    df = df.reset_index()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    else:
        df.columns = ["date", "open", "high", "low", "close", "volume", "amount",
                      "outstanding_share", "turnover"][:len(df.columns)]

    # 按日期过滤
    if start_date:
        start_str = start_date.replace("-", "")
        df = df[df["date"] >= start_str]
    if end_date:
        end_str = end_date.replace("-", "")
        df = df[df["date"] <= end_str]

    # 转换金额单位（元 -> 万元）保持一致
    if "amount" in df.columns:
        df["amount"] = df["amount"] / 10000  # 新浪原始是元，DB用万元

    return df.to_dict(orient="records")


def fetch_and_save_kline(
    symbol: str,
    start_date: str = "",
    end_date: str = "",
    symbol_name: str = "",
) -> Dict:
    """
    拉取并写入单只股票的日线K线（仅写入 start_date 之后的数据）。

    参数:
        symbol: 股票代码
        start_date: 起始日期 YYYY-MM-DD 或 YYYYMMDD（空则从2026-01-01起）
        end_date: 截止日期
        symbol_name: 股票名称

    返回:
        {"inserted": N, "updated": N, "failed": N}
    """
    # 默认从2026-01-01开始
    if not start_date:
        start_date = "20260101"
    else:
        start_date = start_date.replace("-", "")

    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")
    else:
        end_date = end_date.replace("-", "")

    try:
        df = fetch_from_akshare(symbol, start_date, end_date)
    except Exception as e:
        logger.error(f"[Kline] fetch failed for {symbol}: {e}")
        return {"inserted": 0, "updated": 0, "failed": 1}

    if not df:
        logger.warning(f"[Kline] No data for {symbol} ({start_date}~{end_date})")
        return {"inserted": 0, "updated": 0, "failed": 0}

    return batch_upsert_klines(symbol, df, symbol_name=symbol_name)


def get_klines(
    symbol: str,
    start_date: str = "",
    end_date: str = "",
    limit: int = 0,
) -> List[Dict]:
    """从数据库读取K线数据。limit>0时从最新往回数，否则按日期正序。"""
    with get_session() as db:
        q = db.query(DailyKlineDB).filter(DailyKlineDB.symbol == symbol)
        if start_date:
            q = q.filter(DailyKlineDB.trade_date >= datetime.strptime(start_date, "%Y-%m-%d").date())
        if end_date:
            q = q.filter(DailyKlineDB.trade_date <= datetime.strptime(end_date, "%Y-%m-%d").date())
        if limit > 0:
            q = q.order_by(DailyKlineDB.trade_date.desc()).limit(limit)
        else:
            q = q.order_by(DailyKlineDB.trade_date.asc())

        rows = q.all()
        return [
            {
                "id": r.id,
                "symbol": r.symbol,
                "symbol_name": r.symbol_name,
                "trade_date": str(r.trade_date),
                "open": float(r.open_price),
                "high": float(r.high_price),
                "low": float(r.low_price),
                "close": float(r.close_price),
                "prev_close": float(r.prev_close) if r.prev_close else None,
                "change_pct": float(r.change_pct) if r.change_pct else None,
                "volume": r.volume,
                "amount": float(r.amount) if r.amount else None,
                "turnover_rate": float(r.turnover_rate) if r.turnover_rate else None,
                "ma5": float(r.ma5) if r.ma5 else None,
                "ma20": float(r.ma20) if r.ma20 else None,
                "ma60": float(r.ma60) if r.ma60 else None,
                "rsi6": float(r.rsi6) if r.rsi6 else None,
                "rsi12": float(r.rsi12) if r.rsi12 else None,
                "rsi24": float(r.rsi24) if r.rsi24 else None,
                "macd_dif": float(r.macd_dif) if r.macd_dif else None,
                "macd_dea": float(r.macd_dea) if r.macd_dea else None,
                "macd_hist": float(r.macd_hist) if r.macd_hist else None,
                "boll_upper": float(r.boll_upper) if r.boll_upper else None,
                "boll_mid": float(r.boll_mid) if r.boll_mid else None,
                "boll_lower": float(r.boll_lower) if r.boll_lower else None,
            }
            for r in rows
        ]


def get_latest_date(symbol: str) -> Optional[str]:
    """获取某股票最新K线日期"""
    with get_session() as db:
        r = db.query(DailyKlineDB.trade_date).filter(
            DailyKlineDB.symbol == symbol
        ).order_by(DailyKlineDB.trade_date.desc()).first()
        return str(r[0]) if r else None


def get_all_symbols() -> List[str]:
    """获取数据库中所有有K线数据的股票"""
    with get_session() as db:
        rows = db.query(DailyKlineDB.symbol).distinct().all()
        return [r[0] for r in rows]


def count_klines(symbol: str) -> int:
    """获取某股票K线条数"""
    with get_session() as db:
        return db.query(DailyKlineDB).filter(
            DailyKlineDB.symbol == symbol
        ).count()

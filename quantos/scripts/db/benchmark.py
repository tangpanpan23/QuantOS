# -*- coding: utf-8 -*-
"""基准指数数据写入层（上证/深证/创业板/沪深300）"""
import logging
import os
from datetime import datetime, date
from typing import List, Dict, Optional

# 清除代理环境变量，避免系统透明代理拦截 AkShare 请求
for _k in list(os.environ.keys()):
    if "proxy" in _k.lower():
        del os.environ[_k]

from .db_client import get_session
from .models import BenchmarkDB

logger = logging.getLogger(__name__)

# 常用基准指数
BENCHMARK_INDICES = [
    {"code": "000001", "name": "上证指数",  "market": "SH"},
    {"code": "399001", "name": "深证成指",  "market": "SZ"},
    {"code": "399006", "name": "创业板指",  "market": "SZ"},
    {"code": "000300", "name": "沪深300",   "market": "SH"},
    {"code": "000016", "name": "上证50",    "market": "SH"},
    {"code": "000905", "name": "中证500",   "market": "SH"},
]


def upsert_index(
    index_code: str,
    index_name: str,
    trade_date: str,
    open_value: float = None,
    high_value: float = None,
    low_value: float = None,
    close_value: float = None,
    prev_close: float = None,
    change_pct: float = None,
    volume: int = None,
    amount: float = None,
    data_source: str = "akshare",
) -> BenchmarkDB:
    """插入或更新指数数据"""
    trade_date_obj = datetime.strptime(trade_date, "%Y-%m-%d").date()

    with get_session() as db:
        existing = db.query(BenchmarkDB).filter(
            BenchmarkDB.index_code == index_code,
            BenchmarkDB.trade_date == trade_date_obj,
        ).first()

        if existing:
            if close_value is not None:
                existing.close_value = close_value
            if open_value is not None:
                existing.open_value = open_value
            if high_value is not None:
                existing.high_value = high_value
            if low_value is not None:
                existing.low_value = low_value
            if prev_close is not None:
                existing.prev_close = prev_close
            if change_pct is not None:
                existing.change_pct = change_pct
            if volume is not None:
                existing.volume = volume
            if amount is not None:
                existing.amount = amount
            db.add(existing)
            return existing
        else:
            idx = BenchmarkDB(
                index_code=index_code,
                index_name=index_name,
                trade_date=trade_date_obj,
                open_value=open_value,
                high_value=high_value,
                low_value=low_value,
                close_value=close_value,
                prev_close=prev_close,
                change_pct=change_pct,
                volume=volume,
                amount=amount,
                data_source=data_source,
            )
            db.add(idx)
            return idx


def batch_upsert_indices(
    index_code: str,
    index_name: str,
    klines: List[Dict],
    data_source: str = "akshare",
) -> Dict:
    """批量写入指数K线"""
    result = {"inserted": 0, "updated": 0}
    for k in klines:
        try:
            trade_date = k.get("date") or k.get("trade_date")
            if not trade_date:
                continue
            upsert_index(
                index_code=index_code,
                index_name=index_name,
                trade_date=str(trade_date),
                open_value=float(k.get("open", 0) or 0),
                high_value=float(k.get("high", 0) or 0),
                low_value=float(k.get("low", 0) or 0),
                close_value=float(k.get("close", 0) or 0),
                prev_close=float(k.get("prev_close", 0) or 0),
                change_pct=float(k.get("change_pct", 0) or 0),
                data_source=data_source,
            )
            result["inserted"] += 1
        except Exception as e:
            logger.warning(f"[Benchmark] Failed {index_code} {k.get('date')}: {e}")
            result["updated"] += 1
    return result


def get_index_klines(
    index_code: str,
    start_date: str = "",
    end_date: str = "",
    limit: int = 0,
) -> List[Dict]:
    """读取指数K线"""
    with get_session() as db:
        q = db.query(BenchmarkDB).filter(BenchmarkDB.index_code == index_code)
        if start_date:
            q = q.filter(BenchmarkDB.trade_date >= datetime.strptime(start_date, "%Y-%m-%d").date())
        if end_date:
            q = q.filter(BenchmarkDB.trade_date <= datetime.strptime(end_date, "%Y-%m-%d").date())
        if limit > 0:
            q = q.order_by(BenchmarkDB.trade_date.desc()).limit(limit)
        else:
            q = q.order_by(BenchmarkDB.trade_date.asc())

        return [
            {
                "index_code": r.index_code,
                "index_name": r.index_name,
                "trade_date": str(r.trade_date),
                "close": float(r.close_value) if r.close_value else None,
                "change_pct": float(r.change_pct) if r.change_pct else None,
            }
            for r in q.all()
        ]

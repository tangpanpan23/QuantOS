# -*- coding: utf-8 -*-
"""股票池管理：增删改查 + 从akshare拉全市场股票基础信息"""
import logging
import os
from datetime import datetime
from typing import List, Optional

# 清除代理环境变量，避免系统透明代理拦截 AkShare 请求
for _k in list(os.environ.keys()):
    if "proxy" in _k.lower():
        del os.environ[_k]

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError

from .db_client import get_session
from .models import StockPoolDB

logger = logging.getLogger(__name__)


# ── Tank 默认自选股池（按之前回测使用的股票）─────────
TANK_DEFAULT_POOL = [
    {"symbol": "600036", "name": "招商银行",  "market": "SH", "industry": "银行"},
    {"symbol": "600900", "name": "长江电力",  "market": "SH", "industry": "电力"},
    {"symbol": "601288", "name": "农业银行",  "market": "SH", "industry": "银行"},
    {"symbol": "601318", "name": "中国平安",  "market": "SH", "industry": "保险"},
    {"symbol": "000858", "name": "五粮液",    "market": "SZ", "industry": "白酒"},
    {"symbol": "002475", "name": "立讯精密",  "market": "SZ", "industry": "消费电子"},
    {"symbol": "300750", "name": "宁德时代",  "market": "SZ", "industry": "新能源"},
    {"symbol": "600519", "name": "贵州茅台",  "market": "SH", "industry": "白酒"},
    {"symbol": "000001", "name": "平安银行",  "market": "SZ", "industry": "银行"},
    {"symbol": "600028", "name": "中国石化",  "market": "SH", "industry": "石油化工"},
]


def _infer_market(symbol: str) -> str:
    """根据代码推断市场"""
    if symbol.startswith(("6", "9", "5", "7")):
        return "SH"
    elif symbol.startswith(("0", "1", "2", "3")):
        return "SZ"
    return "SZ"


def upsert_stock(
    symbol: str,
    name: str = "",
    market: str = "",
    industry: str = "",
    sector: str = "",
    is_watched: bool = True,
    is_paper_simulated: bool = True,
    notes: str = "",
) -> StockPoolDB:
    """
    插入或更新股票到股票池。
    - symbol 不存在 → INSERT
    - symbol 已存在 → UPDATE（保留 is_watched 状态）
    """
    if not market:
        market = _infer_market(symbol)

    with get_session() as db:
        existing = db.query(StockPoolDB).filter(
            StockPoolDB.symbol == symbol
        ).first()

        if existing:
            existing.name = name or existing.name
            existing.market = market
            existing.industry = industry or existing.industry
            existing.sector = sector or existing.sector
            existing.is_watched = 1 if is_watched else 0
            existing.is_paper_simulated = 1 if is_paper_simulated else 0
            existing.notes = notes or existing.notes
            existing.updated_at = datetime.now()
            db.add(existing)
            logger.debug(f"[StockPool] Updated: {symbol} {name}")
            return existing
        else:
            stock = StockPoolDB(
                symbol=symbol,
                name=name,
                market=market,
                industry=industry,
                sector=sector,
                status=1,
                is_watched=1 if is_watched else 0,
                is_paper_simulated=1 if is_paper_simulated else 0,
                notes=notes,
            )
            db.add(stock)
            logger.info(f"[StockPool] Added: {symbol} {name}")
            return stock


def add_tank_defaults() -> int:
    """添加 Tank 默认股票池，返回添加数量"""
    count = 0
    for s in TANK_DEFAULT_POOL:
        try:
            upsert_stock(**s, is_watched=True, is_paper_simulated=True)
            count += 1
        except Exception as e:
            logger.warning(f"[StockPool] Failed to add {s['symbol']}: {e}")
    return count


def remove_stock(symbol: str) -> bool:
    """从股票池移除（设置 is_watched=0）"""
    with get_session() as db:
        stock = db.query(StockPoolDB).filter(
            StockPoolDB.symbol == symbol
        ).first()
        if stock:
            stock.is_watched = 0
            stock.updated_at = datetime.now()
            logger.info(f"[StockPool] Removed: {symbol}")
            return True
        return False


def get_watched_symbols() -> List[str]:
    """获取所有关注的股票代码列表"""
    with get_session() as db:
        rows = db.query(StockPoolDB.symbol).filter(
            StockPoolDB.is_watched == 1,
            StockPoolDB.status == 1,
        ).all()
        return [r[0] for r in rows]


def get_stock_pool(market: str = "", industry: str = "") -> List[dict]:
    """获取股票池列表（返回字典，不返回 ORM 对象，避免 session detach 问题）"""
    with get_session() as db:
        q = db.query(StockPoolDB).filter(StockPoolDB.is_watched == 1)
        if market:
            q = q.filter(StockPoolDB.market == market)
        if industry:
            q = q.filter(StockPoolDB.industry == industry)
        rows = q.order_by(StockPoolDB.symbol).all()
        return [_to_dict(r) for r in rows]


def get_stock(symbol: str) -> Optional[dict]:
    """获取单只股票信息（返回字典）"""
    with get_session() as db:
        r = db.query(StockPoolDB).filter(StockPoolDB.symbol == symbol).first()
        return _to_dict(r) if r else None


def _to_dict(r) -> dict:
    """ORM 对象转 dict（session 外部使用）"""
    return {
        "id": r.id, "symbol": r.symbol, "name": r.name,
        "market": r.market, "industry": r.industry,
        "sector": r.sector, "status": r.status,
        "is_watched": bool(r.is_watched),
        "is_paper_simulated": bool(r.is_paper_simulated),
    } if r else {}


def sync_from_akshare(symbols: Optional[List[str]] = None) -> dict:
    """
    从 AkShare 拉取股票基础信息并同步到数据库。

    参数:
        symbols: 股票代码列表。None 时同步股票池中所有关注的股票。
    Returns:
        {"added": N, "updated": N, "failed": [symbols]}
    """
    try:
        import akshare as ak
        import pandas as pd
    except ImportError:
        return {"error": "akshare not installed", "added": 0, "updated": 0, "failed": []}

    result = {"added": 0, "updated": 0, "failed": []}

    # 如果没有指定代码，从数据库取关注的股票
    if not symbols:
        symbols = get_watched_symbols()

    # 批量拉全市场快照（一次性拉完，过滤目标）
    try:
        logger.info("[StockPool] Fetching stock info from AkShare...")
        df = ak.stock_info_a_code_name()
        # df 列名: code, name
        name_map = dict(zip(df["code"].astype(str), df["name"]))
    except Exception as e:
        logger.warning(f"[StockPool] Failed to fetch stock names: {e}")
        name_map = {}

    for symbol in symbols:
        try:
            # 尝试拉个股详情
            try:
                info = ak.stock_individual_info_em(symbol=symbol)
                info_dict = dict(zip(info["item"], info["value"]))
                industry = info_dict.get("行业", "")
                sector = info_dict.get("板块", "")
            except Exception:
                industry = ""
                sector = ""

            # 用 AkShare 的名称覆盖
            name = name_map.get(symbol, symbol)

            upsert_stock(
                symbol=symbol,
                name=name,
                industry=industry,
                sector=sector,
            )
            result["updated"] += 1
            logger.debug(f"[StockPool] Synced: {symbol} {name}")
        except Exception as e:
            result["failed"].append(symbol)
            logger.warning(f"[StockPool] Failed to sync {symbol}: {e}")

    return result


def init_tank_pool() -> dict:
    """
    初始化 Tank 股票池：
    1. 添加默认股票
    2. 同步 AkShare 基础信息
    """
    added = add_tank_defaults()
    synced = sync_from_akshare()
    return {
        "defaults_added": added,
        "synced": synced,
    }

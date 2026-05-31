# -*- coding: utf-8 -*-
"""数据库连接客户端"""
import os
import sys
import logging
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# ── 连接配置 ───────────────────────────────────────────
DB_HOST     = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT     = os.environ.get("DB_PORT", "3306")
DB_USER     = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "tangpanpan314")
DB_NAME     = os.environ.get("DB_NAME", "stock")

# SQLAlchemy 连接 URL
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?charset=utf8mb4"
)

# 全局引擎（进程内单例）
_engine = None
_SessionFactory = None


def get_engine():
    """获取 SQLAlchemy 引擎（懒加载，进程单例）"""
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,          # 连接前 ping，防断连
            pool_recycle=3600,           # 1小时回收连接
            echo=False,                  # True=打印SQL，调试用
        )
        logger.info(f"[DB] Engine created: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    return _engine


def get_session_factory():
    """获取 SessionFactory"""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
        )
    return _SessionFactory


@contextmanager
def get_session() -> Session:
    """
    获取数据库 Session 的上下文管理器。

    用法：
        with get_session() as db:
            db.query(...)
            db.commit()
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """初始化数据库（建库 + 建表）

    注意：表已通过 SQL migration 创建（000005_create_trading_tables.up.sql），
    此函数仅用于 ORM 模型与现有表的映射验证。
    """
    from .models import Base  # SQLAlchemy Base - registers all models
    engine = get_engine()
    # 只验证连接，不重建表
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("[DB] ORM models registered, connection verified")


# ── 诊断 ───────────────────────────────────────────────

def health_check() -> dict:
    """数据库健康检查"""
    try:
        with get_session() as db:
            result = db.execute(text("SELECT 1")).scalar()
            return {"ok": result == 1}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def table_stats() -> dict:
    """各表数据量统计"""
    tables = [
        "q_stock_pool", "q_daily_kline", "q_paper_account",
        "q_paper_position", "q_trade_log", "q_daily_snapshot",
        "q_evolution_log", "q_benchmark_index",
    ]
    stats = {}
    try:
        with get_session() as db:
            for t in tables:
                try:
                    r = db.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                    stats[t] = r
                except Exception:
                    stats[t] = -1   # 表不存在
    except Exception as e:
        return {"error": str(e)}
    return stats

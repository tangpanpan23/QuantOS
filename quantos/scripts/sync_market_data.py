#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时同步脚本：AkShare 免费数据 → quantos 数据库

数据内容：
  1. 股票基础信息（q_stock_basic）  — 全量初始化 + 增量更新
  2. 日线行情（q_daily_kline）      — 只同步最近交易日

使用方式：
  python sync_market_data.py --mode=all     # 初始化全量 + 日线
  python sync_market_data.py --mode=basic   # 仅同步股票基础信息
  python sync_market_data.py --mode=kline   # 仅同步最新日线
  python sync_market_data.py --mode=realtime # 仅同步实时行情（分钟级）

Crontab 示例：
  # 工作日 9:35 / 11:30 / 15:05 同步最新日线数据
  35 9 * * 1-5 cd ~/Code/QuantOS/quantos && python scripts/sync_market_data.py --mode=kline >> logs/sync_kline.log 2>&1
  30 11,15 * * 1-5 cd ~/Code/QuantOS/quantos && python scripts/sync_market_data.py --mode=kline >> logs/sync_kline.log 2>&1
  # 每周一 08:30 全量同步股票基础信息
  30 8 * * 1 cd ~/Code/QuantOS/quantos && python scripts/sync_market_data.py --mode=all >> logs/sync_all.log 2>&1
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

# ── 路径设置 ────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

# ── 日志配置 ────────────────────────────────────────────
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "sync_market.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("sync")

# ── 数据库连接（quantos）─────────────────────────────────
DB_HOST     = os.environ.get("Q_DB_HOST", "127.0.0.1")
DB_PORT     = os.environ.get("Q_DB_PORT", "3306")
DB_USER     = os.environ.get("Q_DB_USER", "root")
DB_PASSWORD = os.environ.get("Q_DB_PASSWORD", "tangpanpan314")
DB_NAME     = os.environ.get("Q_DB_NAME", "quantos")

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import QueuePool
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

# ── AkShare 依赖 ────────────────────────────────────────
try:
    import akshare as ak
    import pandas as pd
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False

# ════════════════════════════════════════════════════════
#  数据库客户端
# ════════════════════════════════════════════════════════

class QuantDB:
    """quantos 数据库写入客户端"""

    def __init__(self):
        url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        self.engine = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=3,
            max_overflow=5,
            pool_pre_ping=True,
            pool_recycle=1800,
            echo=False,
        )
        self.Session = sessionmaker(bind=self.engine)

    def execute(self, sql: str, params: dict = None):
        with self.engine.connect() as conn:
            return conn.execute(text(sql), params or {})

    def fetch_one(self, sql: str, params: dict = None) -> Optional[tuple]:
        with self.engine.connect() as conn:
            r = conn.execute(text(sql), params or {})
            row = r.fetchone()
            return tuple(row) if row else None

    def fetch_all(self, sql: str, params: dict = None) -> List[tuple]:
        with self.engine.connect() as conn:
            r = conn.execute(text(sql), params or {})
            return list(r.fetchall())

    def upsert_basic(self, row: Dict[str, Any]):
        """upsert q_stock_basic"""
        sql = text("""
            INSERT INTO q_stock_basic
              (symbol, name, market, exchange, board, industry, sector,
               list_date, total_share, float_share, status, is_st, is_suspended,
               update_date, created_at, updated_at)
            VALUES
              (:symbol, :name, :market, :exchange, :board, :industry, :sector,
               :list_date, :total_share, :float_share, :status, :is_st, :is_suspended,
               :update_date, NOW(), NOW())
            ON DUPLICATE KEY UPDATE
              name        = VALUES(name),
              industry    = VALUES(industry),
              sector      = VALUES(sector),
              status      = VALUES(status),
              update_date = NOW(),
              updated_at  = NOW()
        """)
        params = {
            "symbol":        row.get("symbol", ""),
            "name":         row.get("name", ""),
            "market":       row.get("market", "SH"),
            "exchange":     row.get("exchange", ""),
            "board":        row.get("board", ""),
            "industry":     row.get("industry", ""),
            "sector":       row.get("sector", ""),
            "list_date":    row.get("list_date", None),
            "total_share":  row.get("total_share", None),
            "float_share":  row.get("float_share", None),
            "status":       row.get("status", 1),
            "is_st":        int(row.get("is_st", False)),
            "is_suspended": int(row.get("is_suspended", False)),
            "update_date":  date.today(),
        }
        self.execute(sql, params)

    def upsert_kline(self, row: Dict[str, Any]):
        """upsert q_daily_kline（唯一索引: symbol+trade_date）"""
        sql = text("""
            INSERT INTO q_daily_kline
              (symbol, symbol_name, trade_date, open_price, high_price, low_price,
               close_price, prev_close, change_pct, volume, amount, turnover_rate,
               market, ma5, ma10, ma20, ma60, rsi6, rsi12, rsi24,
               macd_dif, macd_dea, macd_hist,
               boll_upper, boll_mid, boll_lower,
               kdj_k, kdj_d, kdj_j, atr,
               data_source, is_adj_close, created_at)
            VALUES
              (:symbol, :symbol_name, :trade_date, :open_price, :high_price, :low_price,
               :close_price, :prev_close, :change_pct, :volume, :amount, :turnover_rate,
               :market, :ma5, :ma10, :ma20, :ma60, :rsi6, :rsi12, :rsi24,
               :macd_dif, :macd_dea, :macd_hist,
               :boll_upper, :boll_mid, :boll_lower,
               :kdj_k, :kdj_d, :kdj_j, :atr,
               :data_source, 1, NOW())
            ON DUPLICATE KEY UPDATE
              close_price  = VALUES(close_price),
              high_price   = VALUES(high_price),
              low_price    = VALUES(low_price),
              volume       = VALUES(volume),
              amount       = VALUES(amount),
              change_pct   = VALUES(change_pct),
              ma5          = VALUES(ma5),
              ma10         = VALUES(ma10),
              ma20         = VALUES(ma20),
              ma60         = VALUES(ma60),
              rsi6         = VALUES(rsi6),
              rsi12        = VALUES(rsi12),
              rsi24        = VALUES(rsi24),
              macd_dif     = VALUES(macd_dif),
              macd_dea     = VALUES(macd_dea),
              macd_hist    = VALUES(macd_hist),
              boll_upper   = VALUES(boll_upper),
              boll_mid     = VALUES(boll_mid),
              boll_lower   = VALUES(boll_lower),
              kdj_k        = VALUES(kdj_k),
              kdj_d        = VALUES(kdj_d),
              kdj_j        = VALUES(kdj_j),
              atr          = VALUES(atr)
        """)
        self.execute(sql, row)

    def get_existing_symbols(self) -> set:
        """获取 quantos 中已有的股票代码"""
        rows = self.fetch_all("SELECT symbol FROM q_stock_basic")
        return {r[0] for r in rows}

    def get_latest_kline_date(self, symbol: str) -> Optional[date]:
        """获取某股票最新 K 线日期"""
        row = self.fetch_one(
            "SELECT MAX(trade_date) FROM q_daily_kline WHERE symbol = %s",
            (symbol,)
        )
        return row[0] if row else None

    def get_pool_symbols(self) -> List[tuple]:
        """从 stock.q_stock_pool 获取所有股票代码"""
        url = "mysql+pymysql://root:tangpanpan314@127.0.0.1:3306/stock?charset=utf8mb4"
        eng = create_engine(url, pool_pre_ping=True)
        with eng.connect() as conn:
            r = conn.execute(text("SELECT symbol, name, market FROM q_stock_pool WHERE status=1"))
            return [(str(row[0]), str(row[1]), str(row[2])) for row in r]

    def migrate_kline_from_stock(self) -> int:
        """一次性迁移：stock.q_daily_kline → quantos.q_daily_kline"""
        sql = text("""
            INSERT IGNORE INTO q_daily_kline
              (symbol, symbol_name, trade_date, open_price, high_price, low_price, close_price,
               prev_close, change_pct, volume, amount, turnover_rate, market,
               ma5, ma10, ma20, ma60,
               rsi6, rsi12, rsi24,
               macd_dif, macd_dea, macd_hist,
               boll_upper, boll_mid, boll_lower,
               kdj_k, kdj_d, kdj_j, atr,
               data_source, is_adj_close, created_at)
            SELECT
              symbol, symbol_name, trade_date, open_price, high_price, low_price, close_price,
              prev_close, change_pct, volume, amount, turnover_rate, market,
              ma5, ma10, ma20, ma60,
              rsi6, rsi12, rsi24,
              macd_dif, macd_dea, macd_hist,
              boll_upper, boll_mid, boll_lower,
              kdj_k, kdj_d, kdj_j, atr,
              data_source, is_adj_close, NOW()
            FROM stock.q_daily_kline AS s
            WHERE NOT EXISTS (
              SELECT 1 FROM q_daily_kline AS q
              WHERE q.symbol = s.symbol AND q.trade_date = s.trade_date
            )
        """)
        self.execute(sql)
        row = self.fetch_one("SELECT COUNT(*) FROM q_daily_kline")
        return row[0] if row else 0

    def table_stats(self) -> Dict[str, int]:
        stats = {}
        for tbl in ["q_stock_basic", "q_daily_kline", "q_market_data"]:
            row = self.fetch_one(f"SELECT COUNT(*) FROM {tbl}")
            stats[tbl] = row[0] if row else 0
        return stats


# ════════════════════════════════════════════════════════
#  数据同步
# ════════════════════════════════════════════════════════

def _market_code(symbol: str) -> str:
    """根据代码判断市场：SH/SZ/BJ"""
    s = symbol.strip()
    if s.startswith(("6", "5", "9", "11")):
        return "SH"
    elif s.startswith(("0", "1", "2", "3")):
        return "SZ"
    elif s.startswith("4") or s.startswith("8"):
        return "BJ"
    return "SH"


def sync_stock_basic(db: QuantDB, batch_size: int = 200) -> int:
    """同步股票基础信息（全量）"""
    if not HAS_AKSHARE:
        logger.error("akshare 未安装，跳过基础信息同步")
        return 0

    logger.info("═" * 50)
    logger.info("开始同步股票基础信息（AkShare 全量）")

    df = None
    # AkShare 东方财富接口不稳定，尝试多次
    for attempt in range(3):
        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://www.eastmoney.com/",
            }
            resp = requests.get(
                "https://80.push2.eastmoney.com/api/qt/clist/get",
                params={
                    "pn": 1, "pz": 5000,
                    "po": 1, "np": 1,
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                    "fltt": 2, "invt": 2,
                    "fid": "f3",
                    "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
                    "fields": "f12,f14,f13,f3,f4,f8,f20,f9,f21,f62,f128,f136,f115,f152",
                    "_": int(time.time() * 1000),
                },
                headers=headers,
                timeout=30,
            )
            data = resp.json()
            rows = data.get("data", {}).get("diff", [])
            df = pd.DataFrame(rows)
            df.columns = ["symbol", "name", "_", "change_pct", "_2", "_3", "total_share",
                           "_4", "_5", "_6", "_7", "_8", "_9", "_10"]
            df = df[["symbol", "name", "change_pct", "total_share"]]
            logger.info(f"  东方财富直连抓取成功：{len(df)} 只股票")
            break
        except Exception as e1:
            logger.warning(f"  直连尝试 {attempt+1} 失败: {e1}")
            try:
                time.sleep(3)
                df = ak.stock_zh_a_spot_em()
                logger.info(f"  AkShare 备援抓取成功：{len(df)} 只股票")
                break
            except Exception as e2:
                logger.warning(f"  AkShare 备援尝试 {attempt+1} 失败: {e2}")
                time.sleep(5)

    if df is None or df.empty:
        logger.error("  ✗ 所有数据源均失败，跳过基础信息同步")
        return 0

    rename = {"代码": "symbol", "名称": "name", "板块": "board", "行业": "industry", "市值": "total_share"}
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    count = 0
    errors = 0
    for _, row in df.iterrows():
        sym = str(row.get("symbol", "")).strip()
        if not sym or len(sym) != 6:
            continue
        try:
            data = {
                "symbol":      sym,
                "name":        str(row.get("name", "")),
                "market":      _market_code(sym),
                "exchange":    "",
                "board":       str(row.get("board", "")),
                "industry":    str(row.get("industry", "")),
                "sector":      "",
                "list_date":   None,
                "total_share": _to_float(row.get("total_share")),
                "float_share": None,
                "status":      1,
                "is_st":       1 if "ST" in str(row.get("name", "")) else 0,
                "is_suspended": 0,
                "update_date": date.today(),
            }
            db.upsert_basic(data)
            count += 1
            if count % batch_size == 0:
                logger.info(f"  已写入 {count} 条 ...")
        except Exception as e:
            errors += 1
            if errors <= 5:
                logger.warning(f"  写入 {sym} 失败: {e}")

    logger.info(f"  ✓ 基础信息同步完成：{count} 条成功，{errors} 条失败")
    return count


def sync_daily_kline(db: QuantDB, symbols: List[tuple] = None, lookback: int = 2) -> int:
    """同步日线 K 线（近 N 个交易日，A股全市场）"""
    if not HAS_AKSHARE:
        logger.warning("akshare 未安装，K线同步跳过（网络不通东方财富时需先确保能访问）")
        # 如果有 stock 库，直接用 MySQL 迁移（一次性）
        try:
            logger.info("  尝试从 stock 库迁移 K 线到 quantos ...")
            migrated = db.migrate_kline_from_stock()
            if migrated > 0:
                logger.info(f"  ✓ 从 stock 库迁移了 {migrated} 条 K 线")
                return migrated
        except Exception as e:
            logger.warning(f"  stock 库迁移失败: {e}")
        return 0

    logger.info("═" * 50)
    logger.info(f"开始同步日线 K 线（回溯 {lookback} 个交易日）")

    # 获取股票列表
    if symbols is None:
        try:
            symbols = db.get_pool_symbols()
            logger.info(f"  从 stock.q_stock_pool 获取 {len(symbols)} 只股票")
        except Exception:
            # 如果 stock 库不可用，直接从 akshare 拉全市场
            logger.info("  从 AkShare 全市场拉取 ...")
            df = ak.stock_zh_a_spot_em()
            symbols = [
                (str(row["代码"]), str(row["名称"]), _market_code(str(row["代码"])))
                for _, row in df.iterrows() if len(str(row["代码"])) == 6
            ]
            logger.info(f"  共 {len(symbols)} 只")

    today = date.today()
    start_date = (today - timedelta(days=lookback * 7)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")

    total_ok = 0
    total_err = 0
    skipped = 0
    done = 0

    for sym, name, market in symbols:
        try:
            df = ak.stock_zh_a_hist(
                symbol=sym,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )
            if df is None or df.empty:
                skipped += 1
                continue

            # 列名标准化
            df = df.rename(columns={
                "日期": "date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "volume",
                "成交额": "amount", "涨跌幅": "change_pct", "涨跌额": "change",
                "换手率": "turnover",
            })

            for _, r in df.iterrows():
                row = {
                    "symbol":      sym,
                    "symbol_name": name,
                    "trade_date":  r["date"],
                    "open_price":  _to_float(r.get("open")),
                    "high_price":  _to_float(r.get("high")),
                    "low_price":   _to_float(r.get("low")),
                    "close_price": _to_float(r.get("close")),
                    "prev_close":  None,
                    "change_pct":  _to_float(r.get("change_pct")),
                    "volume":      int(_to_float(r.get("volume")) or 0),
                    "amount":      _to_float(r.get("amount")),
                    "turnover_rate": _to_float(r.get("turnover")),
                    "market":      market,
                    "ma5": None, "ma10": None, "ma20": None, "ma60": None,
                    "rsi6": None, "rsi12": None, "rsi24": None,
                    "macd_dif": None, "macd_dea": None, "macd_hist": None,
                    "boll_upper": None, "boll_mid": None, "boll_lower": None,
                    "kdj_k": None, "kdj_d": None, "kdj_j": None, "atr": None,
                    "data_source": "akshare",
                }
                db.upsert_kline(row)
                total_ok += 1

            done += 1
            if done % 100 == 0:
                logger.info(f"  已处理 {done}/{len(symbols)} 只，成功写入 {total_ok} 条")

        except Exception as e:
            total_err += 1
            if total_err <= 5:
                logger.warning(f"  {sym} K线失败: {e}")

    logger.info(f"  ✓ K线同步完成：{done} 只股票，{total_ok} 条写入，{total_err} 只失败，{skipped} 只无数据")
    return total_ok


def sync_realtime(db: QuantDB) -> int:
    """同步实时行情到 q_market_data"""
    if not HAS_AKSHARE:
        return 0

    logger.info("═" * 50)
    logger.info("开始同步实时行情")

    try:
        df = ak.stock_zh_a_spot_em()
        count = 0
        for _, r in df.iterrows():
            sym = str(r.get("代码", "")).strip()
            if len(sym) != 6:
                continue
            try:
                sql = text("""
                    INSERT INTO q_market_data
                      (symbol, symbol_name, open_price, high_price, low_price, close_price,
                       volume, amount, trade_date, market, data_source, created_at, updated_at)
                    VALUES
                      (:symbol, :symbol_name, :open_price, :high_price, :low_price, :close_price,
                       :volume, :amount, :trade_date, :market, 1, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                      close_price  = VALUES(close_price),
                      high_price   = VALUES(high_price),
                      low_price    = VALUES(low_price),
                      volume       = VALUES(volume),
                      amount       = VALUES(amount),
                      updated_at   = NOW()
                """)
                db.execute(sql, {
                    "symbol":      sym,
                    "symbol_name": str(r.get("名称", "")),
                    "open_price":  _to_float(r.get("今开")),
                    "high_price":  _to_float(r.get("最高")),
                    "low_price":   _to_float(r.get("最低")),
                    "close_price": _to_float(r.get("最新价")),
                    "volume":      int(_to_float(r.get("成交量")) or 0),
                    "amount":      _to_float(r.get("成交额")),
                    "trade_date":  date.today(),
                    "market":      _market_code(sym),
                })
                count += 1
            except Exception:
                pass
        logger.info(f"  ✓ 实时行情写入 {count} 条")
        return count
    except Exception as e:
        logger.error(f"  ✗ 实时行情同步失败: {e}")
        return 0


def _to_float(val) -> Optional[float]:
    """安全转 float"""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


# ════════════════════════════════════════════════════════
#  主入口
# ════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="quantos 数据同步")
    parser.add_argument("--mode", choices=["all", "basic", "kline", "realtime"],
                        default="all", help="同步模式")
    parser.add_argument("--batch-size", type=int, default=200, help="每批提交数")
    parser.add_argument("--lookback", type=int, default=5, help="K线回溯天数")
    args = parser.parse_args()

    t0 = time.time()
    logger.info("=" * 60)
    logger.info(f"quantos 数据同步启动 | 模式={args.mode} | 时间={datetime.now()}")
    logger.info("=" * 60)

    if not HAS_SQLALCHEMY:
        logger.error("缺少 sqlalchemy，请: pip install sqlalchemy pymysql")
        sys.exit(1)

    db = QuantDB()
    stats_before = db.table_stats()
    logger.info(f"同步前: {stats_before}")

    total_written = 0

    if args.mode in ("all", "basic"):
        n = sync_stock_basic(db, batch_size=args.batch_size)
        total_written += n

    if args.mode in ("all", "kline"):
        n = sync_daily_kline(db, lookback=args.lookback)
        total_written += n

    if args.mode == "realtime":
        n = sync_realtime(db)
        total_written += n

    stats_after = db.table_stats()
    elapsed = time.time() - t0

    logger.info("=" * 60)
    logger.info(f"同步完成！耗时 {elapsed:.1f}s，合计写入 {total_written} 条")
    logger.info(f"同步后: {stats_after}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantOS 每日定时同步脚本
每天 3 次市场数据 + 收盘后模拟盘快照
"""
import os, sys, time, logging, argparse
from datetime import datetime, date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "daily_sync.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("sync")

# ---- 数据库 ----
import pymysql, requests, json

DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "root"
DB_PASS = "tangpanpan314"
DB_NAME = "quantos"

def get_conn():
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER,
                           password=DB_PASS, database=DB_NAME, charset="utf8mb4")

def query(sql, args=(), fetch=True, conn=None):
    c = conn or get_conn()
    try:
        with c.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall() if fetch else cur.rowcount
    finally:
        if not conn: c.close()

# ---- 数据源（使用 stock_fetcher 多源冗余模块）----
import sys
sys.path.insert(0, str(BASE_DIR))
from stock_fetcher import get_router

def fetch_realtime_multi(symbols):
    """使用 stock_fetcher 多源冗余获取实时行情"""
    try:
        router = get_router()
        result = {}
        for sym in symbols:
            res = router.fetch_realtime(sym)
            if res and res.data:
                d = res.data
                result[sym] = {
                    "close": d.get("close", 0),
                    "pct": d.get("change_pct", 0),
                    "high": d.get("high", 0),
                    "low": d.get("low", 0),
                    "open": d.get("open", 0),
                    "vol": d.get("volume", 0),
                    "amount": d.get("amount", 0),
                }
        return result
    except Exception as e:
        log.warning(f"stock_fetcher 多源获取失败: {e}")
        return {}

def fetch_all_a_stock():
    """使用 Sina 批量接口获取所有 A 股实时行情（分批限流）"""
    import requests as _req2
    try:
        # 先从数据库拿关注列表的股票 symbol
        conn = get_conn()
        rows = query("""SELECT DISTINCT symbol FROM q_stock_pool WHERE is_watched=1
                         UNION
                         SELECT symbol FROM q_paper_position WHERE account_id=1
                         UNION
                         SELECT symbol FROM q_positions WHERE portfolio_id=1
                         LIMIT 500""", conn=conn)
        conn.close()
        if not rows:
            # 没有持仓就跳过全量
            log.info("无持仓/关注股票，跳过全量行情同步")
            return {}
        all_syms = list(set([str(r[0]) for r in rows]))
        result = {}
        batch_size = 50
        for i in range(0, len(all_syms), batch_size):
            batch = all_syms[i:i+batch_size]
            sina_codes = ",".join([("sh"+s if s.startswith("6") else "sz"+s) for s in batch])
            try:
                r = _req2.get(f"https://hq.sinajs.cn/list={sina_codes}",
                    headers={"Referer": "https://finance.sina.com.cn/", "User-Agent": "Mozilla/5.0"},
                    timeout=10)
                r.encoding = "gbk"
                for line in r.text.strip().split("\n"):
                    if '=""' in line: continue
                    parts = line.split('="')
                    if len(parts) < 2: continue
                    sym_match = re.search(r'hq_str_[a-z]+(\d+)', parts[0])
                    if not sym_match: continue
                    sym = sym_match.group(1)
                    data = parts[1].rstrip('";\r\n ')
                    if not data: continue
                    fields = data.split(",")
                    if len(fields) < 10: continue
                    try:
                        close = float(fields[3])
                        prev = float(fields[2])
                        pct = (close - prev) / prev * 100 if prev > 0 else 0
                        result[sym] = {
                            "close": close, "pct": pct,
                            "high": float(fields[4]) if fields[4] else close,
                            "low": float(fields[5]) if fields[5] else close,
                            "open": float(fields[1]) if fields[1] else close,
                            "vol": float(fields[8]) if fields[8] else 0,
                            "amount": float(fields[9]) if fields[9] else 0,
                        }
                    except (ValueError, IndexError): continue
            except Exception as e:
                log.warning(f"Sina 第{i//batch_size+1}批获取失败: {e}")
            time.sleep(0.3)  # 限流
        return result
    except Exception as e:
        log.warning(f"全市场行情获取失败: {e}")
        return {}

import re
requests_locked = None  # lazy import

def sync_realtime_quotes():
    """同步实时行情 → q_market_data（批量全市场）"""
    log.info(">>> 同步实时行情...")
    quotes = fetch_all_a_stock()
    if not quotes:
        log.warning("行情数据为空，跳过")
        return

    conn = get_conn()
    updated = 0
    today = date.today().strftime("%Y-%m-%d")
    try:
        for sym, q in quotes.items():
            if q["close"] <= 0:
                continue
            try:
                query("""INSERT INTO q_market_data
                    (symbol, trade_date, open_price, high_price, low_price, close_price, volume, amount, change_pct)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                    open_price=VALUES(open_price), high_price=VALUES(high_price),
                    low_price=VALUES(low_price), close_price=VALUES(close_price),
                    volume=VALUES(volume), amount=VALUES(amount), change_pct=VALUES(change_pct)""",
                    (sym, today, q["open"], q["high"], q["low"], q["close"], q["vol"], q["amount"], q["pct"]),
                    fetch=False, conn=conn)
                updated += 1
            except Exception:
                pass
        conn.commit()
        log.info(f"实时行情更新 {updated} 条")
    finally:
        conn.close()

# ---- 模拟盘快照 ----
def take_paper_snapshot():
    """收盘后记录模拟盘每日快照"""
    log.info(">>> 生成模拟盘每日快照...")
    conn = get_conn()
    try:
        today = date.today().strftime("%Y-%m-%d")

        # 账户信息
        row = query("SELECT initial_capital, total_pnl, total_value FROM q_paper_account WHERE id=1", conn=conn)
        if not row:
            log.warning("模拟账户不存在")
            return
        init_cap = float(row[0][0])
        total_pnl = float(row[0][1])
        total_val = float(row[0][2])

        row2 = query("SELECT COALESCE(SUM(shares*avg_cost),0) FROM q_paper_position WHERE account_id=1", conn=conn)
        pos_val = float(row2[0][0]) if row2 else 0.0

        cash = total_val - pos_val
        prev_row = query("""SELECT total_value FROM q_daily_snapshot
            WHERE account_id=1 ORDER BY snapshot_date DESC LIMIT 1""", conn=conn)
        prev_val = float(prev_row[0][0]) if prev_row else init_cap

        daily_pnl = total_val - prev_val
        daily_pnl_pct = (daily_pnl / prev_val * 100) if prev_val > 0 else 0
        return_pct = (total_val - init_cap) / init_cap * 100 if init_cap > 0 else 0

        query("""INSERT INTO q_daily_snapshot
            (account_id, snapshot_date, total_value, cash, positions_value,
             daily_pnl, daily_pnl_pct, return_pct, created_at)
            VALUES (1, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
            total_value=VALUES(total_value), cash=VALUES(cash),
            positions_value=VALUES(positions_value), daily_pnl=VALUES(daily_pnl),
            daily_pnl_pct=VALUES(daily_pnl_pct), return_pct=VALUES(return_pct)""",
            (today, total_val, cash, pos_val, daily_pnl, daily_pnl_pct, return_pct),
            fetch=False, conn=conn)
        conn.commit()
        log.info(f"快照完成: 总资产={total_val:.2f}, 今日盈亏={daily_pnl:.2f}({daily_pnl_pct:+.2f}%)")
    finally:
        conn.close()

# ---- 指数数据 ----
def sync_index_data():
    """同步主要指数行情（新浪指数接口）"""
    log.info(">>> 同步指数数据...")
    # Sina 格式: var hq_str_sh000001="上证指数,昨收,今开,今收,最高,最低,...
    sina_codes = "sh000001,sh399001,sh399006,sh000688,sh000300,sh000016,sh000905"
    today = date.today().strftime("%Y-%m-%d")
    import requests as _req
    try:
        r = _req.get(f"https://hq.sinajs.cn/list={sina_codes}",
                     headers={"Referer": "https://finance.sina.com.cn/", "User-Agent": "Mozilla/5.0"},
                     timeout=8)
        r.encoding = "gbk"

        # 解析: var hq_str_sh000001="数据"
        # fields[0]=指数名, [1]=昨收, [2]=今开, [3]=今收, [4]=最高, [5]=最低, [8]=成交量, [9]=成交额
        quotes = {}
        for line in r.text.strip().split("\n"):
            if '=""' in line or '="";' in line:
                continue  # 跳过空数据
            parts = line.split('="')
            if len(parts) < 2:
                continue
            header = parts[0]  # var hq_str_sh000001
            data = parts[1].rstrip('";\r\n ')
            if not data:
                continue
            # 从 header 提取 symbol
            sym_match = re.search(r'hq_str_[a-z]+(\d+)', header)
            if not sym_match:
                continue
            sym = sym_match.group(1)
            fields = data.split(",")
            if len(fields) < 10:
                continue
            try:
                prev_close = float(fields[1])
                close = float(fields[3])
                pct = (close - prev_close) / prev_close * 100 if prev_close > 0 else 0
                quotes[sym] = {
                    "close": close,
                    "pct": pct,
                    "high": float(fields[4]) if fields[4] else close,
                    "low": float(fields[5]) if fields[5] else close,
                    "open": float(fields[2]) if fields[2] else close,
                    "vol": float(fields[8]) if fields[8] else 0,
                    "amount": float(fields[9]) if fields[9] else 0,
                }
            except (ValueError, IndexError):
                continue

        conn = get_conn()
        updated = 0
        try:
            for sym, q in quotes.items():
                try:
                    query("""INSERT INTO q_market_data
                        (symbol, trade_date, open_price, high_price, low_price, close_price, volume, amount, change_pct)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON DUPLICATE KEY UPDATE
                        open_price=VALUES(open_price), high_price=VALUES(high_price),
                        low_price=VALUES(low_price), close_price=VALUES(close_price),
                        volume=VALUES(volume), amount=VALUES(amount), change_pct=VALUES(change_pct)""",
                        (sym, today, q["open"], q["high"], q["low"], q["close"], q["vol"], q["amount"], q["pct"]),
                        fetch=False, conn=conn)
                    updated += 1
                except Exception as e:
                    log.warning(f"指数 {sym} 更新失败: {e}")
            conn.commit()
            log.info(f"指数更新 {updated} 条: {list(quotes.keys())}")
        finally:
            conn.close()
    except Exception as e:
        log.warning(f"指数同步失败: {e}")

# ---- 主程序 ----
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="all",
                        choices=["all","realtime","snapshot","index"])
    parser.add_argument("--lookback", type=int, default=0)
    args = parser.parse_args()

    log.info(f"=== 同步开始: {datetime.now():%Y-%m-%d %H:%M:%S} mode={args.mode} ===")

    try:
        if args.mode == "realtime":
            sync_realtime_quotes()
            sync_index_data()
        elif args.mode == "snapshot":
            take_paper_snapshot()
        elif args.mode == "index":
            sync_index_data()
        elif args.mode == "all":
            sync_index_data()
            sync_realtime_quotes()
    except Exception as e:
        log.error(f"同步异常: {e}", exc_info=True)

    log.info(f"=== 同步完成: {datetime.now():%Y-%m-%d %H:%M:%S} ===")

if __name__ == "__main__":
    main()

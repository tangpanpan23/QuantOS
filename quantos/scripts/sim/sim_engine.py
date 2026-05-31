#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantOS Simulated Trading Engine
Tank's QuantOS Project
"""

import sys
import os
import json
import time
import math
import argparse
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, List, Tuple, Any

import pymysql
import requests

# ─── Setup ───────────────────────────────────────────────────────────────────
WORKSPACE = "/Users/tank/Code/QuantOS/quantos/scripts"
sys.path.insert(0, WORKSPACE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("SimEngine")

# ─── DB Config ───────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "tangpanpan314",
    "database": "stock",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

# ─── Tank's 10 stocks ─────────────────────────────────────────────────────────
TANK_STOCKS = [
    "600519", "000858", "601318", "600900", "600028",
    "002475", "000001", "601288", "600036", "000002",
]

# ─── Commission rates ─────────────────────────────────────────────────────────
COMMISSION_BUY  = 0.0003   # 0.03%
COMMISSION_SELL = 0.0013   # 0.13% (including stamp duty)

# ─── Strategy universe ────────────────────────────────────────────────────────
STRATEGY_TYPE_LIST = [
    "trend_following", "momentum", "mean_reversion",
    "breakout", "value", "grid_trading",
]


# ═══════════════════════════════════════════════════════════════════════════════
#  Database Utilities
# ═══════════════════════════════════════════════════════════════════════════════

def get_conn():
    """Get a fresh DB connection."""
    return pymysql.connect(**DB_CONFIG)


def fetch_kline_history(conn, symbols: List[str],
                        start_date: str, end_date: str) -> Dict[str, List[Dict]]:
    """Load K-line history from q_daily_kline table."""
    placeholders = ",".join(["%s"] * len(symbols))
    sql = f"""
        SELECT symbol, trade_date,
               open_price, high_price, low_price, close_price,
               volume, amount,
               ma5, ma10, ma20, ma60,
               rsi6, rsi12, rsi24,
               macd_dif, macd_dea, macd_hist,
               kdj_k, kdj_d, kdj_j,
               boll_upper, boll_mid, boll_lower
        FROM q_daily_kline
        WHERE symbol IN ({placeholders})
          AND trade_date BETWEEN %s AND %s
        ORDER BY symbol, trade_date
    """
    with conn.cursor() as cur:
        cur.execute(sql, symbols + [start_date, end_date])
        rows = cur.fetchall()

    data = {}
    for r in rows:
        sym = r["symbol"]
        data.setdefault(sym, []).append(r)
    return data


def fetch_latest_price_eastmoney(symbol: str) -> Optional[float]:
    """Fetch real-time price from Eastmoney push2 API."""
    # Clear proxy env
    for k in list(os.environ.keys()):
        if "proxy" in k.lower():
            del os.environ[k]

    # Determine market: 1=SH, 0=SZ, 2=HK, 300=BJ
    code = symbol.lstrip("0") if symbol.startswith("0") else symbol
    if symbol.startswith("6"):
        secid = f"1.{symbol}"
    elif symbol.startswith("0") or symbol.startswith("3"):
        secid = f"0.{symbol}"
    elif symbol.startswith("4") or symbol.startswith("8"):
        secid = f"0.{symbol}"
    else:
        secid = f"0.{symbol}"

    url = (
        "https://push2.eastmoney.com/api/qt/stock/get"
        f"?secid={secid}&fields=f43,f169,f170,f171,f45,f46,f44,f168"
        "&ut=fa5fd1943c7b386f172d6893dbfba10b"
    )
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        j = resp.json()
        fields = j.get("data", {})
        # f43 = latest price (×100 for yuan)
        price = fields.get("f43")
        if price:
            return float(price) / 100.0
    except Exception as e:
        log.warning("Failed to fetch price for %s: %s", symbol, e)
    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  Account Management
# ═══════════════════════════════════════════════════════════════════════════════

def load_or_create_account(conn, account_name: str,
                            initial_capital: float = 1_000_000.0,
                            strategy_id: int = 1) -> Dict:
    """Load existing account or create a new one."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM q_sim_account WHERE account_name=%s",
            (account_name,),
        )
        row = cur.fetchone()
        if row:
            return row

        cur.execute("""
            INSERT INTO q_sim_account
                (account_name, strategy_id, initial_capital, current_capital,
                 total_asset, status)
            VALUES (%s, %s, %s, %s, %s, 1)
        """, (account_name, strategy_id, initial_capital,
              initial_capital, initial_capital))
        conn.commit()
        with conn.cursor() as cur2:
            cur2.execute("SELECT * FROM q_sim_account WHERE account_name=%s", (account_name,))
            return cur2.fetchone()
        return load_or_create_account(conn, account_name)


def update_account_stats(conn, account_id: int):
    """Recalculate and persist account-level stats."""
    with conn.cursor() as cur:
        # Sum positions
        cur.execute("""
            SELECT SUM(market_value) as pos_value, SUM(total_profit) as pos_pnl
            FROM q_sim_position
            WHERE account_id=%s AND status='OPEN' AND quantity > 0
        """, (account_id,))
        pos_row = cur.fetchone()
        pos_value = float(pos_row["pos_value"] or 0)
        pos_pnl   = float(pos_row["pos_pnl"] or 0)

        # Capital
        cur.execute(
            "SELECT current_capital, frozen_capital, total_pnl, total_trades, winning_trades, initial_capital FROM q_sim_account WHERE id=%s",
            (account_id,))
        acc = cur.fetchone()
        cash = float(acc["current_capital"]) - float(acc["frozen_capital"])
        total_asset = cash + pos_value

        cur.execute("""
            UPDATE q_sim_account
            SET current_capital=%s, total_asset=%s, total_pnl=%s,
                total_pnl_pct=(%s - initial_capital) / initial_capital * 100
            WHERE id=%s
        """, (cash, total_asset, total_asset - float(acc["initial_capital"]),
              total_asset, account_id))
        conn.commit()


def update_account_after_trade(conn, account_id: int, trade_value: float,
                                 direction: str, commission: float):
    """Update capital after each trade."""
    with conn.cursor() as cur:
        if direction == "BUY":
            cur.execute(
                "UPDATE q_sim_account SET current_capital = current_capital - %s WHERE id=%s",
                (trade_value + commission, account_id),
            )
        else:  # SELL
            cur.execute(
                "UPDATE q_sim_account SET current_capital = current_capital + %s WHERE id=%s",
                (trade_value - commission, account_id),
            )
        conn.commit()


# ═══════════════════════════════════════════════════════════════════════════════
#  Position Management
# ═══════════════════════════════════════════════════════════════════════════════

def get_position(conn, account_id: int, symbol: str) -> Optional[Dict]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM q_sim_position WHERE account_id=%s AND symbol=%s AND status='OPEN'",
            (account_id, symbol),
        )
        return cur.fetchone()


def get_all_positions(conn, account_id: int) -> List[Dict]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM q_sim_position WHERE account_id=%s AND status='OPEN' AND quantity>0",
            (account_id,),
        )
        return cur.fetchall()


def update_position_on_buy(conn, account_id: int, symbol: str,
                             quantity: int, price: float, commission: float,
                             stop_loss_pct: float, take_profit_pct: float,
                             trade_date: str):
    """Add to or open a position after a BUY trade."""
    with conn.cursor() as cur:
        pos = get_position(conn, account_id, symbol)
        cost = quantity * price

        if pos is None:
            avg_cost = price
            stop_loss = round(price * (1 - stop_loss_pct / 100), 3)
            take_profit = round(price * (1 + take_profit_pct / 100), 3)
            cur.execute("""
                INSERT INTO q_sim_position
                    (account_id, symbol, quantity, avg_cost, today_cost,
                     stop_loss_price, take_profit_price, first_buy_date, last_buy_date, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'OPEN')
            """, (account_id, symbol, quantity, avg_cost, cost,
                  stop_loss, take_profit, trade_date, trade_date))
        else:
            old_qty   = int(pos["quantity"])
            old_cost  = old_qty * float(pos["avg_cost"])
            new_qty   = old_qty + quantity
            new_avg   = (old_cost + cost) / new_qty
            stop_loss = round(new_avg * (1 - stop_loss_pct / 100), 3)
            take_profit = round(new_avg * (1 + take_profit_pct / 100), 3)
            today_cost  = float(pos["today_cost"]) + cost
            cur.execute("""
                UPDATE q_sim_position
                SET quantity=%s, avg_cost=%s, today_cost=%s,
                    stop_loss_price=%s, take_profit_price=%s,
                    last_buy_date=%s
                WHERE account_id=%s AND symbol=%s AND status='OPEN'
            """, (new_qty, new_avg, today_cost,
                  stop_loss, take_profit, trade_date,
                  account_id, symbol))
        conn.commit()


def update_position_on_sell(conn, account_id: int, symbol: str,
                              quantity: int, price: float, commission: float,
                              stamp_duty: float, trade_date: str,
                              strategy_id: int, order_id: int = None,
                              reason: str = ""):
    """Reduce or close a position after a SELL trade."""
    with conn.cursor() as cur:
        pos = get_position(conn, account_id, symbol)
        if pos is None:
            return

        old_qty   = int(pos["quantity"])
        avg_cost  = float(pos["avg_cost"])
        profit    = (price - avg_cost) * quantity - commission - stamp_duty
        profit_pct = (price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0

        remaining = old_qty - quantity
        if remaining <= 0:
            # Close position
            cur.execute("""
                UPDATE q_sim_position
                SET quantity=0, status='CLOSED',
                    total_profit=total_profit+%s
                WHERE account_id=%s AND symbol=%s
            """, (profit, account_id, symbol))
            new_qty = 0
        else:
            cur.execute("""
                UPDATE q_sim_position
                SET quantity=%s, total_profit=total_profit+%s
                WHERE account_id=%s AND symbol=%s
            """, (remaining, profit, account_id, symbol))
            new_qty = remaining
        conn.commit()

        # Record trade
        cur.execute("""
            INSERT INTO q_sim_trade
                (account_id, strategy_id, order_id, symbol, direction,
                 trade_price, quantity, trade_value, commission, stamp_duty,
                 profit, profit_pct, trade_date, reason)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (account_id, strategy_id, order_id, symbol, "SELL",
              price, quantity, price * quantity, commission, stamp_duty,
              profit, profit_pct, trade_date, reason))
        trade_id = cur.lastrowid

        # Update account stats
        cur.execute(
            "UPDATE q_sim_account SET total_trades=total_trades+1, winning_trades=winning_trades+%s WHERE id=%s",
            (1 if profit > 0 else 0, account_id),
        )
        conn.commit()
        return trade_id


def sync_position_market_value(conn, account_id: int,
                                 current_prices: Dict[str, float]):
    """Update market_value and floating P&L for all open positions."""
    with conn.cursor() as cur:
        positions = get_all_positions(conn, account_id)
        for p in positions:
            sym = p["symbol"]
            if sym not in current_prices:
                continue
            price = current_prices[sym]
            qty   = int(p["quantity"])
            cost  = float(p["avg_cost"]) * qty
            mkt   = price * qty
            pnl   = mkt - cost + float(p["total_profit"] or 0)
            cur.execute("""
                UPDATE q_sim_position
                SET market_value=%s, today_profit=%s
                WHERE id=%s
            """, (mkt, pnl, p["id"]))
        conn.commit()


# ═══════════════════════════════════════════════════════════════════════════════
#  Order Management
# ═══════════════════════════════════════════════════════════════════════════════

def create_order(conn, account_id: int, strategy_id: int, signal_id: int,
                 symbol: str, direction: str, order_type: str,
                 order_price: Optional[float], quantity: int) -> int:
    """Create and insert a new order, return order_id."""
    with conn.cursor() as cur:
        order_value = (order_price or 0) * quantity
        cur.execute("""
            INSERT INTO q_sim_order
                (account_id, strategy_id, signal_id, symbol, direction,
                 order_type, order_price, quantity, order_value, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'SUBMITTED')
        """, (account_id, strategy_id, signal_id, symbol, direction,
              order_type, order_price, quantity, order_value))
        conn.commit()
        return cur.lastrowid


def fill_market_order(conn, order_id: int, fill_price: float,
                        fill_qty: int, trade_date: str):
    """Mark an order as filled."""
    with conn.cursor() as cur:
        commission = fill_price * fill_qty * (COMMISSION_BUY if True else COMMISSION_SELL)
        cur.execute("""
            UPDATE q_sim_order
            SET status='FILLED', filled_qty=%s, avg_fill_price=%s,
                filled_value=%s, commission=%s, filled_at=NOW()
            WHERE id=%s
        """, (fill_qty, fill_price, fill_price * fill_qty, commission, order_id))
        conn.commit()


# ═══════════════════════════════════════════════════════════════════════════════
#  Trade Execution
# ═══════════════════════════════════════════════════════════════════════════════

def execute_buy(conn, account_id: int, strategy_id: int, signal_id: int,
                symbol: str, price: float, quantity: int,
                stop_loss_pct: float, take_profit_pct: float,
                order_type: str = "MARKET", trade_date: str = None) -> Dict:
    """Execute a BUY: create order, fill, update position + capital."""
    trade_date = trade_date or datetime.now().strftime("%Y-%m-%d")
    commission = round(price * quantity * COMMISSION_BUY, 2)
    total_cost = price * quantity + commission

    with conn.cursor() as cur:
        cur.execute(
            "SELECT current_capital FROM q_sim_account WHERE id=%s",
            (account_id,))
        cash = float(cur.fetchone()["current_capital"])

    if total_cost > cash:
        log.warning("[%s] Insufficient capital for BUY %s: need %.2f, have %.2f",
                    symbol, symbol, total_cost, cash)
        return {"success": False, "reason": "insufficient_capital"}

    order_id = create_order(conn, account_id, strategy_id, signal_id,
                            symbol, "BUY", order_type, price, quantity)

    fill_market_order(conn, order_id, price, quantity, trade_date)

    update_position_on_buy(conn, account_id, symbol, quantity, price,
                             commission, stop_loss_pct, take_profit_pct, trade_date)
    update_account_after_trade(conn, account_id, price * quantity,
                                  "BUY", commission)

    log.info("[BUY]  %s @ %.3f x %d = %.2f  (commission %.2f)",
             symbol, price, quantity, price * quantity, commission)

    return {"success": True, "order_id": order_id,
            "price": price, "quantity": quantity,
            "commission": commission}


def execute_sell(conn, account_id: int, strategy_id: int,
                 symbol: str, price: float, quantity: int,
                 order_type: str = "MARKET", reason: str = "",
                 trade_date: str = None) -> Dict:
    """Execute a SELL: create order, fill, update position + capital."""
    trade_date = trade_date or datetime.now().strftime("%Y-%m-%d")
    commission = round(price * quantity * (COMMISSION_SELL - 0.001), 2)  # ~0.13% incl stamp
    stamp_duty = round(price * quantity * 0.001, 2)
    total_cost = price * quantity - commission - stamp_duty

    order_id = create_order(conn, account_id, strategy_id, 0,
                            symbol, "SELL", order_type, price, quantity)

    fill_market_order(conn, order_id, price, quantity, trade_date)

    trade_id = update_position_on_sell(
        conn, account_id, symbol, quantity, price,
        commission, stamp_duty, trade_date, strategy_id, order_id, reason)

    update_account_after_trade(conn, account_id, price * quantity,
                                  "SELL", commission + stamp_duty)

    log.info("[SELL] %s @ %.3f x %d = %.2f  (commission %.2f + stamp %.2f) reason=%s",
             symbol, price, quantity, price * quantity, commission, stamp_duty, reason)

    return {"success": True, "order_id": order_id, "trade_id": trade_id,
            "price": price, "quantity": quantity,
            "commission": commission, "stamp_duty": stamp_duty}


# ═══════════════════════════════════════════════════════════════════════════════
#  Strategy Signal Generation
# ═══════════════════════════════════════════════════════════════════════════════

def _to_float(v, default=0.0):
    if v is None:
        return default
    f = float(v)
    return f if math.isfinite(f) else default


def generate_signals_trend_following(klines: List[Dict],
                                       stop_loss_pct: float = 5.0,
                                       take_profit_pct: float = 20.0) -> List[Dict]:
    """Strategy A: MA5/MA20 crossover + RSI filter."""
    if len(klines) < 25:
        return []
    signals = []
    for i in range(1, len(klines)):
        prev = klines[i - 1]
        curr = klines[i]
        ma5_prev  = _to_float(prev.get("ma5"))
        ma5_curr  = _to_float(curr.get("ma5"))
        ma20_prev = _to_float(prev.get("ma20"))
        ma20_curr = _to_float(curr.get("ma20"))
        rsi6      = _to_float(curr.get("rsi6"), 50)
        close     = _to_float(curr.get("close_price"))

        # Golden cross: MA5 crosses above MA20
        if ma5_prev <= ma20_prev and ma5_curr > ma20_curr and rsi6 < 70:
            prev_5_vols = [_to_float(k.get("volume")) for k in klines[max(0,i-5):i]]
            avg_vol = sum(prev_5_vols) / len(prev_5_vols) if prev_5_vols else 1
            vol_ratio = _to_float(curr.get("volume")) / max(avg_vol, 1)
            confidence = min(50 + (70 - rsi6) / 2 + vol_ratio * 10, 95)
            signals.append({
                "signal_type": "BUY",
                "confidence": round(confidence, 2),
                "urgency": 7,
                "reason": f"MA5({ma5_curr:.2f}) crosses above MA20({ma20_curr:.2f}), RSI6={rsi6:.1f}",
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
            })

        # Death cross: MA5 crosses below MA20, or RSI overbought
        elif ma5_prev >= ma20_prev and ma5_curr < ma20_curr:
            signals.append({
                "signal_type": "SELL",
                "confidence": 80,
                "urgency": 9,
                "reason": f"MA5({ma5_curr:.2f}) crosses below MA20({ma20_curr:.2f})",
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
            })
        elif rsi6 > 80:
            signals.append({
                "signal_type": "SELL",
                "confidence": 85,
                "urgency": 8,
                "reason": f"RSI6={rsi6:.1f} overbought",
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
            })
    return signals


def generate_signals_momentum(klines: List[Dict],
                                stop_loss_pct: float = 5.0,
                                take_profit_pct: float = 20.0) -> List[Dict]:
    """Strategy B: RSI + MACD momentum."""
    if len(klines) < 25:
        return []
    signals = []
    for i in range(1, len(klines)):
        curr = klines[i]
        rsi6   = _to_float(curr.get("rsi6"), 50)
        dif    = _to_float(curr.get("macd_dif"))
        dea    = _to_float(curr.get("macd_dea"))
        macd_h = _to_float(curr.get("macd_hist"), dif - dea)
        prev_dif = _to_float(klines[i-1].get("macd_dif"))
        prev_dea = _to_float(klines[i-1].get("macd_dea"))
        macd_h_prev = _to_float(klines[i-1].get("macd_hist"), prev_dif - prev_dea)
        close  = _to_float(curr.get("close_price"))
        ma20   = _to_float(curr.get("ma20"))
        ma60   = _to_float(curr.get("ma60"))

        # BUY: RSI oversold + MACD histogram turning positive + price above MA20
        if rsi6 < 35 and macd_h > 0 and macd_h_prev <= 0 and close > ma20:
            confidence = min(50 + (35 - rsi6) * 2, 95)
            signals.append({
                "signal_type": "BUY",
                "confidence": round(confidence, 2),
                "urgency": 7,
                "reason": f"RSI6={rsi6:.1f} oversold, MACD histogram positive, close>{ma20:.2f}",
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
            })

        # SELL: RSI overbought + histogram negative + price below MA60
        elif rsi6 > 65 and macd_h < 0 and close < ma60:
            confidence = min(50 + (rsi6 - 65) * 2, 95)
            signals.append({
                "signal_type": "SELL",
                "confidence": round(confidence, 2),
                "urgency": 8,
                "reason": f"RSI6={rsi6:.1f} overbought, MACD histogram negative, close<{ma60:.2f}",
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
            })
    return signals


def generate_signals_bollinger_breakout(klines: List[Dict],
                                          stop_loss_pct: float = 5.0,
                                          take_profit_pct: float = 20.0) -> List[Dict]:
    """Strategy C: Bollinger Band breakout + volume confirmation."""
    if len(klines) < 25:
        return []
    signals = []
    vol_avg = sum(_to_float(k["volume"]) for k in klines[-20:]) / 20

    for i in range(1, len(klines)):
        curr = klines[i]
        close   = _to_float(curr.get("close_price"))
        open_p  = _to_float(curr.get("open_price"))
        volume  = _to_float(curr.get("volume"))
        boll_up = _to_float(curr.get("boll_upper"))
        boll_lo = _to_float(curr.get("boll_lower"))
        prev_close = _to_float(klines[i-1].get("close_price"))

        # BUY: break above upper band + volume surge + bullish candle
        if (close > boll_up > 0 and prev_close <= boll_up and
                volume > 1.5 * vol_avg and close > open_p):
            signals.append({
                "signal_type": "BUY",
                "confidence": min(50 + volume / vol_avg * 10, 95),
                "urgency": 8,
                "reason": f"Break BOLL_upper({boll_up:.2f}), vol={volume:.0f}>1.5x avg",
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
            })

        # SELL: break below lower band
        elif (close < boll_lo > 0 and prev_close >= boll_lo):
            signals.append({
                "signal_type": "SELL",
                "confidence": 80,
                "urgency": 9,
                "reason": f"Break BOLL_lower({boll_lo:.2f})",
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
            })
    return signals


def generate_signals_grid(klines: List[Dict],
                            grid_pct: float = 5.0,
                            stop_loss_pct: float = 10.0,
                            take_profit_pct: float = 20.0) -> List[Dict]:
    """Strategy D: Grid trading — buy on dips, sell on rallies from reference."""
    if len(klines) < 20:
        return []
    signals = []
    # Reference = 20-day average
    ref_price = sum(_to_float(k["close"]) for k in klines[-20:]) / 20

    for i in range(1, len(klines)):
        curr = klines[i]
        close = _to_float(curr.get("close_price"))

        # BUY when price drops grid_pct% below reference
        if close < ref_price * (1 - grid_pct / 100):
            signals.append({
                "signal_type": "BUY",
                "confidence": min(50 + (1 - close / ref_price) * 500, 90),
                "urgency": 6,
                "reason": f"Price {close:.2f} < grid({ref_price:.2f} x {1-grid_pct/100:.2f})",
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
            })
        # SELL when price rises grid_pct% above reference
        elif close > ref_price * (1 + grid_pct / 100):
            signals.append({
                "signal_type": "SELL",
                "confidence": 70,
                "urgency": 6,
                "reason": f"Price {close:.2f} > grid({ref_price:.2f} x {1+grid_pct/100:.2f})",
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
            })
    return signals


def generate_signals_value(conn, klines: List[Dict],
                              stop_loss_pct: float = 15.0,
                              take_profit_pct: float = 30.0) -> List[Dict]:
    """Strategy E: Value investing — PE/PB/ROE screening."""
    if len(klines) < 25:
        return []
    # Get industry avg PE from q_stock_pool
    signals = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT main_business, industry FROM q_stock_pool LIMIT 1")
        # We use a simplified approach: check price vs 20-day low
        low_20 = min(_to_float(k["close"]) for k in klines[-20:])
        avg_20 = sum(_to_float(k["close"]) for k in klines[-20:]) / 20

    for i in range(1, len(klines)):
        curr = klines[i]
        close = _to_float(curr.get("close_price"))
        rsi6  = _to_float(curr.get("rsi6"), 50)

        # BUY: price near 20-day low + RSI not overbought
        if close <= low_20 * 1.05 and rsi6 < 60:
            signals.append({
                "signal_type": "BUY",
                "confidence": 65,
                "urgency": 5,
                "reason": f"Price {close:.2f} near 20-day low {low_20:.2f}",
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
            })

        # SELL: price significantly above 20-day avg
        elif close > avg_20 * 1.15:
            signals.append({
                "signal_type": "SELL",
                "confidence": 70,
                "urgency": 6,
                "reason": f"Price {close:.2f} > 15% above 20-day avg {avg_20:.2f}",
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
            })
    return signals


# ─── Dispatcher ──────────────────────────────────────────────────────────────

SIGNAL_GENERATORS = {
    "trend_following": generate_signals_trend_following,
    "momentum":        generate_signals_momentum,
    "breakout":        generate_signals_bollinger_breakout,
    "grid_trading":    generate_signals_grid,
    "value":           generate_signals_value,
}


def generate_signals(conn, strategy_type: str, klines: List[Dict],
                     stop_loss_pct: float, take_profit_pct: float) -> List[Dict]:
    """Generate signals based on strategy type."""
    if strategy_type == "mean_reversion":
        # Simplified mean reversion: price < MA20*0.95 → BUY, price > MA20*1.05 → SELL
        if len(klines) < 20:
            return []
        signals = []
        for i in range(1, len(klines)):
            curr = klines[i]
            close = _to_float(curr.get("close_price"))
            ma20  = _to_float(curr.get("ma20"))
            if ma20 <= 0:
                continue
            if close < ma20 * 0.95:
                signals.append({
                    "signal_type": "BUY", "confidence": 70, "urgency": 7,
                    "reason": f"Price {close:.2f} < 95% of MA20 {ma20:.2f}",
                    "stop_loss_pct": stop_loss_pct, "take_profit_pct": take_profit_pct,
                })
            elif close > ma20 * 1.05:
                signals.append({
                    "signal_type": "SELL", "confidence": 70, "urgency": 7,
                    "reason": f"Price {close:.2f} > 105% of MA20 {ma20:.2f}",
                    "stop_loss_pct": stop_loss_pct, "take_profit_pct": take_profit_pct,
                })
        return signals

    gen = SIGNAL_GENERATORS.get(strategy_type)
    if gen is None:
        log.warning("Unknown strategy type: %s", strategy_type)
        return []
    return gen(klines, stop_loss_pct, take_profit_pct)


# ═══════════════════════════════════════════════════════════════════════════════
#  Daily PnL Snapshot
# ═══════════════════════════════════════════════════════════════════════════════

def record_daily_snapshot(conn, account_id: int, trade_date: str,
                           benchmark_closes: Dict[str, float],
                           current_prices: Dict[str, float]):
    """Calculate and write end-of-day snapshot to q_sim_daily_pnl."""
    with conn.cursor() as cur:
        # Yesterday's snapshot
        prev_date = (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        cur.execute("""
            SELECT close_capital FROM q_sim_daily_pnl
            WHERE account_id=%s ORDER BY trade_date DESC LIMIT 1
        """, (account_id,))
        prev_row = cur.fetchone()
        open_capital = float(prev_row["close_capital"]) if prev_row else None

        # Current positions
        cur.execute("""
            SELECT SUM(market_value) as pos_value, SUM(total_profit) as pos_pnl,
                   SUM(today_profit) as today_pnl
            FROM q_sim_position WHERE account_id=%s AND status='OPEN'
        """, (account_id,))
        row = cur.fetchone()
        pos_value = float(row["pos_value"] or 0)
        pos_pnl   = float(row["pos_pnl"] or 0)

        # Account capital
        cur.execute("SELECT current_capital, total_asset FROM q_sim_account WHERE id=%s", (account_id,))
        acc = cur.fetchone()
        close_capital = float(acc["current_capital"])
        total_asset   = float(acc["total_asset"])

        if open_capital is None:
            open_capital = close_capital + pos_value

        daily_pnl      = total_asset - open_capital
        daily_pnl_pct  = daily_pnl / open_capital * 100 if open_capital else 0

        # Benchmark (use last close price)
        bench_close = benchmark_closes.get("000300", None)
        bench_pnl_pct = 0.0
        alpha = daily_pnl_pct - bench_pnl_pct

        realized_pnl = pos_pnl  # simplified

        # New orders / filled
        cur.execute("""
            SELECT COUNT(*) as cnt FROM q_sim_order
            WHERE account_id=%s AND DATE(submitted_at)=%s AND status='FILLED'
        """, (account_id, trade_date))
        filled_orders = cur.fetchone()["cnt"]

        cur.execute("""
            SELECT COUNT(*) as cnt FROM q_sim_order
            WHERE account_id=%s AND DATE(submitted_at)=%s
        """, (account_id, trade_date))
        new_orders = cur.fetchone()["cnt"]

        turnover = abs(daily_pnl) / open_capital * 100 if open_capital else 0

        cur.execute("""
            INSERT INTO q_sim_daily_pnl
                (account_id, trade_date, open_capital, close_capital,
                 daily_pnl, daily_pnl_pct, position_value, position_pnl,
                 realized_pnl, bench_close, bench_pnl_pct, alpha,
                 turnover, new_orders, filled_orders)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                close_capital=VALUES(close_capital),
                daily_pnl=VALUES(daily_pnl),
                daily_pnl_pct=VALUES(daily_pnl_pct),
                position_value=VALUES(position_value),
                position_pnl=VALUES(position_pnl),
                realized_pnl=VALUES(realized_pnl),
                alpha=VALUES(alpha),
                turnover=VALUES(turnover),
                filled_orders=VALUES(filled_orders)
        """, (account_id, trade_date,
              open_capital, close_capital,
              daily_pnl, daily_pnl_pct,
              pos_value, pos_pnl, realized_pnl,
              bench_close, bench_pnl_pct, alpha,
              turnover, new_orders, filled_orders))
        conn.commit()
        return daily_pnl, daily_pnl_pct


# ═══════════════════════════════════════════════════════════════════════════════
#  Performance Metrics
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_performance_metrics(conn, account_id: int) -> Dict:
    """Calculate Sharpe, Max Drawdown, Win Rate from daily PnL snapshots."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT trade_date, daily_pnl_pct, alpha
            FROM q_sim_daily_pnl
            WHERE account_id=%s
            ORDER BY trade_date
        """, (account_id,))
        rows = cur.fetchall()

    if not rows:
        return {}

    pcts = [float(r["daily_pnl_pct"] or 0) for r in rows]

    # Sharpe ratio (annualized, assuming 252 trading days)
    mean_d = sum(pcts) / len(pcts)
    std_d  = math.sqrt(sum((x - mean_d)**2 for x in pcts) / len(pcts)) if len(pcts) > 1 else 1e-9
    sharpe = (mean_d / std_d) * math.sqrt(252) if std_d > 0 else 0

    # Max drawdown
    peak = -1e18
    max_dd = 0
    cumulative = 0.0
    for pct in pcts:
        cumulative += pct
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd

    # Win rate (new cursor)
    with conn.cursor() as cur2:
        cur2.execute(
            "SELECT total_trades, winning_trades FROM q_sim_account WHERE id=%s",
            (account_id,))
        acc = cur2.fetchone()
    total_trades = int(acc["total_trades"] or 0)
    winning_trades = int(acc["winning_trades"] or 0)
    win_rate = winning_trades / total_trades if total_trades > 0 else 0

    return {
        "total_days": len(rows),
        "sharpe_ratio": round(sharpe, 4),
        "max_drawdown": round(max_dd, 4),
        "win_rate": round(win_rate, 4),
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "mean_daily_pct": round(mean_d, 4),
        "std_daily_pct": round(std_d, 4),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Backtest Engine
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest(account_id: int, strategy_type: str,
                 symbols: List[str], start_date: str, end_date: str,
                 initial_capital: float = 1_000_000.0,
                 max_positions: int = 5,
                 verbose: bool = False) -> Dict:
    """Walk-forward backtest over historical K-line data."""
    conn = get_conn()
    log.info("=" * 60)
    log.info("BACKTEST START  strategy=%s  symbols=%d  period=%s ~ %s",
             strategy_type, len(symbols), start_date, end_date)
    log.info("=" * 60)

    # Reset account (no locking needed)
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE q_sim_account SET
                current_capital=%s, frozen_capital=0, total_asset=%s,
                total_cost=0, total_pnl=0, total_pnl_pct=0,
                bench_pnl_pct=0, total_trades=0, winning_trades=0,
                max_drawdown=0, sharpe_ratio=NULL, status=1
            WHERE id=%s
        """, (initial_capital, initial_capital, account_id))
        # Clear positions, trades, orders, daily pnl
        for table in ["q_sim_position", "q_sim_trade", "q_sim_order", "q_sim_daily_pnl"]:
            cur.execute(f"DELETE FROM {table} WHERE account_id=%s", (account_id,))
        conn.commit()

    # Load all K-line data
    kline_data = fetch_kline_history(conn, symbols, start_date, end_date)

    # Get strategy params from DB
    with conn.cursor() as cur:
        cur.execute("""
            SELECT stop_loss_pct, take_profit_pct, params_json
            FROM q_sim_strategy WHERE strategy_type=%s AND is_active=1 LIMIT 1
        """, (strategy_type,))
        row = cur.fetchone()
    if row:
        stop_loss_pct  = float(row["stop_loss_pct"] or 5.0)
        take_profit_pct = float(row["take_profit_pct"] or 20.0)
        params = json.loads(row["params_json"]) if row["params_json"] else {}
    else:
        stop_loss_pct  = 5.0
        take_profit_pct = 20.0
        params = {}

    log.info("Strategy params: stop_loss=%.2f%%, take_profit=%.2f%%",
             stop_loss_pct, take_profit_pct)

    # Collect all trading dates
    all_dates = set()
    for sym in symbols:
        for k in kline_data.get(sym, []):
            all_dates.add(str(k["trade_date"]))
    sorted_dates = sorted(all_dates)

    trade_log = []
    positions_held = {}

    for trade_date in sorted_dates:
        current_prices = {}
        daily_signals = []

        # Generate signals for each symbol (use data up to day before)
        for sym in symbols:
            klines = kline_data.get(sym, [])
            # Find today's index
            today_idx = None
            for idx, k in enumerate(klines):
                if str(k["trade_date"]) == trade_date:
                    today_idx = idx
                    break
            if today_idx is None or today_idx < 2:
                continue

            # Use prior day's data for signal generation
            history = klines[:today_idx]
            if len(history) < 2:
                continue

            sigs = generate_signals(conn, strategy_type, history,
                                     stop_loss_pct, take_profit_pct)
            if sigs:
                # Pick the last generated signal
                sig = sigs[-1]
                price_row = klines[today_idx]
                current_prices[sym] = _to_float(price_row.get("close_price"))
                daily_signals.append((sym, sig, price_row))

        # Check existing positions for stop-loss / take-profit
        pos_list = get_all_positions(conn, account_id)
        for pos in pos_list:
            sym = pos["symbol"]
            qty = int(pos["quantity"])
            avg_cost = float(pos["avg_cost"])
            stop_loss = float(pos["stop_loss_price"] or 0)
            take_profit = float(pos["take_profit_price"] or 0)
            close_price = None

            # Find today's close
            for k in kline_data.get(sym, []):
                if str(k["trade_date"]) == trade_date:
                    close_price = _to_float(k.get("close_price"))
                    break

            if close_price is None:
                continue

            reason = ""
            if stop_loss > 0 and close_price <= stop_loss:
                reason = "STOP_LOSS"
            elif take_profit > 0 and close_price >= take_profit:
                reason = "TAKE_PROFIT"

            if reason:
                execute_sell(conn, account_id, 1, sym,
                             close_price, qty, "MARKET", reason, trade_date)
                trade_log.append({
                    "date": trade_date, "symbol": sym,
                    "action": "SELL", "price": close_price,
                    "qty": qty, "reason": reason,
                })
                if verbose:
                    log.info("[BACKTEST] %s %s SELL @ %.3f x %d  (%s)",
                             trade_date, sym, close_price, qty, reason)

        # Execute new signals
        for sym, sig, kline_row in daily_signals:
            current_price = current_prices.get(sym, _to_float(kline_row.get("close_price")))
            if current_price <= 0:
                continue

            pos = get_position(conn, account_id, sym)
            pos_qty = int(pos["quantity"]) if pos else 0
            current_positions = sum(int(p["quantity"]) for p in get_all_positions(conn, account_id))

            if sig["signal_type"] == "BUY":
                if current_positions >= max_positions:
                    continue
                # Position sizing: use 20% of capital per position
                cap = initial_capital  # simplified (use initial)
                position_value = cap * 0.2
                qty = max(100, int(position_value / current_price / 100) * 100)

                result = execute_buy(conn, account_id, 1, 0,
                                     sym, current_price, qty,
                                     stop_loss_pct, take_profit_pct,
                                     "MARKET", trade_date)
                if result.get("success"):
                    trade_log.append({
                        "date": trade_date, "symbol": sym,
                        "action": "BUY", "price": current_price,
                        "qty": qty, "reason": sig.get("reason", ""),
                    })
                    if verbose:
                        log.info("[BACKTEST] %s %s BUY @ %.3f x %d  confidence=%.1f",
                                 trade_date, sym, current_price, qty,
                                 sig.get("confidence", 0))

            elif sig["signal_type"] == "SELL" and pos_qty > 0:
                qty = pos_qty
                execute_sell(conn, account_id, 1, sym,
                             current_price, qty, "MARKET",
                             sig.get("reason", ""), trade_date)
                trade_log.append({
                    "date": trade_date, "symbol": sym,
                    "action": "SELL", "price": current_price,
                    "qty": qty, "reason": sig.get("reason", ""),
                })
                if verbose:
                    log.info("[BACKTEST] %s %s SELL @ %.3f x %d",
                             trade_date, sym, current_price, qty)

        # Sync position market values for this day's close prices
        sync_position_market_value(conn, account_id, current_prices)

        # Daily snapshot
        record_daily_snapshot(conn, account_id, trade_date, {}, current_prices)

    # Final account update
    update_account_stats(conn, account_id)

    # Performance metrics
    metrics = calculate_performance_metrics(conn, account_id)

    # Final positions
    final_positions = get_all_positions(conn, account_id)

    log.info("=" * 60)
    log.info("BACKTEST COMPLETE")
    log.info("=" * 60)

    conn.close()

    return {
        "trade_log": trade_log,
        "total_trades": len(trade_log),
        "final_positions": final_positions,
        "metrics": metrics,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Live Trading Mode
# ═══════════════════════════════════════════════════════════════════════════════

def run_live(account_id: int, strategy_type: str,
             trade_date: str = None, verbose: bool = False):
    """Run live (simulated) trading for today."""
    conn = get_conn()
    trade_date = trade_date or datetime.now().strftime("%Y-%m-%d")
    log.info("LIVE MODE starting for %s  strategy=%s", trade_date, strategy_type)

    # Load today's K-line data (last available)
    symbols = TANK_STOCKS
    kline_data = fetch_kline_history(conn, symbols, trade_date, trade_date)

    # Get strategy params
    with conn.cursor() as cur:
        cur.execute("""
            SELECT stop_loss_pct, take_profit_pct FROM q_sim_strategy
            WHERE strategy_type=%s AND is_active=1 LIMIT 1
        """, (strategy_type,))
        row = cur.fetchone()
    stop_loss_pct   = float(row["stop_loss_pct"]) if row else 5.0
    take_profit_pct = float(row["take_profit_pct"]) if row else 20.0

    for sym in symbols:
        klines = kline_data.get(sym, [])
        if not klines:
            # Try to get from DB with history
            klines = fetch_kline_history(conn, [sym],
                                         (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                                         trade_date).get(sym, [])

        if len(klines) < 2:
            continue

        history = klines[:-1]
        today_k = klines[-1]
        today_close = _to_float(today_k.get("close_price"))

        sigs = generate_signals(conn, strategy_type, history,
                                 stop_loss_pct, take_profit_pct)
        if not sigs:
            continue

        sig = sigs[-1]
        price = today_close
        if price is None or price <= 0:
            price = fetch_latest_price_eastmoney(sym)
        if price is None or price <= 0:
            continue

        pos = get_position(conn, account_id, sym)
        pos_qty = int(pos["quantity"]) if pos else 0
        current_positions = sum(int(p["quantity"]) for p in get_all_positions(conn, account_id))

        if sig["signal_type"] == "BUY" and current_positions < 10:
            qty = max(100, int(20000 / price / 100) * 100)
            execute_buy(conn, account_id, 1, 0, sym, price, qty,
                        stop_loss_pct, take_profit_pct)
        elif sig["signal_type"] == "SELL" and pos_qty > 0:
            execute_sell(conn, account_id, 1, sym, price, pos_qty,
                         reason=sig.get("reason", ""))

    sync_position_market_value(conn, account_id,
                                 {sym: fetch_latest_price_eastmoney(sym) for sym in symbols})
    record_daily_snapshot(conn, account_id, trade_date, {}, {})
    update_account_stats(conn, account_id)

    log.info("LIVE MODE complete.")
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  Strategy Management
# ═══════════════════════════════════════════════════════════════════════════════

def ensure_default_strategies(conn):
    """Insert default strategies if none exist."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM q_sim_strategy")
        if cur.fetchone()["cnt"] > 0:
            return

    defaults = [
        ("趋势跟踪", "trend_following", 5.0, 20.0, {}),
        ("动量策略", "momentum", 5.0, 20.0, {}),
        ("布林带突破", "breakout", 5.0, 20.0, {}),
        ("网格交易", "grid_trading", 10.0, 20.0, {"grid_pct": 5.0}),
        ("均值回归", "mean_reversion", 5.0, 15.0, {}),
        ("价值投资", "value", 15.0, 30.0, {}),
    ]
    with conn.cursor() as cur:
        for name, stype, sl, tp, params in defaults:
            cur.execute("""
                INSERT INTO q_sim_strategy
                    (strategy_name, strategy_type, description,
                     params_json, stop_loss_pct, take_profit_pct, is_active)
                VALUES (%s,%s,%s,%s,%s,%s,1)
            """, (name, stype, f"{name}策略",
                  json.dumps(params, ensure_ascii=False), sl, tp))
        conn.commit()
    log.info("Inserted %d default strategies.", len(defaults))


# ═══════════════════════════════════════════════════════════════════════════════
#  Main CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="QuantOS Simulated Trading Engine")
    parser.add_argument("--account-id", type=int, default=1,
                        help="Account ID to use")
    parser.add_argument("--account-name", type=str, default="Tank_Default",
                        help="Account name for new accounts")
    parser.add_argument("--backtest", action="store_true",
                        help="Run backtest mode")
    parser.add_argument("--live", action="store_true",
                        help="Run live (simulated) mode")
    parser.add_argument("--start-date", type=str, default="2026-01-05",
                        help="Backtest start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default="2026-05-21",
                        help="Backtest end date (YYYY-MM-DD)")
    parser.add_argument("--trade-date", type=str, default=None,
                        help="Trade date for live mode (YYYY-MM-DD)")
    parser.add_argument("--strategy-type", type=str, default="trend_following",
                        choices=STRATEGY_TYPE_LIST,
                        help="Strategy type")
    parser.add_argument("--symbols", type=str, default=",".join(TANK_STOCKS),
                        help="Comma-separated stock codes")
    parser.add_argument("--initial-capital", type=float, default=1_000_000.0,
                        help="Initial capital for new account")
    parser.add_argument("--max-positions", type=int, default=5,
                        help="Max simultaneous positions")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    conn = get_conn()
    ensure_default_strategies(conn)

    # Get or create account
    account = load_or_create_account(conn, args.account_name,
                                      args.initial_capital)
    account_id = account["id"]
    log.info("Using account_id=%d  name=%s", account_id, args.account_name)

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    if args.backtest:
        result = run_backtest(
            account_id=account_id,
            strategy_type=args.strategy_type,
            symbols=symbols,
            start_date=args.start_date,
            end_date=args.end_date,
            initial_capital=args.initial_capital,
            max_positions=args.max_positions,
            verbose=args.verbose,
        )

        # Print summary
        print("\n" + "=" * 60)
        print("BACKTEST RESULTS")
        print("=" * 60)
        print(f"Strategy:       {args.strategy_type}")
        print(f"Period:         {args.start_date} ~ {args.end_date}")
        print(f"Symbols:        {len(symbols)}")
        m = result["metrics"]
        print(f"Total days:     {m.get('total_days', 0)}")
        print(f"Total trades:  {m.get('total_trades', 0)}")
        print(f"Winning trades: {m.get('winning_trades', 0)}")
        print(f"Win rate:       {m.get('win_rate', 0)*100:.1f}%")
        print(f"Sharpe ratio:   {m.get('sharpe_ratio', 0):.4f}")
        print(f"Max drawdown:  {m.get('max_drawdown', 0):.2f}%")
        print(f"Mean daily:    {m.get('mean_daily_pct', 0):.4f}%")
        print(f"Std daily:     {m.get('std_daily_pct', 0):.4f}%")

        positions = result["final_positions"]
        print(f"\nPositions held: {len(positions)}")
        for p in positions:
            print(f"  {p['symbol']}: qty={p['quantity']}  "
                  f"avg_cost={p['avg_cost']}  "
                  f"market_value={p['market_value']}  "
                  f"pnl={p['today_profit']}")

        # Final account state
        conn2 = get_conn()
        with conn2.cursor() as cur:
            cur.execute("SELECT * FROM q_sim_account WHERE id=%s", (account_id,))
            acc = cur.fetchone()
        conn2.close()
        print(f"\nAccount state:")
        print(f"  Initial capital: {acc['initial_capital']}")
        print(f"  Current capital: {acc['current_capital']}")
        print(f"  Total asset:     {acc['total_asset']}")
        print(f"  Total P&L:       {acc['total_pnl']} ({acc['total_pnl_pct']}%)")
        print("=" * 60)

    elif args.live:
        run_live(account_id, args.strategy_type, args.trade_date, args.verbose)

    else:
        print("Please specify --backtest or --live mode. Use --help for options.")
        parser.print_help()

    conn.close()


if __name__ == "__main__":
    main()

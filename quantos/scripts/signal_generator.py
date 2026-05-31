#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantOS 策略信号生成器
每天扫描股票池，基于6种策略生成BUY/SELL信号，写入q_sim_signal表
用法: python3 signal_generator.py [--date YYYY-MM-DD] [--strategy TYPE] [--symbols s1,s2]
"""
import sys, os, json, time, argparse, logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple
for k in list(os.environ.keys()):
    if 'proxy' in k.lower(): del os.environ[k]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymysql
import requests
import numpy as np
import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('signal_gen')

# ─── DB ───────────────────────────────────────────────────────────────────────
DB = dict(host='127.0.0.1', port=3306, user='root', password='tangpanpan314', database='stock', charset='utf8mb4')

def get_conn():
    return pymysql.connect(**DB, cursorclass=pymysql.cursors.DictCursor)

# ─── 新浪实时行情 ─────────────────────────────────────────────────────────────
def fetch_sina_realtime(symbols: List[str]) -> Dict[str, dict]:
    """获取实时行情，返回 {symbol: {price, open, high, low, close, volume, amount}}"""
    codes = ','.join(f'sh{s}' if s.startswith(('6','9')) else f'sz{s}' for s in symbols)
    url = f'https://hq.sinajs.cn/list={codes}'
    try:
        r = requests.get(url, headers={
            'Referer': 'https://finance.sina.com.cn',
            'User-Agent': 'Mozilla/5.0'
        }, timeout=10)
        r.encoding = 'gbk'
        lines = r.text.strip().split('\n')
        result = {}
        for line in lines:
            sym = line.split('=')[0].split('_')[-1].strip()
            sym = sym.replace('hq_str_', '')
            # 解析: 名称,今开,昨收,现价,最高,最低,...
            parts = line.split('"')[1].split(',')
            if len(parts) < 10:
                continue
            s = sym[2:] if sym.startswith(('sh','sz')) else sym
            result[s] = {
                'name':    parts[0],
                'open':    float(parts[1]) if parts[1]  else 0,
                'close':   float(parts[2]) if parts[2]  else 0,   # 昨收
                'price':   float(parts[3]) if parts[3]  else 0,   # 现价
                'high':    float(parts[4]) if parts[4]  else 0,
                'low':     float(parts[5]) if parts[5]  else 0,
                'volume':  float(parts[8]) if parts[8]  else 0,   # 成交量(股)
                'amount':  float(parts[9]) if parts[9]  else 0,   # 成交额(元)
                'time':    parts[30] if len(parts) > 30 else '',
            }
        return result
    except Exception as e:
        log.error(f"新浪行情获取失败: {e}")
        return {}

# ─── 获取历史K线 ──────────────────────────────────────────────────────────────
def fetch_kline_history(symbol: str, count: int = 60) -> List[dict]:
    """从DB读取最近N条K线"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT trade_date, open_price as open, high_price as high,
                       low_price as low, close_price as close, volume, amount,
                       ma5, ma10, ma20, ma60,
                       rsi6, rsi12, rsi24,
                       macd_dif, macd_dea, macd_hist as macd,
                       kdj_k, kdj_d, kdj_j,
                       boll_upper, boll_mid, boll_lower
                FROM q_daily_kline
                WHERE symbol=%s
                ORDER BY trade_date DESC
                LIMIT %s
            """, (symbol, count))
            rows = cur.fetchall()
    # 倒序
    rows = list(reversed(rows))
    for r in rows:
        r['trade_date'] = r['trade_date'].isoformat() if hasattr(r['trade_date'], 'isoformat') else str(r['trade_date'])
    return rows

# ─── 技术指标计算 ─────────────────────────────────────────────────────────────
def calc_ma(closes: List[float], period: int) -> List[Optional[float]]:
    result = []
    for i in range(len(closes)):
        if i < period - 1:
            result.append(None)
        else:
            result.append(round(sum(closes[i-period+1:i+1]) / period, 3))
    return result

def calc_rsi(closes: List[float], period: int = 6) -> List[Optional[float]]:
    if len(closes) < period + 1:
        return [None] * len(closes)
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    result = [None] * period
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(closes)):
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(round(100 - 100 / (1 + rs), 4))
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
    return result

def calc_macd(closes: List[float], fast=12, slow=26, signal=9) -> Tuple[List, List, List]:
    def ema(data, period):
        k = 2 / (period + 1)
        result = [data[0]]
        for v in data[1:]:
            result.append(v * k + result[-1] * (1 - k))
        return result
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    dif = [f - s for f, s in zip(ema_fast, ema_slow)]
    dea = ema(dif, signal)
    macd = [2 * (d - de) for d, de in zip(dif, dea)]
    return dif, dea, macd

def calc_boll(closes: List[float], period=20, std_dev=2) -> Tuple[List, List, List]:
    upper, mid, lower = [], [], []
    for i in range(len(closes)):
        if i < period - 1:
            upper.append(None); mid.append(None); lower.append(None)
        else:
            chunk = closes[i-period+1:i+1]
            m = sum(chunk) / period
            s = (sum((x - m)**2 for x in chunk) / period) ** 0.5
            mid.append(round(m, 3))
            upper.append(round(m + std_dev * s, 3))
            lower.append(round(m - std_dev * s, 3))
    return upper, mid, lower

def calc_atr(highs, lows, closes, period=14) -> List[Optional[float]]:
    if len(highs) < 2:
        return [None] * len(closes)
    trs = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i-1]),
                 abs(lows[i] - closes[i-1]))
        trs.append(tr)
    result = [None] * period
    if len(trs) >= period:
        result.append(round(sum(trs[:period]) / period, 4))
        for i in range(period, len(trs)):
            result.append(round(result[-1] * (period - 1) + trs[i]) / period, 4)
    return result

# ─── 策略信号 ─────────────────────────────────────────────────────────────────
class SignalGenerator:
    def __init__(self, strategy_type: str, params: dict):
        self.strategy_type = strategy_type
        self.params = params

    def generate(self, symbol: str, klines: List[dict], realtime: dict) -> List[dict]:
        if len(klines) < 30:
            return []
        closes = [float(k['close']) for k in klines]
        highs  = [float(k['high'])  for k in klines]
        lows   = [float(k['low'])   for k in klines]
        cur = realtime.get(symbol, {})

        if self.strategy_type == 'trend_following':
            return self._trend_following(symbol, klines, closes, highs, lows, cur)
        elif self.strategy_type == 'momentum':
            return self._momentum(symbol, klines, closes, highs, lows, cur)
        elif self.strategy_type == 'breakout':
            return self._breakout(symbol, klines, closes, highs, lows, cur)
        elif self.strategy_type == 'mean_reversion':
            return self._mean_reversion(symbol, klines, closes, highs, lows, cur)
        elif self.strategy_type == 'value':
            return self._value(symbol, klines, closes, highs, lows, cur)
        elif self.strategy_type == 'grid_trading':
            return self._grid_trading(symbol, klines, closes, highs, lows, cur)
        return []

    def _trend_following(self, symbol, klines, closes, highs, lows, cur):
        """MA金叉/死叉 + RSI确认"""
        if len(closes) < 25:
            return []
        ma5  = calc_ma(closes, 5)
        ma20 = calc_ma(closes, 20)
        rsi  = calc_rsi(closes, 6)
        price = cur.get('price', closes[-1])
        signals = []
        n = len(closes)
        if n < 3:
            return []

        ma5_prev  = ma5[-3]  if len(ma5) >= 3 and ma5[-3]  else 0
        ma20_prev = ma20[-3] if len(ma20) >= 3 and ma20[-3] else 0
        ma5_cur   = ma5[-1]  if ma5[-1]  else 0
        ma20_cur  = ma20[-1] if ma20[-1] else 0
        rsi_cur   = rsi[-1]  if rsi[-1]  else 50

        if ma5_prev > ma20_prev and ma5_cur < ma20_cur:
            signals.append({
                'signal_type': 'SELL',
                'confidence': min(95.0, round(70 + (80 - rsi_cur) * 0.5, 1)),
                'signal_reason': f'MA5({ma5_cur:.2f})死叉MA20({ma20_cur:.2f}) RSI={rsi_cur:.1f}',
                'urgency': 7
            })
        elif ma5_prev < ma20_prev and ma5_cur > ma20_cur:
            if rsi_cur < 75:
                signals.append({
                    'signal_type': 'BUY',
                    'confidence': min(95.0, round(60 + (50 - abs(50 - rsi_cur)) * 0.8, 1)),
                    'signal_reason': f'MA5({ma5_cur:.2f})金叉MA20({ma20_cur:.2f}) RSI={rsi_cur:.1f}',
                    'urgency': 6
                })
        if rsi_cur > 80:
            signals.append({'signal_type': 'SELL', 'confidence': min(95.0, float(rsi_cur)),
                           'signal_reason': f'RSI超买 RSI={rsi_cur:.1f}', 'urgency': 9})
        elif rsi_cur < 25:
            signals.append({'signal_type': 'BUY', 'confidence': min(95.0, 100 - float(rsi_cur)),
                           'signal_reason': f'RSI超卖 RSI={rsi_cur:.1f}', 'urgency': 8})
        return signals

    def _momentum(self, symbol, klines, closes, highs, lows, cur) -> List[dict]:
        """RSI + MACD 动量"""
        if len(closes) < 20:
            return []
        rsi6  = calc_rsi(closes, 6)
        rsi14 = calc_rsi(closes, 14)
        dif, dea, hist = calc_macd(closes)
        ma20  = calc_ma(closes, 20)
        price = cur.get('price', closes[-1])
        r6  = rsi6[-1]  if rsi6[-1]  else 50
        r14 = rsi14[-1] if rsi14[-1] else 50
        d   = dif[-1]   if dif[-1]   else 0
        h   = hist[-1]  if hist[-1]  else 0
        m20 = ma20[-1]  if ma20[-1]  else 0
        signals = []

        # 买入：RSI超卖 + MACD转正 + 价格在MA20上方
        if r6 < 35 and d > 0 and h > 0 and price > m20:
            signals.append({'signal_type': 'BUY', 'confidence': round(60 + (35 - r6), 1),
                           'signal_reason': f'RSI6={r6:.1f} MACD转正 价>MA20', 'urgency': 8})
        # 卖出：RSI超买 + MACD转负
        elif r6 > 70 and d < 0:
            signals.append({'signal_type': 'SELL', 'confidence': round(60 + r6 - 70, 1),
                           'signal_reason': f'RSI6={r6:.1f} MACD转负', 'urgency': 7})
        elif r14 > 75:
            signals.append({'signal_type': 'SELL', 'confidence': round(r14 - 10, 1),
                           'signal_reason': f'RSI14={r14:.1f} 超买', 'urgency': 6})
        return signals

    def _breakout(self, symbol, klines, closes, highs, lows, cur) -> List[dict]:
        """布林带突破 + 成交量确认"""
        if len(closes) < 25:
            return []
        upper, mid, lower = calc_boll(closes, 20, 2)
        ma20vol = calc_ma([float(k.get('volume', 0)) for k in klines], 20)
        dif, dea, hist = calc_macd(closes)
        u = upper[-1] if upper[-1] else 0
        l = lower[-1] if lower[-1] else 0
        p = cur.get('price', closes[-1])
        vol = cur.get('volume', 0)
        mvol = ma20vol[-1] if ma20vol[-1] else 1
        signals = []

        if u and l:
            vol_ratio = vol / mvol if mvol else 1
            prev_c = closes[-2] if len(closes) > 1 else p
            if p > u and prev_c <= (upper[-2] if len(upper) > 1 else u):
                conf = min(95.0, round(60 + vol_ratio * 20, 1))
                signals.append({'signal_type': 'BUY', 'confidence': conf,
                               'signal_reason': f'突破布林上轨({u:.2f}) 量比={vol_ratio:.1f}', 'urgency': 7})
            elif p < l and prev_c >= (lower[-2] if len(lower) > 1 else l):
                signals.append({'signal_type': 'SELL', 'confidence': 80.0,
                               'signal_reason': f'跌破布林下轨({l:.2f})', 'urgency': 8})
        return signals

    def _mean_reversion(self, symbol, klines, closes, highs, lows, cur) -> List[dict]:
        """均值回归：价格在布林带极端位置"""
        if len(closes) < 25:
            return []
        upper, mid, lower = calc_boll(closes, 20, 2)
        rsi = calc_rsi(closes, 14)
        p = cur.get('price', closes[-1])
        m = mid[-1] if mid[-1] else p
        u = upper[-1] if upper[-1] else p
        l = lower[-1] if lower[-1] else p
        r = rsi[-1] if rsi[-1] else 50
        signals = []

        if u and l and m:
            dev = (p - m) / m if m else 0
            if dev > 0.1 and r > 65:
                signals.append({'signal_type': 'SELL', 'confidence': min(90.0, round(65 + r - 65, 1)),
                               'signal_reason': f'价格偏离均值+{(dev*100):.1f}% RSI={r:.1f}', 'urgency': 6})
            elif dev < -0.1 and r < 40:
                signals.append({'signal_type': 'BUY', 'confidence': min(90.0, round(65 + (40 - r), 1)),
                               'signal_reason': f'价格偏离均值-{-dev*100:.1f}% RSI={r:.1f}', 'urgency': 7})
        return signals

    def _value(self, symbol, klines, closes, highs, lows, cur) -> List[dict]:
        """价值投资：从DB读取基本面数据"""
        if len(closes) < 25:
            return []
        with get_conn() as conn:
            with conn.cursor() as c:
                c.execute("""
                    SELECT pe_ratio, pb_ratio, roe, dividend_yield, risk_level
                    FROM q_stock_pool WHERE symbol=%s
                """, (symbol,))
                row = c.fetchone()
        if not row:
            return []
        pe = float(row['pe_ratio'] or 0)
        pb = float(row['pb_ratio'] or 0)
        roe = float(row['roe'] or 0)
        p = cur.get('price', closes[-1])
        signals = []

        ma20 = calc_ma(closes, 20)
        m20 = ma20[-1] if ma20[-1] else p
        if 5 < pe < 30 and roe > 8 and p < m20 * 1.05:
            signals.append({'signal_type': 'BUY', 'confidence': min(90.0, round(50 + roe, 1)),
                           'signal_reason': f'PE={pe:.1f} ROE={roe:.1f}% 价格接近MA20低位', 'urgency': 5})
        elif pe > 50 and roe < 5:
            signals.append({'signal_type': 'SELL', 'confidence': 75.0,
                           'signal_reason': f'PE={pe:.1f}偏高 ROE={roe:.1f}%偏低', 'urgency': 6})
        return signals

    def _grid_trading(self, symbol, klines, closes, highs, lows, cur) -> List[dict]:
        """网格交易：基于偏离度"""
        if len(closes) < 20:
            return []
        grid_pct = self.params.get('grid_pct', 3)
        base = self.params.get('base_price')
        if not base:
            base = sum(closes[-20:]) / 20  # 20日均价作为基准

        p = cur.get('price', closes[-1])
        dev = (p - base) / base if base else 0
        signals = []

        # 偏离-3%以下买入格，-6%以下加倍
        if dev < -0.06:
            signals.append({'signal_type': 'BUY', 'confidence': 85.0,
                           'signal_reason': f'价格偏离基准-{abs(dev)*100:.1f}% 接近网格买点', 'urgency': 6})
        elif dev < -0.03:
            signals.append({'signal_type': 'BUY', 'confidence': 65.0,
                           'signal_reason': f'价格偏离基准-{abs(dev)*100:.1f}%', 'urgency': 4})
        # 偏离+3%以上卖格
        elif dev > 0.06:
            signals.append({'signal_type': 'SELL', 'confidence': 85.0,
                           'signal_reason': f'价格偏离基准+{dev*100:.1f}% 接近网格卖点', 'urgency': 6})
        elif dev > 0.03:
            signals.append({'signal_type': 'SELL', 'confidence': 65.0,
                           'signal_reason': f'价格偏离基准+{dev*100:.1f}%', 'urgency': 4})
        return signals


# ─── 过滤已有信号 ─────────────────────────────────────────────────────────────
def existing_signals(symbol: str, strategy_id: int, valid_hours: int = 24) -> set:
    """返回当天已有的信号类型"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT signal_type FROM q_sim_signal
                WHERE symbol=%s AND strategy_id=%s
                  AND valid_from >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            """, (symbol, strategy_id, valid_hours))
            return {r['signal_type'] for r in cur.fetchall()}

# ─── 写入信号 ────────────────────────────────────────────────────────────────
def write_signal(conn, strategy_id: int, symbol: str, sig: dict, price: float, now: datetime):
    with conn.cursor() as cur:
        # 基础字段
        cur.execute("""
            INSERT INTO q_sim_signal
            (strategy_id, symbol, signal_type, signal_reason, signal_price,
             target_price, target_pct, confidence, quantity, urgency,
             valid_from, valid_until, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING')
        """, (
            strategy_id, symbol, sig['signal_type'],
            sig.get('signal_reason', ''),
            price,
            round(price * 1.05, 2) if sig['signal_type'] == 'BUY' else round(price * 0.95, 2),
            5.0 if sig['signal_type'] == 'BUY' else -5.0,
            sig.get('confidence'),
            sig.get('quantity'),
            sig.get('urgency', 5),
            now, now + timedelta(hours=24),
        ))

# ─── 主程序 ─────────────────────────────────────────────────────────────────
def run(date_str: Optional[str] = None, strategy_type: Optional[str] = None,
        symbols: Optional[List[str]] = None, verbose: bool = False):
    now = datetime.now()
    log.info("=" * 60)
    log.info("策略信号生成 · %s · %s", now.strftime('%Y-%m-%d %H:%M'), strategy_type or '全部策略')
    log.info("=" * 60)

    # 加载策略
    with get_conn() as conn:
        with conn.cursor() as cur:
            if strategy_type:
                cur.execute("SELECT * FROM q_sim_strategy WHERE strategy_type=%s AND is_active=1", (strategy_type,))
            else:
                cur.execute("SELECT * FROM q_sim_strategy WHERE is_active=1")
            strategies = cur.fetchall()

            # 加载股票池
            if symbols:
                placeholders = ','.join(['%s'] * len(symbols))
                cur.execute(f"SELECT symbol FROM q_stock_pool WHERE symbol IN ({placeholders})", symbols)
            else:
                # 默认：Tank自选股
                default_pool = ['600519','000858','601318','600900','600028','002475','000001','601288','600036','000002']
                placeholders = ','.join(['%s'] * len(default_pool))
                cur.execute(f"SELECT symbol FROM q_stock_pool WHERE symbol IN ({placeholders})", default_pool)
            pool = [r['symbol'] for r in cur.fetchall()]

    if not strategies:
        log.warning("没有找到活跃策略")
        return
    if not pool:
        log.warning("股票池为空")
        return

    # 获取实时行情
    log.info("获取实时行情: %s 只", len(pool))
    realtime = fetch_sina_realtime(pool)
    log.info("行情获取: %d 只", len(realtime))

    total_signals = 0
    with get_conn() as conn:
        try:
            for strat in strategies:
                sid = strat['id']
                stype = strat['strategy_type']
                # 分离参数JSON和数组JSON
                params = json.loads(strat.get('params_json') or '{}')
                universe_raw = strat.get('universe_json') or '[]'
                try:
                    universe = json.loads(universe_raw)
                    if isinstance(universe, list):
                        params['_symbols'] = universe
                except (json.JSONDecodeError, TypeError):
                    pass

                generator = SignalGenerator(stype, params)

                for sym in tqdm.tqdm(pool, desc=f"[{stype[:12]}]", leave=False):
                    klines = fetch_kline_history(sym, 80)
                    cur_price = realtime.get(sym, {}).get('price', 0)
                    if not cur_price:
                        continue

                    # 过滤近期已发信号
                    existing = existing_signals(sym, sid)
                    sigs = generator.generate(sym, klines, realtime.get(sym, {}))

                    for sig in sigs:
                        if sig['signal_type'] in existing:
                            continue
                        write_signal(conn, sid, sym, sig, cur_price, now)
                        existing.add(sig['signal_type'])
                        log.info("  [%s] %s %s @ %.2f conf=%.1f %s",
                                 stype[:12], sym, sig['signal_type'], cur_price,
                                 sig.get('confidence', 0), sig.get('signal_reason', ''))
                        total_signals += 1
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    log.info("=" * 60)
    log.info("信号生成完成: %d 个信号", total_signals)
    log.info("=" * 60)

    # 显示结果
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.signal_type, s.symbol, sp.strategy_name, s.confidence,
                       s.signal_reason, s.signal_price, s.created_at
                FROM q_sim_signal s
                JOIN q_sim_strategy sp ON sp.id=s.strategy_id
                WHERE s.status='PENDING'
                ORDER BY s.confidence DESC, s.created_at DESC
                LIMIT 20
            """)
            rows = cur.fetchall()
            if rows:
                print("\n📊 TOP信号:")
                for r in rows:
                    print(f"  [{r['signal_type']:4}] {r['symbol']} {r['strategy_name']:10} "
                          f"conf={r['confidence']:.0f} price={r['signal_price']:.2f}")
                    print(f"         {r['signal_reason']}")
            else:
                print("\n当前无待执行信号")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='策略信号生成器')
    parser.add_argument('--date', default=None, help='日期 YYYY-MM-DD')
    parser.add_argument('--strategy', default=None, help='策略类型')
    parser.add_argument('--symbols', default=None, help='股票代码(逗号分隔)')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    syms = args.symbols.split(',') if args.symbols else None
    run(date_str=args.date, strategy_type=args.strategy, symbols=syms, verbose=args.verbose)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量A股K线采集器
数据源: 新浪历史K线 API (直连，无代理)
入库: q_daily_kline (完整技术指标字段)
"""
import os, sys, time, json, re, urllib.parse
[os.environ.pop(k, None) for k in list(os.environ.keys()) if 'proxy' in k.lower()]

import pymysql
import pandas as pd
import numpy as np
import urllib.request

# ── DB ─────────────────────────────────────────────────────────────
DB = dict(host='127.0.0.1', port=3306, user='root',
          password='tangpanpan314', database='stock', charset='utf8mb4')

def get_conn():
    return pymysql.connect(**DB)

# ── 技术指标 ──────────────────────────────────────────────────────
def calc_ma(closes, n):
    if len(closes) < n: return None
    return round(sum(closes[-n:]) / n, 4)

def calc_rsi(closes, period):
    if len(closes) < period + 1: return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i - 1]) / period
        avg_l = (avg_l * (period - 1) + losses[i - 1]) / period
    if avg_l == 0: return 100.0
    return round(100 - 100 / (1 + avg_g / avg_l), 4)

def calc_macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal: return None, None, None
    def ema(data, n):
        k = 2 / (n + 1); r = [data[0]]
        for v in data[1:]: r.append(v * k + r[-1] * (1 - k))
        return r
    ef = ema(closes, fast)
    es = ema(closes, slow)
    dif = [ef[i] - es[i] for i in range(len(closes))]
    dea = ema(dif, signal)
    hist = [(dif[i] - dea[i]) * 2 for i in range(len(closes))]
    return round(dif[-1], 6), round(dea[-1], 6), round(hist[-1], 6)

def calc_boll(closes, n=20, k=2):
    if len(closes) < n: return None, None, None
    mid = sum(closes[-n:]) / n
    std = (sum((c - mid)**2 for c in closes[-n:]) / n) ** 0.5
    return round(mid + k * std, 4), round(mid, 4), round(mid - k * std, 4)

def calc_kdj(highs, lows, closes, n=9, m1=3, m2=3):
    if len(closes) < n: return None, None, None
    lows_n = lows[-n:]; highs_n = highs[-n:]
    lv = min(lows_n); hv = max(highs_n)
    rsv = (closes[-1] - lv) / (hv - lv) * 100 if hv != lv else 50
    k = 50; d = 50
    k = 2/3 * k + 1/3 * rsv
    d = 2/3 * d + 1/3 * k
    j = 3 * k - 2 * d
    return round(k, 4), round(d, 4), round(j, 4)

def calc_atr(highs, lows, closes, n=14):
    if len(closes) < n + 1: return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i]-lows[i],
                 abs(highs[i]-closes[i-1]),
                 abs(lows[i]-closes[i-1]))
        trs.append(tr)
    if len(trs) < n: return None
    return round(sum(trs[-n:]) / n, 4)

# ── K线采集 ───────────────────────────────────────────────────────
def fetch_sina_kline(symbol: str) -> list:
    """从新浪获取日K线，返回 [{day, open, high, low, close, volume}, ...]"""
    m = re.match(r'^(sh|sz)(\d{6})$', symbol)
    if not m:
        # 纯数字symbol
        code = symbol.strip()
        exchange = 'sh' if code.startswith(('6', '5', '9')) else 'sz'
    else:
        exchange, code = m.group(1), m.group(2)

    url = 'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
    params = urllib.parse.urlencode({
        'symbol': f'{exchange}{code}',
        'scale': 240,   # 日K
        'ma': 'no',
        'datalen': 2500
    })
    req = urllib.request.Request(url + '?' + params, headers={
        'Referer': 'https://finance.sina.com.cn/',
        'User-Agent': 'Mozilla/5.0'
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode('utf-8'))
    return data  # list of dicts

def collect_klines(symbol: str, name: str = '') -> int:
    """采集单只股票，填入完整技术指标，返回新增行数"""
    try:
        raw = fetch_sina_kline(symbol)
    except Exception as e:
        return 0

    if not raw or len(raw) < 30:
        return 0

    # 计算所有技术指标（用完整序列）
    closes = [float(d['close']) for d in raw]
    highs  = [float(d['high'])  for d in raw]
    lows   = [float(d['low'])   for d in raw]

    macd_dif, macd_dea, macd_hist = calc_macd(closes)
    ma5  = calc_ma(closes, 5)
    ma10 = calc_ma(closes, 10)
    ma20 = calc_ma(closes, 20)
    ma60 = calc_ma(closes, 60) if len(closes) >= 60 else None
    rsi6  = calc_rsi(closes, 6)
    rsi12 = calc_rsi(closes, 12)
    rsi24 = calc_rsi(closes, 24)
    boll_upper, boll_mid, boll_lower = calc_boll(closes)
    kdj_k, kdj_d, kdj_j = calc_kdj(highs, lows, closes)
    atr = calc_atr(highs, lows, closes)

    # 判断市场
    code = re.sub(r'^(sh|sz)', '', symbol)
    market = 'SH' if code.startswith(('6', '5', '9', '7')) else ('SZ' if code.startswith(('0', '3', '2')) else 'BJ')

    inserted = 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            for i, d in enumerate(raw):
                prev_close = closes[i-1] if i > 0 else None
                change_pct = round((float(d['close']) - prev_close) / prev_close * 100, 4) if prev_close else 0

                prev_c = prev_close
                vals = (
                    code, name, d['day'],
                    float(d['open']), float(d['high']), float(d['low']), float(d['close']),
                    prev_c, change_pct,
                    int(d['volume']), 0.0,
                    None, market,
                    ma5, ma10, ma20, ma60,
                    rsi6, rsi12, rsi24,
                    macd_dif, macd_dea, macd_hist,
                    boll_upper, boll_mid, boll_lower,
                    kdj_k, kdj_d, kdj_j,
                    atr, 'sina', 1
                )
                placeholders = ','.join(['%s'] * len(vals))
                cur.execute(f"""
                    INSERT IGNORE INTO q_daily_kline
                      (symbol,symbol_name,trade_date,open_price,high_price,low_price,
                       close_price,prev_close,change_pct,volume,amount,turnover_rate,market,
                       ma5,ma10,ma20,ma60,rsi6,rsi12,rsi24,
                       macd_dif,macd_dea,macd_hist,boll_upper,boll_mid,boll_lower,
                       kdj_k,kdj_d,kdj_j,atr,data_source,is_adj_close)
                    VALUES ({placeholders})
                """, vals)
                if cur.rowcount > 0:
                    inserted += 1
            conn.commit()
    return inserted

# ── 主程序 ───────────────────────────────────────────────────────
def main():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol, name FROM q_stock_pool
                WHERE market IN ('SH', 'SZ')
                  AND symbol IS NOT NULL
                ORDER BY IFNULL(market_cap, 0) DESC
            """)
            stocks = cur.fetchall()

    total = len(stocks)
    success = fail = total_inserted = 0
    print(f"[INFO] 共 {total} 只A股，开始采集...")
    print(f"[INFO] 开始: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    for i, (symbol, name) in enumerate(stocks):
        label = f"{symbol} {name or ''}"
        try:
            n = collect_klines(str(symbol), name or '')
            if n > 0:
                success += 1
                total_inserted += n
                if n >= 100:
                    print(f"[{i+1}/{total}] ✅ {label}: +{n}条 (共{total_inserted}入库)")
            else:
                fail += 1
                print(f"[{i+1}/{total}] ⚠️  {label}: 无新数据")
        except Exception as e:
            fail += 1
            print(f"[{i+1}/{total}] ❌ {label}: {str(e)[:80]}")

        if (i + 1) % 100 == 0:
            print(f"\n[PROGRESS] {i+1}/{total} | 成功 {success} | 失败 {fail} | 新增 {total_inserted} 条\n")
            sys.stdout.flush()

        if (i + 1) % 500 == 0:
            time.sleep(3)

    print(f"\n[DONE] {success}/{total} 成功 | 新增 {total_inserted} 条K线 | 失败 {fail}")
    print(f"[INFO] 结束: {time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main()

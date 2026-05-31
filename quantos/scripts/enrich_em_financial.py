#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东财直连 PE/PB/市值采集器
绕过 AkShare 代理，直连东方财富 API
"""
import os, time, json
[os.environ.pop(k, None) for k in list(os.environ.keys()) if 'proxy' in k.lower()]
import pymysql, requests

DB = dict(host='127.0.0.1', port=3306, user='root', password='tangpanpan314', database='stock', charset='utf8mb4')

def get_conn():
    return pymysql.connect(**DB, cursorclass=pymysql.cursors.DictCursor)

def fetch_em_financial(mkt: str, code: str) -> dict:
    """东方财富直连 API 获取 PE/PB/总市值"""
    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={mkt}.{code}&fields=f57,f162,f167,f116"
    try:
        r = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Referer': 'https://finance.eastmoney.com/'
        }, timeout=5)
        d = r.json()
        if not d.get('data'):
            return {}
        data = d['data']
        return {
            'pe':  data.get('f57'),      # 市盈率
            'pb':  data.get('f162'),    # 市净率
            'mkt': data.get('f116'),    # 总市值(万元)
        }
    except:
        return {}

def get_market_code(symbol: str) -> tuple:
    """返回 (mkt_code, em_code)"""
    if symbol.startswith(('6', '5', '9')):
        return '1', symbol
    return '0', symbol

def main():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT symbol FROM q_stock_pool ORDER BY symbol")
            symbols = [r['symbol'] for r in cur.fetchall()]

    print(f"待采集 PE/PB/市值: {len(symbols)} 只")
    updated_pe = updated_pb = updated_mc = failed = 0
    batch = 50

    for i, sym in enumerate(symbols):
        mkt, code = get_market_code(sym)
        data = fetch_em_financial(mkt, code)
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                fields, vals = [], []
                if data.get('pe') and 0 < float(data['pe']) < 9999:
                    fields.append("pe_ratio=%s"); vals.append(data['pe']); updated_pe += 1
                if data.get('pb') and 0 < float(data['pb']) < 100:
                    fields.append("pb_ratio=%s"); vals.append(data['pb']); updated_pb += 1
                if data.get('mkt') and float(data['mkt']) > 0:
                    fields.append("market_cap=%s"); vals.append(float(data['mkt']) * 10000); updated_mc += 1
                
                if fields:
                    vals.append(sym)
                    cur.execute(f"UPDATE q_stock_pool SET {','.join(fields)} WHERE symbol=%s", vals)
                    conn.commit()
        
        failed += (1 if not data else 0)
        if (i + 1) % 100 == 0:
            print(f"进度: {i+1}/{len(symbols)}  PE:{updated_pe} PB:{updated_pb} MC:{updated_mc}")
        
        # 防限流: 50ms/只
        time.sleep(0.05)
    
    print(f"完成! PE:{updated_pe} PB:{updated_pb} MC:{updated_mc} 失败:{failed}")

if __name__ == '__main__':
    main()

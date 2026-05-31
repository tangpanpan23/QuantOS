#!/usr/bin/env python3
"""
补全 q_stock_pool 的 PE/PB/市值 字段
数据源：东方财富直连 API（绕过 AkShare，避免代理拦截）
API: https://push2.eastmoney.com/api/qt/stock/get?secid={market}.{code}&fields=f57,f162,f167,f173,f116,f117,f162
  f57=股票代码 f162=市盈率(动) f167=市净率 f173=总市值 f116=流通市值 f117=每股收益(年化)
"""
import os, sys, time, logging, json
for k in list(os.environ.keys()):
    if 'proxy' in k.lower(): del os.environ[k]

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db.db_client import get_session
from db.models import StockPoolDB

logging.basicConfig(level=logging.INFO, format='%H:%M:%S [%(levelname)s] %(message)s')
logger = logging.getLogger("em_enrich")

import requests
import tqdm

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://quote.eastmoney.com/',
    'Accept': 'application/json',
}

def em_code(symbol):
    """转换为东财 secid: 6开头=1.沪市 0/3=0.深市"""
    s = symbol.lstrip('0')
    if symbol.startswith('6') or symbol.startswith('9'):
        return f'1.{symbol}'
    else:
        return f'0.{symbol}'

FIELDS = 'f57,f116,f117,f162,f167,f173,f47,f48'

def fetch_em_data(symbol):
    """获取东方财富个股数据，返回 dict"""
    try:
        secid = em_code(symbol)
        url = f'https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields={FIELDS}&ut=fa5fd1943c7b386f172d6893dbfba10b'
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return None
        data = resp.json()
        d = data.get('data', {}) or {}
        if not d.get('f57'):
            return None
        return {
            'symbol': symbol,
            'pe': d.get('f162'),       # 市盈率(动)
            'pb': d.get('f167'),       # 市净率
            'total_market_cap': d.get('f173'),  # 总市值（元）
            'float_market_cap': d.get('f116'),  # 流通市值（元）
            'eps': d.get('f117'),      # 每股收益(年化)
            'price': d.get('f43'),     # 当前价格
            'name': d.get('f58'),      # 股票名称
        }
    except Exception as e:
        return None

def main():
    with get_session() as session:
        stocks = session.query(StockPoolDB.symbol, StockPoolDB.name,
                                StockPoolDB.pe_ratio, StockPoolDB.pb_ratio,
                                StockPoolDB.market_cap).all()
    symbols = [(r.symbol, r.name, r.pe_ratio, r.pb_ratio, r.market_cap) for r in stocks]
    total = len(symbols)
    
    # 只处理缺少关键数据的
    to_fetch = [(s, n) for s, n, pe, pb, mc in symbols
                if (not pe or pe <= 0 or pe > 9999) or (not pb or pb <= 0) or (not mc or mc <= 0)]
    logger.info(f"总 {total} 只，需要补全 {len(to_fetch)} 只（PE/PB/市值）")

    updated = 0
    failed = 0
    seen = set()

    for symbol, name in tqdm.tqdm(to_fetch, desc="东财市值"):
        if symbol in seen:
            continue
        seen.add(symbol)

        data = fetch_em_data(symbol)
        if data:
            # PE: 保留现有值除非它不合理
            pe = data['pe']
            if pe and 0 < pe < 9999:
                pb = data['pb']
                mc = data['total_market_cap']
                
                with get_session() as session2:
                    row = session2.query(StockPoolDB).filter_by(symbol=symbol).first()
                    if row:
                        if not row.pe_ratio or row.pe_ratio <= 0 or row.pe_ratio > 9999:
                            row.pe_ratio = round(pe, 2) if pe else None
                        if not row.pb_ratio or row.pb_ratio <= 0:
                            row.pb_ratio = round(pb, 4) if pb else None
                        if not row.market_cap or row.market_cap <= 0:
                            row.market_cap = round(mc / 1e8, 2) if mc else None  # 转为亿元
                        session2.commit()
                        updated += 1
        else:
            failed += 1

        time.sleep(0.15)  # 礼貌限速

    logger.info(f"东财市值补全完成: 成功 {updated} 只, 失败 {failed} 只")

if __name__ == '__main__':
    main()

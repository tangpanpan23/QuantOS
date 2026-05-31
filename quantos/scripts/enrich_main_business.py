#!/usr/bin/env python3
"""补全 q_stock_pool 的 main_business 字段（THS同花顺接口，全通）"""
import os, sys, time, logging
for k in list(os.environ.keys()):
    if 'proxy' in k.lower(): del os.environ[k]

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db.db_client import get_session
from db.models import StockPoolDB

logging.basicConfig(level=logging.INFO, format='%H:%M:%S [%(levelname)s] %(message)s')
logger = logging.getLogger("enrich")

import akshare as ak
import tqdm

def main():
    # 加载所有股票
    with get_session() as session:
        rows = session.query(StockPoolDB.symbol, StockPoolDB.name, StockPoolDB.main_business).all()

    stocks = [(r.symbol, r.name, r.main_business) for r in rows]
    total = len(stocks)
    logger.info(f"总股票: {total}，开始补全 main_business...")

    updated = 0
    failed = 0
    seen = set()

    for symbol, name, current_biz in tqdm.tqdm(stocks, desc="THS主营"):
        if symbol in seen:
            continue
        seen.add(symbol)

        try:
            df = ak.stock_zyjs_ths(symbol=symbol)
            if df is not None and not df.empty:
                biz = str(df.iloc[0].get('主营业务', '')).strip()
                if biz and biz not in ('nan', 'None', '') and biz != current_biz:
                    with get_session() as session2:
                        row = session2.query(StockPoolDB).filter_by(symbol=symbol).first()
                        if row:
                            row.main_business = biz[:500]
                            session2.commit()
                            updated += 1
                    continue
        except Exception:
            pass
        failed += 1
        time.sleep(0.2)

    logger.info(f"完成: 成功更新 {updated} 只，失败/无数据 {failed} 只")

if __name__ == '__main__':
    main()

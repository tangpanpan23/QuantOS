#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantOS 实时行情采集器
采集 Tank 自选股 + 全市场股票的实时价格/PE/PB/市值，写入 DB 并更新 q_stock_pool
同时支持采集指数实时数据

用法:
  python3 realtime_collector.py              # Tank自选股实时行情
  python3 realtime_collector.py --all        # 全市场5519只（慢，约30分钟）
  python3 realtime_collector.py --indices   # 6大指数
  python3 realtime_collector.py --watched    # Tank自选股实时快照
"""
import sys, os, json, time, argparse, logging
from datetime import datetime, date
from typing import Dict, List
for k in list(os.environ.keys()):
    if 'proxy' in k.lower(): del os.environ[k]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymysql
import requests
import tqdm

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('realtime')

DB = dict(host='127.0.0.1', port=3306, user='root', password='tangpanpan314', database='stock', charset='utf8mb4')

def get_conn():
    return pymysql.connect(**DB, cursorclass=pymysql.cursors.DictCursor)

# ─── 新浪实时行情 ─────────────────────────────────────────────────────────────
def fetch_sina_realtime(codes: List[str]) -> Dict[str, dict]:
    """
    新浪实时行情，返回 {symbol: {name, price, open, high, low, close, volume, amount, ...}}
    codes格式: sh600519, sz000858
    """
    if not codes:
        return {}
    batch = []
    for c in codes:
        if c.startswith(('6','9')):
            batch.append(f'sh{c}')
        else:
            batch.append(f'sz{c}')
    
    result = {}
    # 分批请求，每批50个
    for i in range(0, len(batch), 50):
        chunk = batch[i:i+50]
        url = 'https://hq.sinajs.cn/list=' + ','.join(chunk)
        try:
            r = requests.get(url, headers={
                'Referer': 'https://finance.sina.com.cn',
                'User-Agent': 'Mozilla/5.0'
            }, timeout=10)
            r.encoding = 'gbk'
            lines = r.text.strip().split('\n')
            for line in lines:
                if '=' not in line or '"' not in line:
                    continue
                raw_sym = line.split('=')[0].replace('hq_str_', '').strip()
                # 去掉 "var " 前缀（新浪有时返回 "var sh600519"）
                raw_sym = raw_sym.replace('var ', '').strip()
                sym = raw_sym[2:] if raw_sym.startswith(('sh','sz')) else raw_sym
                parts = line.split('"')[1].split(',')
                if len(parts) < 10:
                    continue
                result[sym] = {
                    'raw':      raw_sym,
                    'name':     parts[0],
                    'open':     to_float(parts[1]),
                    'prev':     to_float(parts[2]),   # 昨收
                    'price':    to_float(parts[3]),    # 现价
                    'high':     to_float(parts[4]),
                    'low':      to_float(parts[5]),
                    'buy1':     to_float(parts[6]),
                    'sell1':    to_float(parts[7]),
                    'volume':   to_float(parts[8]),    # 成交量(股)
                    'amount':   to_float(parts[9]),    # 成交额(元)
                    # parts[10-19] 委买1-10
                    # parts[20-29] 委卖1-10
                    'date':     parts[30] if len(parts) > 30 else '',
                    'time':     parts[31] if len(parts) > 31 else '',
                    'change_pct': None,  # 计算
                }
                p = result[sym]['prev']
                c = result[sym]['price']
                if p and c and p > 0:
                    result[sym]['change_pct'] = round((c - p) / p * 100, 2)
        except Exception as e:
            log.warning("批次%d/%d 获取失败: %s", i//50+1, (len(batch)+49)//50, e)
    return result

def to_float(v) -> float:
    try: return float(v)
    except: return 0.0

# ─── 新浪财务数据（PE/PB/市值）───────────────────────────────────────────────
def fetch_sina_financial(codes: List[str]) -> Dict[str, dict]:
    """
    新浪行情扩展数据：PE/PB/总市值
    使用 hq.sinajs.cn/rn=xxx 格式（带随机数避免304缓存）
    """
    if not codes:
        return {}
    result = {}
    for i in range(0, len(codes), 30):
        chunk = codes[i:i+30]
        batch = [f'sh{c}' if c.startswith(('6','9')) else f'sz{c}' for c in chunk]
        url = f'https://hq.sinajs.cn/rn={int(time.time()*1000)}&list={",".join(batch)}'
        try:
            r = requests.get(url, headers={
                'Referer': 'https://finance.sina.com.cn',
                'User-Agent': 'Mozilla/5.0'
            }, timeout=10)
            r.encoding = 'gbk'
            lines = r.text.strip().split('\n')
            for line in lines:
                if '=' not in line or '"' not in line:
                    continue
                raw_sym = line.split('=')[0].replace('hq_str_', '').strip()
                raw_sym = raw_sym.replace('var ', '').strip()
                sym = raw_sym[2:] if raw_sym.startswith(('sh','sz')) else raw_sym
                parts = line.split('"')[1].split(',')
                if len(parts) < 40:
                    continue
                # PE=parts[39], PB=parts[46], 总市值=parts[44] (万元)
                mktcap_raw = to_float(parts[44]) if len(parts) > 44 and parts[44] else None
                result[sym] = {
                    'pe':    to_float(parts[39]) if len(parts) > 39 and parts[39] else None,
                    'pb':    to_float(parts[46]) if len(parts) > 46 and parts[46] else None,
                    'mktcap': mktcap_raw / 10000 if mktcap_raw else None,
                }
        except Exception as e:
            log.warning("财务数据批次%d失败: %s", i//30+1, e)
        time.sleep(0.2)
    return result

# ─── 指数实时行情 ─────────────────────────────────────────────────────────────
INDICES = {
    '000001': '上证指数',
    '399001': '深证成指', 
    '399006': '创业板指',
    '000300': '沪深300',
    '000016': '上证50',
    '000688': '科创50',
}

def fetch_index_realtime() -> Dict[str, dict]:
    """采集6大指数实时数据"""
    codes = list(INDICES.keys())
    # 指数前缀 sh=沪 sz=深
    prefixed = ['sh' + c if c.startswith('0') else 'sz' + c for c in codes]
    url = 'https://hq.sinajs.cn/list=' + ','.join(prefixed)
    result = {}
    try:
        r = requests.get(url, headers={'Referer':'https://finance.sina.com.cn','User-Agent':'Mozilla/5.0'}, timeout=10)
        r.encoding = 'gbk'
        lines = r.text.strip().split('\n')
        for line in lines:
            if '=' not in line or '"' not in line:
                continue
            raw_sym = line.split('=')[0].replace('hq_str_', '').strip()
            raw_sym = raw_sym.replace('var ', '').strip()
            sym = raw_sym[2:] if raw_sym.startswith(('sh', 'sz')) else raw_sym
            parts = line.split('"')[1].split(',')
            if len(parts) < 10:
                continue
            prev = to_float(parts[2])
            price = to_float(parts[3])
            result[sym] = {
                'name': INDICES.get(sym, sym),
                'price': price,
                'prev_close': prev,
                'change': price - prev if price and prev else 0,
                'change_pct': round((price - prev) / prev * 100, 2) if prev else 0,
                'high': to_float(parts[4]),
                'low':  to_float(parts[5]),
                'time': f"{parts[31] if len(parts) > 31 else ''} {parts[30] if len(parts) > 30 else ''}".strip(),
            }
    except Exception as e:
        log.error("指数行情获取失败: %s", e)
    return result

# ─── 更新 q_stock_pool ────────────────────────────────────────────────────────
def update_stock_pool(realtime: Dict, financial: Dict):
    """更新 q_stock_pool 的实时价格"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            for sym, data in realtime.items():
                fin = financial.get(sym, {})
                pe = fin.get('pe')
                pb = fin.get('pb')
                mc = fin.get('mktcap')
                cur.execute("""
                    UPDATE q_stock_pool SET
                        current_price = %s,
                        current_change_pct = %s,
                        pe_ratio = COALESCE(NULLIF(%s, 0), pe_ratio),
                        pb_ratio = COALESCE(NULLIF(%s, 0), pb_ratio),
                        market_cap = COALESCE(NULLIF(%s, 0), market_cap)
                    WHERE symbol = %s
                """, (
                    data.get('price'), data.get('change_pct'),
                    pe, pb, mc,
                    sym
                ))
        conn.commit()
    log.info("更新 q_stock_pool: %d 只", len(realtime))
# ─── 写入实时行情快照 ────────────────────────────────────────────────────────
def write_snapshot(realtime: Dict, source: str = 'sina'):
    """将实时行情写入 q_realtime_snapshot 表"""
    now = datetime.now()
    with get_conn() as conn:
        with conn.cursor() as cur:
            for sym, data in realtime.items():
                fin_data = {}  # financial data if available
                cur.execute("""
                    INSERT INTO q_realtime_snapshot
                    (symbol, snapshot_date, snapshot_time, name, price, prev_close,
                     open_price, high, low, volume, amount, change_pct, source)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                        price=VALUES(price),
                        high=GREATEST(IFNULL(high,0),VALUES(high)),
                        low=LEAST(IFNULL(low,0),VALUES(low)),
                        volume=VALUES(volume), amount=VALUES(amount),
                        change_pct=VALUES(change_pct)
                """, (
                    sym, now.date(), now,
                    data.get('name'),
                    data.get('price'),
                    data.get('prev'),
                    data.get('open'),
                    data.get('high'),
                    data.get('low'),
                    data.get('volume'),
                    data.get('amount'),
                    data.get('change_pct'),
                    source
                ))
        conn.commit()
    log.info("快照写入 q_realtime_snapshot: %d 只", len(realtime))

# ─── 全市场采集（分批）───────────────────────────────────────────────────────
def collect_all_market():
    """全市场5519只股票实时行情（分100批，约20分钟）"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT symbol FROM q_stock_pool ORDER BY symbol")
            symbols = [r['symbol'] for r in cur.fetchall()]
    total = len(symbols)
    log.info("全市场采集: %d 只", total)
    
    all_realtime = {}
    all_financial = {}
    batch_size = 50
    
    for i in tqdm.tqdm(range(0, total, batch_size), desc="全市场行情"):
        chunk = symbols[i:i+batch_size]
        rt = fetch_sina_realtime(chunk)
        all_realtime.update(rt)
        fin = fetch_sina_financial(chunk)
        all_financial.update(fin)
        time.sleep(0.3)
    
    update_stock_pool(all_realtime, all_financial)
    return all_realtime

# ─── 显示实时行情 ────────────────────────────────────────────────────────────
def show_realtime(realtime: Dict, title: str = "实时行情"):
    if not realtime:
        print("无数据")
        return
    print(f"\n{'='*70}")
    print(f"  {title}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    print(f"  {'代码':<8} {'名称':<10} {'现价':>8} {'涨跌%':>8} {'最高':>8} {'最低':>8} {'成交量':>12}")
    print(f"  {'-'*8} {'-'*10} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*12}")
    for sym in list(realtime.keys())[:30]:
        d = realtime[sym]
        pct = d['change_pct']
        pct_str = f"{pct:+.2f}%" if pct else "N/A"
        vol = d['volume'] or 0
        vol_str = f"{vol/1e4:.0f}万" if vol < 1e8 else f"{vol/1e8:.2f}亿"
        print(f"  {sym:<8} {d['name']:<10} {d['price']:>8.2f} {pct_str:>8} "
              f"{d['high']:>8.2f} {d['low']:>8.2f} {vol_str:>12}")

def show_indices(indices: Dict):
    print(f"\n{'='*70}")
    print(f"  指数实时行情  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    print(f"  {'指数':<12} {'代码':<8} {'最新':>10} {'涨跌':>10} {'涨跌幅':>8} {'最高':>10} {'最低':>10}")
    print(f"  {'-'*12} {'-'*8} {'-'*10} {'-'*10} {'-'*8} {'-'*10} {'-'*10}")
    for sym, d in indices.items():
        pct = d['change_pct']
        chg = d['change']
        print(f"  {d['name']:<12} {sym:<8} {d['price']:>10.2f} {chg:>+10.2f} {pct:>+7.2f}% "
              f"{d['high']:>10.2f} {d['low']:>10.2f}")

def show_watched(realtime: Dict, financial: Dict):
    """显示 Tank 自选股实时行情"""
    TANK_POOL = ['600519','000858','601318','600900','600028','002475','000001','601288','600036','000002']
    # 尝试从DB读取当前价格（作为fallback）
    db_prices = {}
    with get_conn() as conn:
        with conn.cursor() as cur:
            placeholders = ','.join(['%s'] * len(TANK_POOL))
            cur.execute(f"SELECT symbol, name, current_price, current_change_pct, pe_ratio, pb_ratio, market_cap FROM q_stock_pool WHERE symbol IN ({placeholders})", TANK_POOL)
            for r in cur.fetchall():
                db_prices[r['symbol']] = {
                    'name': r['name'], 'price': float(r['current_price'] or 0),
                    'pct': float(r['current_change_pct'] or 0),
                    'pe': float(r['pe_ratio'] or 0), 'pb': float(r['pb_ratio'] or 0),
                    'mc': float(r['market_cap'] or 0),
                }

    print(f"\n{'='*75}")
    print(f"  Tank 自选股实时行情  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*75}")
    print(f"  {'代码':<8} {'名称':<12} {'现价':>8} {'涨跌幅':>7} {'PE':>6} {'PB':>6} {'市值(亿)':>10}")
    print(f"  {'-'*8} {'-'*12} {'-'*8} {'-'*7} {'-'*6} {'-'*6} {'-'*10}")

    for sym in TANK_POOL:
        rt = realtime.get(sym, {})
        fin = financial.get(sym, {})
        db = db_prices.get(sym, {})

        # 优先用实时数据，没有则用DB数据
        price = rt.get('price') or db.get('price', 0)
        pct   = rt.get('change_pct') if rt.get('change_pct') is not None else db.get('pct', 0)
        name  = rt.get('name') or db.get('name', '')
        pe    = fin.get('pe') or db.get('pe', 0)
        pb    = fin.get('pb') or db.get('pb', 0)
        mc    = fin.get('mktcap') or db.get('mc', 0)

        if not name:
            continue

        pct_str = f"{pct:+.2f}%" if pct else "N/A"
        pe_str  = f"{pe:.1f}" if pe and 0 < pe < 9999 else '-'
        pb_str  = f"{pb:.2f}" if pb and 0 < pb < 100 else '-'
        mc_str  = f"{mc:.0f}" if mc > 0 else '-'

        print(f"  {sym:<8} {name:<12} {price:>8.2f} {pct_str:>7} {pe_str:>6} {pb_str:>6} {mc_str:>10}")

# ─── 主程序 ─────────────────────────────────────────────────────────────────


# ─── 新闻-股票关联 ───────────────────────────────────────────────────────────
def write_news_stock_relations():
    """根据关键词将新闻与股票关联，写入 q_news_stock_relation"""
    import re, json
    keywords = {
        '贵州茅台': ['600519'],
        '五粮液': ['000858'],
        '中国平安': ['601318'],
        '平安银行': ['000001'],
        '长江电力': ['600900'],
        '中国石化': ['600028'],
        '立讯精密': ['002475'],
        '招商银行': ['600036'],
        '农业银行': ['601288'],
        '万科': ['000002'],
        '白酒': ['600519', '000858'],
        '银行': ['000001', '600036', '601288'],
        '保险': ['601318'],
        '电力': ['600900'],
        '新能源': ['002475'],
        '房地产': ['000002'],
    }

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, content_summary FROM q_market_news
                WHERE id NOT IN (SELECT news_id FROM q_news_stock_relation)
                LIMIT 100
            """)
            news_items = cur.fetchall()
            total = 0
            for news in news_items:
                nid = news['id']
                text = (news.get('title') or '') + (news.get('content_summary') or '')
                found = set()
                for kw, syms in keywords.items():
                    if kw in text:
                        found.update(syms)
                for sym in found:
                    cur.execute("""
                        INSERT IGNORE INTO q_news_stock_relation (news_id, symbol, relation_type, impact_strength, created_at)
                        VALUES (%s, %s, 'keyword', 50, NOW())
                    """, (nid, sym))
                total += len(found)
            conn.commit()
            if total > 0:
                log.info("新闻-股票关联: %d 条记录写入", total)


def main():
    parser = argparse.ArgumentParser(description='实时行情采集')
    parser.add_argument('--all', action='store_true', help='全市场5519只')
    parser.add_argument('--indices', action='store_true', help='采集指数')
    parser.add_argument('--watched', action='store_true', help='Tank自选股')
    parser.add_argument('--batch-size', type=int, default=50, help='每批数量')
    args = parser.parse_args()

    if args.indices:
        indices = fetch_index_realtime()
        show_indices(indices)
        write_news_stock_relations()
        return

    if args.all:
        rt = collect_all_market()
        return

    # 默认: Tank自选股 + 指数
    tank = ['600519','000858','601318','600900','600028','002475','000001','601288','600036','000002']
    log.info("采集 Tank 自选股实时行情...")
    rt = fetch_sina_realtime(tank)
    fin = fetch_sina_financial(tank)
    update_stock_pool(rt, fin)
    write_snapshot(rt)
    show_watched(rt, fin)

    # 指数
    indices = fetch_index_realtime()
    show_indices(indices)
    write_news_stock_relations()

if __name__ == '__main__':
    main()

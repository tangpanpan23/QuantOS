#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻-股票关联写入器
基于关键词匹配将新闻/政策与股票关联
"""
import pymysql, re, json
from datetime import datetime, timedelta

DB = dict(host='127.0.0.1', port=3306, user='root',
          password='tangpanpan314', database='stock', charset='utf8mb4')

def get_conn():
    return pymysql.connect(**DB)

# Tank 自选股关键词映射（扩大覆盖）
KEYWORDS = {
    # 白酒
    '贵州茅台': '600519', '五粮液': '000858', '泸州老窖': '000568',
    '洋河股份': '002304', '山西汾酒': '600809', '古井贡酒': '000596',
    # 银行
    '招商银行': '600036', '工商银行': '601398', '建设银行': '601939',
    '农业银行': '601288', '中国银行': '601988', '平安银行': '000001',
    '兴业银行': '601166', '交通银行': '601328', '浦发银行': '600000',
    # 保险/金融
    '中国平安': '601318', '中国人寿': '601628', '新华保险': '601336',
    '中国太保': '601601', '中信证券': '600030', '东方财富': '300059',
    '同花顺': '300033',
    # 新能源
    '宁德时代': '300750', '比亚迪': '002594', '隆基绿能': '601012',
    '阳光电源': '300274', '通威股份': '600438',
    # 消费/其他
    '长江电力': '600900', '中国中免': '601888', '伊利股份': '600887',
    '美的集团': '000333', '格力电器': '000651', '海康威视': '002415',
    '立讯精密': '002475', '海天味业': '603288',
    # 宏观经济关键词
    '央行': 'central_bank', '降息': 'macro', '加息': 'macro',
    '降准': 'macro', '量化宽松': 'macro', '美股': 'index',
    'A股': 'index', '上证': 'index', '创业板': 'index',
    '北向资金': 'index', '外资': 'index', '汇率': 'macro',
    '人民币': 'macro', '美元': 'macro', '黄金': 'commodity',
    '原油': 'commodity', '大宗商品': 'commodity',
}

RELATION_TYPE_MAP = {
    'central_bank': '政策关联', 'macro': '宏观关联',
    'index': '市场关联', 'commodity': '商品关联'
}

def match_news(content: str, title: str) -> list:
    """从内容+标题中匹配股票，返回 [(symbol, relation_type), ...]"""
    text = f"{title} {content or ''}"
    found = []
    for keyword, code in KEYWORDS.items():
        if keyword in text:
            # 确定关联类型
            if code in RELATION_TYPE_MAP:
                rel_type = RELATION_TYPE_MAP[code]
            else:
                rel_type = '关键词关联'
            found.append((code, rel_type))
    return found

def write_relations():
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 取所有未关联的新闻
            cur.execute("""
                SELECT id, title, content_summary, source, publish_date
                FROM q_market_news
            """)
            news_list = cur.fetchall()

            # 也取所有已有关联的新闻看有没有新的关键词
            cur.execute("SELECT news_id, symbol FROM q_news_stock_relation")
            existing = set((str(nid), sym) for nid, sym in cur.fetchall())

            inserted = 0
            for (nid, title, content, source, pub_at) in news_list:
                matches = match_news(content or '', title or '')
                for sym, rel_type in matches:
                    if (str(nid), sym) not in existing:
                        cur.execute("""
                            INSERT IGNORE INTO q_news_stock_relation
                              (news_id, symbol, relation_type, impact_strength, created_at)
                            VALUES (%s, %s, %s, %s, NOW())
                        """, (nid, sym, rel_type, 5))
                        if cur.rowcount > 0:
                            inserted += 1
                            print(f"  + {title[:40]} → {sym} ({rel_type})")

            # 政策文档也做关联
            cur.execute("""
                SELECT id, doc_title, content_summary, effective_date
                FROM q_policy_doc
            """)
            policies = cur.fetchall()
            for (pid, title, summary, eff_date) in policies:
                matches = match_news(summary or '', title or '')
                for sym, rel_type in matches:
                    if (str(pid + 10000), sym) not in existing:
                        cur.execute("""
                            INSERT IGNORE INTO q_news_stock_relation
                              (news_id, symbol, relation_type, impact_strength, created_at)
                            VALUES (%s, %s, %s, %s, NOW())
                        """, (pid + 10000, sym, '政策关联', 7))
                        if cur.rowcount > 0:
                            inserted += 1
                            print(f"  + [政策] {title[:40]} → {sym}")

            conn.commit()
            print(f"\n[OK] 写入 {inserted} 条关联")
            return inserted

if __name__ == '__main__':
    n = write_relations()
    # 验证
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM q_news_stock_relation")
            print(f"[INFO] q_news_stock_relation 现有 {cur.fetchone()[0]} 条")
            cur.execute("""
                SELECT r.symbol, s.name, COUNT(*) as cnt
                FROM q_news_stock_relation r
                LEFT JOIN q_stock_pool s ON r.symbol = s.symbol
                GROUP BY r.symbol ORDER BY cnt DESC LIMIT 10
            """)
            print("TOP关联股票:")
            for row in cur.fetchall():
                print(f"  {row[0]} {row[1] or ''}: {row[2]}条")

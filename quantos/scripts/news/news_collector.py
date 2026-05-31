#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantOS News Collector
----------------------
Collects market news from Eastmoney/Sina, performs rule-based sentiment
analysis, identifies related stocks, and writes to q_market_news and
q_policy_doc tables.

Usage:
    python news_collector.py [--limit N] [--sources eastmoney,sina] [--hours H]
    python news_collector.py --test    # dry-run without DB writes

Tank QuantOS · 2026-05-21
"""
import os
import sys
import re
import json
import time
import logging
import argparse
import hashlib
from datetime import datetime, date
from typing import Optional

# ── Setup ──────────────────────────────────────────────────────────────────
# Clear macOS proxy env vars before any HTTP calls
for _var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
             "all_proxy", "ALL_PROXY", "no_proxy", "NO_PROXY"):
    os.environ.pop(_var, None)
    os.environ.pop(_var.lower(), None)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("news_collector")

# ── DB Config ───────────────────────────────────────────────────────────────
DB_KWARGS = dict(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="tangpanpan314",
    database="stock",
    charset="utf8mb4",
    autocommit=False,
)

# ── Sentiment Lexicons (Chinese) ────────────────────────────────────────────
POSITIVE_WORDS = [
    "涨", "大涨", "涨停", "上涨", "反弹", "回升", "走强", "上行", "突破",
    "看好", "增持", "买入", "推荐", "超配", "跑赢", "超预期", "盈利",
    "增长", "提升", "加速", "扩张", "放量", "活跃", "创新高", "史上最高",
    "政策利好", "重磅", "提振", "回暖", "复苏", "景气", "强劲", "亮眼",
    "爆发", "井喷", "狂飙", "攀升", "上扬", "开门红", "收涨", "收阳",
    "护盘", "抄底", "做多", "牛市", "分红", "回购", "业绩预增", "扭亏",
    "净利", "营收", "订单", "签约", "合作", "中标", "研发", "获批",
    "特斯拉", "宁德时代", "比亚迪", "华为", "苹果", "OpenAI",
    "降息", "宽松", "放水", "万亿", "万亿级", "救市",
]
NEGATIVE_WORDS = [
    "跌", "大跌", "跌停", "下跌", "回落", "下探", "走弱", "下行", "破位",
    "看空", "减持", "卖出", "警告", "下调", "跑输", "不及预期", "亏损",
    "下滑", "萎缩", "收缩", "缩量", "低迷", "创新低", "史上最低",
    "政策利空", "暴雷", "爆雷", "造假", "欺诈", "造假", "退市", "清盘",
    "裁员", "破产", "违约", "债务", "流动性", "踩雷", "做空", "熊市",
    "业绩预减", "首亏", "续亏", "商誉", "减值", "诉讼", "调查", "处罚",
    "制裁", "加税", "缩表", "收紧",
]

# ── Stock name → symbol mapping (compile from DB at startup) ────────────────
def _load_stock_map() -> dict[str, str]:
    """Load stock name -> symbol mapping from DB."""
    try:
        import pymysql
        conn = pymysql.connect(**DB_KWARGS)
        cur = conn.cursor()
        cur.execute("SELECT symbol, name FROM q_stock_pool WHERE status=1")
        rows = cur.fetchall()
        conn.close()
        # name -> symbol
        return {name: sym for sym, name in rows}
    except Exception as e:
        logger.warning(f"Could not load stock map: {e}")
        return {}


def _load_symbol_map() -> dict[str, str]:
    """Load symbol -> name mapping from DB."""
    try:
        import pymysql
        conn = pymysql.connect(**DB_KWARGS)
        cur = conn.cursor()
        cur.execute("SELECT symbol, name FROM q_stock_pool WHERE status=1")
        rows = cur.fetchall()
        conn.close()
        return {sym: name for sym, name in rows}
    except Exception:
        return {}


# ── HTTP Helpers ─────────────────────────────────────────────────────────────
import urllib.request
import urllib.error

def _http_get(url: str, timeout: int = 10) -> Optional[bytes]:
    """GET url, return bytes or None. No proxy."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        logger.debug(f"HTTP GET failed {url}: {e}")
        return None


# ── Sentiment Analysis ───────────────────────────────────────────────────────
def analyze_sentiment(title: str, summary: str = "") -> tuple[float, str, float]:
    """
    Rule-based Chinese sentiment scoring.
    Returns (score, label, confidence).
    score: -1.0 (most negative) to 1.0 (most positive)
    label: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL'
    confidence: 0-100
    """
    text = (str(title) + " " + str(summary)).lower()
    pos_count = sum(1 for w in POSITIVE_WORDS if w in text)
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in text)
    total = pos_count + neg_count

    if total == 0:
        return 0.0, "NEUTRAL", 30.0

    score = (pos_count - neg_count) / total
    score = max(-1.0, min(1.0, score))

    if score > 0.2:
        label = "POSITIVE"
    elif score < -0.2:
        label = "NEGATIVE"
    else:
        label = "NEUTRAL"

    confidence = min(95.0, 40.0 + total * 10)
    return score, label, confidence


# ── Related Stock Identification ────────────────────────────────────────────
# A-share stock code patterns: 6 digits, optionally prefixed with sh/sz/bj
_STOCK_CODE_RE = re.compile(r'\b(\d{6})\b')
# Chinese stock names (loaded from DB)
_stock_name_map: dict[str, str] = {}
_symbol_name_map: dict[str, str] = {}


def load_stock_mappings():
    global _stock_name_map, _symbol_name_map
    _stock_name_map = _load_stock_map()
    _symbol_name_map = _load_symbol_map()


def identify_related_stocks(title: str, summary: str = "") -> list[str]:
    """
    Identify stock codes mentioned in title/summary.
    1. Pattern-match 6-digit codes
    2. Match known stock names
    """
    text = str(title) + " " + str(summary)
    codes: set[str] = set()

    # Extract 6-digit codes (exclude common non-stock numbers)
    for m in _STOCK_CODE_RE.findall(text):
        if m in _symbol_name_map:
            codes.add(m)
        # Also add SH/SZ/BJ prefix if followed by context suggesting a stock
        elif _looks_like_stock_code(m, text):
            codes.add(m)

    # Match known company names
    for name in _stock_name_map:
        if len(name) >= 2 and name in text:
            codes.add(_stock_name_map[name])

    return list(codes)


def _looks_like_stock_code(code: str, text: str) -> bool:
    """Heuristic: 6-digit code is likely a stock if near market keywords."""
    market_kw = any(kw in text for kw in [
        "股", "股价", "股票", "上市", "涨停", "跌停", "A股", "港股",
        "沪市", "深市", "北交所", "科创板", "主板", "创业板", "指数",
    ])
    return market_kw


# ── Impact Assessment ────────────────────────────────────────────────────────
def assess_impact(title: str, summary: str = "") -> tuple[str, list[str]]:
    """
    Assess news impact level and affected sectors.
    Returns (impact_level, sector_keywords_found).
    """
    text = (str(title) + " " + str(summary)).lower()

    critical_kw = ["央行", "降息", "加息", "万亿", "救市", "制裁", "贸易战",
                   "黑天鹅", "清仓", "退市", "暂停上市", "处罚", "调查"]
    high_kw = ["政策", "监管", "业绩", "预增", "预亏", "回购", "分红",
               "华为", "特斯拉", "苹果", "宁德", "比亚迪", "茅台", "鹅",
               "降准", "宽松", "缩表", "科创板", "创业板", "北交所"]
    medium_kw = ["行业", "板块", "景气", "产业链", "涨价", "产能", "出货"]

    crit_count = sum(1 for kw in critical_kw if kw in text)
    high_count = sum(1 for kw in high_kw if kw in text)
    med_count = sum(1 for kw in medium_kw if kw in text)

    if crit_count >= 2 or (crit_count >= 1 and high_count >= 2):
        level = "CRITICAL"
    elif high_count >= 2:
        level = "HIGH"
    elif high_count >= 1 or med_count >= 2:
        level = "MEDIUM"
    else:
        level = "LOW"

    # Identify sectors
    sector_map = {
        "新能源": ["新能源", "锂电", "光伏", "储能", "电动车", "电车"],
        "半导体": ["半导体", "芯片", "集成电路", "晶圆", "光刻"],
        "医药": ["医药", "疫苗", "医疗器械", "中药", "创新药"],
        "消费": ["消费", "白酒", "食品", "家电", "零售"],
        "金融": ["银行", "保险", "券商", "信托", "金融"],
        "地产": ["房地产", "地产", "万科", "恒大", "碧桂园", "房价"],
        "科技": ["科技", "人工智能", "AI", "互联网", "软件", "云计算"],
        "军工": ["军工", "国防", "航天", "航空", "船舶"],
        "农业": ["农业", "种植", "养殖", "粮食", "猪周期"],
        "基建": ["基建", "建筑", "水泥", "钢铁", "工程机械"],
    }
    found = [sector for sector, kws in sector_map.items() if any(kw in text for kw in kws)]
    return level, found


# ── News Type Classification ────────────────────────────────────────────────
def classify_news_type(title: str, summary: str = "") -> str:
    """Classify news into one of: MACRO/INDUSTRY/COMPANY/MARKET/TECH/POLICY/INTERNATIONAL"""
    text = (str(title) + " " + str(summary)).lower()

    if any(k in text for k in ["政策", "央行", "证监会", "银保监", "财政部", "国务院", "监管", "法规", "意见", "通知"]):
        return "POLICY"
    if any(k in text for k in ["美联储", "欧洲", "美股", "港股", "英国", "日本", "德国", "中美", "G20", "OPEC"]):
        return "INTERNATIONAL"
    if any(k in text for k in ["降息", "加息", "降准", "CPI", "GDP", "PMI", "LPR", "社融", "M2", "宏观", "经济"]):
        return "MACRO"
    if any(k in text for k in ["AI", "人工智能", "ChatGPT", "OpenAI", "算力", "大模型", "芯片", "半导体"]):
        return "TECH"
    if any(k in text for k in ["板块", "行业", "产业", "产业链", "景气"]):
        return "INDUSTRY"
    if any(k in text for k in ["涨", "跌", "大盘", "指数", "收盘", "开盘", "成交额", "放量"]):
        return "MARKET"
    return "COMPANY"


# ── Eastmoney Fetcher ───────────────────────────────────────────────────────
def fetch_eastmoney_news(limit: int = 20, hours: int = 24) -> list[dict]:
    """Fetch latest market news from Eastmoney news API."""
    # Eastmoney latest news API
    url = (
        "https://np-listapi.eastmoney.com/comm/web/getNPList"
        "?client=web&b斓Type=0&startTime=&endTime=&fields=datetime,Title,ccode,"
        "Content,url,imageurls,level&pageSize=50&pageIndex=1&isCrawling=1"
        "&orderby=datetime&order=desc"
    )
    # Also try the news list API
    url2 = (
        "https://newsapi.eastmoney.com/kuaixun/v1/getlist_112_"
        "ajaxResult_20_1_.html"
    )
    news_list = []

    # Try Eastmoney stock news feed
    feeds = [
        "https://push2.eastmoney.com/api/qt/clist/get?cb=jQuery&pn=1&pz=20&po=1&np=1"
        "&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:13,"
        "m:0+t:80,m:1+t:2,m:1+t:23,m:1+t:A01H02E8,m:0+t:81+s:2048&fields=f1,f2,f3,f4,f5,"
        "f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,"
        "f128,f136,f115,f152&_=1",
    ]

    for feed_url in feeds:
        raw = _http_get(feed_url, timeout=8)
        if raw:
            try:
                text = raw.decode("utf-8", errors="ignore")
                # Try to extract JSON
                m = re.search(r'\{.*\}', text, re.DOTALL)
                if m:
                    data = json.loads(m.group())
                    items = data.get("data", {}).get("diff", [])
                    for item in items[:limit]:
                        title = item.get("f14", "") or item.get("title", "")
                        if not title:
                            continue
                        news_list.append({
                            "title": title,
                            "summary": item.get("f13", "") or "",
                            "source": "Eastmoney",
                            "url": f"https://guba.eastmoney.com/news,{item.get('f12','')},1.html",
                            "publish_date": datetime.fromtimestamp(
                                item.get("f3", 0) / 1000
                            ) if item.get("f3") else datetime.now(),
                            "news_type": "MARKET",
                        })
            except Exception as e:
                logger.debug(f"Eastmoney parse error: {e}")

    # Also try a simpler approach: fetch recent news from a known endpoint
    if not news_list:
        simple_url = "https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_MUTUAL_FUND_NET&columns=ALL&pageNumber=1&pageSize=5"
        raw = _http_get(simple_url, timeout=8)
        if raw:
            try:
                data = json.loads(raw.decode("utf-8", errors="ignore"))
                logger.debug(f"Eastmoney data: {str(data)[:200]}")
            except Exception as e:
                logger.debug(f"Eastmoney fallback error: {e}")

    logger.info(f"Eastmoney fetched {len(news_list)} items")
    return news_list


def fetch_eastmoney_policy(limit: int = 10) -> list[dict]:
    """Fetch latest policy documents from Eastmoney."""
    policies = []
    # Try fetching from Eastmoney policy center
    url = (
        "https://www.eastmoney.com/search.html?mode=news&type=policy"
    )
    # Use a known policy API endpoint
    policy_url = (
        "https://np-anotice-stock.eastmoney.com/api/security/ann"
        "?cb=&sr=-1&page_size=20&page_index=1&ann_type=SHA,CYB,SZA,BJA,SHS"
        "&client_source=web&stock=&keyword="
    )
    raw = _http_get(policy_url, timeout=8)
    if raw:
        try:
            data = json.loads(raw.decode("utf-8", errors="ignore"))
            notices = data.get("data", {}).get("list", [])
            for item in notices[:limit]:
                title = item.get("title", "")
                if not title:
                    continue
                publish_str = item.get("notice_date", "")
                try:
                    publish_date = datetime.strptime(publish_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    publish_date = datetime.now()
                policies.append({
                    "doc_title": title,
                    "issuing_org": item.get("org_name", "东方财富"),
                    "doc_level": "MINISTRY",
                    "doc_type": _classify_doc_type(title),
                    "content_summary": item.get("summary", "") or item.get("title", ""),
                    "url": item.get("art_url", ""),
                    "effective_date": None,
                    "related_sectors": [],
                    "stock_impact": "UNKNOWN",
                    "market_sentiment": "NEUTRAL",
                    "keywords": [],
                    "publish_date": publish_date.date(),
                })
        except Exception as e:
            logger.debug(f"Eastmoney policy parse error: {e}")

    logger.info(f"Eastmoney policy fetched {len(policies)} items")
    return policies


def _classify_doc_type(title: str) -> str:
    t = title.lower()
    if "规定" in title or "办法" in title:
        return "REGULATION"
    if "通知" in title:
        return "NOTICE"
    if "意见" in title:
        return "OPINION"
    if "决定" in title:
        return "RULE"
    if "标准" in title:
        return "STANDARD"
    if "法律" in title or "法" in title:
        return "LAW"
    if "指南" in title or "指引" in title:
        return "GUIDANCE"
    return "NOTICE"


# ── Sina Fetcher ────────────────────────────────────────────────────────────
def fetch_sina_news(limit: int = 20, hours: int = 24) -> list[dict]:
    """Fetch latest market news from Sina Finance API."""
    news_list = []

    # Sina finance news API
    urls = [
        ("https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num=20&page=1",
         "Sina_A股"),
        ("https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=1686&k=&num=20&page=1",
         "Sina_财经"),
        ("https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2517&k=&num=20&page=1",
         "Sina_宏观"),
    ]

    for url, source_label in urls:
        raw = _http_get(url, timeout=8)
        if not raw:
            continue
        try:
            data = json.loads(raw.decode("utf-8", errors="ignore"))
            items = data.get("result", {}).get("data", [])
            for item in items[:limit]:
                title = item.get("title", "")
                if not title:
                    continue
                ctime = item.get("ctime", "")
                try:
                    publish_date = datetime.strptime(ctime, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    publish_date = datetime.now()

                news_list.append({
                    "title": title,
                    "summary": item.get("intro", "") or "",
                    "source": source_label.split("_")[0],
                    "url": item.get("url", ""),
                    "publish_date": publish_date,
                    "news_type": classify_news_type(title, item.get("intro", "")),
                })
        except Exception as e:
            logger.debug(f"Sina parse error ({source_label}): {e}")

    logger.info(f"Sina fetched {len(news_list)} items")
    return news_list


def fetch_sina_policy(limit: int = 10) -> list[dict]:
    """Fetch policy documents from Sina finance."""
    policies = []
    # Sina policy/news - try their regulatory feed
    url = "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2166&k=&num=20&page=1"
    raw = _http_get(url, timeout=8)
    if raw:
        try:
            data = json.loads(raw.decode("utf-8", errors="ignore"))
            items = data.get("result", {}).get("data", [])
            for item in items[:limit]:
                title = item.get("title", "")
                if not title:
                    continue
                ctime = item.get("ctime", "")
                try:
                    publish_date = datetime.strptime(ctime, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    publish_date = datetime.now()

                # Only include policy-like content
                if not any(k in title for k in ["部", "委", "局", "通知", "规定", "意见", "公告", "政策"]):
                    continue

                policies.append({
                    "doc_title": title,
                    "issuing_org": _extract_issuer(title),
                    "doc_level": "CENTRAL",
                    "doc_type": _classify_doc_type(title),
                    "content_summary": item.get("intro", "") or title,
                    "url": item.get("url", ""),
                    "effective_date": None,
                    "related_sectors": [],
                    "stock_impact": "UNKNOWN",
                    "market_sentiment": "NEUTRAL",
                    "keywords": [],
                    "publish_date": publish_date.date(),
                })
        except Exception as e:
            logger.debug(f"Sina policy parse error: {e}")
    logger.info(f"Sina policy fetched {len(policies)} items")
    return policies


def _extract_issuer(title: str) -> str:
    """Try to extract issuing organization from title."""
    # Pattern: "XX部/委/局：XXX"
    m = re.search(r'([\u4e00-\u9fa5]{2,10}(?:部|委|局|办|总署))', title)
    if m:
        return m.group(1)
    issuers = {
        "证监会": "证监会", "银保监": "银保监会", "央行": "央行",
        "财政部": "财政部", "发改委": "发改委", "工信部": "工信部",
        "商务部": "商务部", "住建部": "住建部", "自然资源部": "自然资源部",
    }
    for kw, org in issuers.items():
        if kw in title:
            return org
    return "Unknown"


# ── Database Operations ──────────────────────────────────────────────────────
def _get_pymysql_conn():
    import pymysql
    return pymysql.connect(**DB_KWARGS)


def _ensure_tables():
    """Create q_market_news and q_policy_doc if they don't exist."""
    conn = _get_pymysql_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS q_market_news (
                id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                title           VARCHAR(500) NOT NULL,
                content_summary VARCHAR(2000) DEFAULT NULL,
                content_full    TEXT DEFAULT NULL,
                source          VARCHAR(50) NOT NULL,
                url             VARCHAR(1000) DEFAULT NULL,
                news_type       VARCHAR(20) NOT NULL,
                related_symbols JSON DEFAULT NULL,
                related_sectors JSON DEFAULT NULL,
                related_indices JSON DEFAULT NULL,
                sentiment_score DECIMAL(5,4) DEFAULT NULL,
                sentiment_label VARCHAR(10) DEFAULT NULL,
                sentiment_conf  DECIMAL(5,2) DEFAULT NULL,
                impact_level    VARCHAR(10) DEFAULT 'LOW',
                impact_sectors  JSON DEFAULT NULL,
                market_reaction VARCHAR(50) DEFAULT NULL,
                publish_date    DATETIME NOT NULL,
                crawl_date      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                KEY ix_publish (publish_date),
                KEY ix_type (news_type),
                KEY ix_sentiment (sentiment_score),
                KEY ix_impact (impact_level)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='市场新闻'
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS q_policy_doc (
                id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                doc_title       VARCHAR(500) NOT NULL,
                doc_number      VARCHAR(100) DEFAULT NULL,
                issuing_org     VARCHAR(100) NOT NULL,
                doc_level       VARCHAR(20) NOT NULL,
                doc_type        VARCHAR(30) NOT NULL,
                content_summary VARCHAR(3000) DEFAULT NULL,
                content_full    LONGTEXT DEFAULT NULL,
                url             VARCHAR(1000) DEFAULT NULL,
                attachment_url  VARCHAR(1000) DEFAULT NULL,
                effective_date  DATE DEFAULT NULL,
                related_sectors JSON DEFAULT NULL,
                related_markets JSON DEFAULT NULL,
                impact_assessment VARCHAR(2000) DEFAULT NULL,
                stock_impact    VARCHAR(20) DEFAULT 'UNKNOWN',
                sector_impact   JSON DEFAULT NULL,
                market_sentiment VARCHAR(10) DEFAULT 'NEUTRAL',
                investor_confidence VARCHAR(10) DEFAULT 'UNCHANGED',
                keywords        JSON DEFAULT NULL,
                publish_date    DATE NOT NULL,
                crawl_date      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                KEY ix_publish (publish_date),
                KEY ix_level (doc_level),
                KEY ix_effective (effective_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='政策文件'
        """)
        conn.commit()
        logger.info("Tables q_market_news and q_policy_doc verified/created")
    finally:
        cur.close()
        conn.close()


def _is_duplicate(title: str, publish_date: datetime, table: str) -> bool:
    """Check if news/policy with same title+date already exists."""
    col = "doc_title" if table == "q_policy_doc" else "title"
    conn = _get_pymysql_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT id FROM {table} WHERE {col}=%s AND publish_date=%s LIMIT 1",
            (title, publish_date)
        )
        return cur.fetchone() is not None
    finally:
        cur.close()
        conn.close()


def insert_market_news(news_list: list[dict], dry_run: bool = False) -> int:
    """Insert market news records, return count of inserted rows."""
    if not news_list:
        return 0
    import pymysql

    inserted = 0
    conn = _get_pymysql_conn()
    cur = conn.cursor()
    try:
        for item in news_list:
            title = item["title"]
            pub_date = item["publish_date"]
            if _is_duplicate(title, pub_date, "q_market_news"):
                logger.debug(f"Skipping duplicate: {title[:50]}")
                continue

            sentiment_score, sentiment_label, sentiment_conf = analyze_sentiment(
                title, item.get("summary", ""))
            impact_level, sectors = assess_impact(title, item.get("summary", ""))
            related_symbols = identify_related_stocks(title, item.get("summary", ""))
            news_type = item.get("news_type") or classify_news_type(title, item.get("summary", ""))

            if dry_run:
                logger.info(f"[DRY RUN] Would insert: {title[:60]} | "
                            f"sentiment={sentiment_label}({sentiment_score:.2f}) | "
                            f"symbols={related_symbols}")
                inserted += 1
                continue

            cur.execute("""
                INSERT INTO q_market_news (
                    title, content_summary, source, url, news_type,
                    related_symbols, related_sectors,
                    sentiment_score, sentiment_label, sentiment_conf,
                    impact_level, impact_sectors,
                    publish_date, crawl_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                title,
                item.get("summary", ""),
                item.get("source", "Unknown"),
                item.get("url", ""),
                news_type,
                json.dumps(related_symbols, ensure_ascii=False),
                json.dumps(sectors, ensure_ascii=False),
                sentiment_score,
                sentiment_label,
                sentiment_conf,
                impact_level,
                json.dumps(sectors, ensure_ascii=False),
                pub_date,
                datetime.now(),
            ))
            inserted += 1
        conn.commit()
    finally:
        cur.close()
        conn.close()

    logger.info(f"Inserted {inserted} market news records")
    return inserted


def insert_policy_docs(policy_list: list[dict], dry_run: bool = False) -> int:
    """Insert policy document records, return count of inserted rows."""
    if not policy_list:
        return 0
    import pymysql

    inserted = 0
    conn = _get_pymysql_conn()
    cur = conn.cursor()
    try:
        for item in policy_list:
            title = item["doc_title"]
            pub_date = item.get("publish_date", date.today())
            if _is_duplicate(title, datetime.combine(pub_date, datetime.min.time()), "q_policy_doc"):
                logger.debug(f"Skipping duplicate policy: {title[:50]}")
                continue

            if dry_run:
                logger.info(f"[DRY RUN] Would insert policy: {title[:60]}")
                inserted += 1
                continue

            cur.execute("""
                INSERT INTO q_policy_doc (
                    doc_title, issuing_org, doc_level, doc_type,
                    content_summary, url, effective_date,
                    related_sectors, stock_impact, market_sentiment,
                    keywords, publish_date, crawl_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                title,
                item.get("issuing_org", "Unknown"),
                item.get("doc_level", "CENTRAL"),
                item.get("doc_type", "NOTICE"),
                item.get("content_summary", ""),
                item.get("url", ""),
                item.get("effective_date"),
                json.dumps(item.get("related_sectors", []), ensure_ascii=False),
                item.get("stock_impact", "UNKNOWN"),
                item.get("market_sentiment", "NEUTRAL"),
                json.dumps(item.get("keywords", []), ensure_ascii=False),
                pub_date,
                datetime.now(),
            ))
            inserted += 1
        conn.commit()
    finally:
        cur.close()
        conn.close()

    logger.info(f"Inserted {inserted} policy doc records")
    return inserted


# ── Main Orchestration ───────────────────────────────────────────────────────
def run(sources: list[str], limit: int, dry_run: bool):
    """Collect news from all specified sources and write to DB."""
    total_news = 0
    total_policy = 0

    if "eastmoney" in sources:
        news = fetch_eastmoney_news(limit=limit)
        for n in news:
            n["news_type"] = classify_news_type(n["title"], n.get("summary", ""))
        total_news += insert_market_news(news, dry_run=dry_run)

        policy = fetch_eastmoney_policy(limit=min(limit, 10))
        total_policy += insert_policy_docs(policy, dry_run=dry_run)

    if "sina" in sources:
        news = fetch_sina_news(limit=limit)
        total_news += insert_market_news(news, dry_run=dry_run)

        policy = fetch_sina_policy(limit=min(limit, 10))
        total_policy += insert_policy_docs(policy, dry_run=dry_run)

    logger.info(f"=== Collection complete ===")
    logger.info(f"  Market news inserted : {total_news}")
    logger.info(f"  Policy docs inserted : {total_policy}")
    return total_news, total_policy


# ── CLI Entry Point ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="QuantOS News Collector")
    parser.add_argument("--limit", type=int, default=20,
                        help="Max items per source (default: 20)")
    parser.add_argument("--sources", type=str, default="eastmoney,sina",
                        help="Comma-separated sources: eastmoney,sina (default: both)")
    parser.add_argument("--hours", type=int, default=24,
                        help="News age window in hours (default: 24)")
    parser.add_argument("--test", action="store_true",
                        help="Dry-run: show what would be inserted without writing to DB")
    args = parser.parse_args()

    sources = [s.strip().lower() for s in args.sources.split(",")]
    for s in sources:
        if s not in ("eastmoney", "sina"):
            parser.error(f"Unknown source: {s}. Valid: eastmoney, sina")

    logger.info(f"Starting news collection — sources={sources}, limit={args.limit}, "
                f"dry_run={args.test}")

    # Ensure tables exist
    if not args.test:
        _ensure_tables()

    # Load stock mappings for related-stock identification
    load_stock_mappings()
    logger.info(f"Loaded {len(_stock_name_map)} stock name mappings")

    run(sources=sources, limit=args.limit, dry_run=args.test)


if __name__ == "__main__":
    main()

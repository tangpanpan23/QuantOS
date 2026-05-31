# -*- coding: utf-8 -*-
"""
全市场股票基本面数据采集脚本
从 cninfo（中证信息）和 AkShare 拉取财务/公司信息，
批量写入 q_stock_pool 表的 19 个基本面字段。

数据源：
1. stock_profile_cninfo        — 公司基本信息（上市日期/法人/注册资金/主营/简介）
2. stock_financial_analysis_indicator  — 财务指标（EPS/BVPS/ROE/毛利率/净利率/股息率）
3. stock_zh_a_daily (sina)      — 最新价格（计算市值/PE/PB）

用法：
    cd /Users/tank/Code/QuantOS/quantos/scripts
    python3 -m db.fundamental_collector --all       # 全量采集
    python3 -m db.fundamental_collector --watched   # 仅 Tank 自选股
    python3 -m db.fundamental_collector --symbol 600036  # 单只
"""
import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# 清除代理
for _k in list(os.environ.keys()):
    if "proxy" in _k.lower():
        del os.environ[_k]

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fundamental")


def _safe_float(val):
    """安全转换为浮点数"""
    if val is None or str(val) in ("nan", "None", ""):
        return None
    try:
        return float(val)
    except Exception:
        return None

# ──────────── 线程安全计数器 ────────────
_counter_lock = Lock()
_done = 0
_total = 0


def _progress(done, total):
    bar_len = 30
    pct = done / total * 100 if total else 0
    filled = int(bar_len * done // total) if total else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    sys.stdout.write(f"\r  {bar} {done}/{total} ({pct:.1f}%)  ")
    sys.stdout.flush()


def _calc_risk(industry: str, roe: float, gross_margin: float, net_margin: float,
               listing_years: int, pb: float, pe: float) -> tuple[int, str]:
    """计算风险等级 1-5 和风险因素描述"""
    score = 0
    factors = []

    # 1. 行业风险（板块特性）
    high_risk_industries = ["证券", "多元金融", "军工", "军工装备", "军工电子",
                             "化学原料", "化学制品", "钢铁", "煤炭开采", "煤炭",
                             "房地产", "石油", "油气开采"]
    low_risk_industries = ["银行", "电力", "水务", "燃气", "港口航运",
                            "公路铁路", "白酒", "中药"]

    if industry in high_risk_industries:
        score += 2
        factors.append("强周期行业")
    elif industry in low_risk_industries:
        score -= 1
        factors.append("防御性行业")
    elif "科创板" == industry or "创业板" == industry:
        score += 1
        factors.append("注册制板块")

    # 2. 财务质量
    if roe and roe > 15:
        score -= 1
        factors.append("高ROE")
    elif roe and roe < 5:
        score += 1
        factors.append("低ROE")

    if gross_margin and gross_margin < 20:
        score += 1
        factors.append("低毛利率")

    if net_margin and net_margin < 5:
        score += 1
        factors.append("低净利率")

    # 3. 估值风险
    if pb and pb > 5:
        score += 1
        factors.append("高PB")
    if pe and pe > 50:
        score += 1
        factors.append("高PE")
    elif pe and pe < 0:
        score += 2
        factors.append("亏损(PE<0)")

    # 4. 上市时间（次新股风险）
    if listing_years < 2:
        score += 2
        factors.append("次新股")
    elif listing_years > 20:
        score -= 1
        factors.append("老牌企业")

    # 5. 特殊处理
    if industry in ["综合"]:
        score += 1
        factors.append("业务多元难评估")

    # 最终等级：score 越小越安全
    level = max(1, min(5, 3 + score))
    return level, "/".join(factors[:3]) if factors else "基本面正常"


def _fetch_fundamental(symbol: str) -> dict:
    """获取单只股票的基本面数据，返回字段字典"""
    result = {
        "listing_date": None, "legal_rep": None, "registered_capital": None,
        "total_shares": None, "main_business": None, "company_intro": None,
        "eps": None, "book_value": None, "roe": None,
        "gross_margin": None, "net_margin": None, "dividend_yield": None,
        "pe_ratio": None, "pb_ratio": None, "market_cap": None,
        "fin_update_date": None,
    }
    try:
        import akshare as ak

        # ── 1. 公司基本信息（cninfo）─────────────────────────────
        try:
            prof = ak.stock_profile_cninfo(symbol=symbol)
            if prof is not None and not prof.empty:
                row = prof.iloc[0]
                result["listing_date"] = str(row.get("上市日期", "") or "")[:10] or None
                result["legal_rep"] = str(row.get("法人代表", "") or "")[:100] or None
                cap = row.get("注册资金", None)
                if cap is not None and str(cap) not in ("nan", ""):
                    result["registered_capital"] = str(cap)
                result["main_business"] = str(row.get("主营业务", "") or "")[:1000] or None
                result["company_intro"] = str(row.get("机构简介", "") or "")[:2000] or None
        except Exception as e:
            logger.debug(f"profile {symbol}: {e}")

        # ── 2. 财务数据：新浪利润表 + 资产负债表（cninfo财务指标被封时降级） ──
        # 尝试 cninfo 财务指标（只有部分股票有数据）
        try:
            fin = ak.stock_financial_analysis_indicator(symbol=symbol)
            if fin is not None and not fin.empty:
                latest = fin.iloc[-1]
                result["fin_update_date"] = str(latest.get("日期", "") or "")[:10] or None
                def _v(col):
                    val = latest.get(col, None)
                    if val is not None and str(val) not in ("nan", ""):
                        try:
                            return float(val)
                        except Exception:
                            return None
                    return None
                result["eps"] = _v("摊薄每股收益(元)")
                result["book_value"] = _v("每股净资产_调整前(元)")
                result["roe"] = _v("净资产收益率(%)")
                result["gross_margin"] = _v("销售毛利率(%)")
                result["net_margin"] = _v("销售净利率(%)")
                result["dividend_yield"] = _v("股息发放率(%)")
        except Exception:
            pass

        # cninfo 无数据时，降级用新浪利润表计算
        if result["fin_update_date"] is None:
            try:
                profit_df = ak.stock_financial_report_sina(stock=symbol, symbol="利润表")
                if profit_df is not None and not profit_df.empty:
                    latest = profit_df.iloc[0]  # 第一行是最新的
                    result["fin_update_date"] = str(latest.get("报告日", ""))[:10] or None

                    # 基本每股收益
                    eps = latest.get("基本每股收益") or latest.get("基本每股收益")
                    if eps is not None:
                        try:
                            result["eps"] = float(eps)
                        except Exception:
                            pass

                    # 毛利率 = (营收 - 营业成本) / 营收
                    revenue = _safe_float(latest.get("营业收入") or latest.get("营业总收入"))
                    cost = _safe_float(latest.get("营业成本"))
                    if revenue and cost and revenue > 0:
                        result["gross_margin"] = round((revenue - cost) / revenue * 100, 4)

                    # 净利率 = 净利润 / 营收
                    net_profit = _safe_float(latest.get("净利润") or latest.get("归属于母公司所有者的净利润"))
                    if net_profit and revenue and revenue > 0:
                        result["net_margin"] = round(net_profit / revenue * 100, 4)

                    # ROE = 归属净利润 / 股东权益（从资产负债表）
                    if net_profit:
                        try:
                            bal_df = ak.stock_financial_report_sina(stock=symbol, symbol="资产负债表")
                            if bal_df is not None and not bal_df.empty:
                                bal_latest = bal_df.iloc[0]
                                equity = _safe_float(
                                    bal_latest.get("归属于母公司股东权益合计")
                                    or bal_latest.get("所有者权益(或股东权益)合计")
                                )
                                if equity and equity > 0:
                                    result["roe"] = round(net_profit / equity * 100, 4)
                                    # BVPS = 股东权益 / 总股本（万股）
                                    shares = result.get("total_shares")
                                    if shares and shares > 0:
                                        result["book_value"] = round(equity / shares / 10000, 4)  # 万元/万股->元
                        except Exception:
                            pass
            except Exception:
                pass

        # ── 3. 最新股价（市值/PE/PB）───────────────────────────
        try:
            # 用新浪日线接口取最新收盘价
            sina_sym = f"sh{symbol}" if symbol.startswith(("6", "9", "5", "7")) else f"sz{symbol}"
            price_df = ak.stock_zh_a_daily(symbol=sina_sym, adjust="qfq")
            if price_df is not None and not price_df.empty:
                latest_row = price_df.iloc[-1]
                close = float(latest_row.get("close", 0))
                # 总股本（万股）从 share_change 取最新一期
                try:
                    share_df = ak.stock_share_change_cninfo(symbol=symbol)
                    if share_df is not None and not share_df.empty:
                        latest_share = share_df.iloc[-1]
                        total = latest_share.get("总股本", None)
                        if total and str(total) not in ("nan", ""):
                            total_wk = float(total)
                            result["total_shares"] = total_wk
                            # 市值(亿元) = 收盘价 × 总股本(万股) / 10000
                            if close > 0 and total_wk > 0:
                                result["market_cap"] = round(close * total_wk / 10000, 2)
                                # PE = 收盘价 / EPS
                                if result["eps"] and result["eps"] > 0:
                                    result["pe_ratio"] = round(close / result["eps"], 2)
                                # PB = 收盘价 / BVPS
                                if result["book_value"] and result["book_value"] > 0:
                                    result["pb_ratio"] = round(close / result["book_value"], 4)
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"price {symbol}: {e}")

    except Exception as e:
        logger.debug(f"fetch {symbol}: {e}")

    return result


def _update_db(symbol: str, data: dict):
    """更新单只股票的基本面数据到数据库"""
    global _done
    from db.db_client import get_session
    from db.models import StockPoolDB
    from datetime import datetime as dt

    # 计算上市年数
    def _parse_date(val):
        """解析各种日期格式为 date 对象"""
        if not val or str(val) in ("nan", "None", ""):
            return None
        s = str(val).strip()[:10]
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                from datetime import datetime
                return datetime.strptime(s, fmt).date()
            except Exception:
                pass
        return None

    listing_years = 0
    listing_date_obj = _parse_date(data.get("listing_date"))
    if listing_date_obj:
        listing_years = (date.today() - listing_date_obj).days // 365

    # 先查出行业（避免 session detach）
    industry = ""
    with get_session() as db2:
        st = db2.query(StockPoolDB).filter(StockPoolDB.symbol == symbol).first()
        if st:
            industry = st.industry or ""

    risk_level, risk_factors = _calc_risk(
        industry=industry,
        roe=float(data["roe"]) if data.get("roe") else None,
        gross_margin=float(data["gross_margin"]) if data.get("gross_margin") else None,
        net_margin=float(data["net_margin"]) if data.get("net_margin") else None,
        listing_years=listing_years,
        pb=float(data["pb_ratio"]) if data.get("pb_ratio") else None,
        pe=float(data["pe_ratio"]) if data.get("pe_ratio") else None,
    )

    update_fields = {
        StockPoolDB.listing_date: _parse_date(data.get("listing_date")),
        StockPoolDB.legal_rep: data.get("legal_rep"),
        StockPoolDB.registered_capital: data.get("registered_capital"),
        StockPoolDB.total_shares: data.get("total_shares"),
        StockPoolDB.main_business: data.get("main_business"),
        StockPoolDB.company_intro: data.get("company_intro"),
        StockPoolDB.eps: data.get("eps"),
        StockPoolDB.book_value: data.get("book_value"),
        StockPoolDB.roe: data.get("roe"),
        StockPoolDB.gross_margin: data.get("gross_margin"),
        StockPoolDB.net_margin: data.get("net_margin"),
        StockPoolDB.dividend_yield: data.get("dividend_yield"),
        StockPoolDB.pe_ratio: data.get("pe_ratio"),
        StockPoolDB.pb_ratio: data.get("pb_ratio"),
        StockPoolDB.market_cap: data.get("market_cap"),
        StockPoolDB.risk_level: risk_level,
        StockPoolDB.risk_factors: risk_factors,
        StockPoolDB.fin_update_date: _parse_date(data.get("fin_update_date")),
        StockPoolDB.business_desc: (data.get("main_business") or "")[:200],
    }

    with get_session() as db:
        db.query(StockPoolDB).filter(
            StockPoolDB.symbol == symbol
        ).update(update_fields)
        db.commit()

    with _counter_lock:
        _done += 1
        if _total > 0:
            _progress(_done, _total)


def cmd_fetch_all(max_workers: int = 8, limit: int = 0):
    """全量采集所有股票"""
    from db.db_client import get_session
    from db.models import StockPoolDB

    with get_session() as db:
        query = db.query(StockPoolDB.symbol).filter(StockPoolDB.status == 1)
        if limit > 0:
            query = query.limit(limit)
        rows = query.all()

    symbols = [r.symbol for r in rows]
    global _done, _total
    _done = 0
    _total = len(symbols)
    logger.info(f"全量采集基本面数据，共 {len(symbols)} 只，{max_workers} 并发")

    success = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_fetch_and_update, sym): sym for sym in symbols}
        for future in as_completed(futures):
            sym = futures[future]
            try:
                data = future.result()
                if data and data.get("listing_date"):
                    success += 1
            except Exception as e:
                logger.debug(f"future error {sym}: {e}")

    print()  # 换行
    logger.info(f"采集完成: 成功 {success}/{len(symbols)} 只")
    return success, len(symbols)


def cmd_fetch_watched():
    """仅采集 Tank 自选股"""
    from db.db_client import get_session
    from db.models import StockPoolDB

    with get_session() as db:
        rows = db.query(StockPoolDB.symbol).filter(
            StockPoolDB.status == 1,
            StockPoolDB.is_watched == 1
        ).all()

    symbols = [r.symbol for r in rows]
    if not symbols:
        # fallback: Tank 默认股池
        symbols = ["600036", "600900", "601288", "601318", "000001",
                   "000858", "002475", "300750", "600028", "600519"]

    global _done, _total
    _done = 0
    _total = len(symbols)
    logger.info(f"采集 Tank 自选股基本面，共 {len(symbols)} 只")

    success = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_fetch_and_update, sym): sym for sym in symbols}
        for future in as_completed(futures):
            sym = futures[future]
            try:
                data = future.result()
                if data and data.get("listing_date"):
                    success += 1
            except Exception as e:
                logger.debug(f"{sym}: {e}")

    print()
    logger.info(f"Tank 自选股采集完成: {success}/{len(symbols)} 只")
    return success, len(symbols)


def _fetch_and_update(symbol: str) -> dict:
    """抓取并写入单只股票数据"""
    data = _fetch_fundamental(symbol)
    _update_db(symbol, data)
    return data


def cmd_fetch_symbol(symbol: str):
    """单只股票"""
    global _done, _total
    _done = 0
    _total = 1
    data = _fetch_and_update(symbol)
    print()
    if data.get("listing_date"):
        logger.info(f"  {symbol} {data.get('listing_date')} 上市，EPS={data.get('eps')} ROE={data.get('roe')}% "
                    f"市值={data.get('market_cap')}亿 PE={data.get('pe_ratio')} PB={data.get('pb_ratio')}")
    else:
        logger.warning(f"  {symbol} 未获取到数据")
    return data


def cmd_status():
    """查看采集状态"""
    from db.db_client import get_session
    from db.models import StockPoolDB
    from sqlalchemy import func

    with get_session() as db:
        total = db.query(func.count(StockPoolDB.id)).filter(StockPoolDB.status == 1).scalar()
        has_data = db.query(func.count(StockPoolDB.id)).filter(
            StockPoolDB.status == 1,
            StockPoolDB.listing_date.isnot(None)
        ).scalar()

        # 各风险等级分布
        risk_stats = db.query(
            StockPoolDB.risk_level,
            func.count(StockPoolDB.id)
        ).filter(
            StockPoolDB.status == 1,
            StockPoolDB.risk_level.isnot(None)
        ).group_by(StockPoolDB.risk_level).order_by(StockPoolDB.risk_level).all()

    print("=" * 50)
    print(f"总股票: {total}")
    print(f"已有基本面数据: {has_data} ({has_data/total*100:.1f}%)" if total else "")
    print(f"无数据: {total - has_data}")
    print(f"\n风险等级分布:")
    risk_names = {1: "极低", 2: "低风险", 3: "中等", 4: "较高", 5: "高风险"}
    for level, cnt in risk_stats:
        bar = "█" * (cnt // 30)
        print(f"  等级{level}({risk_names.get(level,''):<4}) {cnt:>5}  {bar}")
    print("=" * 50)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="基本面数据采集")
    parser.add_argument("--all", action="store_true", help="全量采集")
    parser.add_argument("--watched", action="store_true", help="Tank自选股")
    parser.add_argument("--symbol", type=str, help="单只股票代码")
    parser.add_argument("--status", action="store_true", help="查看采集状态")
    parser.add_argument("--workers", type=int, default=8, help="并发数(默认8)")
    parser.add_argument("--limit", type=int, default=0, help="限制数量(测试用)")
    args = parser.parse_args()

    if args.status:
        cmd_status()
    elif args.symbol:
        cmd_fetch_symbol(args.symbol)
    elif args.watched:
        cmd_fetch_watched()
    elif args.all:
        cmd_fetch_all(max_workers=args.workers, limit=args.limit)
    else:
        parser.print_help()

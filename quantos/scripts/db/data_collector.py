# -*- coding: utf-8 -*-
"""
数据收集器 - QuantOS 本地化数据库核心脚本

功能：
1. 收集股票基础信息（AkShare）
2. 收集日线K线 + 计算技术指标，写入数据库
3. 收集基准指数（上证/深证/创业板/沪深300）
4. Tank 股票池优先，保证每日收盘后增量更新

用法：
    cd /Users/tank/Code/QuantOS/quantos/scripts
    python3 -m db.data_collector                    # 全量更新 Tank 股票池
    python3 -m db.data_collector --symbol 600036    # 单只股票
    python3 -m db.data_collector --symbols 600036,600900   # 指定股票
    python3 -m db.data_collector --init             # 初始化（建表+默认股票池）
    python3 -m db.data_collector --status           # 查看各表数据量
    python3 -m db.data_collector --index-only        # 只更新指数
    python3 -m db.data_collector --days 365         # 拉1年历史K线
"""
import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# 确保 scripts 目录在 Python 路径
SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

# ── 日志配置 ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("collector")


# ══════════════════════════════════════════════════════
#  1. 数据库初始化
# ══════════════════════════════════════════════════════

def cmd_init():
    """初始化：建表 + 填充 Tank 默认股票池"""
    logger.info("=" * 50)
    logger.info("初始化 QuantOS 数据库...")
    logger.info("=" * 50)

    from .db_client import health_check, init_db
    from .stock_pool import init_tank_pool, add_tank_defaults

    # 健康检查
    h = health_check()
    if not h.get("ok"):
        logger.error(f"数据库连接失败: {h.get('error')}")
        logger.error("请确保 MySQL 已启动: brew services start mysql")
        sys.exit(1)
    logger.info("✓ 数据库连接正常")

    # 建表
    init_db()
    logger.info("✓ 表结构就绪")

    # 填充默认股票池
    logger.info("填充 Tank 默认股票池...")
    result = init_tank_pool()
    logger.info(f"✓ 默认股票: {result['defaults_added']} 只")
    logger.info(f"✓ AkShare 同步: {result.get('synced', {})}")
    logger.info("=" * 50)
    logger.info("初始化完成！")
    logger.info("下一步: python3 -m db.data_collector --days 365")


# ══════════════════════════════════════════════════════
#  2. 状态查看
# ══════════════════════════════════════════════════════

def cmd_status():
    """查看各表数据量"""
    from .db_client import table_stats, health_check

    h = health_check()
    print(f"\n{'='*50}")
    print(f"QuantOS 数据库状态  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")

    if not h.get("ok"):
        print(f"❌ 数据库连接失败: {h.get('error')}")
        return

    stats = table_stats()
    print(f"\n数据量统计：")
    print(f"  {'表名':<30} {'记录数':>10}")
    print(f"  {'-'*30} {'-'*10}")
    for table, count in stats.items():
        if count < 0:
            print(f"  {table:<30} {'❌ 不存在':>10}")
        else:
            print(f"  {table:<30} {count:>10,}")

    print(f"\n{'='*50}")


# ══════════════════════════════════════════════════════
#  3. K线收集
# ══════════════════════════════════════════════════════

def cmd_fetch_klines(symbols: list, days: int = 365, incremental: bool = True):
    """
    收集日线K线数据。

    参数:
        symbols: 股票代码列表
        days: 拉取多少天的历史数据
        incremental: True=增量（只拉比库里最新的日期更新的数据），False=全量
    """
    from .daily_kline import batch_upsert_klines, get_latest_date, count_klines
    from .stock_pool import get_watched_symbols
    from .technical import calc_all_indicators

    # 确定要更新的股票列表
    if not symbols:
        symbols = get_watched_symbols()
        logger.info(f"股票池: {len(symbols)} 只")

    if not symbols:
        logger.warning("没有要更新的股票，请先运行 --init 或添加股票到股票池")
        return

    total_inserted = 0
    total_updated = 0
    failed = []

    for i, symbol in enumerate(symbols):
        logger.info(f"[{i+1}/{len(symbols)}] 处理 {symbol}...")
        t0 = time.time()

        try:
            # 判断增量还是全量
            if incremental:
                latest = get_latest_date(symbol)
                if latest:
                    logger.info(f"  增量模式，已入库最新: {latest}")
                    # 不需要再拉，直接跳过
                    continue
                else:
                    # 库里没数据，拉全量
                    logger.info(f"  全量模式，库中无数据，拉取 {days} 天")
            else:
                logger.info(f"  全量模式，拉取 {days} 天")

            # 从 AkShare 拉K线
            result_fetch = _fetch_kline_from_akshare(symbol, days=days)
            if not result_fetch["klines"]:
                logger.warning(f"  无K线数据: {symbol}")
                failed.append(symbol)
                continue

            klines = result_fetch["klines"]
            name = result_fetch.get("name", symbol)

            # 写入数据库
            result = batch_upsert_klines(
                symbol=symbol,
                klines=klines,
                data_source="akshare",
                symbol_name=name,
            )
            total_inserted += result["inserted"]
            total_updated += result["updated"]
            elapsed = time.time() - t0
            logger.info(
                f"  ✓ {symbol} {name}: "
                f"+{result['inserted']} / ~{result['updated']}条 "
                f"(耗时 {elapsed:.1f}s)"
            )

        except Exception as e:
            logger.error(f"  ✗ {symbol} 失败: {e}")
            failed.append(symbol)

        # 限速：避免被 AkShare 限流
        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"K线收集完成")
    print(f"  总新增: {total_inserted} 条")
    print(f"  总更新: {total_updated} 条")
    print(f"  失败: {len(failed)} 只")
    if failed:
        print(f"  失败列表: {failed}")
    print(f"{'='*50}")


def _to_sina_symbol(symbol: str) -> str:
    """股票代码转新浪格式"""
    if symbol.startswith(("6", "9", "5", "7")):
        return f"sh{symbol}"
    return f"sz{symbol}"


def _fetch_kline_from_akshare(symbol: str, days: int = 365) -> dict:
    """从 AkShare 新浪接口拉取单只股票的日线K线（东财接口被封，降级走新浪）"""
    try:
        import akshare as ak
        import pandas as pd
        from datetime import datetime, timedelta
    except ImportError:
        logger.error("akshare 未安装: pip install akshare")
        return {"klines": [], "symbol": symbol, "name": ""}

    try:
        # 清除代理环境变量
        import os
        for _k in list(os.environ.keys()):
            if "proxy" in _k.lower():
                del os.environ[_k]

        sina_sym = _to_sina_symbol(symbol)

        # 新浪日线接口（东方财富被代理封禁后降级用）
        df = ak.stock_zh_a_daily(symbol=sina_sym, adjust="qfq")

        if df is None or df.empty:
            return {"klines": [], "symbol": symbol, "name": ""}

        # 统一列名
        df = df.reset_index()
        # 新浪原始列: date, open, high, low, close, volume, amount, outstanding_share, turnover
        rename_map = {
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
            "涨幅": "change_pct",
            "换手率": "turnover",
        }
        df = df.rename(columns=rename_map)

        # 转换日期格式
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

        # 按日期过滤（只取 days 天内的数据，减少处理量）
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        df = df[df["date"] >= cutoff]

        if df.empty:
            return {"klines": [], "symbol": symbol, "name": ""}

        # 成交额从元转为万元（与 DB 存储单位一致）
        if "amount" in df.columns:
            df["amount"] = df["amount"] / 10000.0

        # 涨跌额转涨跌幅（新浪原始数据是涨跌额，不是涨跌幅）
        if "涨跌幅" in df.columns:
            df["change_pct"] = df["涨跌幅"] * 100  # 新浪原始是小数，转为%
        elif "change" in df.columns and "close" in df.columns:
            prev = df["close"].shift(1)
            df["change_pct"] = (df["close"] - prev) / prev * 100

        # 股票名称（从第一行读）
        name = ""
        if "symbol" in df.columns and df["symbol"].iloc[0]:
            name = str(df["symbol"].iloc[0])
        elif len(df) > 0:
            name = ""

        klines = []
        for _, row in df.iterrows():
            try:
                klines.append({
                    "date":       str(row.get("date", ""))[:10],
                    "open":       float(row.get("open", 0) or 0),
                    "high":       float(row.get("high", 0) or 0),
                    "low":        float(row.get("low", 0) or 0),
                    "close":      float(row.get("close", 0) or 0),
                    "volume":     int(row.get("volume", 0) or 0),
                    "amount":     float(row.get("amount", 0) or 0),
                    "change_pct": float(row.get("change_pct", 0) or 0),
                    "turnover":   float(row.get("turnover", 0) or 0),
                })
            except Exception:
                continue

        return {"klines": klines, "symbol": symbol, "name": name}

    except Exception as e:
        logger.error(f"  AkShare fetch failed for {symbol}: {e}")
        return {"klines": [], "symbol": symbol, "name": ""}


# ══════════════════════════════════════════════════════
#  4. 指数收集
# ══════════════════════════════════════════════════════

def cmd_fetch_indices():
    """收集基准指数数据"""
    from .benchmark import batch_upsert_indices, BENCHMARK_INDICES

    logger.info(f"收集 {len(BENCHMARK_INDICES)} 个基准指数...")

    for idx in BENCHMARK_INDICES:
        code = idx["code"]
        name = idx["name"]
        logger.info(f"  {code} {name}...")

        try:
            result = _fetch_index_from_akshare(code, name)
            if result.get("klines"):
                r = batch_upsert_indices(
                    index_code=code,
                    index_name=name,
                    klines=result["klines"],
                    data_source="akshare",
                )
                logger.info(f"    ✓ +{r['inserted']} 条")
            else:
                logger.warning(f"    无数据")
        except Exception as e:
            logger.error(f"    ✗ {e}")

        time.sleep(0.3)

    print(f"\n基准指数收集完成！")


def _fetch_index_from_akshare(index_code: str, index_name: str) -> dict:
    """从 AkShare 拉取指数K线"""
    try:
        import akshare as ak
        from datetime import datetime, timedelta
    except ImportError:
        return {"klines": []}

    try:
        # 清除代理环境变量（避免东方财富被拦截）
        for _k in list(os.environ.keys()):
            if "proxy" in _k.lower():
                del os.environ[_k]

        end = datetime.now()
        start = end - timedelta(days=365)

        # 上证指数用 sh000001，深证用 sz399001
        symbol_map = {
            "000001": ("sh000001", "index"),
            "399001": ("sz399001", "index"),
            "399006": ("sz399006", "index"),
            "000300": ("sh000300", "index"),
            "000016": ("sh000016", "index"),
            "000905": ("sh000905", "index"),
        }

        ak_symbol, _ = symbol_map.get(index_code, (f"sh{index_code}", "index"))

        # 新浪指数历史（东方财富接口被封，降级走新浪）
        df = ak.stock_zh_index_daily(symbol=ak_symbol)

        if df is None or df.empty:
            return {"klines": []}

        # 过滤日期范围（stock_zh_index_daily 返回的 date 列是 date 对象）
        import pandas as pd
        cutoff = pd.Timestamp(start).date()
        df = df[df["date"] >= cutoff]

        klines = []
        for _, row in df.iterrows():
            try:
                klines.append({
                    "date": str(row.get("date", ""))[:10],
                    "open": float(row.get("open", 0) or 0),
                    "high": float(row.get("high", 0) or 0),
                    "low": float(row.get("low", 0) or 0),
                    "close": float(row.get("close", 0) or 0),
                    "volume": int(row.get("volume", 0) or 0),
                })
            except Exception:
                continue

        return {"klines": klines}

    except Exception as e:
        logger.warning(f"指数 {index_code} fetch failed: {e}")
        return {"klines": []}


# ══════════════════════════════════════════════════════
#  5. 全量更新（每日定时任务用）
# ══════════════════════════════════════════════════════

def cmd_daily_update(days: int = 30):
    """
    每日收盘后执行的全量更新：
    1. 更新 Tank 股票池 K线
    2. 更新基准指数
    """
    from .stock_pool import get_watched_symbols

    logger.info("=" * 50)
    logger.info(f"每日更新 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info("=" * 50)

    # 1. 更新指数
    logger.info("\n[1/2] 更新基准指数...")
    cmd_fetch_indices()

    # 2. 更新 K 线
    symbols = get_watched_symbols()
    logger.info(f"\n[2/2] 更新 {len(symbols)} 只股票K线...")
    cmd_fetch_klines(symbols, days=days, incremental=True)

    logger.info("\n" + "=" * 50)
    logger.info("每日更新完成！")
    logger.info("=" * 50)


# ══════════════════════════════════════════════════════
#  6. 本地查询接口（供 Go/其他脚本调用）
# ══════════════════════════════════════════════════════

def query_klines(symbol: str, days: int = 60) -> list:
    """查询本地K线（带指标），返回 JSON 列表"""
    from .daily_kline import get_klines
    klines = get_klines(symbol, limit=days)
    return klines


def query_indicators(symbol: str, date: str = "") -> dict:
    """查询某只股票最新的技术指标"""
    from .daily_kline import get_klines
    klines = get_klines(symbol, limit=100)
    if not klines:
        return {}
    k = klines[-1]
    return {
        "symbol": symbol,
        "date": k["trade_date"],
        "close": k["close"],
        "ma5": k.get("ma5"), "ma20": k.get("ma20"), "ma60": k.get("ma60"),
        "rsi6": k.get("rsi6"), "rsi12": k.get("rsi12"),
        "macd_dif": k.get("macd_dif"), "macd_dea": k.get("macd_dea"),
        "boll_upper": k.get("boll_upper"), "boll_mid": k.get("boll_mid"),
        "boll_lower": k.get("boll_lower"),
    }


# ══════════════════════════════════════════════════════
#  CLI 入口
# ══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="QuantOS 数据收集器 - 本地化股票数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--init", action="store_true", help="初始化数据库（建表+默认股票池）")
    parser.add_argument("--status", action="store_true", help="查看各表数据量")
    parser.add_argument("--symbol", type=str, help="指定单个股票代码")
    parser.add_argument("--symbols", type=str, help="指定股票代码列表（逗号分隔）")
    parser.add_argument("--days", type=int, default=365, help="拉取历史天数（默认365）")
    parser.add_argument("--incremental", action="store_true", default=True, help="增量更新（默认开启）")
    parser.add_argument("--full", action="store_true", help="全量更新（覆盖已有数据）")
    parser.add_argument("--index-only", action="store_true", help="只更新基准指数")
    parser.add_argument("--daily", action="store_true", help="每日定时更新（K线+指数）")
    parser.add_argument("--query", type=str, metavar="SYMBOL", help="查询某只股票本地K线（返回JSON）")
    parser.add_argument("--indicators", type=str, metavar="SYMBOL", help="查询某只股票最新技术指标")
    parser.add_argument("--watched", action="store_true", help="查看股票池列表")
    args = parser.parse_args()

    # 初始化
    if args.init:
        cmd_init()
        return

    # 状态
    if args.status:
        cmd_status()
        return

    # 查股票池
    if args.watched:
        from .stock_pool import get_stock_pool
        stocks = get_stock_pool()
        print(f"\n股票池（共 {len(stocks)} 只）：")
        print(f"  {'代码':<10} {'名称':<12} {'市场':<6} {'行业':<15} {'关注':<6} {'模拟':<6}")
        print(f"  {'-'*60}")
        for s in stocks:
            print(f"  {s['symbol']:<10} {s['name']:<12} {s['market']:<6} {(s['industry'] or ''):<15} {'✓' if s['is_watched'] else '':<6} {'✓' if s['is_paper_simulated'] else '':<6}")
        return

    # 查询K线
    if args.query:
        result = query_klines(args.query, days=args.days)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 查询指标
    if args.indicators:
        result = query_indicators(args.indicators)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 只更新指数
    if args.index_only:
        cmd_fetch_indices()
        return

    # 每日更新
    if args.daily:
        cmd_daily_update(days=args.days)
        return

    # 指定股票
    symbols = []
    if args.symbol:
        symbols = [args.symbol]
    elif args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    # 执行
    if args.full:
        cmd_fetch_klines(symbols, days=args.days, incremental=False)
    else:
        cmd_fetch_klines(symbols, days=args.days, incremental=True)


if __name__ == "__main__":
    main()

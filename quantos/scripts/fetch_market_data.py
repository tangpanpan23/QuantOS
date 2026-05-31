#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场数据获取脚本（多源冗余版）

用法（完全兼容原接口）：
    python3 fetch_market_data.py realtime <股票代码>
    python3 fetch_market_data.py kline <股票代码> [period] [adjust] [limit]
    python3 fetch_market_data.py rsi <股票代码> [period]
    python3 fetch_market_data.py signal <股票代码>

示例：
    python3 fetch_market_data.py realtime 600036
    python3 fetch_market_data.py kline 600036 daily qfq 60
    python3 fetch_market_data.py rsi 600036 14
    python3 fetch_market_data.py signal 600036

多源架构：
    实时行情（A股）: Sina > Tencent > AkShare
    K线数据（A股）  : AkShare > yfinance
    全球市场        : yfinance

熔断降级：某源连续失败3次后跳过，最长等待30s恢复
缓存：60s 内同名请求直接返回（内存 LRU）
"""

import sys
import json
import logging
import argparse
from datetime import datetime

# 配置日志（安静模式，默认只输出数据）
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
)

# ── 延迟导入 router（可选依赖不影响核心功能）────────────────

try:
    from stock_fetcher import get_router
    ROUTER_OK = True
except ImportError:
    ROUTER_OK = False
    print("# [WARNING] stock_fetcher 模块未找到，请检查 PYTHONPATH", file=sys.stderr)
    print("# 安装依赖: pip install requests akshare pandas numpy yfinance", file=sys.stderr)


# ══════════════════════════════════════════════════════
#  CLI 入口
# ══════════════════════════════════════════════════════

def cmd_realtime(symbol: str) -> dict:
    """实时行情"""
    if not ROUTER_OK:
        return _mock_realtime(symbol)
    router = get_router()
    return router.fetch_realtime(symbol)


def cmd_kline(symbol: str, period: str = "daily",
              adjust: str = "qfq", limit: int = 60) -> dict:
    """K线数据"""
    if not ROUTER_OK:
        return _mock_kline(symbol, limit)
    router = get_router()
    return router.fetch_kline(symbol, period, adjust, limit)


def cmd_rsi(symbol: str, period: int = 14) -> dict:
    """计算RSI"""
    if not ROUTER_OK:
        return {"symbol": symbol, "rsi": 50.0, "source": "mock"}
    router = get_router()
    klines = router.fetch_kline(symbol, period="daily", limit=period * 3)
    closes = [k["close"] for k in klines.get("klines", [])]
    if len(closes) < period + 1:
        return {"symbol": symbol, "rsi": 50.0, "source": klines.get("_source", "unknown")}
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains  = [d for d in deltas if d > 0]
    losses = [-d for d in deltas if d < 0]
    avg_g  = sum(gains[-period:]) / period if gains else 0
    avg_l  = sum(losses[-period:]) / period if losses else 0
    rsi    = 100 - (100 / (1 + avg_g / max(avg_l, 1e-9))) if avg_l else 100
    return {
        "symbol":   symbol,
        "rsi":      round(rsi, 2),
        "source":   klines.get("_source", "unknown"),
    }


def cmd_signal(symbol: str) -> dict:
    """选股信号"""
    if not ROUTER_OK:
        return _mock_signal(symbol)
    router = get_router()
    return router.fetch_signal(symbol)


# ══════════════════════════════════════════════════════
#  诊断命令（新增）
# ══════════════════════════════════════════════════════

def cmd_health() -> dict:
    """数据源健康检查"""
    if not ROUTER_OK:
        return {"ok": False, "reason": "stock_fetcher not available"}
    router = get_router()
    return {
        "ok":    True,
        "health": router.health_check(),
        "circuit": router.circuit_status(),
        "stats":  router.stats(),
    }


def cmd_cache_clear():
    """清除缓存"""
    if not ROUTER_OK:
        print("# stock_fetcher not available", file=sys.stderr)
        return
    router = get_router()
    if router.cache:
        router.cache._mem.clear()
        print("# 缓存已清除")
    else:
        print("# 缓存未启用")


# ══════════════════════════════════════════════════════
#  模拟兜底（所有源不可用时的最后防线）
# ══════════════════════════════════════════════════════

def _mock_realtime(symbol: str) -> dict:
    prices = {
        "600036": {"name": "招商银行", "price": 35.50},
        "600900": {"name": "长江电力", "price": 22.50},
        "601288": {"name": "农业银行", "price": 3.20},
        "000858": {"name": "五粮液",   "price": 150.00},
        "300750": {"name": "宁德时代", "price": 200.00},
        "601318": {"name": "中国平安", "price": 42.00},
        "002475": {"name": "立讯精密", "price": 28.00},
        "600519": {"name": "贵州茅台", "price": 1600.00},
    }
    data = prices.get(symbol, {"name": symbol, "price": 20.0})
    data.update({
        "symbol":    symbol,
        "change_pct": 0.0,
        "change":     0.0,
        "open":       data["price"] * 0.99,
        "high":       data["price"] * 1.02,
        "low":        data["price"] * 0.98,
        "prev_close": data["price"],
        "volume":     1_000_000,
        "amount":     data["price"] * 1_000_000,
        "bid_vols":   [0]*5,
        "ask_vols":   [0]*5,
        "bid_prs":    [0.0]*5,
        "ask_prs":    [0.0]*5,
        "rsi":        50.0,
        "timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "_source":    "mock",
        "_fallback":  "all_sources_failed",
    })
    return data


def _mock_kline(symbol: str, limit: int = 60) -> dict:
    import random
    base_prices = {
        "600036": 35.0, "600900": 22.0, "601288": 3.2,
        "000858": 150.0, "300750": 200.0, "601318": 42.0,
        "002475": 28.0, "600519": 1600.0,
    }
    base_price = base_prices.get(symbol, 20.0)
    current    = base_price
    klines     = []
    import time as _time
    for i in range(limit - 1, -1, -1):
        date = _time.gmtime(_time.time() - i * 86400)
        if date.tm_wday >= 5:
            continue
        change = (random.random() - 0.5) * 0.04
        current = current * (1 + change)
        open_   = current * (1 + (random.random() - 0.5) * 0.01)
        high    = current * (1 + random.random() * 0.02)
        low     = current * (1 - random.random() * 0.02)
        vol     = int(1_000_000 + random.random() * 500_000)
        klines.append({
            "date":    _time.strftime("%Y-%m-%d", date),
            "open":    round(open_, 2),
            "high":    round(high, 2),
            "low":     round(low, 2),
            "close":   round(current, 2),
            "volume":  vol,
            "amount":  current * vol,
            "turnover": round(random.random() * 3, 2),
        })
    return {
        "klines":    klines,
        "symbol":    symbol,
        "period":    "daily",
        "adjust":    "qfq",
        "_source":   "mock",
        "_fallback": "all_sources_failed",
    }


def _mock_signal(symbol: str) -> dict:
    return {
        "symbol":     symbol,
        "name":       symbol,
        "price":      35.0,
        "rsi":        45.0,
        "ma5":        34.5,
        "ma20":       34.0,
        "ma60":       33.5,
        "score":      85,
        "reasons":    ["RSI=45", "MA20>MA60", "价格>MA20"],
        "suggestion": "BUY",
        "_source":    "mock",
    }


# ══════════════════════════════════════════════════════
#  main
# ══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="QuantOS 多源股票数据获取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "cmd",
        choices=["realtime", "kline", "rsi", "signal", "health", "cache_clear"],
        help=(
            "realtime   - 实时行情\n"
            "kline      - K线数据\n"
            "rsi        - RSI指标\n"
            "signal     - 选股信号\n"
            "health     - 数据源健康检查（新增）\n"
            "cache_clear- 清除缓存（新增）"
        ),
    )
    parser.add_argument("symbol", nargs="?", help="股票代码")
    parser.add_argument("--period",  default="daily",  help="周期: daily, weekly, monthly")
    parser.add_argument("--adjust",  default="qfq",    help="复权: qfq, hfqf, none")
    parser.add_argument("--limit",   type=int, default=60, help="K线条数")
    parser.add_argument("--rsi-period", type=int, default=14, help="RSI周期")
    parser.add_argument(
        "--skip-cache", action="store_true",
        help="跳过缓存，强制从网络获取（新增）"
    )

    args = parser.parse_args()

    # 健康检查 / 缓存清除 单独处理
    if args.cmd == "health":
        print(json.dumps(cmd_health(), ensure_ascii=False))
        return
    if args.cmd == "cache_clear":
        cmd_cache_clear()
        return

    if not args.symbol:
        parser.print_help()
        return

    symbol = args.symbol.strip()

    if args.cmd == "realtime":
        result = cmd_realtime(symbol)
    elif args.cmd == "kline":
        result = cmd_kline(symbol, args.period, args.adjust, args.limit)
    elif args.cmd == "rsi":
        result = cmd_rsi(symbol, args.rsi_period)
    elif args.cmd == "signal":
        result = cmd_signal(symbol)
    else:
        result = {}

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

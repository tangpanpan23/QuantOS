#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场数据获取脚本
通过 akshare 获取 A 股实时行情和历史 K 线数据
输出 JSON 格式供 Go 调用

用法:
    python3 fetch_market_data.py realtime <股票代码>
    python3 fetch_market_data.py kline <股票代码> [period] [adjust] [limit]
    python3 fetch_market_data.py rsi <股票代码> [period]
    python3 fetch_market_data.py signal <股票代码>

示例:
    python3 fetch_market_data.py realtime 600036
    python3 fetch_market_data.py kline 600036 daily qfq 60
    python3 fetch_market_data.py rsi 600036 14
"""

import sys
import json
import argparse
from datetime import datetime, timedelta

try:
    import akshare as ak
    import pandas as pd
    import numpy as np
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("警告: akshare 未安装，将返回模拟数据")
    print("安装命令: pip install akshare pandas numpy")


def get_realtime_data(symbol):
    """获取实时行情数据"""
    if not AKSHARE_AVAILABLE:
        return get_mock_realtime(symbol)
    
    try:
        # 获取实时行情（东方财富）
        df = ak.stock_zh_a_spot_em()
        
        # 转换代码格式（去掉前缀0）
        # A股代码格式: 600036
        row = df[df['代码'] == symbol]
        
        if row.empty:
            return get_mock_realtime(symbol)
        
        row = row.iloc[0]
        
        # 获取K线计算RSI
        rsi = calculate_rsi(symbol, 14)
        
        return {
            "symbol": symbol,
            "name": str(row['名称']),
            "price": float(row['最新价']) if pd.notna(row['最新价']) else 0,
            "change_pct": float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0,
            "volume": int(row['成交量']) if pd.notna(row['成交量']) else 0,
            "amount": float(row['成交额']) if pd.notna(row['成交额']) else 0,
            "open": float(row['今开']) if pd.notna(row['今开']) else 0,
            "high": float(row['最高']) if pd.notna(row['最高']) else 0,
            "low": float(row['最低']) if pd.notna(row['最低']) else 0,
            "prev_close": float(row['昨收']) if pd.notna(row['昨收']) else 0,
            "rsi": rsi,
            "ma5": 0,
            "ma10": 0,
            "ma20": 0,
            "timestamp": int(datetime.now().timestamp())
        }
    except Exception as e:
        print(f"获取实时数据失败: {e}", file=sys.stderr)
        return get_mock_realtime(symbol)


def get_mock_realtime(symbol):
    """返回模拟实时数据"""
    prices = {
        "600036": {"name": "招商银行", "price": 35.50},
        "600900": {"name": "长江电力", "price": 22.50},
        "601288": {"name": "农业银行", "price": 3.20},
        "000858": {"name": "五粮液", "price": 150.00},
        "300750": {"name": "宁德时代", "price": 200.00},
        "601318": {"name": "中国平安", "price": 42.00},
        "002475": {"name": "立讯精密", "price": 28.00},
        "600519": {"name": "贵州茅台", "price": 1600.00},
    }
    
    data = prices.get(symbol, {"name": symbol, "price": 20.0})
    
    return {
        "symbol": symbol,
        "name": data["name"],
        "price": data["price"],
        "change_pct": 0.0,
        "volume": 1000000,
        "amount": data["price"] * 1000000,
        "open": data["price"] * 0.99,
        "high": data["price"] * 1.02,
        "low": data["price"] * 0.98,
        "prev_close": data["price"],
        "rsi": 50.0,
        "ma5": data["price"],
        "ma10": data["price"],
        "ma20": data["price"],
        "timestamp": int(datetime.now().timestamp())
    }


def get_kline_data(symbol, period="daily", adjust="qfq", limit=60):
    """获取K线数据"""
    if not AKSHARE_AVAILABLE:
        return get_mock_kline(symbol, limit)
    
    try:
        # period: daily, weekly, monthly
        # adjust: qfq(前复权), hfqf(后复权), none(不复权)
        
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period=period,
            start_date=(datetime.now() - timedelta(days=limit * 2)).strftime("%Y%m%d"),
            end_date=datetime.now().strftime("%Y%m%d"),
            adjust=adjust
        )
        
        if df is None or df.empty:
            return get_mock_kline(symbol, limit)
        
        # 重命名列
        df.columns = ['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']
        
        # 只返回最近的limit条
        df = df.tail(limit)
        
        # 转换为字典列表
        result = []
        for _, row in df.iterrows():
            result.append({
                "日期": str(row['日期']),
                "开盘": float(row['开盘']),
                "最高": float(row['最高']),
                "最低": float(row['最低']),
                "收盘": float(row['收盘']),
                "成交量": int(row['成交量']),
                "成交额": float(row['成交额']) if pd.notna(row['成交额']) else 0,
                "换手率": float(row['换手率']) if pd.notna(row['换手率']) else 0
            })
        
        return result
        
    except Exception as e:
        print(f"获取K线数据失败: {e}", file=sys.stderr)
        return get_mock_kline(symbol, limit)


def get_mock_kline(symbol, limit=60):
    """返回模拟K线数据"""
    base_prices = {
        "600036": 35.0, "600900": 22.0, "601288": 3.2,
        "000858": 150.0, "300750": 200.0, "601318": 42.0,
        "002475": 28.0, "600519": 1600.0,
    }
    
    base_price = base_prices.get(symbol, 20.0)
    
    result = []
    current_price = base_price
    
    for i in range(limit - 1, -1, -1):
        date = datetime.now() - timedelta(days=i)
        
        # 跳过周末
        if date.weekday() >= 5:
            continue
        
        # 随机波动
        import random
        change = (random.random() - 0.5) * 0.04
        current_price = current_price * (1 + change)
        
        open_price = current_price * (1 + (random.random() - 0.5) * 0.01)
        high_price = current_price * (1 + random.random() * 0.02)
        low_price = current_price * (1 - random.random() * 0.02)
        
        result.append({
            "日期": date.strftime("%Y-%m-%d"),
            "开盘": round(open_price, 2),
            "最高": round(high_price, 2),
            "最低": round(low_price, 2),
            "收盘": round(current_price, 2),
            "成交量": int(1000000 + random.random() * 500000),
            "成交额": current_price * 1000000,
            "换手率": round(random.random() * 3, 2)
        })
    
    return result


def calculate_rsi(symbol, period=14):
    """计算RSI指标"""
    if not AKSHARE_AVAILABLE:
        return 50.0
    
    try:
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=(datetime.now() - timedelta(days=period * 3)).strftime("%Y%m%d"),
            end_date=datetime.now().strftime("%Y%m%d"),
            adjust="qfq"
        )
        
        if df is None or len(df) < period + 1:
            return 50.0
        
        # 计算价格变化
        deltas = df['收盘'].diff()
        
        # 分离涨跌
        gains = deltas.where(deltas > 0, 0)
        losses = -deltas.where(deltas < 0, 0)
        
        # 计算平均涨跌
        avg_gain = gains.tail(period).mean()
        avg_loss = losses.tail(period).mean()
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
        
    except Exception as e:
        print(f"计算RSI失败: {e}", file=sys.stderr)
        return 50.0


def generate_signal(symbol):
    """生成选股信号"""
    if not AKSHARE_AVAILABLE:
        return get_mock_signal(symbol)
    
    try:
        # 获取实时数据
        quote = get_realtime_data(symbol)
        
        # 获取K线数据
        klines = get_kline_data(symbol, limit=60)
        
        if len(klines) < 20:
            return get_mock_signal(symbol)
        
        # 计算技术指标
        closes = [k['收盘'] for k in klines]
        
        # MA5, MA20, MA60
        ma5 = sum(closes[-5:]) / 5
        ma20 = sum(closes[-20:]) / 20
        ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else ma20
        
        # RSI
        rsi = quote['rsi']
        
        # 判断条件
        signal = {
            "symbol": symbol,
            "name": quote['name'],
            "price": quote['price'],
            "rsi": rsi,
            "ma5": round(ma5, 2),
            "ma20": round(ma20, 2),
            "ma60": round(ma60, 2),
            "score": 0,
            "reasons": [],
            "suggestion": "HOLD"
        }
        
        # 成交额 > 3亿
        if quote['amount'] > 300000000:
            signal['score'] += 20
            signal['reasons'].append("成交额>3亿")
        
        # 价格 10-100元
        if 10 <= quote['price'] <= 100:
            signal['score'] += 15
        
        # RSI 35-65
        if 35 <= rsi <= 65:
            signal['score'] += 20
            signal['reasons'].append(f"RSI={rsi:.0f}")
        
        # MA20 > MA60
        if ma20 > ma60:
            signal['score'] += 25
            signal['reasons'].append("MA20>MA60")
        
        # 股价在 MA20 上方
        if quote['price'] > ma20:
            signal['score'] += 20
            signal['reasons'].append("价格>MA20")
        
        # 生成建议
        if signal['score'] >= 80:
            signal['suggestion'] = "BUY"
        elif rsi > 70:
            signal['suggestion'] = "SELL"
        elif rsi < 30:
            signal['suggestion'] = "BUY"
        
        return signal
        
    except Exception as e:
        print(f"生成信号失败: {e}", file=sys.stderr)
        return get_mock_signal(symbol)


def get_mock_signal(symbol):
    """返回模拟选股信号"""
    names = {
        "600036": "招商银行", "600900": "长江电力", "601288": "农业银行",
        "000858": "五粮液", "300750": "宁德时代", "601318": "中国平安",
        "002475": "立讯精密", "600519": "贵州茅台",
    }
    
    return {
        "symbol": symbol,
        "name": names.get(symbol, symbol),
        "price": 35.0,
        "rsi": 45.0,
        "ma5": 34.5,
        "ma20": 34.0,
        "ma60": 33.5,
        "score": 85,
        "reasons": ["RSI=45", "MA20>MA60", "价格>MA20"],
        "suggestion": "BUY"
    }


def main():
    parser = argparse.ArgumentParser(description='市场数据获取工具')
    parser.add_argument('cmd', choices=['realtime', 'kline', 'rsi', 'signal'], 
                        help='命令: realtime(实时行情), kline(K线), rsi(RSI), signal(选股信号)')
    parser.add_argument('symbol', help='股票代码')
    parser.add_argument('--period', default='daily', help='周期: daily, weekly, monthly')
    parser.add_argument('--adjust', default='qfq', help='复权: qfq, hfqf, none')
    parser.add_argument('--limit', type=int, default=60, help='数据条数')
    parser.add_argument('--rsi-period', type=int, default=14, help='RSI周期')
    
    args = parser.parse_args()
    
    if args.cmd == 'realtime':
        result = get_realtime_data(args.symbol)
    elif args.cmd == 'kline':
        result = get_kline_data(args.symbol, args.period, args.adjust, args.limit)
    elif args.cmd == 'rsi':
        result = {"symbol": args.symbol, "rsi": calculate_rsi(args.symbol, args.rsi_period)}
    elif args.cmd == 'signal':
        result = generate_signal(args.symbol)
    else:
        result = {}
    
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

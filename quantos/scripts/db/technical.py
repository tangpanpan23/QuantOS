# -*- coding: utf-8 -*-
"""技术指标计算器"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional


def calc_ma(closes: List[float], period: int) -> Optional[float]:
    """计算移动平均线"""
    if len(closes) < period:
        return None
    return round(float(np.mean(closes[-period:])), 4)


def calc_rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """计算 RSI"""
    if len(closes) < period + 1:
        return None
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(float(100 - (100 / (1 + rs))), 4)


def calc_macd(
    closes: List[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Dict[str, Optional[float]]:
    """
    计算 MACD (DIF/DEA/HIST)
    """
    if len(closes) < slow + signal:
        return {"dif": None, "dea": None, "hist": None}

    prices = pd.Series(closes)
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = (dif - dea) * 2

    return {
        "dif": round(float(dif.iloc[-1]), 6),
        "dea": round(float(dea.iloc[-1]), 6),
        "hist": round(float(hist.iloc[-1]), 6),
    }


def calc_boll(
    closes: List[float],
    period: int = 20,
    std_dev: float = 2.0,
) -> Dict[str, Optional[float]]:
    """计算布林带"""
    if len(closes) < period:
        return {"upper": None, "mid": None, "lower": None}
    series = pd.Series(closes[-period:])
    mid = series.rolling(period).mean().iloc[-1]
    std = series.rolling(period).std().iloc[-1]
    return {
        "upper": round(float(mid + std_dev * std), 4),
        "mid": round(float(mid), 4),
        "lower": round(float(mid - std_dev * std), 4),
    }


def calc_kdj(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    n: int = 9,
    m1: int = 3,
    m2: int = 3,
) -> Dict[str, Optional[float]]:
    """计算 KDJ"""
    if len(closes) < n:
        return {"k": None, "d": None, "j": None}

    low_list = pd.Series(lows[-n:])
    high_list = pd.Series(highs[-n:])
    close_list = pd.Series(closes[-n:])

    low_n = low_list.rolling(n).min().iloc[-1]
    high_n = high_list.rolling(n).min().iloc[-1]

    if high_n == low_n:
        rsv = 50
    else:
        rsv = (closes[-1] - low_n) / (high_n - low_n) * 100

    k = (2/3) * 50 + (1/3) * rsv
    d = (2/3) * 50 + (1/3) * k
    j = 3 * k - 2 * d

    return {
        "k": round(float(k), 4),
        "d": round(float(d), 4),
        "j": round(float(j), 4),
    }


def calc_atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14,
) -> Optional[float]:
    """计算 ATR（真实波幅）"""
    if len(closes) < period + 1:
        return None

    high = np.array(highs)
    low = np.array(lows)
    close = np.array(closes)

    tr1 = high[1:] - low[1:]
    tr2 = np.abs(high[1:] - close[:-1])
    tr3 = np.abs(low[1:] - close[:-1])
    tr = np.maximum(np.maximum(tr1, tr2), tr3)

    if len(tr) < period:
        return None

    atr = float(np.mean(tr[-period:]))
    return round(atr, 4)


def calc_all_indicators(
    klines: List[Dict],
    periods: Dict[str, int] = None,
) -> Dict:
    """
    一次性计算所有指标。

    参数:
        klines: K线列表，每条包含 open/high/low/close
        periods: 周期配置，如 {"ma": [5, 10, 20, 60], "rsi": [6, 12, 24]}

    返回:
        包含所有指标的字典
    """
    if periods is None:
        periods = {"ma": [5, 10, 20, 60], "rsi": [6, 12, 24]}

    closes = [k["close"] for k in klines]
    highs  = [k["high"] for k in klines]
    lows   = [k["low"] for k in klines]

    result = {}

    # MA
    for p in periods.get("ma", [5, 10, 20, 60]):
        val = calc_ma(closes, p)
        result[f"ma{p}"] = val

    # RSI
    for p in periods.get("rsi", [6, 12, 24]):
        result[f"rsi{p}"] = calc_rsi(closes, p)

    # MACD
    macd = calc_macd(closes)
    result["macd_dif"]  = macd["dif"]
    result["macd_dea"]  = macd["dea"]
    result["macd_hist"] = macd["hist"]

    # BOLL
    boll = calc_boll(closes)
    result["boll_upper"] = boll["upper"]
    result["boll_mid"]   = boll["mid"]
    result["boll_lower"] = boll["lower"]

    # KDJ
    if len(klines) >= 9:
        kdj = calc_kdj(highs, lows, closes)
        result["kdj_k"] = kdj["k"]
        result["kdj_d"] = kdj["d"]
        result["kdj_j"] = kdj["j"]

    # ATR
    result["atr"] = calc_atr(highs, lows, closes)

    return result

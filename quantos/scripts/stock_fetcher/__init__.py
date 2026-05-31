# -*- coding: utf-8 -*-
"""
QuantOS 多源股票数据获取器

架构：多源冗余 + 熔断降级
- AkShare  : A股 K线/实时（东方财富数据）
- Sina     : A股 实时行情（最稳的实时源）
- Tencent  : A股 实时行情（腾讯财经）
- yfinance : 全球（美股/港股/ETF/虚拟货币）

优先级：Sina > Tencent > AkShare（实时）；AkShare（K线）
降级策略：优先源失败 → 自动切换备选源 → 全部失败 → 返回缓存/模拟数据
"""

from .base import BaseFetcher, FetchResult, SourceTag
from .router import StockRouter, get_router

__all__ = [
    "BaseFetcher",
    "FetchResult",
    "SourceTag",
    "StockRouter",
    "get_router",
]

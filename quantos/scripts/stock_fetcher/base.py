# -*- coding: utf-8 -*-
"""
BaseFetcher - 抽象基类

所有数据源必须继承此类，实现统一的接口。
"""

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from enum import IntEnum
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)


class SourceTag(IntEnum):
    """数据源标签（数值越小优先级越高）"""
    AKSHARE  = 1   # A股 K线/实时
    SINA     = 2   # A股 实时（新浪）
    TENCENT  = 3   # A股 实时（腾讯）
    YFINANCE = 4   # 全球（yfinance）


class DataType(IntEnum):
    """数据类型"""
    REALTIME   = 1
    KLINE      = 2
    BASIC      = 3
    FUNDAMENTAL = 4


@dataclass
class FetchResult:
    """
    统一的_fetch结果包装器

    所有数据源返回结果必须包装为此格式，
    方便 router 做多源聚合、交叉验证、熔断降级。
    """
    source:       str          # 数据源名称，如 "akshare", "sina", "tencent"
    source_tag:   SourceTag   # 数据源优先级标签
    data_type:    DataType     # 数据类型
    symbol:       str          # 股票代码
    data:         Optional[Dict[str, Any]] = None   # 实际数据字典
    error:        Optional[str] = None
    latency_ms:   float       = 0.0    # 请求耗时（毫秒）
    timestamp:    float       = field(default_factory=time.time)  # 请求时间戳
    valid:        bool        = True    # 数据是否有效

    def to_dict(self) -> dict:
        d = asdict(self)
        d["source_tag"] = int(self.source_tag)
        d["data_type"]  = int(self.data_type)
        return d


class BaseFetcher(ABC):
    """
    数据源抽象基类

    子类必须实现：
    - _fetch_realtime  : 获取实时行情
    - _fetch_kline     : 获取K线数据

    可选重写：
    - _fetch_basic     : 获取股票基本信息
    - _validate        : 自定义数据校验逻辑
    """

    name:       str      = "base"
    source_tag: SourceTag = SourceTag.AKSHARE

    def __init__(self, timeout: float = 8.0, retry: int = 2):
        self.timeout = timeout
        self.retry   = retry
        self._stats  = {"ok": 0, "fail": 0, "total_ms": 0.0}

    # ── 主入口 ───────────────────────────────────────────────

    def fetch_realtime(self, symbol: str) -> FetchResult:
        """获取实时行情（带计时/重试/wrap）"""
        return self._wrap(symbol, DataType.REALTIME, self._fetch_realtime, symbol)

    def fetch_kline(
        self,
        symbol: str,
        period: str = "daily",
        adjust: str = "qfq",
        limit: int = 60,
    ) -> FetchResult:
        """获取K线数据"""
        return self._wrap(
            symbol, DataType.KLINE, self._fetch_kline,
            symbol, period, adjust, limit,
        )

    # ── 子类必须实现 ─────────────────────────────────────────

    @abstractmethod
    def _fetch_realtime(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取单个股票的实时行情。

        Returns:
            成功返回字段字典，失败返回 None。
            字段规范见 _standard_realtime_fields()
        """
        ...

    def _fetch_kline(
        self,
        symbol: str,
        period: str = "daily",
        adjust: str = "qfq",
        limit: int = 60,
    ) -> Optional[Dict[str, Any]]:
        """
        获取K线数据（子类可选实现）。

        Returns:
            成功返回 {"klines": [...]} 格式，失败返回 None。
            不实现则返回 None，由 Router 自动降级到其他源。
        """
        return None

    # ── 标准化字段 ──────────────────────────────────────────

    @staticmethod
    def _standard_realtime_fields() -> list:
        """实时数据标准字段名列表"""
        return [
            "symbol", "name", "price", "change", "change_pct",
            "open", "high", "low", "prev_close",
            "volume", "amount",
            "bid", "ask", "bid_vol", "ask_vol",
            "ma5", "ma10", "ma20",
            "turnover", "pe_ttm", "pb",
            "market_cap", "float_market_cap",
            "52w_high", "52w_low",
            "timestamp",
        ]

    # ── 工具方法 ────────────────────────────────────────────

    def _wrap(
        self,
        symbol: str,
        data_type: DataType,
        fn,
        *args,
        **kwargs,
    ) -> FetchResult:
        """通用包装器：计时 + 异常捕获"""
        t0 = time.time()
        err_msg = None
        data    = None

        for attempt in range(1, self.retry + 1):
            try:
                data = fn(*args, **kwargs)
                if data is not None:
                    break
            except Exception as e:
                err_msg = f"[attempt {attempt}/{self.retry}] {type(e).__name__}: {e}"
                logger.warning(f"{self.name} fetch failed (attempt {attempt}): {e}")

        latency = (time.time() - t0) * 1000
        self._stats["total_ms"] += latency

        if data is not None:
            self._stats["ok"] += 1
            # 注入元数据
            data["_source"]    = self.name
            data["_latency_ms"] = latency
            return FetchResult(
                source     = self.name,
                source_tag = self.source_tag,
                data_type  = data_type,
                symbol     = symbol,
                data       = data,
                error      = None,
                latency_ms = latency,
                valid      = True,
            )
        else:
            self._stats["fail"] += 1
            return FetchResult(
                source     = self.name,
                source_tag = self.source_tag,
                data_type  = data_type,
                symbol     = symbol,
                data       = None,
                error      = err_msg or "unknown error",
                latency_ms = latency,
                valid      = False,
            )

    def stats(self) -> dict:
        """返回简单统计"""
        return dict(self._stats)

    def health_check(self) -> bool:
        """健康检查：子类可重写"""
        try:
            r = self.fetch_realtime("000001")
            return r.valid
        except Exception:
            return False

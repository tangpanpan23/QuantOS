# -*- coding: utf-8 -*-
"""SQLAlchemy ORM 模型（与数据库表一一对应）"""
from datetime import datetime, date
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# ── 股票池 ─────────────────────────────────────────────

from sqlalchemy import Column, BigInteger, Integer, String, Date, DateTime, Numeric, Text, Boolean, SmallInteger

class StockPoolDB(Base):
    """股票池（q_stock_pool）"""
    __tablename__ = "q_stock_pool"

    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at  = Column(DateTime, default=datetime.now)
    updated_at  = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    symbol      = Column(String(20), nullable=False, unique=True)
    name        = Column(String(100), nullable=False)
    market      = Column(String(10), nullable=False)          # SH/SZ/BJ
    industry    = Column(String(100), nullable=True)
    sector      = Column(String(100), nullable=True)
    status      = Column(Integer, nullable=False, default=1)  # 1-正常 2-停牌 3-退市
    is_watched  = Column(Integer, nullable=False, default=1)
    is_paper_simulated = Column(Integer, nullable=False, default=1)
    notes       = Column(String(500), nullable=True)
    # ── 基本面信息 ──────────────────────────
    listing_date      = Column(Date, nullable=True)        # 上市日期
    legal_rep        = Column(String(100), nullable=True)   # 法人代表
    registered_capital = Column(String(50), nullable=True) # 注册资金(万元)
    total_shares     = Column(Numeric(20,2), nullable=True) # 总股本(万股)
    main_business    = Column(Text, nullable=True)         # 主营业务
    company_intro    = Column(Text, nullable=True)        # 公司介绍
    eps              = Column(Numeric(10,4), nullable=True) # 每股收益EPS(元)
    book_value       = Column(Numeric(10,4), nullable=True) # 每股净资产BVPS(元)
    roe              = Column(Numeric(8,4), nullable=True)  # 净资产收益率ROE(%)
    gross_margin     = Column(Numeric(8,4), nullable=True)  # 销售毛利率(%)
    net_margin       = Column(Numeric(8,4), nullable=True) # 销售净利率(%)
    dividend_yield   = Column(Numeric(8,4), nullable=True) # 股息率(%)
    pe_ratio         = Column(Numeric(10,2), nullable=True) # 市盈率TTM
    pb_ratio         = Column(Numeric(8,4), nullable=True) # 市净率PB
    market_cap       = Column(Numeric(20,2), nullable=True) # 总市值(亿元)
    risk_level       = Column(Integer, nullable=True, default=3) # 风险等级1-5
    risk_factors     = Column(String(500), nullable=True)   # 风险因素
    fin_update_date  = Column(Date, nullable=True)          # 财务数据更新日期
    business_desc    = Column(String(500), nullable=True)   # 业务描述摘要

    @property
    def is_active(self) -> bool:
        return self.status == 1

    def to_dict(self):
        return {
            "id": self.id, "symbol": self.symbol, "name": self.name,
            "market": self.market, "industry": self.industry,
            "sector": self.sector, "status": self.status,
            "is_watched": bool(self.is_watched),
            "is_paper_simulated": bool(self.is_paper_simulated),
        }


# ── 历史日线行情 ───────────────────────────────────────

class DailyKlineDB(Base):
    """历史日线行情（q_daily_kline）"""
    __tablename__ = "q_daily_kline"

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at   = Column(DateTime, default=datetime.now)
    symbol       = Column(String(20), nullable=False)
    symbol_name  = Column(String(100), nullable=True)
    trade_date   = Column(Date, nullable=False)
    open_price   = Column(Numeric(10,4), nullable=False)
    high_price   = Column(Numeric(10,4), nullable=False)
    low_price    = Column(Numeric(10,4), nullable=False)
    close_price  = Column(Numeric(10,4), nullable=False)
    prev_close   = Column(Numeric(10,4), nullable=True)
    change_pct   = Column(Numeric(8,4), nullable=True)
    volume       = Column(BigInteger, nullable=True)
    amount       = Column(Numeric(20,2), nullable=True)
    turnover_rate= Column(Numeric(8,4), nullable=True)
    market       = Column(String(10), nullable=False)
    # 技术指标
    ma5          = Column(Numeric(10,4), nullable=True)
    ma10         = Column(Numeric(10,4), nullable=True)
    ma20         = Column(Numeric(10,4), nullable=True)
    ma60         = Column(Numeric(10,4), nullable=True)
    rsi6         = Column(Numeric(7,4), nullable=True)
    rsi12        = Column(Numeric(7,4), nullable=True)
    rsi24        = Column(Numeric(7,4), nullable=True)
    macd_dif     = Column(Numeric(10,6), nullable=True)
    macd_dea     = Column(Numeric(10,6), nullable=True)
    macd_hist    = Column(Numeric(10,6), nullable=True)
    boll_upper   = Column(Numeric(10,4), nullable=True)
    boll_mid     = Column(Numeric(10,4), nullable=True)
    boll_lower   = Column(Numeric(10,4), nullable=True)
    kdj_k        = Column(Numeric(7,4), nullable=True)
    kdj_d        = Column(Numeric(7,4), nullable=True)
    kdj_j        = Column(Numeric(7,4), nullable=True)
    atr          = Column(Numeric(10,4), nullable=True)
    data_source  = Column(String(20), nullable=False, default="akshare")
    is_adj_close = Column(Integer, nullable=False, default=1)

    def to_dict(self):
        return {
            "symbol": self.symbol, "trade_date": str(self.trade_date),
            "open": float(self.open_price), "high": float(self.high_price),
            "low": float(self.low_price), "close": float(self.close_price),
            "volume": self.volume, "amount": float(self.amount) if self.amount else None,
            "ma5": float(self.ma5) if self.ma5 else None,
            "ma20": float(self.ma20) if self.ma20 else None,
            "ma60": float(self.ma60) if self.ma60 else None,
            "rsi6": float(self.rsi6) if self.rsi6 else None,
            "rsi12": float(self.rsi12) if self.rsi12 else None,
        }


# ── 模拟账户 ──────────────────────────────────────────

class PaperAccountDB(Base):
    """模拟账户（q_paper_account）"""
    __tablename__ = "q_paper_account"

    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at       = Column(DateTime, default=datetime.now)
    updated_at       = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    user_id          = Column(BigInteger, nullable=False, unique=True, default=1)
    name             = Column(String(100), nullable=False, default="默认模拟账户")
    status           = Column(Integer, nullable=False, default=1)
    initial_capital  = Column(Numeric(20,2), nullable=False, default=100000)
    cash_reserve     = Column(Numeric(20,2), nullable=False, default=40000)
    current_capital  = Column(Numeric(20,2), nullable=False, default=60000)
    total_value      = Column(Numeric(20,2), nullable=False, default=100000)
    positions_value  = Column(Numeric(20,2), nullable=False, default=0)
    total_pnl        = Column(Numeric(20,2), nullable=True, default=0)
    total_return_pct = Column(Numeric(10,4), nullable=True, default=0)
    total_trades     = Column(Integer, nullable=False, default=0)
    buy_trades       = Column(Integer, nullable=False, default=0)
    sell_trades      = Column(Integer, nullable=False, default=0)
    win_trades       = Column(Integer, nullable=False, default=0)
    loss_trades      = Column(Integer, nullable=False, default=0)
    win_rate         = Column(Numeric(5,4), nullable=True, default=0)
    avg_win          = Column(Numeric(20,2), nullable=True, default=0)
    avg_loss         = Column(Numeric(20,2), nullable=True, default=0)
    stop_loss_pct    = Column(Numeric(5,4), nullable=False, default=0.03)
    take_profit1_pct = Column(Numeric(5,4), nullable=False, default=0.05)
    take_profit2_pct = Column(Numeric(5,4), nullable=False, default=0.08)
    max_position_value=Column(Numeric(20,2), nullable=False, default=15000)
    max_positions    = Column(Integer, nullable=False, default=4)
    last_reset_at    = Column(DateTime, nullable=True)
    last_trade_at    = Column(DateTime, nullable=True)
    note             = Column(String(500), nullable=True)


# ── 模拟持仓 ──────────────────────────────────────────

class PaperPositionDB(Base):
    """模拟持仓（q_paper_position）"""
    __tablename__ = "q_paper_position"

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at      = Column(DateTime, default=datetime.now)
    updated_at      = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    account_id      = Column(BigInteger, nullable=False)
    symbol          = Column(String(20), nullable=False)
    symbol_name     = Column(String(100), nullable=True)
    shares          = Column(Integer, nullable=False)
    avg_cost        = Column(Numeric(10,4), nullable=False)
    current_price   = Column(Numeric(10,4), nullable=True)
    market_value    = Column(Numeric(20,2), nullable=True)
    unrealized_pnl  = Column(Numeric(20,2), nullable=True)
    unrealized_pnl_pct = Column(Numeric(10,4), nullable=True)
    stop_loss       = Column(Numeric(10,4), nullable=False)
    take_profit1    = Column(Numeric(10,4), nullable=False)
    take_profit2    = Column(Numeric(10,4), nullable=False)
    stop_moved      = Column(Integer, nullable=False, default=0)
    entry_date      = Column(Date, nullable=False)
    entry_price     = Column(Numeric(10,4), nullable=False)
    entry_reason    = Column(String(500), nullable=True)
    entry_rsi       = Column(Numeric(7,4), nullable=True)
    entry_ma5       = Column(Numeric(10,4), nullable=True)
    entry_ma20      = Column(Numeric(10,4), nullable=True)
    entry_ma60      = Column(Numeric(10,4), nullable=True)
    hold_days       = Column(Integer, nullable=True, default=0)
    last_check_price= Column(Numeric(10,4), nullable=True)
    last_check_at   = Column(DateTime, nullable=True)


# ── 交易记录 ───────────────────────────────────────────

class TradeLogDB(Base):
    """交易记录（q_trade_log）"""
    __tablename__ = "q_trade_log"

    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at  = Column(DateTime, default=datetime.now)
    account_id  = Column(BigInteger, nullable=False)
    trade_no    = Column(String(64), nullable=False, unique=True)
    trade_date  = Column(Date, nullable=False)
    trade_time  = Column(String(10), nullable=True)
    action      = Column(String(10), nullable=False)      # BUY/SELL
    action_type = Column(String(20), nullable=False)      # MANUAL/STOP_LOSS/TAKE_PROFIT1...
    symbol      = Column(String(20), nullable=False)
    symbol_name = Column(String(100), nullable=True)
    price       = Column(Numeric(10,4), nullable=False)
    shares      = Column(Integer, nullable=False)
    amount      = Column(Numeric(20,2), nullable=False)
    commission  = Column(Numeric(10,2), nullable=True, default=0)
    cash_before = Column(Numeric(20,2), nullable=False)
    cash_after  = Column(Numeric(20,2), nullable=False)
    position_id = Column(BigInteger, nullable=True)
    avg_cost    = Column(Numeric(10,4), nullable=True)
    entry_price = Column(Numeric(10,4), nullable=True)
    entry_date  = Column(Date, nullable=True)
    pnl         = Column(Numeric(20,2), nullable=True)
    pnl_pct     = Column(Numeric(10,4), nullable=True)
    hold_days   = Column(Integer, nullable=True)
    is_win      = Column(Integer, nullable=True)
    entry_reason= Column(String(500), nullable=True)
    entry_rsi   = Column(Numeric(7,4), nullable=True)
    note        = Column(String(500), nullable=True)


# ── 每日快照 ──────────────────────────────────────────

class DailySnapshotDB(Base):
    """每日账户快照（q_daily_snapshot）"""
    __tablename__ = "q_daily_snapshot"

    id             = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at     = Column(DateTime, default=datetime.now)
    account_id     = Column(BigInteger, nullable=False)
    snapshot_date  = Column(Date, nullable=False)
    total_value    = Column(Numeric(20,2), nullable=False)
    cash           = Column(Numeric(20,2), nullable=False)
    positions_value= Column(Numeric(20,2), nullable=False)
    positions_count= Column(Integer, nullable=False, default=0)
    total_pnl      = Column(Numeric(20,2), nullable=True, default=0)
    daily_pnl      = Column(Numeric(20,2), nullable=True, default=0)
    daily_pnl_pct  = Column(Numeric(10,4), nullable=True, default=0)
    return_pct     = Column(Numeric(10,4), nullable=True, default=0)
    return_vs_initial = Column(Numeric(10,4), nullable=True, default=0)
    max_drawdown   = Column(Numeric(10,4), nullable=True, default=0)
    trades_count   = Column(Integer, nullable=True, default=0)
    benchmark_value= Column(Numeric(20,2), nullable=True)
    note           = Column(String(500), nullable=True)


# ── 进化历史 ──────────────────────────────────────────

class EvolutionLogDB(Base):
    """进化历史（q_evolution_log）"""
    __tablename__ = "q_evolution_log"

    id             = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at     = Column(DateTime, default=datetime.now)
    account_id     = Column(BigInteger, nullable=False)
    param_key      = Column(String(100), nullable=False)
    param_name     = Column(String(100), nullable=True)
    old_value      = Column(Numeric(20,4), nullable=True)
    new_value      = Column(Numeric(20,4), nullable=True)
    change_reason  = Column(String(500), nullable=True)
    evidence_trades= Column(Integer, nullable=True, default=0)
    old_win_rate   = Column(Numeric(5,4), nullable=True)
    new_win_rate   = Column(Numeric(5,4), nullable=True)
    trigger_type   = Column(String(20), nullable=True)
    status         = Column(Integer, nullable=False, default=1)


# ── 基准指数 ──────────────────────────────────────────

class BenchmarkDB(Base):
    """基准指数（q_benchmark_index）"""
    __tablename__ = "q_benchmark_index"

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at   = Column(DateTime, default=datetime.now)
    index_code   = Column(String(20), nullable=False)
    index_name   = Column(String(100), nullable=False)
    trade_date   = Column(Date, nullable=False)
    open_value   = Column(Numeric(12,4), nullable=True)
    high_value   = Column(Numeric(12,4), nullable=True)
    low_value    = Column(Numeric(12,4), nullable=True)
    close_value  = Column(Numeric(12,4), nullable=False)
    prev_close   = Column(Numeric(12,4), nullable=True)
    change_pct   = Column(Numeric(8,4), nullable=True)
    volume       = Column(BigInteger, nullable=True)
    amount       = Column(Numeric(20,2), nullable=True)
    data_source  = Column(String(20), nullable=False, default="akshare")

    def to_dict(self):
        return {
            "index_code": self.index_code, "index_name": self.index_name,
            "trade_date": str(self.trade_date), "close": float(self.close_value),
        }

-- ================================================================
-- 0006_trading_and_news_tables.sql
-- Tank QuantOS 数据库设计 — 第四部分
--
-- 包含四大域：
--   Part 1  模拟交易系统（Simulated Trading）
--   Part 2  个人交易记录（Personal Trading）
--   Part 3  新闻与政策（News & Policy）
--   Part 4  宏观经济指标（Macro Indicators）
--
-- Tank 量化系统 · 2026-05-21
-- ================================================================

-- ───────────────────────────────────────────────────────────────
-- Part 1 · 模拟交易系统
-- 完整闭环：策略 → 信号 → 订单 → 成交 → 持仓 → 每日快照 → 账户盈亏
-- ───────────────────────────────────────────────────────────────

-- 1.1 模拟账户表（可创建多个策略账户）
CREATE TABLE IF NOT EXISTS q_sim_account (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    account_name    VARCHAR(50) NOT NULL COMMENT '账户名称，如"趋势跟踪_v1.0"',
    strategy_id     BIGINT UNSIGNED NOT NULL COMMENT '关联策略ID',
    initial_capital DECIMAL(16,2) NOT NULL DEFAULT 100000.00 COMMENT '初始资金（元）',
    current_capital DECIMAL(16,2) NOT NULL DEFAULT 100000.00 COMMENT '当前可用资金',
    frozen_capital  DECIMAL(16,2) NOT NULL DEFAULT 0.00 COMMENT '挂单冻结资金',
    total_asset     DECIMAL(16,2) NOT NULL DEFAULT 100000.00 COMMENT '总资产（含持仓市值）',
    total_cost      DECIMAL(16,2) NOT NULL DEFAULT 0.00 COMMENT '累计投入成本',
    total_pnl       DECIMAL(16,2) NOT NULL DEFAULT 0.00 COMMENT '累计绝对盈亏',
    total_pnl_pct   DECIMAL(10,4) NOT NULL DEFAULT 0.0000 COMMENT '累计收益率（%）',
    bench_symbol    VARCHAR(10) DEFAULT '000300' COMMENT '对标基准指数代码',
    bench_pnl_pct   DECIMAL(10,4) NOT NULL DEFAULT 0.0000 COMMENT '基准同期收益率',
    total_trades    INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '累计交易次数',
    winning_trades  INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '盈利交易次数',
    max_drawdown    DECIMAL(10,4) NOT NULL DEFAULT 0.0000 COMMENT '最大回撤（%）',
    sharpe_ratio    DECIMAL(8,4) DEFAULT NULL COMMENT '夏普比率',
    status          TINYINT NOT NULL DEFAULT 1 COMMENT '1=运行中 2=暂停 3=已结束',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_name (account_name),
    KEY ix_strategy (strategy_id),
    KEY ix_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟交易账户';

-- 1.2 策略配置表
CREATE TABLE IF NOT EXISTS q_sim_strategy (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    strategy_name   VARCHAR(80) NOT NULL COMMENT '策略名称',
    strategy_type   VARCHAR(30) NOT NULL COMMENT '策略类型：trend_following/momentum/mean_reversion/breakout/value/other',
    description     VARCHAR(500) DEFAULT NULL COMMENT '策略描述',
    params_json     JSON DEFAULT NULL COMMENT '策略参数字典 JSON',
    universe_json   JSON DEFAULT NULL COMMENT '股票池定义 JSON',
    max_position_pct   DECIMAL(6,2) NOT NULL DEFAULT 20.00 COMMENT '单股最大持仓比例（%）',
    max_total_positions INT UNSIGNED NOT NULL DEFAULT 10 COMMENT '最大同时持仓数',
    stop_loss_pct   DECIMAL(6,2) NOT NULL DEFAULT -5.00 COMMENT '止损比例（%）',
    take_profit_pct DECIMAL(6,2) NOT NULL DEFAULT 20.00 COMMENT '止盈比例（%）',
    signal_enabled  TINYINT NOT NULL DEFAULT 1 COMMENT '1=启用信号 0=暂停',
    auto_trade      TINYINT NOT NULL DEFAULT 0 COMMENT '1=自动执行 0=仅信号',
    backtest_start  DATE DEFAULT NULL COMMENT '回测开始日期',
    backtest_end    DATE DEFAULT NULL COMMENT '回测结束日期',
    backtest_return DECIMAL(10,4) DEFAULT NULL COMMENT '回测收益率（%）',
    backtest_sharpe DECIMAL(8,4) DEFAULT NULL COMMENT '回测夏普比率',
    backtest_max_dd DECIMAL(10,4) DEFAULT NULL COMMENT '回测最大回撤',
    is_active       TINYINT NOT NULL DEFAULT 1 COMMENT '1=激活 0=归档',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_name (strategy_name),
    KEY ix_type (strategy_type),
    KEY ix_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟交易策略配置';

-- 1.3 策略信号表（每日策略输出的交易信号）
CREATE TABLE IF NOT EXISTS q_sim_signal (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    strategy_id     BIGINT UNSIGNED NOT NULL COMMENT '策略ID',
    symbol          VARCHAR(10) NOT NULL COMMENT '股票代码',
    signal_type     VARCHAR(10) NOT NULL COMMENT 'BUY/SELL/HOLD/COVER/SHORT',
    signal_reason   VARCHAR(200) DEFAULT NULL COMMENT '信号产生原因',
    signal_price    DECIMAL(12,4) NOT NULL COMMENT '信号触发价格',
    target_price    DECIMAL(12,4) DEFAULT NULL COMMENT '目标价格',
    target_pct      DECIMAL(8,2) DEFAULT NULL COMMENT '目标涨跌幅（%）',
    confidence      DECIMAL(5,2) DEFAULT NULL COMMENT '信号置信度 0-100',
    quantity        INT UNSIGNED DEFAULT NULL COMMENT '建议买入数量（手）',
    urgency         TINYINT NOT NULL DEFAULT 5 COMMENT '紧急程度 1-10',
    valid_from      DATETIME NOT NULL COMMENT '信号生效时间',
    valid_until     DATETIME DEFAULT NULL COMMENT '信号失效时间',
    status          VARCHAR(10) NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/EXPIRED/EXECUTED/IGNORED',
    related_news_id BIGINT UNSIGNED DEFAULT NULL COMMENT '关联新闻ID（如有）',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sid_symbol_time (strategy_id, symbol, signal_type, valid_from),
    KEY ix_symbol (symbol),
    KEY ix_status (status),
    KEY ix_valid_until (valid_until)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='策略交易信号';

-- 1.4 模拟订单表
CREATE TABLE IF NOT EXISTS q_sim_order (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    account_id      BIGINT UNSIGNED NOT NULL COMMENT '账户ID',
    strategy_id     BIGINT UNSIGNED NOT NULL COMMENT '策略ID',
    signal_id       BIGINT UNSIGNED DEFAULT NULL COMMENT '关联信号ID',
    symbol          VARCHAR(10) NOT NULL COMMENT '股票代码',
    direction       VARCHAR(5) NOT NULL COMMENT 'BUY/SELL',
    order_type      VARCHAR(10) NOT NULL DEFAULT 'MARKET' COMMENT 'MARKET/LIMIT/STOP',
    order_price     DECIMAL(12,4) DEFAULT NULL COMMENT '限价/止损价格',
    quantity        INT UNSIGNED NOT NULL COMMENT '委托数量（股）',
    filled_qty      INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '已成交数量',
    order_value     DECIMAL(16,2) NOT NULL COMMENT '委托金额',
    filled_value    DECIMAL(16,2) NOT NULL DEFAULT 0.00 COMMENT '成交金额',
    avg_fill_price   DECIMAL(12,4) DEFAULT NULL COMMENT '成交均价',
    commission      DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '手续费',
    status          VARCHAR(15) NOT NULL DEFAULT 'SUBMITTED' COMMENT 'SUBMITTED/PARTIAL/FILLED/CANCELLED/REJECTED/EXPIRED',
    submitted_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '下单时间',
    filled_at       DATETIME DEFAULT NULL COMMENT '全部成交时间',
    cancelled_at    DATETIME DEFAULT NULL COMMENT '撤单时间',
    cancel_reason   VARCHAR(200) DEFAULT NULL COMMENT '撤单原因',
    note            VARCHAR(500) DEFAULT NULL COMMENT '备注',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY ix_account (account_id),
    KEY ix_symbol_status (symbol, status),
    KEY ix_submitted (submitted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟交易订单';

-- 1.5 模拟持仓表
CREATE TABLE IF NOT EXISTS q_sim_position (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    account_id      BIGINT UNSIGNED NOT NULL COMMENT '账户ID',
    symbol          VARCHAR(10) NOT NULL COMMENT '股票代码',
    quantity        INT NOT NULL DEFAULT 0 COMMENT '持仓数量（股，负数=做空）',
    avg_cost        DECIMAL(12,4) NOT NULL DEFAULT 0.00 COMMENT '平均持仓成本',
    today_cost      DECIMAL(16,2) NOT NULL DEFAULT 0.00 COMMENT '今日买入总额',
    today_profit    DECIMAL(16,2) NOT NULL DEFAULT 0.00 COMMENT '今日浮动盈亏',
    total_profit    DECIMAL(16,2) NOT NULL DEFAULT 0.00 COMMENT '累计浮动盈亏',
    market_value    DECIMAL(16,2) NOT NULL DEFAULT 0.00 COMMENT '持仓市值',
    position_pct    DECIMAL(6,2) NOT NULL DEFAULT 0.00 COMMENT '持仓占总资产比例（%）',
    stop_loss_price DECIMAL(12,4) DEFAULT NULL COMMENT '止损价',
    take_profit_price DECIMAL(12,4) DEFAULT NULL COMMENT '止盈价',
    first_buy_date  DATE DEFAULT NULL COMMENT '首次建仓日期',
    last_buy_date   DATE DEFAULT NULL COMMENT '最后加仓日期',
    is_long         TINYINT NOT NULL DEFAULT 1 COMMENT '1=多头 0=空头',
    status          VARCHAR(10) NOT NULL DEFAULT 'OPEN' COMMENT 'OPEN/FROZEN/CLOSED',
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_account_symbol (account_id, symbol),
    KEY ix_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟持仓';

-- 1.6 模拟成交记录表
CREATE TABLE IF NOT EXISTS q_sim_trade (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    account_id      BIGINT UNSIGNED NOT NULL COMMENT '账户ID',
    order_id        BIGINT UNSIGNED DEFAULT NULL COMMENT '关联订单ID',
    strategy_id     BIGINT UNSIGNED NOT NULL COMMENT '策略ID',
    symbol          VARCHAR(10) NOT NULL COMMENT '股票代码',
    direction       VARCHAR(5) NOT NULL COMMENT 'BUY/SELL',
    trade_price     DECIMAL(12,4) NOT NULL COMMENT '成交价格',
    quantity        INT UNSIGNED NOT NULL COMMENT '成交数量（股）',
    trade_value     DECIMAL(16,2) NOT NULL COMMENT '成交金额',
    commission      DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '手续费',
    stamp_duty      DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '印花税（仅卖出）',
    profit          DECIMAL(16,2) DEFAULT NULL COMMENT '本笔盈亏（卖出时计算）',
    profit_pct      DECIMAL(10,4) DEFAULT NULL COMMENT '收益率（%）',
    position_id     BIGINT UNSIGNED DEFAULT NULL COMMENT '关联持仓ID',
    trade_date      DATE NOT NULL COMMENT '交易日期',
    trade_time      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '成交时间',
    reason          VARCHAR(200) DEFAULT NULL COMMENT '成交原因',
    KEY ix_account_date (account_id, trade_date),
    KEY ix_symbol_date (symbol, trade_date),
    KEY ix_strategy (strategy_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟成交记录';

-- 1.7 模拟账户每日盈亏快照
CREATE TABLE IF NOT EXISTS q_sim_daily_pnl (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    account_id      BIGINT UNSIGNED NOT NULL COMMENT '账户ID',
    trade_date      DATE NOT NULL COMMENT '快照日期',
    open_capital    DECIMAL(16,2) NOT NULL COMMENT '日初资金',
    close_capital   DECIMAL(16,2) NOT NULL COMMENT '日终资金',
    daily_pnl       DECIMAL(16,2) NOT NULL COMMENT '当日盈亏',
    daily_pnl_pct   DECIMAL(10,4) NOT NULL COMMENT '当日收益率（%）',
    position_value  DECIMAL(16,2) NOT NULL DEFAULT 0.00 COMMENT '收盘持仓市值',
    position_pnl    DECIMAL(16,2) NOT NULL DEFAULT 0.00 COMMENT '持仓浮动盈亏',
    realized_pnl    DECIMAL(16,2) NOT NULL DEFAULT 0.00 COMMENT '当日已实现盈亏',
    bench_open      DECIMAL(12,4) DEFAULT NULL COMMENT '基准开盘',
    bench_close     DECIMAL(12,4) DEFAULT NULL COMMENT '基准收盘',
    bench_pnl_pct   DECIMAL(10,4) DEFAULT NULL COMMENT '基准涨跌幅',
    alpha           DECIMAL(10,4) DEFAULT NULL COMMENT 'Alpha（跑赢基准）',
    turnover        DECIMAL(10,4) NOT NULL DEFAULT 0.00 COMMENT '换手率（%）',
    new_orders      INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '当日新订单数',
    filled_orders    INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '当日成交订单数',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_account_date (account_id, trade_date),
    KEY ix_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟账户每日盈亏快照';


-- ───────────────────────────────────────────────────────────────
-- Part 2 · 个人交易记录
-- ───────────────────────────────────────────────────────────────

-- 2.1 个人投资者画像
CREATE TABLE IF NOT EXISTS q_personal_profile (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    investor_name   VARCHAR(50) NOT NULL DEFAULT 'Tank',
    age             TINYINT UNSIGNED DEFAULT 36,
    risk_tolerance  VARCHAR(10) NOT NULL DEFAULT 'MODERATE' COMMENT 'CONSERVATIVE/MODERATE/AGGRESSIVE',
    investment_goal  VARCHAR(200) DEFAULT NULL,
    investment_horizon VARCHAR(20) NOT NULL DEFAULT 'MEDIUM' COMMENT 'SHORT/MEDIUM/LONG',
    expected_return DECIMAL(8,2) DEFAULT NULL COMMENT '预期年化收益率（%）',
    max_loss_tolerance DECIMAL(8,2) DEFAULT -15.00 COMMENT '最大可承受亏损（%）',
    trading_experience VARCHAR(20) DEFAULT 'SENIOR' COMMENT 'BEGINNER/INTERMEDIATE/SENIOR/EXPERT',
    familiar_strategies JSON DEFAULT NULL,
    investable_asset DECIMAL(16,2) DEFAULT NULL,
    annual_income   DECIMAL(16,2) DEFAULT NULL,
    income_source   VARCHAR(100) DEFAULT NULL,
    prefer_sectors  JSON DEFAULT NULL,
    avoid_sectors   JSON DEFAULT NULL,
    prefer_capital_size VARCHAR(10) DEFAULT 'MID' COMMENT 'SMALL/MID/LARGE/MIX',
    prefer_dividend TINYINT NOT NULL DEFAULT 0,
    prefer_growth   TINYINT NOT NULL DEFAULT 1,
    prefer_value    TINYINT NOT NULL DEFAULT 0,
    liquidity_need   VARCHAR(20) DEFAULT 'LOW',
    tax_considerations TINYINT NOT NULL DEFAULT 0,
    trading_frequency VARCHAR(20) NOT NULL DEFAULT 'OCCASIONAL' COMMENT 'RARELY/OCCASIONAL/MONTHLY/WEEKLY/DAILY',
    avg_holding_days  INT UNSIGNED DEFAULT 90,
    bias_patterns   JSON DEFAULT NULL COMMENT 'overconfidence/loss_aversion/anchoring',
    current_cash    DECIMAL(16,2) NOT NULL DEFAULT 0.00,
    total_market_value DECIMAL(16,2) NOT NULL DEFAULT 0.00,
    total_assets   DECIMAL(16,2) NOT NULL DEFAULT 0.00,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_name (investor_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='个人投资者画像';

-- 2.2 个人策略倾向
CREATE TABLE IF NOT EXISTS q_personal_strategy_pref (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    profile_id      BIGINT UNSIGNED NOT NULL,
    strategy_type   VARCHAR(30) NOT NULL,
    preference_score DECIMAL(5,2) NOT NULL COMMENT '偏好程度 0-100',
    start_date      DATE DEFAULT NULL,
    end_date        DATE DEFAULT NULL,
    is_active       TINYINT NOT NULL DEFAULT 1,
    avg_win_rate    DECIMAL(6,2) DEFAULT NULL,
    avg_holding_days INT UNSIGNED DEFAULT NULL,
    notes           VARCHAR(500) DEFAULT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_profile_strategy (profile_id, strategy_type),
    KEY ix_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='个人策略倾向';

-- 2.3 个人实际持股表
CREATE TABLE IF NOT EXISTS q_personal_holding (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    profile_id      BIGINT UNSIGNED NOT NULL DEFAULT 1,
    symbol          VARCHAR(10) NOT NULL,
    quantity        INT NOT NULL DEFAULT 0,
    avg_cost        DECIMAL(12,4) NOT NULL DEFAULT 0.00,
    total_cost      DECIMAL(16,2) NOT NULL DEFAULT 0.00,
    current_price   DECIMAL(12,4) DEFAULT NULL,
    market_value    DECIMAL(16,2) DEFAULT NULL,
    floating_pnl    DECIMAL(16,2) NOT NULL DEFAULT 0.00,
    floating_pnl_pct DECIMAL(10,4) DEFAULT NULL,
    position_ratio  DECIMAL(6,2) DEFAULT NULL COMMENT '占总仓位（%）',
    position_type   VARCHAR(15) NOT NULL DEFAULT 'LONG' COMMENT 'LONG/SHORT/CASH',
    holding_status  VARCHAR(15) NOT NULL DEFAULT 'OPEN' COMMENT 'OPEN/PROFIT_TARGET/STOP_LOSS/WATCH',
    first_buy_date  DATE DEFAULT NULL,
    last_buy_date   DATE DEFAULT NULL,
    first_buy_price DECIMAL(12,4) DEFAULT NULL,
    first_buy_pct   DECIMAL(6,2) DEFAULT NULL,
    target_price    DECIMAL(12,4) DEFAULT NULL,
    stop_loss_price DECIMAL(12,4) DEFAULT NULL,
    target_return_pct DECIMAL(8,2) DEFAULT NULL,
    entry_reason    VARCHAR(200) DEFAULT NULL,
    follow_strategy VARCHAR(30) DEFAULT NULL,
    related_news_id BIGINT UNSIGNED DEFAULT NULL,
    last_updated    DATETIME DEFAULT NULL,
    notes           VARCHAR(500) DEFAULT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_profile_symbol (profile_id, symbol),
    KEY ix_updated (updated_at),
    KEY ix_status (holding_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='个人实际持股';

-- 2.4 个人实盘交易记录
CREATE TABLE IF NOT EXISTS q_personal_trade (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    profile_id      BIGINT UNSIGNED NOT NULL DEFAULT 1,
    symbol          VARCHAR(10) NOT NULL,
    direction       VARCHAR(5) NOT NULL COMMENT 'BUY/SELL',
    trade_price     DECIMAL(12,4) NOT NULL,
    quantity        INT UNSIGNED NOT NULL,
    trade_value     DECIMAL(16,2) NOT NULL,
    commission      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    stamp_duty      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    profit          DECIMAL(16,2) DEFAULT NULL COMMENT '本笔盈亏（SELL时）',
    profit_pct      DECIMAL(10,4) DEFAULT NULL,
    holding_days    INT UNSIGNED DEFAULT NULL,
    trade_date      DATE NOT NULL,
    trade_time      DATETIME DEFAULT NULL,
    trade_type      VARCHAR(20) DEFAULT NULL COMMENT 'MANUAL/STRATEGY/CUT_LOSS/TAKE_PROFIT/REBALANCE/DIVIDEND',
    follow_strategy VARCHAR(30) DEFAULT NULL,
    entry_trade_id  BIGINT UNSIGNED DEFAULT NULL,
    emotional_state VARCHAR(20) DEFAULT NULL COMMENT 'CALM/EXCITED/FEARFUL/GREEDY',
    market_phase    VARCHAR(20) DEFAULT NULL COMMENT 'TREND/CONSOLIDATION/VOLATILE/BULL/BEAR',
    related_news_id BIGINT UNSIGNED DEFAULT NULL,
    review_notes    VARCHAR(500) DEFAULT NULL,
    review_rating   TINYINT DEFAULT NULL COMMENT '交易评分 1-5',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY ix_profile_date (profile_id, trade_date),
    KEY ix_symbol (symbol),
    KEY ix_direction (direction)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='个人实盘交易记录';

-- 2.5 分红送股记录
CREATE TABLE IF NOT EXISTS q_personal_dividend (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    profile_id      BIGINT UNSIGNED NOT NULL DEFAULT 1,
    symbol          VARCHAR(10) NOT NULL,
    dividend_type   VARCHAR(20) NOT NULL COMMENT 'CASH_DIVIDEND/SPLIT/SPINOFF/RIGHTS_ISSUE',
    record_date     DATE NOT NULL COMMENT '股权登记日',
    pay_date        DATE DEFAULT NULL COMMENT '派息日/除权日',
    dividend_per_share DECIMAL(10,4) DEFAULT NULL,
    tax_rate        DECIMAL(6,4) NOT NULL DEFAULT 0.10,
    tax_amount      DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    cash_received   DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    shares_before   INT UNSIGNED DEFAULT NULL,
    shares_after    INT UNSIGNED DEFAULT NULL,
    price_adjust    DECIMAL(12,4) DEFAULT NULL,
    total_value_gain DECIMAL(12,2) DEFAULT NULL,
    status          VARCHAR(15) NOT NULL DEFAULT 'DECLARED' COMMENT 'DECLARED/EX_DIVIDEND/PAID/RECEIVED',
    notes           VARCHAR(500) DEFAULT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_profile_symbol_record (profile_id, symbol, record_date, dividend_type),
    KEY ix_symbol (symbol),
    KEY ix_pay_date (pay_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='个人分红送股记录';


-- ───────────────────────────────────────────────────────────────
-- Part 3 · 新闻与政策
-- ───────────────────────────────────────────────────────────────

-- 3.1 市场新闻表
CREATE TABLE IF NOT EXISTS q_market_news (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(500) NOT NULL,
    content_summary VARCHAR(2000) DEFAULT NULL,
    content_full    TEXT DEFAULT NULL,
    source          VARCHAR(50) NOT NULL COMMENT 'Xinhua/CCTV/Sina/Caixin/Jiemian/Securities_Times/other',
    url             VARCHAR(1000) DEFAULT NULL,
    news_type       VARCHAR(20) NOT NULL COMMENT 'MACRO/INDUSTRY/COMPANY/MARKET/TECH/POLICY/INTERNATIONAL',
    related_symbols JSON DEFAULT NULL COMMENT '关联股票代码列表',
    related_sectors JSON DEFAULT NULL,
    related_indices JSON DEFAULT NULL,
    sentiment_score DECIMAL(5,4) DEFAULT NULL COMMENT '-1.0~1.0',
    sentiment_label VARCHAR(10) DEFAULT NULL COMMENT 'POSITIVE/NEGATIVE/NEUTRAL',
    sentiment_conf  DECIMAL(5,2) DEFAULT NULL COMMENT '置信度 0-100',
    impact_level    VARCHAR(10) DEFAULT 'LOW' COMMENT 'LOW/MEDIUM/HIGH/CRITICAL',
    impact_sectors  JSON DEFAULT NULL,
    market_reaction VARCHAR(50) DEFAULT NULL,
    publish_date    DATETIME NOT NULL,
    crawl_date      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY ix_publish (publish_date),
    KEY ix_type (news_type),
    KEY ix_sentiment (sentiment_score),
    KEY ix_impact (impact_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='市场新闻';

-- 3.2 政策文件表
CREATE TABLE IF NOT EXISTS q_policy_doc (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    doc_title       VARCHAR(500) NOT NULL,
    doc_number      VARCHAR(100) DEFAULT NULL COMMENT '文号',
    issuing_org     VARCHAR(100) NOT NULL COMMENT '发文机构',
    doc_level       VARCHAR(20) NOT NULL COMMENT 'CENTRAL/MINISTRY/LOCAL/EXCHANGE/SELF_REGULATION',
    doc_type        VARCHAR(30) NOT NULL COMMENT 'LAW/REGULATION/RULE/GUIDANCE/NOTICE/OPINION/STANDARD',
    content_summary VARCHAR(3000) DEFAULT NULL,
    content_full    LONGTEXT DEFAULT NULL,
    url             VARCHAR(1000) DEFAULT NULL,
    attachment_url   VARCHAR(1000) DEFAULT NULL,
    effective_date  DATE DEFAULT NULL,
    related_sectors JSON DEFAULT NULL,
    related_markets JSON DEFAULT NULL,
    impact_assessment VARCHAR(2000) DEFAULT NULL,
    stock_impact    VARCHAR(20) DEFAULT 'UNKNOWN' COMMENT 'POSITIVE/NEGATIVE/NEUTRAL/UNKNOWN',
    sector_impact   JSON DEFAULT NULL,
    market_sentiment VARCHAR(10) DEFAULT 'NEUTRAL',
    investor_confidence VARCHAR(10) DEFAULT 'UNCHANGED' COMMENT 'IMPROVED/DECLINED/UNCHANGED',
    keywords        JSON DEFAULT NULL,
    publish_date    DATE NOT NULL,
    crawl_date      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY ix_publish (publish_date),
    KEY ix_level (doc_level),
    KEY ix_effective (effective_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='政策文件';

-- 3.3 新闻-股票关联表（多对多）
CREATE TABLE IF NOT EXISTS q_news_stock_relation (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    news_id         BIGINT UNSIGNED NOT NULL,
    symbol          VARCHAR(10) NOT NULL,
    relation_type   VARCHAR(20) NOT NULL COMMENT 'DIRECTLY_RELATED/INDUSTRY_IMPACT/SENTIMENT_IMPACT/UNAFFECTED',
    impact_strength DECIMAL(5,2) DEFAULT NULL COMMENT '影响强度 0-100',
    price_correlation DECIMAL(8,4) DEFAULT NULL,
    note            VARCHAR(200) DEFAULT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_news_symbol (news_id, symbol),
    KEY ix_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻股票关联';


-- ───────────────────────────────────────────────────────────────
-- Part 4 · 宏观经济指标
-- ───────────────────────────────────────────────────────────────

-- 4.1 宏观经济指标表
CREATE TABLE IF NOT EXISTS q_macro_indicator (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    indicator_name  VARCHAR(100) NOT NULL,
    indicator_code  VARCHAR(30) NOT NULL COMMENT '如 GDP_Q1 / CPI_MM',
    country         VARCHAR(20) NOT NULL DEFAULT 'CN',
    region          VARCHAR(50) DEFAULT NULL,
    value           DECIMAL(18,4) DEFAULT NULL,
    unit            VARCHAR(20) DEFAULT NULL COMMENT '%/亿元/万人/美元',
    previous_value  DECIMAL(18,4) DEFAULT NULL,
    change_pct      DECIMAL(10,4) DEFAULT NULL COMMENT '环比变化（%）',
    yoy_change_pct  DECIMAL(10,4) DEFAULT NULL COMMENT '同比变化（%）',
    period_type     VARCHAR(10) NOT NULL COMMENT 'DAILY/MONTHLY/QUARTERLY/YEARLY',
    period_start    DATE NOT NULL,
    period_end      DATE DEFAULT NULL,
    figure          VARCHAR(10) DEFAULT 'ACTUAL' COMMENT 'PRELIMINARY/REVISED/ACTUAL/FORECAST',
    surprise        VARCHAR(10) DEFAULT NULL COMMENT 'BEAT/MISS/INLINE',
    surprise_pct    DECIMAL(8,4) DEFAULT NULL,
    market_consensus DECIMAL(18,4) DEFAULT NULL,
    source_org      VARCHAR(100) DEFAULT NULL,
    publish_date    DATETIME NOT NULL,
    next_publish    DATE DEFAULT NULL,
    category        VARCHAR(30) NOT NULL COMMENT 'GDP/PRICE/PMI/TRADE/FINANCE/EMPLOYMENT/CONSUMER/PROPERTY/INTEREST_RATE/EXCHANGE_RATE',
    importance      VARCHAR(10) NOT NULL DEFAULT 'MEDIUM' COMMENT 'LOW/MEDIUM/HIGH/CRITICAL',
    is_monetary     TINYINT NOT NULL DEFAULT 0 COMMENT '是否货币政策指标',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_code_period (indicator_code, period_type, period_start),
    KEY ix_publish (publish_date),
    KEY ix_category (category),
    KEY ix_importance (importance)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='宏观经济指标';

-- 4.2 央行货币政策记录
CREATE TABLE IF NOT EXISTS q_central_bank_policy (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    bank_name       VARCHAR(50) NOT NULL DEFAULT 'PBOC' COMMENT 'PBOC/FED/ECB/BOJ/BOE',
    policy_type     VARCHAR(30) NOT NULL COMMENT 'RATE_CUT/RATE_HIKE/RRR_CUT/RRR_RAISE/QE/TAPERING/LTRO/OMO',
    rate_before     DECIMAL(10,4) DEFAULT NULL COMMENT '政策前利率（%）',
    rate_after      DECIMAL(10,4) DEFAULT NULL COMMENT '政策后利率（%）',
    rate_change     DECIMAL(8,4) DEFAULT NULL COMMENT '利率变化（bp）',
    rrr_before      DECIMAL(8,4) DEFAULT NULL COMMENT '政策前RRR（%）',
    rrr_after       DECIMAL(8,4) DEFAULT NULL COMMENT '政策后RRR（%）',
    amount          DECIMAL(18,2) DEFAULT NULL COMMENT '操作金额',
    tenor_days      INT UNSIGNED DEFAULT NULL COMMENT '期限天数',
    description     VARCHAR(500) DEFAULT NULL,
    announcement_url VARCHAR(1000) DEFAULT NULL,
    announce_date   DATE NOT NULL,
    effective_date  DATE DEFAULT NULL,
    market_impact   VARCHAR(10) DEFAULT 'NEUTRAL' COMMENT '对A股影响：POSITIVE/NEGATIVE/NEUTRAL',
    a_share_probability DECIMAL(6,2) DEFAULT NULL COMMENT '对A股影响概率（%）',
    sector_impact   JSON DEFAULT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY ix_announce (announce_date),
    KEY ix_effective (effective_date),
    KEY ix_bank (bank_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='央行货币政策';

-- 4.3 重大市场事件表（用于事件驱动策略）
CREATE TABLE IF NOT EXISTS q_market_event (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_name      VARCHAR(200) NOT NULL,
    event_type      VARCHAR(30) NOT NULL COMMENT 'EARNINGS/IPO/DELISTING/MERGER/SPINOFF/RIGHTS/INDEX_REBALANCE/OPTIONS_EXPIRY/TARIFF/ELECTION',
    symbol          VARCHAR(10) DEFAULT NULL,
    related_sectors JSON DEFAULT NULL,
    related_indices JSON DEFAULT NULL,
    description     VARCHAR(1000) DEFAULT NULL,
    event_date      DATE NOT NULL,
    expected_impact VARCHAR(20) DEFAULT 'UNKNOWN' COMMENT 'UP/DOWN/SIDEWAYS/UNKNOWN',
    historical_winrate DECIMAL(6,2) DEFAULT NULL COMMENT '历史类似事件胜率（%）',
    historical_avg_return DECIMAL(10,4) DEFAULT NULL COMMENT '历史平均收益（%）',
    confidence      DECIMAL(5,2) DEFAULT NULL COMMENT '预期置信度 0-100',
    actual_return_1d DECIMAL(10,4) DEFAULT NULL COMMENT '事件后1日收益（%）',
    actual_return_3d DECIMAL(10,4) DEFAULT NULL COMMENT '事件后3日收益（%）',
    actual_return_5d DECIMAL(10,4) DEFAULT NULL COMMENT '事件后5日收益（%）',
    actual_outcome  VARCHAR(20) DEFAULT NULL,
    related_news_ids JSON DEFAULT NULL,
    related_policy_ids JSON DEFAULT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_event_date (event_date),
    KEY ix_symbol (symbol),
    KEY ix_type (event_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='重大市场事件';


-- ═════════════════════════════════════════════════════════════════
-- 初始数据
-- ═════════════════════════════════════════════════════════════════

INSERT INTO q_personal_profile (
    investor_name, age, risk_tolerance, investment_goal,
    investment_horizon, expected_return, max_loss_tolerance,
    trading_experience, familiar_strategies, investable_asset,
    annual_income, income_source,
    prefer_sectors, avoid_sectors, prefer_capital_size,
    prefer_dividend, prefer_growth, prefer_value,
    liquidity_need, tax_considerations,
    trading_frequency, avg_holding_days, bias_patterns,
    current_cash, total_market_value, total_assets
) VALUES (
    'Tank', 36, 'MODERATE',
    '追求财务自由，通过量化策略实现稳健增值，关注长期复利效应',
    'LONG', 15.00, -20.00,
    'SENIOR',
    '["趋势跟踪", "价值投资", "网格交易", "动量策略"]',
    4000000.00,
    500000.00, '工资+投资收益',
    '["银行", "白酒", "新能源", "消费"]',
    '["ST", "高杠杆", "纯题材炒作"]',
    'LARGE',
    1, 1, 1,
    'LOW', 0,
    'OCCASIONAL', 90,
    '["loss_aversion", "overconfidence"]',
    57376.09, 0.00, 57376.09
) ON DUPLICATE KEY UPDATE updated_at=NOW();

INSERT INTO q_personal_strategy_pref (profile_id, strategy_type, preference_score, start_date, is_active, notes) VALUES
(1, 'trend_following', 80.00, '2024-01-01', 1, '主要策略，顺势而为'),
(1, 'value_investing', 75.00, '2024-01-01', 1, '核心持仓逻辑'),
(1, 'momentum', 65.00, '2025-01-01', 1, '动量交易增强收益'),
(1, 'grid_trading', 70.00, '2025-06-01', 1, '震荡市稳定现金流'),
(1, 'mean_reversion', 50.00, '2025-01-01', 0, '尝试过，效果一般')
ON DUPLICATE KEY UPDATE preference_score=VALUES(preference_score);

SELECT 'done' as result;

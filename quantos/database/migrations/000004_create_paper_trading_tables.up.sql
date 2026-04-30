-- 模拟盘交易系统数据库表
-- 版本: 1.0.0
-- 创建时间: 2026-04-29

-- 模拟账户表
CREATE TABLE IF NOT EXISTS q_paper_account (
    id bigint unsigned NOT NULL AUTO_INCREMENT,
    user_id bigint unsigned NOT NULL DEFAULT 1 COMMENT '用户ID',
    initial_capital decimal(20,2) NOT NULL DEFAULT 100000.00 COMMENT '初始资金',
    current_capital decimal(20,2) NOT NULL DEFAULT 60000.00 COMMENT '当前现金',
    total_value decimal(20,2) NOT NULL DEFAULT 100000.00 COMMENT '总资产',
    total_pnl decimal(20,2) DEFAULT 0.00 COMMENT '总盈亏',
    created_at datetime DEFAULT CURRENT_TIMESTAMP,
    updated_at datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模拟账户表';

-- 持仓表
CREATE TABLE IF NOT EXISTS q_paper_position (
    id bigint unsigned NOT NULL AUTO_INCREMENT,
    account_id bigint unsigned NOT NULL COMMENT '账户ID',
    symbol varchar(20) NOT NULL COMMENT '股票代码',
    symbol_name varchar(100) COMMENT '股票名称',
    shares int NOT NULL COMMENT '股数',
    avg_cost decimal(10,4) NOT NULL COMMENT '成本价',
    stop_loss decimal(10,4) COMMENT '止损价',
    take_profit1 decimal(10,4) COMMENT '止盈价1',
    take_profit2 decimal(10,4) COMMENT '止盈价2',
    entry_date date NOT NULL COMMENT '入场日期',
    reason varchar(500) COMMENT '买入理由',
    rsi decimal(7,4) COMMENT '入场RSI',
    stop_moved tinyint(1) DEFAULT 0 COMMENT '止损线是否已移动',
    created_at datetime DEFAULT CURRENT_TIMESTAMP,
    updated_at datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_account_id (account_id),
    KEY idx_symbol (symbol),
    UNIQUE KEY uk_account_symbol (account_id, symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模拟盘持仓表';

-- 交易记录表
CREATE TABLE IF NOT EXISTS q_paper_trade (
    id bigint unsigned NOT NULL AUTO_INCREMENT,
    account_id bigint unsigned NOT NULL COMMENT '账户ID',
    trade_date date NOT NULL COMMENT '交易日期',
    action varchar(10) NOT NULL COMMENT 'BUY/SELL',
    symbol varchar(20) NOT NULL COMMENT '股票代码',
    symbol_name varchar(100) COMMENT '股票名称',
    price decimal(10,4) NOT NULL COMMENT '成交价',
    shares int NOT NULL COMMENT '股数',
    amount decimal(20,2) NOT NULL COMMENT '成交金额',
    avg_cost decimal(10,4) COMMENT '成本价(卖出时)',
    pnl decimal(20,2) COMMENT '盈亏金额',
    pnl_pct decimal(10,4) COMMENT '盈亏比例',
    reason varchar(500) COMMENT '交易理由',
    hold_days int COMMENT '持有天数',
    cash_after decimal(20,2) COMMENT '交易后现金',
    created_at datetime DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_account_id (account_id),
    KEY idx_trade_date (trade_date),
    KEY idx_symbol (symbol),
    KEY idx_action (action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模拟盘交易记录表';

-- 策略参数表（用于自主进化）
CREATE TABLE IF NOT EXISTS q_strategy_params (
    id bigint unsigned NOT NULL AUTO_INCREMENT,
    param_key varchar(100) NOT NULL COMMENT '参数键',
    param_value decimal(20,4) NOT NULL COMMENT '参数值',
    win_rate decimal(5,2) COMMENT '对应胜率',
    avg_win decimal(10,2) COMMENT '对应均盈',
    avg_loss decimal(10,2) COMMENT '对应均亏',
    trade_count int DEFAULT 0 COMMENT '样本数',
    updated_at datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_param_key (param_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='策略参数表';

-- 每日统计表
CREATE TABLE IF NOT EXISTS q_daily_stats (
    id bigint unsigned NOT NULL AUTO_INCREMENT,
    stat_date date NOT NULL COMMENT '统计日期',
    initial_capital decimal(20,2) COMMENT '初始资金',
    total_value decimal(20,2) COMMENT '总资产',
    positions_value decimal(20,2) COMMENT '持仓市值',
    cash decimal(20,2) COMMENT '现金',
    daily_pnl decimal(20,2) COMMENT '当日盈亏',
    daily_pnl_pct decimal(10,4) COMMENT '当日盈亏比例',
    total_pnl decimal(20,2) COMMENT '累计盈亏',
    positions int COMMENT '持仓数',
    trades int COMMENT '当日交易数',
    created_at datetime DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_stat_date (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日统计表';

-- 进化历史记录表
CREATE TABLE IF NOT EXISTS q_evolution_log (
    id bigint unsigned NOT NULL AUTO_INCREMENT,
    param_key varchar(100) NOT NULL COMMENT '参数键',
    old_value decimal(20,4) COMMENT '原参数值',
    new_value decimal(20,4) COMMENT '新参数值',
    reason varchar(500) COMMENT '调整原因',
    old_win_rate decimal(5,2) COMMENT '原胜率',
    new_win_rate decimal(5,2) COMMENT '新胜率',
    created_at datetime DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_param_key (param_key),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='进化历史记录表';

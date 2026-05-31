-- ============================================================
-- QuantOS 交易系统核心表
-- 版本: 1.1.0
-- 创建时间: 2026-05-21
-- 作者: Tank
-- 说明: 历史行情 + 模拟盘 + 个人交易记录
-- ============================================================

-- ----------------------------------------------------------
-- 1. 股票池表（Tank自选股/关注股）
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `q_stock_pool` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `symbol` varchar(20) NOT NULL COMMENT '股票代码',
    `name` varchar(100) NOT NULL COMMENT '股票名称',
    `market` varchar(10) NOT NULL COMMENT '市场: SH/SZ/BJ',
    `industry` varchar(100) DEFAULT NULL COMMENT '行业',
    `sector` varchar(100) DEFAULT NULL COMMENT '板块',
    `status` tinyint(4) NOT NULL DEFAULT 1 COMMENT '状态: 1-正常, 2-停牌, 3-退市',
    `is_watched` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否关注: 0-否, 1-是',
    `is_paper_simulated` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否参与模拟盘: 0-否, 1-是',
    `notes` varchar(500) DEFAULT NULL COMMENT '备注',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol` (`symbol`),
    KEY `idx_market` (`market`),
    KEY `idx_industry` (`industry`),
    KEY `idx_watched` (`is_watched`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='股票池表';

-- ----------------------------------------------------------
-- 2. 历史日线行情表（核心行情数据）
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `q_daily_kline` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `symbol` varchar(20) NOT NULL COMMENT '股票代码',
    `symbol_name` varchar(100) DEFAULT NULL COMMENT '股票名称',
    `trade_date` date NOT NULL COMMENT '交易日期',
    `open_price` decimal(10,4) NOT NULL COMMENT '开盘价',
    `high_price` decimal(10,4) NOT NULL COMMENT '最高价',
    `low_price` decimal(10,4) NOT NULL COMMENT '最低价',
    `close_price` decimal(10,4) NOT NULL COMMENT '收盘价',
    `prev_close` decimal(10,4) DEFAULT NULL COMMENT '昨收价',
    `change_pct` decimal(8,4) DEFAULT NULL COMMENT '涨跌幅(%)',
    `volume` bigint DEFAULT NULL COMMENT '成交量(股)',
    `amount` decimal(20,2) DEFAULT NULL COMMENT '成交额(元)',
    `turnover_rate` decimal(8,4) DEFAULT NULL COMMENT '换手率(%)',
    `market` varchar(10) NOT NULL COMMENT '市场: SH/SZ/BJ',
    -- 技术指标
    `ma5` decimal(10,4) DEFAULT NULL COMMENT '5日均线',
    `ma10` decimal(10,4) DEFAULT NULL COMMENT '10日均线',
    `ma20` decimal(10,4) DEFAULT NULL COMMENT '20日均线',
    `ma60` decimal(10,4) DEFAULT NULL COMMENT '60日均线',
    `rsi6` decimal(7,4) DEFAULT NULL COMMENT 'RSI(6日)',
    `rsi12` decimal(7,4) DEFAULT NULL COMMENT 'RSI(12日)',
    `rsi24` decimal(7,4) DEFAULT NULL COMMENT 'RSI(24日)',
    `macd_dif` decimal(10,6) DEFAULT NULL COMMENT 'MACD DIF',
    `macd_dea` decimal(10,6) DEFAULT NULL COMMENT 'MACD DEA',
    `macd_hist` decimal(10,6) DEFAULT NULL COMMENT 'MACD 柱',
    `boll_upper` decimal(10,4) DEFAULT NULL COMMENT '布林上轨',
    `boll_mid` decimal(10,4) DEFAULT NULL COMMENT '布林中轨',
    `boll_lower` decimal(10,4) DEFAULT NULL COMMENT '布林下轨',
    `kdj_k` decimal(7,4) DEFAULT NULL COMMENT 'KDJ K值',
    `kdj_d` decimal(7,4) DEFAULT NULL COMMENT 'KDJ D值',
    `kdj_j` decimal(7,4) DEFAULT NULL COMMENT 'KDJ J值',
    `atr` decimal(10,4) DEFAULT NULL COMMENT 'ATR真实波幅',
    `data_source` varchar(20) NOT NULL DEFAULT 'akshare' COMMENT '数据源',
    `is_adj_close` tinyint(1) NOT NULL DEFAULT 1 COMMENT '是否复权: 0-不复权, 1-前复权, 2-后复权',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol_date` (`symbol`, `trade_date`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_symbol_date_desc` (`symbol`, `trade_date` DESC),
    KEY `idx_market` (`market`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='历史日线行情表';

-- ----------------------------------------------------------
-- 3. 模拟账户表（纠正0004错误，增加核心字段）
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `q_paper_account` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `user_id` bigint unsigned NOT NULL DEFAULT 1 COMMENT '用户ID',
    `name` varchar(100) NOT NULL DEFAULT '默认模拟账户' COMMENT '账户名称',
    `status` tinyint(4) NOT NULL DEFAULT 1 COMMENT '状态: 1-正常, 2-暂停, 3-已重置',
    -- 资金配置
    `initial_capital` decimal(20,2) NOT NULL DEFAULT 100000.00 COMMENT '初始资金',
    `cash_reserve` decimal(20,2) NOT NULL DEFAULT 40000.00 COMMENT '保留现金',
    `current_capital` decimal(20,2) NOT NULL DEFAULT 60000.00 COMMENT '当前可用资金(不含持仓)',
    `total_value` decimal(20,2) NOT NULL DEFAULT 100000.00 COMMENT '总资产(含持仓市值)',
    `positions_value` decimal(20,2) NOT NULL DEFAULT 0.00 COMMENT '持仓市值',
    -- 盈亏统计
    `total_pnl` decimal(20,2) DEFAULT 0.00 COMMENT '累计已实现盈亏',
    `total_return_pct` decimal(10,4) DEFAULT 0.0000 COMMENT '累计收益率(%)',
    -- 交易统计
    `total_trades` int NOT NULL DEFAULT 0 COMMENT '总交易次数(含买卖)',
    `buy_trades` int NOT NULL DEFAULT 0 COMMENT '买入次数',
    `sell_trades` int NOT NULL DEFAULT 0 COMMENT '卖出次数',
    `win_trades` int NOT NULL DEFAULT 0 COMMENT '盈利次数',
    `loss_trades` int NOT NULL DEFAULT 0 COMMENT '亏损次数',
    `win_rate` decimal(5,4) DEFAULT 0.0000 COMMENT '胜率',
    `avg_win` decimal(20,2) DEFAULT 0.00 COMMENT '平均盈利金额',
    `avg_loss` decimal(20,2) DEFAULT 0.00 COMMENT '平均亏损金额',
    -- 风控参数
    `stop_loss_pct` decimal(5,4) NOT NULL DEFAULT 0.0300 COMMENT '止损比例(%)',
    `take_profit1_pct` decimal(5,4) NOT NULL DEFAULT 0.0500 COMMENT '第一止盈比例(%)',
    `take_profit2_pct` decimal(5,4) NOT NULL DEFAULT 0.0800 COMMENT '第二止盈比例(%)',
    `max_position_value` decimal(20,2) NOT NULL DEFAULT 15000.00 COMMENT '单只最大持仓金额',
    `max_positions` int NOT NULL DEFAULT 4 COMMENT '最大持仓只数',
    -- 运行时状态
    `last_reset_at` datetime DEFAULT NULL COMMENT '最后重置时间',
    `last_trade_at` datetime DEFAULT NULL COMMENT '最后交易时间',
    `note` varchar(500) DEFAULT NULL COMMENT '备注',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_id` (`user_id`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模拟账户表';

-- ----------------------------------------------------------
-- 4. 模拟盘持仓表
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `q_paper_position` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `account_id` bigint unsigned NOT NULL COMMENT '账户ID',
    `symbol` varchar(20) NOT NULL COMMENT '股票代码',
    `symbol_name` varchar(100) DEFAULT NULL COMMENT '股票名称',
    `shares` int NOT NULL COMMENT '持股数(手×100)',
    `avg_cost` decimal(10,4) NOT NULL COMMENT '持仓成本价',
    `current_price` decimal(10,4) DEFAULT NULL COMMENT '当前市场价',
    `market_value` decimal(20,2) DEFAULT NULL COMMENT '持仓市值',
    `unrealized_pnl` decimal(20,2) DEFAULT NULL COMMENT '未实现盈亏',
    `unrealized_pnl_pct` decimal(10,4) DEFAULT NULL COMMENT '未实现盈亏比例(%)',
    -- 止损止盈线
    `stop_loss` decimal(10,4) NOT NULL COMMENT '止损价',
    `take_profit1` decimal(10,4) NOT NULL COMMENT '第一止盈价',
    `take_profit2` decimal(10,4) NOT NULL COMMENT '第二止盈价',
    `stop_moved` tinyint(1) NOT NULL DEFAULT 0 COMMENT '止损线是否已移动',
    -- 入场信息
    `entry_date` date NOT NULL COMMENT '入场日期',
    `entry_price` decimal(10,4) NOT NULL COMMENT '入场价格',
    `entry_reason` varchar(500) DEFAULT NULL COMMENT '入场理由',
    `entry_rsi` decimal(7,4) DEFAULT NULL COMMENT '入场时RSI',
    `entry_ma5` decimal(10,4) DEFAULT NULL COMMENT '入场时MA5',
    `entry_ma20` decimal(10,4) DEFAULT NULL COMMENT '入场时MA20',
    `entry_ma60` decimal(10,4) DEFAULT NULL COMMENT '入场时MA60',
    -- 持仓时长
    `hold_days` int DEFAULT 0 COMMENT '持有天数',
    `last_check_price` decimal(10,4) DEFAULT NULL COMMENT '上次检查价格',
    `last_check_at` datetime DEFAULT NULL COMMENT '上次检查时间',
    PRIMARY KEY (`id`),
    KEY `idx_account_id` (`account_id`),
    KEY `idx_symbol` (`symbol`),
    UNIQUE KEY `uk_account_symbol` (`account_id`, `symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模拟盘持仓表';

-- ----------------------------------------------------------
-- 5. 交易记录表（核心交易日志）
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `q_trade_log` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `account_id` bigint unsigned NOT NULL COMMENT '账户ID',
    `trade_no` varchar(64) NOT NULL COMMENT '交易编号(YYYYMMDD-序号)',
    `trade_date` date NOT NULL COMMENT '交易日期',
    `trade_time` time DEFAULT NULL COMMENT '交易时间',
    `action` varchar(10) NOT NULL COMMENT 'BUY/SELL',
    `action_type` varchar(20) NOT NULL COMMENT '交易类型: MANUAL/AUTO/STOP_LOSS/TAKE_PROFIT1/TAKE_PROFIT2/SIM_END',
    `symbol` varchar(20) NOT NULL COMMENT '股票代码',
    `symbol_name` varchar(100) DEFAULT NULL COMMENT '股票名称',
    `price` decimal(10,4) NOT NULL COMMENT '成交价格',
    `shares` int NOT NULL COMMENT '成交数量(股)',
    `amount` decimal(20,2) NOT NULL COMMENT '成交金额(元)',
    `commission` decimal(10,2) DEFAULT 0.00 COMMENT '手续费(模拟为0)',
    `cash_before` decimal(20,2) NOT NULL COMMENT '交易前现金',
    `cash_after` decimal(20,2) NOT NULL COMMENT '交易后现金',
    -- 持仓关联(SELL时记录入场信息)
    `position_id` bigint unsigned DEFAULT NULL COMMENT '关联持仓ID',
    `avg_cost` decimal(10,4) DEFAULT NULL COMMENT '持仓成本价(卖出时)',
    `entry_price` decimal(10,4) DEFAULT NULL COMMENT '入场价格(卖出时)',
    `entry_date` date DEFAULT NULL COMMENT '入场日期(卖出时)',
    -- 盈亏计算(SELL时)
    `pnl` decimal(20,2) DEFAULT NULL COMMENT '盈亏金额',
    `pnl_pct` decimal(10,4) DEFAULT NULL COMMENT '盈亏比例(%)',
    `hold_days` int DEFAULT NULL COMMENT '持有天数',
    `is_win` tinyint(1) DEFAULT NULL COMMENT '是否盈利: 0-亏, 1-盈',
    -- 入场理由(买入时)
    `entry_reason` varchar(500) DEFAULT NULL COMMENT '入场理由',
    `entry_rsi` decimal(7,4) DEFAULT NULL COMMENT '入场RSI',
    -- 备注
    `note` varchar(500) DEFAULT NULL COMMENT '备注',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_trade_no` (`trade_no`),
    KEY `idx_account_id` (`account_id`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_symbol` (`symbol`),
    KEY `idx_action` (`action`),
    KEY `idx_action_type` (`action_type`),
    KEY `idx_is_win` (`is_win`),
    KEY `idx_symbol_date` (`symbol`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='交易记录表';

-- ----------------------------------------------------------
-- 6. 每日账户快照表（用于回测分析和净值曲线）
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `q_daily_snapshot` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `account_id` bigint unsigned NOT NULL COMMENT '账户ID',
    `snapshot_date` date NOT NULL COMMENT '快照日期',
    `total_value` decimal(20,2) NOT NULL COMMENT '总资产',
    `cash` decimal(20,2) NOT NULL COMMENT '现金',
    `positions_value` decimal(20,2) NOT NULL COMMENT '持仓市值',
    `positions_count` int NOT NULL DEFAULT 0 COMMENT '持仓只数',
    `total_pnl` decimal(20,2) DEFAULT 0.00 COMMENT '累计盈亏',
    `daily_pnl` decimal(20,2) DEFAULT 0.00 COMMENT '当日盈亏',
    `daily_pnl_pct` decimal(10,4) DEFAULT 0.0000 COMMENT '当日盈亏比例(%)',
    `return_pct` decimal(10,4) DEFAULT 0.0000 COMMENT '累计收益率(%)',
    `return_vs_initial` decimal(10,4) DEFAULT 0.0000 COMMENT '相对初始资金收益率(%)',
    `max_drawdown` decimal(10,4) DEFAULT 0.0000 COMMENT '历史最大回撤(%)',
    `trades_count` int DEFAULT 0 COMMENT '当日交易次数',
    `benchmark_value` decimal(20,2) DEFAULT NULL COMMENT '同期大盘指数点位(可选)',
    `note` varchar(500) DEFAULT NULL COMMENT '备注',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_account_date` (`account_id`, `snapshot_date`),
    KEY `idx_snapshot_date` (`snapshot_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日账户快照表';

-- ----------------------------------------------------------
-- 7. 进化历史表（策略参数自适应调整记录）
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `q_evolution_log` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `account_id` bigint unsigned NOT NULL COMMENT '账户ID',
    `param_key` varchar(100) NOT NULL COMMENT '参数键: stop_loss_pct/take_profit1_pct/...',
    `param_name` varchar(100) DEFAULT NULL COMMENT '参数名称',
    `old_value` decimal(20,4) DEFAULT NULL COMMENT '原参数值',
    `new_value` decimal(20,4) DEFAULT NULL COMMENT '新参数值',
    `change_reason` varchar(500) DEFAULT NULL COMMENT '调整原因',
    `evidence_trades` int DEFAULT 0 COMMENT '调整依据的交易样本数',
    `old_win_rate` decimal(5,4) DEFAULT NULL COMMENT '原胜率',
    `new_win_rate` decimal(5,4) DEFAULT NULL COMMENT '新胜率',
    `trigger_type` varchar(20) DEFAULT NULL COMMENT '触发类型: AUTO/MANUAL/BENCHMARK',
    `status` tinyint(4) NOT NULL DEFAULT 1 COMMENT '状态: 1-生效, 2-回滚',
    PRIMARY KEY (`id`),
    KEY `idx_account_id` (`account_id`),
    KEY `idx_param_key` (`param_key`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='进化历史表';

-- ----------------------------------------------------------
-- 8. 基准指数表（用于对比回测收益）
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS `q_benchmark_index` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `index_code` varchar(20) NOT NULL COMMENT '指数代码: 000001(上证), 399001(深证), 399006(创业板)',
    `index_name` varchar(100) NOT NULL COMMENT '指数名称',
    `trade_date` date NOT NULL COMMENT '交易日期',
    `open_value` decimal(12,4) DEFAULT NULL COMMENT '开盘点位',
    `high_value` decimal(12,4) DEFAULT NULL COMMENT '最高点位',
    `low_value` decimal(12,4) DEFAULT NULL COMMENT '最低点位',
    `close_value` decimal(12,4) NOT NULL COMMENT '收盘点位',
    `prev_close` decimal(12,4) DEFAULT NULL COMMENT '昨收点位',
    `change_pct` decimal(8,4) DEFAULT NULL COMMENT '涨跌幅(%)',
    `volume` bigint DEFAULT NULL COMMENT '成交量',
    `amount` decimal(20,2) DEFAULT NULL COMMENT '成交额',
    `data_source` varchar(20) NOT NULL DEFAULT 'akshare' COMMENT '数据源',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_index_date` (`index_code`, `trade_date`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_index_name` (`index_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='基准指数表';

-- ----------------------------------------------------------
-- 种子数据: Tank默认模拟账户
-- ----------------------------------------------------------
INSERT INTO `q_paper_account` (user_id, name, initial_capital, cash_reserve, current_capital, total_value, positions_value, total_pnl)
VALUES (1, 'Tank默认模拟账户', 100000.00, 40000.00, 60000.00, 100000.00, 0.00, 0.00)
ON DUPLICATE KEY UPDATE name = VALUES(name);

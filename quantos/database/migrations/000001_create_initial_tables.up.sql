-- 初始化数据库表结构
-- 执行时间: 2025年12月25日
-- 版本: 1.0.0

-- 创建用户表
CREATE TABLE IF NOT EXISTS `q_users` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT NULL COMMENT '创建时间',
    `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
    `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
    `username` varchar(50) NOT NULL COMMENT '用户名',
    `email` varchar(100) NOT NULL COMMENT '邮箱地址',
    `password` varchar(255) NOT NULL COMMENT '密码哈希',
    `phone` varchar(20) DEFAULT NULL COMMENT '手机号',
    `avatar` varchar(500) DEFAULT NULL COMMENT '头像URL',
    `nickname` varchar(50) DEFAULT NULL COMMENT '昵称',
    `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态: 1-正常, 2-禁用',
    `role` tinyint(4) NOT NULL DEFAULT '4' COMMENT '角色: 1-管理员, 2-交易员, 3-分析师, 4-投资者',
    `subscription` tinyint(4) NOT NULL DEFAULT '1' COMMENT '订阅计划: 1-免费, 2-专业, 3-企业',
    `last_login_at` datetime DEFAULT NULL COMMENT '最后登录时间',
    `last_login_ip` varchar(45) DEFAULT NULL COMMENT '最后登录IP',
    `risk_tolerance` decimal(5,4) DEFAULT '0.5000' COMMENT '风险容忍度(0-1)',
    `time_horizon` tinyint(4) DEFAULT '2' COMMENT '投资期限: 1-短期, 2-中期, 3-长期',
    `total_assets` decimal(20,2) DEFAULT '0.00' COMMENT '总资产',
    `total_returns` decimal(10,4) DEFAULT '0.0000' COMMENT '总收益率',
    `win_rate` decimal(5,4) DEFAULT '0.0000' COMMENT '胜率',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`),
    UNIQUE KEY `uk_email` (`email`),
    KEY `idx_status` (`status`),
    KEY `idx_role` (`role`),
    KEY `idx_subscription` (`subscription`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 创建策略表
CREATE TABLE IF NOT EXISTS `q_strategies` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT NULL COMMENT '创建时间',
    `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
    `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
    `user_id` bigint unsigned NOT NULL COMMENT '用户ID',
    `name` varchar(100) NOT NULL COMMENT '策略名称',
    `description` text COMMENT '策略描述',
    `code` longtext COMMENT '策略代码',
    `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态: 1-草稿, 2-测试, 3-发布, 4-运行, 5-暂停, 6-停止',
    `type` tinyint(4) NOT NULL DEFAULT '1' COMMENT '类型: 1-手动, 2-AI生成, 3-模板',
    `category` varchar(50) DEFAULT NULL COMMENT '策略分类',
    `max_drawdown` decimal(7,4) DEFAULT '0.0000' COMMENT '最大回撤',
    `sharpe_ratio` decimal(7,4) DEFAULT '0.0000' COMMENT '夏普比率',
    `annual_return` decimal(7,4) DEFAULT '0.0000' COMMENT '年化收益率',
    `volatility` decimal(7,4) DEFAULT '0.0000' COMMENT '波动率',
    `parameters` json DEFAULT NULL COMMENT '策略参数',
    `last_run_at` datetime DEFAULT NULL COMMENT '最后运行时间',
    `run_count` int DEFAULT '0' COMMENT '运行次数',
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_status` (`status`),
    KEY `idx_type` (`type`),
    KEY `idx_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='策略表';

-- 创建投资组合表
CREATE TABLE IF NOT EXISTS `q_portfolios` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT NULL COMMENT '创建时间',
    `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
    `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
    `user_id` bigint unsigned NOT NULL COMMENT '用户ID',
    `name` varchar(100) NOT NULL COMMENT '组合名称',
    `description` text COMMENT '组合描述',
    `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态: 1-正常, 2-暂停, 3-清盘',
    `initial_cash` decimal(20,2) NOT NULL COMMENT '初始资金',
    `total_value` decimal(20,2) DEFAULT '0.00' COMMENT '总价值',
    `total_return` decimal(10,4) DEFAULT '0.0000' COMMENT '总收益率',
    `max_drawdown` decimal(7,4) DEFAULT '0.0000' COMMENT '最大回撤',
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='投资组合表';

-- 创建持仓表
CREATE TABLE IF NOT EXISTS `q_positions` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT NULL COMMENT '创建时间',
    `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
    `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
    `portfolio_id` bigint unsigned NOT NULL COMMENT '组合ID',
    `symbol` varchar(20) NOT NULL COMMENT '证券代码',
    `symbol_name` varchar(100) DEFAULT NULL COMMENT '证券名称',
    `quantity` decimal(20,4) NOT NULL COMMENT '持仓数量',
    `avg_cost` decimal(10,4) NOT NULL COMMENT '平均成本',
    `current_price` decimal(10,4) DEFAULT '0.0000' COMMENT '当前价格',
    `market_value` decimal(20,2) DEFAULT '0.00' COMMENT '市值',
    `unrealized_pnl` decimal(20,2) DEFAULT '0.00' COMMENT '未实现盈亏',
    `realized_pnl` decimal(20,2) DEFAULT '0.00' COMMENT '已实现盈亏',
    PRIMARY KEY (`id`),
    KEY `idx_portfolio_id` (`portfolio_id`),
    KEY `idx_symbol` (`symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='持仓表';

-- 创建市场行情数据表
CREATE TABLE IF NOT EXISTS `q_market_data` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT NULL COMMENT '创建时间',
    `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
    `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
    `symbol` varchar(20) NOT NULL COMMENT '证券代码',
    `symbol_name` varchar(100) DEFAULT NULL COMMENT '证券名称',
    `open_price` decimal(10,4) DEFAULT NULL COMMENT '开盘价',
    `high_price` decimal(10,4) DEFAULT NULL COMMENT '最高价',
    `low_price` decimal(10,4) DEFAULT NULL COMMENT '最低价',
    `close_price` decimal(10,4) NOT NULL COMMENT '收盘价',
    `volume` bigint DEFAULT NULL COMMENT '成交量',
    `amount` decimal(20,2) DEFAULT NULL COMMENT '成交额',
    `trade_date` date NOT NULL COMMENT '交易日期',
    `trade_time` time DEFAULT NULL COMMENT '交易时间',
    `market` varchar(10) NOT NULL COMMENT '市场代码',
    `data_source` tinyint(4) NOT NULL DEFAULT '1' COMMENT '数据源: 1-实时, 2-历史',
    `ma5` decimal(10,4) DEFAULT NULL COMMENT '5日均线',
    `ma10` decimal(10,4) DEFAULT NULL COMMENT '10日均线',
    `ma20` decimal(10,4) DEFAULT NULL COMMENT '20日均线',
    `rsi` decimal(7,4) DEFAULT NULL COMMENT 'RSI指标',
    `macd` decimal(10,6) DEFAULT NULL COMMENT 'MACD指标',
    PRIMARY KEY (`id`),
    KEY `idx_symbol_time` (`symbol`, `trade_date`, `trade_time`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_market` (`market`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='市场行情数据表';

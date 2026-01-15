-- StockAPI功能扩展数据库表结构
-- 执行时间: 2025年12月25日
-- 版本: 1.0.0

-- 创建股票基础信息表
CREATE TABLE IF NOT EXISTS `q_stock_basic` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT NULL COMMENT '创建时间',
    `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
    `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
    `symbol` varchar(20) NOT NULL COMMENT '股票代码',
    `name` varchar(100) NOT NULL COMMENT '股票名称',
    `full_name` varchar(200) DEFAULT NULL COMMENT '股票全称',
    `market` varchar(10) NOT NULL COMMENT '市场代码',
    `exchange` varchar(20) DEFAULT NULL COMMENT '交易所',
    `board` varchar(50) DEFAULT NULL COMMENT '板块',
    `industry` varchar(100) DEFAULT NULL COMMENT '行业',
    `sector` varchar(100) DEFAULT NULL COMMENT '板块',
    `list_date` date DEFAULT NULL COMMENT '上市日期',
    `total_share` decimal(20,4) DEFAULT NULL COMMENT '总股本',
    `float_share` decimal(20,4) DEFAULT NULL COMMENT '流通股本',
    `status` tinyint(4) NOT NULL DEFAULT '1' COMMENT '状态: 1-正常, 2-ST, 3-停牌',
    `is_st` tinyint(4) DEFAULT '0' COMMENT '是否ST股',
    `is_suspended` tinyint(4) DEFAULT '0' COMMENT '是否停牌',
    `update_date` date DEFAULT NULL COMMENT '更新日期',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol` (`symbol`),
    KEY `idx_market` (`market`),
    KEY `idx_industry` (`industry`),
    KEY `idx_sector` (`sector`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='股票基础信息表';

-- 创建基金基础信息表
CREATE TABLE IF NOT EXISTS `q_fund_basic` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT NULL COMMENT '创建时间',
    `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
    `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
    `fund_code` varchar(20) NOT NULL COMMENT '基金代码',
    `name` varchar(100) NOT NULL COMMENT '基金名称',
    `short_name` varchar(50) DEFAULT NULL COMMENT '基金简称',
    `type` varchar(20) DEFAULT NULL COMMENT '基金类型',
    `management` varchar(100) DEFAULT NULL COMMENT '基金管理人',
    `custodian` varchar(100) DEFAULT NULL COMMENT '基金托管人',
    `total_asset` decimal(20,4) DEFAULT NULL COMMENT '基金规模',
    `share_size` decimal(20,4) DEFAULT NULL COMMENT '份额规模',
    `establish_date` date DEFAULT NULL COMMENT '成立日期',
    `update_date` date DEFAULT NULL COMMENT '更新日期',
    `status` tinyint(4) DEFAULT '1' COMMENT '状态: 1-正常, 2-停止',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_fund_code` (`fund_code`),
    KEY `idx_type` (`type`),
    KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='基金基础信息表';

-- 创建涨停股池表
CREATE TABLE IF NOT EXISTS `q_limit_up_pool` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT NULL COMMENT '创建时间',
    `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
    `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
    `symbol` varchar(20) NOT NULL COMMENT '股票代码',
    `name` varchar(100) DEFAULT NULL COMMENT '股票名称',
    `trade_date` date NOT NULL COMMENT '交易日期',
    `limit_up_price` decimal(10,4) DEFAULT NULL COMMENT '涨停价',
    `close_price` decimal(10,4) DEFAULT NULL COMMENT '收盘价',
    `limit_up_amount` decimal(20,2) DEFAULT NULL COMMENT '封单金额',
    `limit_up_volume` bigint DEFAULT NULL COMMENT '封单量',
    `first_limit_up_time` datetime DEFAULT NULL COMMENT '首次涨停时间',
    `open_times` tinyint(4) DEFAULT '0' COMMENT '打开次数',
    `open_amount` decimal(20,2) DEFAULT NULL COMMENT '打开金额',
    `reason` varchar(200) DEFAULT NULL COMMENT '涨停原因',
    `category` varchar(50) DEFAULT NULL COMMENT '涨停类型',
    `update_time` datetime DEFAULT NULL COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_symbol_date` (`symbol`, `trade_date`),
    KEY `idx_trade_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='涨停股池表';

-- 创建龙虎榜表
CREATE TABLE IF NOT EXISTS `q_dragon_tiger_list` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT NULL COMMENT '创建时间',
    `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
    `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
    `symbol` varchar(20) NOT NULL COMMENT '股票代码',
    `name` varchar(100) DEFAULT NULL COMMENT '股票名称',
    `trade_date` date NOT NULL COMMENT '交易日期',
    `rank_type` varchar(20) DEFAULT NULL COMMENT '榜单类型',
    `rank_position` tinyint(4) DEFAULT NULL COMMENT '排名',
    `buy_amount` decimal(20,2) DEFAULT NULL COMMENT '买入金额',
    `buy_volume` bigint DEFAULT NULL COMMENT '买入量',
    `sell_amount` decimal(20,2) DEFAULT NULL COMMENT '卖出金额',
    `sell_volume` bigint DEFAULT NULL COMMENT '卖出量',
    `broker_name` varchar(200) DEFAULT NULL COMMENT '营业部名称',
    `broker_code` varchar(20) DEFAULT NULL COMMENT '营业部代码',
    `update_time` datetime DEFAULT NULL COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_symbol_date` (`symbol`, `trade_date`),
    KEY `idx_trade_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='龙虎榜表';

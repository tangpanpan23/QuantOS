-- 创建数据相关表结构
-- 执行时间: 2025年12月25日
-- 版本: 1.0.0

-- 创建新闻数据表
CREATE TABLE IF NOT EXISTS `q_news_data` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT NULL COMMENT '创建时间',
    `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
    `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
    `title` varchar(500) NOT NULL COMMENT '新闻标题',
    `content` longtext COMMENT '新闻内容',
    `summary` text COMMENT '新闻摘要',
    `source` varchar(100) NOT NULL COMMENT '新闻来源',
    `source_url` varchar(1000) DEFAULT NULL COMMENT '原文链接',
    `author` varchar(100) DEFAULT NULL COMMENT '作者',
    `publish_time` datetime NOT NULL COMMENT '发布时间',
    `sentiment_score` decimal(5,4) DEFAULT '0.0000' COMMENT '情感得分(-1到1)',
    `sentiment_label` varchar(20) DEFAULT NULL COMMENT '情感标签',
    `entities` json DEFAULT NULL COMMENT '识别的实体(JSON)',
    `category` varchar(50) DEFAULT NULL COMMENT '新闻分类',
    `tags` json DEFAULT NULL COMMENT '标签(JSON)',
    `is_processed` tinyint(4) DEFAULT '0' COMMENT '是否已处理: 0-未处理, 1-已处理',
    `process_time` datetime DEFAULT NULL COMMENT '处理时间',
    PRIMARY KEY (`id`),
    KEY `idx_publish_time` (`publish_time`),
    KEY `idx_source` (`source`),
    KEY `idx_category` (`category`),
    KEY `idx_sentiment_score` (`sentiment_score`),
    KEY `idx_is_processed` (`is_processed`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='新闻数据表';

-- 创建政策数据表
CREATE TABLE IF NOT EXISTS `q_policy_data` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT NULL COMMENT '创建时间',
    `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
    `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
    `title` varchar(500) NOT NULL COMMENT '政策标题',
    `content` longtext COMMENT '政策内容',
    `summary` text COMMENT '政策摘要',
    `source` varchar(100) NOT NULL COMMENT '政策来源',
    `source_url` varchar(1000) DEFAULT NULL COMMENT '原文链接',
    `issuer` varchar(100) DEFAULT NULL COMMENT '发布机构',
    `publish_time` datetime NOT NULL COMMENT '发布时间',
    `category` varchar(50) DEFAULT NULL COMMENT '政策分类',
    `sub_category` varchar(50) DEFAULT NULL COMMENT '政策子分类',
    `impact_level` tinyint(4) DEFAULT '1' COMMENT '影响级别: 1-低, 2-中, 3-高',
    `impact_scope` varchar(200) DEFAULT NULL COMMENT '影响范围',
    `sentiment_score` decimal(5,4) DEFAULT '0.0000' COMMENT '政策情感得分',
    `related_entities` json DEFAULT NULL COMMENT '相关实体(JSON)',
    `is_processed` tinyint(4) DEFAULT '0' COMMENT '是否已处理',
    `process_time` datetime DEFAULT NULL COMMENT '处理时间',
    PRIMARY KEY (`id`),
    KEY `idx_publish_time` (`publish_time`),
    KEY `idx_source` (`source`),
    KEY `idx_category` (`category`),
    KEY `idx_impact_level` (`impact_level`),
    KEY `idx_is_processed` (`is_processed`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='政策数据表';

-- 创建因子数据表
CREATE TABLE IF NOT EXISTS `q_factor_data` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT NULL COMMENT '创建时间',
    `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
    `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
    `factor_code` varchar(50) NOT NULL COMMENT '因子代码',
    `factor_name` varchar(100) NOT NULL COMMENT '因子名称',
    `value` decimal(15,8) NOT NULL COMMENT '因子值',
    `date` date NOT NULL COMMENT '日期',
    `time` time DEFAULT NULL COMMENT '时间',
    `type` tinyint(4) NOT NULL COMMENT '因子类型: 1-技术, 2-基本面, 3-情感, 4-宏观, 5-自定义',
    `category` varchar(50) DEFAULT NULL COMMENT '因子分类',
    `symbol` varchar(20) DEFAULT NULL COMMENT '关联证券代码',
    `sector` varchar(50) DEFAULT NULL COMMENT '关联行业',
    `parameters` json DEFAULT NULL COMMENT '计算参数(JSON)',
    `description` text COMMENT '因子描述',
    `data_quality` tinyint(4) DEFAULT '1' COMMENT '数据质量: 1-低, 2-中, 3-高',
    PRIMARY KEY (`id`),
    KEY `idx_factor_code_time` (`factor_code`, `date`, `time`),
    KEY `idx_symbol` (`symbol`),
    KEY `idx_type` (`type`),
    KEY `idx_category` (`category`),
    KEY `idx_sector` (`sector`),
    KEY `idx_data_quality` (`data_quality`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='因子数据表';

-- 创建指数数据表
CREATE TABLE IF NOT EXISTS `q_index_data` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT NULL COMMENT '创建时间',
    `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
    `deleted_at` datetime DEFAULT NULL COMMENT '删除时间',
    `index_code` varchar(20) NOT NULL COMMENT '指数代码',
    `index_name` varchar(100) NOT NULL COMMENT '指数名称',
    `open_value` decimal(12,4) DEFAULT NULL COMMENT '开盘值',
    `high_value` decimal(12,4) DEFAULT NULL COMMENT '最高值',
    `low_value` decimal(12,4) DEFAULT NULL COMMENT '最低值',
    `close_value` decimal(12,4) NOT NULL COMMENT '收盘值',
    `volume` bigint DEFAULT NULL COMMENT '成交量',
    `amount` decimal(20,2) DEFAULT NULL COMMENT '成交额',
    `trade_date` date NOT NULL COMMENT '交易日期',
    `market` varchar(10) NOT NULL COMMENT '市场代码',
    `data_source` tinyint(4) NOT NULL DEFAULT '1' COMMENT '数据源',
    PRIMARY KEY (`id`),
    KEY `idx_index_code_time` (`index_code`, `trade_date`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_market` (`market`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='指数数据表';

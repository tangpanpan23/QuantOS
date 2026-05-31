-- 策略管理表（用于量化策略的创建、配置和启用管理）
-- 版本: 1.0.0
-- 创建时间: 2026-05-30

CREATE TABLE IF NOT EXISTS `q_strategy` (
    `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `name` varchar(100) NOT NULL COMMENT '策略名称',
    `type` varchar(50) NOT NULL COMMENT '策略类型: RSI_REVERSAL/MA_CROSS/MOMENTUM/MEAN_REVERT/BREAKOUT/GRID/MARTINGALE',
    `description` varchar(500) DEFAULT NULL COMMENT '策略描述',
    `params` json DEFAULT NULL COMMENT '策略参数JSON配置',
    `is_active` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否启用: 0-禁用, 1-启用',
    `is_deleted` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否删除: 0-正常, 1-已删除',
    `last_run_at` datetime DEFAULT NULL COMMENT '最后运行时间',
    `run_count` int NOT NULL DEFAULT 0 COMMENT '累计运行次数',
    `note` varchar(500) DEFAULT NULL COMMENT '备注',
    PRIMARY KEY (`id`),
    KEY `idx_type` (`type`),
    KEY `idx_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='策略管理表';

-- 种子数据：Tank 默认量化策略
INSERT INTO `q_strategy` (`name`, `type`, `description`, `params`, `is_active`, `created_at`) VALUES
('RSI均值回归', 'RSI_REVERSAL', 'RSI超卖买入，超买卖出。适用于震荡市。', '{"rsi_buy": 30, "rsi_sell": 70, "rsi_period": 6, "hold_days": 5}', 1, NOW()),
('MA双均线策略', 'MA_CROSS', '短期均线上穿长期均线买入，下穿卖出。趋势跟踪。', '{"fast_ma": 5, "slow_ma": 20, "ma_type": "EMA", "position_pct": 0.3}', 1, NOW()),
('动量突破策略', 'MOMENTUM', '价格突破N日高点买入，跌破N日低点卖出。趋势跟踪。', '{"breakout_period": 20, "atr_multiplier": 2.0, "stop_loss_pct": 0.05}', 0, NOW()),
('网格交易策略', 'GRID', '在价格区间内等间隔网格买入卖出。震荡市专用。', '{"grid_count": 10, "price_range_pct": 0.10, "per_grid_amount": 1000}', 0, NOW()),
('MACD金叉死叉', 'BREAKOUT', 'MACD零轴上方金叉买入，死叉卖出。趋势过滤。', '{"fast_period": 12, "slow_period": 26, "signal_period": 9, "position_pct": 0.5}', 0, NOW())
ON DUPLICATE KEY UPDATE name = VALUES(name);

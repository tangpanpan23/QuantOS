-- 投资组合模块种子数据
-- 用于测试 portfoliohandlers.go API 端点
-- 执行时间: 2026-05-30

USE quantos;

-- ----------------------------------------------------------
-- 1. 股票池数据（自选股/关注列表）
-- ----------------------------------------------------------
INSERT IGNORE INTO q_stock_pool (symbol, name, market, industry, is_watched, notes) VALUES
('000001', '平安银行', 'SZ', '银行', 1, '银行板块，低估值'),
('000002', '万科A', 'SZ', '房地产', 1, '地产龙头'),
('600519', '贵州茅台', 'SH', '白酒', 1, '白酒之王，价值投资'),
('600036', '招商银行', 'SH', '银行', 1, '零售银行标杆'),
('000858', '五粮液', 'SZ', '白酒', 1, '浓香白酒龙头'),
('300750', '宁德时代', 'SZ', '新能源汽车', 1, '锂电龙头'),
('688981', '中芯国际', 'SH', '半导体', 1, '芯片代工'),
('002475', '立讯精密', 'SZ', '消费电子', 1, '苹果产业链'),
('000596', '古井贡酒', 'SZ', '白酒', 1, '徽酒龙头'),
('601318', '中国平安', 'SH', '保险', 1, '综合金融');

-- ----------------------------------------------------------
-- 2. 模拟账户（如不存在则创建）
-- ----------------------------------------------------------
INSERT IGNORE INTO q_paper_account (id, user_id, name, initial_capital, cash_reserve, current_capital, total_value, positions_value, total_pnl)
VALUES (1, 1, 'Tank默认模拟账户', 100000.00, 40000.00, 70000.00, 105000.00, 35000.00, 5000.00);

-- ----------------------------------------------------------
-- 3. 模拟盘持仓（如不存在则创建）
-- ----------------------------------------------------------
INSERT IGNORE INTO q_paper_position (account_id, symbol, shares, avg_cost, entry_date)
VALUES
(1, '600519', 100, 1680.00, DATE_SUB(CURDATE(), INTERVAL 15 DAY)),
(1, '000001', 1000, 12.50, DATE_SUB(CURDATE(), INTERVAL 7 DAY)),
(1, '300750', 200, 180.00, DATE_SUB(CURDATE(), INTERVAL 3 DAY));

-- ----------------------------------------------------------
-- 4. 策略表种子数据（确保表存在后插入）
-- ----------------------------------------------------------
INSERT IGNORE INTO q_strategy (name, type, description, params, is_active, created_at) VALUES
('RSI均值回归', 'RSI_REVERSAL', 'RSI超卖买入，超买卖出。适用于震荡市。', '{"rsi_buy": 30, "rsi_sell": 70, "rsi_period": 6, "hold_days": 5}', 1, NOW()),
('MA双均线策略', 'MA_CROSS', '短期均线上穿长期均线买入，下穿卖出。趋势跟踪。', '{"fast_ma": 5, "slow_ma": 20, "ma_type": "EMA", "position_pct": 0.3}', 1, NOW()),
('动量突破策略', 'MOMENTUM', '价格突破N日高点买入，跌破N日低点卖出。趋势跟踪。', '{"breakout_period": 20, "atr_multiplier": 2.0, "stop_loss_pct": 0.05}', 0, NOW()),
('网格交易策略', 'GRID', '在价格区间内等间隔网格买入卖出。震荡市专用。', '{"grid_count": 10, "price_range_pct": 0.10, "per_grid_amount": 1000}', 0, NOW()),
('MACD金叉死叉', 'BREAKOUT', 'MACD零轴上方金叉买入，死叉卖出。趋势过滤。', '{"fast_period": 12, "slow_period": 26, "signal_period": 9, "position_pct": 0.5}', 0, NOW());

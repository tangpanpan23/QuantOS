
-- 更新策略参数（更详细配置）
UPDATE q_sim_strategy SET 
    params_json = '{"ma_short":5,"ma_long":20,"rsi_period":6,"rsi_oversold":35,"rsi_overbought":65}'
WHERE strategy_type = 'trend_following';

UPDATE q_sim_strategy SET 
    params_json = '{"rsi_period":6,"rsi_oversold":30,"rsi_overbought":70,"macd_fast":12,"macd_slow":26,"macd_signal":9}'
WHERE strategy_type = 'momentum';

UPDATE q_sim_strategy SET 
    params_json = '{"boll_period":20,"boll_std":2,"volume_ratio":1.5}'
WHERE strategy_type = 'breakout';

UPDATE q_sim_strategy SET 
    params_json = '{"grid_pct":3,"num_grids":10,"base_price":null}'
WHERE strategy_type = 'grid_trading';

UPDATE q_sim_strategy SET 
    params_json = '{"rsi_period":14,"bb_period":20,"bb_std":2,"mean_reversion_threshold":0.05}'
WHERE strategy_type = 'mean_reversion';

UPDATE q_sim_strategy SET 
    params_json = '{"pe_threshold":15,"pb_threshold":1.5,"roe_min":10,"dividend_yield_min":2}'
WHERE strategy_type = 'value';

-- 更新股票池（Tank自选股作为默认universe）
UPDATE q_sim_strategy SET 
    universe_json = '["600519","000858","601318","600900","600028","002475","000001","601288","600036","000002"]'
WHERE strategy_type = 'trend_following';

UPDATE q_sim_strategy SET 
    universe_json = '["600519","000858","601318","600900","600028","002475","000001","601288","600036","000002"]'
WHERE strategy_type = 'momentum';

-- 创建Tank的主策略账户
INSERT INTO q_sim_account (account_name, strategy_id, initial_capital, current_capital, total_asset, status)
SELECT 'Tank_趋势账户', id, 1000000.00, 1000000.00, 1000000.00, 1
FROM q_sim_strategy WHERE strategy_type = 'trend_following'
ON DUPLICATE KEY UPDATE updated_at=NOW();

INSERT INTO q_sim_account (account_name, strategy_id, initial_capital, current_capital, total_asset, status)
SELECT 'Tank_动量账户', id, 1000000.00, 1000000.00, 1000000.00, 1
FROM q_sim_strategy WHERE strategy_type = 'momentum'
ON DUPLICATE KEY UPDATE updated_at=NOW();

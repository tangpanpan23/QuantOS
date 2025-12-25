-- 回滚初始化数据库表结构
-- 执行时间: 2025年12月25日
-- 版本: 1.0.0

-- 删除表（按照依赖关系倒序删除）
DROP TABLE IF EXISTS `q_positions`;
DROP TABLE IF EXISTS `q_portfolios`;
DROP TABLE IF EXISTS `q_strategies`;
DROP TABLE IF EXISTS `q_users`;
DROP TABLE IF EXISTS `q_market_data`;

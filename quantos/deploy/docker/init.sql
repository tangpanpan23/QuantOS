-- QuantSaaS 数据库初始化脚本
-- 执行时间: 2025年12月25日

-- 创建数据库
CREATE DATABASE IF NOT EXISTS quantos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE quantos;

-- 创建用户并授权
CREATE USER IF NOT EXISTS 'quantos'@'%' IDENTIFIED BY 'quantos123';
GRANT ALL PRIVILEGES ON quantos.* TO 'quantos'@'%';
FLUSH PRIVILEGES;

-- 设置时区
SET time_zone = '+08:00';

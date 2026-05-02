# Changelog

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [Unreleased]

### 新增

- **`stubhandlers.go`** - 所有未实现路由的完整 Stub Handler 实现（49个），项目现在可以完整编译和运行
- **`docs/API.md`** - 完整的 REST API 接口文档（含所有 60+ 端点的请求/响应示例、错误码说明）
- **`docs/DEVELOPER.md`** - 开发者指南（含添加 Handler 完整教程、项目结构说明、数据库模型）
- **`docs/SETUP.md`** - 三种快速上手方式（Docker / 本地开发 / 模拟盘独立），含常见问题解答
- **`docs/CHANGELOG.md`** - 项目变更日志
- **`.env.example`** - 完整的环境变量配置模板（含所有配置项说明）
- **`CONTRIBUTING.md`** - 贡献指南（代码规范、PR 流程、测试要求）
- **`ROADMAP.md`**（项目根目录）- 开发路线图（Phase 0-5 规划）

### 修复

- **`scripts/fetch_market_data.py`** - 修复 `get_realtime_data()` 中 `df` 变量命名冲突导致的数据获取失败
- **`servicecontext.go`** - 修复 RPC 客户端初始化逻辑：改为 nil 延迟初始化，避免服务启动时 panic（RPC 服务目前为 stub）
- **`routes.go`** - 修复 JWT 中间件配置：`/health` 端点改为公开访问（无需认证）
- **`go.mod`** - 修正 Go 版本为 `1.22.0`（兼容当前 go-zero 1.7.x）

### 优化

- **根目录 `README.md`** - 大幅重写：增加项目状态总览表、技术架构图、快速开始、常用命令、开发路线
- **`quantos/README.md`** - 重写为更清晰的项目结构说明
- **`.gitignore`**（根目录）- 扩充为完整的 Go 项目 ignore 规则

### 重构

- **`routes.go`** - 重构路由分组，将公开端点和认证端点分离，使路由结构更清晰
- **`servicecontext.go`** - 重构为安全的 RPC 客户端初始化，支持按需启用

---

## [v0.3.0] - 2026-04-30

### 新增

- 自主进化引擎 `papertrading/evolve.go`
  - RSI 区间胜率分析
  - 均线策略效果分析
  - 持仓时长与盈亏关系
  - 自动参数调优建议
- 每日报告系统 `paper report [today|weekly|monthly]`
- 每日数据更新命令 `paper daily`
- 历史模拟回测 `paper simulate`
- Tank 快捷操作脚本 `tank-ops.sh`

### 新增 CLI 命令

- `paper evolve [--analyze] [--suggest]` - 自主进化分析
- `paper report <period>` - 生成定期报告
- `paper daily` - 每日市场数据更新
- `paper signal [code]` - 选股信号生成
- `paper reset` - 重置账户

---

## [v0.2.0] - 2026-04-20

### 新增

- 完整的模拟盘交易系统（数据库持久化版）
  - `papertrading/db.go` - GORM 数据库操作层
  - `papertrading/market.go` - 市场数据客户端
  - `papertrading/strategy.go` - 选股信号系统
  - 支持 MySQL 存储交易记录和持仓
- 命令行完整 CRUD：`paper buy/sell/status/trades`
- 持仓盈亏实时计算
- 止损止盈自动检查

### 改进

- `paper.go` CLI 从文件存储迁移到数据库存储
- 支持多用户账户（通过 `user_id` 隔离）
- 每日统计数据持久化

---

## [v0.1.0] - 2026-04-10

### 新增

- go-zero REST API 框架搭建
- 用户管理系统（注册/登录/JWT认证）
- `app/api/internal/types/types.go` - 完整请求/响应类型定义
- `app/model/user/user.go` - 用户数据模型
- 数据库迁移系统 `console.go migrate`
- Docker Compose 开发环境配置
- Kubernetes 部署 YAML
- Proto 文件定义（5个服务：stock/market_analysis/strategy/trading/special_analysis）
- 基础 `routes.go` 路由注册（包含 60+ 路由）

### 新增 CLI 命令

- `console.go migrate up/down/status` - 数据库迁移管理

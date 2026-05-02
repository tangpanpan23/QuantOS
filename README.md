# QuantSaaS - 量化策略 SaaS 平台

> 基于感知-决策智能的量化策略平台，让量化投资不再是少数人的游戏 🚀

[![Go](https://img.shields.io/badge/Go-1.22+-blue.svg)](https://golang.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 项目定位

QuantSaaS 是首个将**宏观政策感知**、**AI辅助决策**与**用户自主创造**深度融合的量化策略 SaaS 平台。

### 核心价值
- 🎯 **技术民主化** - 让机构级量化能力惠及专业投资者
- 🤖 **AI + 人工协同** - AI负责分析，人负责决策
- 📊 **全链路服务** - 数据感知 → 策略构建 → 回测验证 → 实盘执行

---

## ✅ 当前状态

| 模块 | 状态 | 说明 |
|------|------|------|
| 基础框架 (go-zero) | ✅ 完成 | REST API + JWT 认证 |
| 用户管理系统 | ✅ 完成 | 注册/登录/用户信息 |
| 数据库迁移 | ✅ 完成 | MySQL + GORM AutoMigrate |
| 模拟交易系统 | ✅ 完成 | CLI + 数据库持久化 |
| 市场数据获取 | ✅ 完成 | Python 脚本（akshare） |
| 自主进化引擎 | ✅ 完成 | RSI/均线/持仓分析 |
| Proto RPC 定义 | ✅ 完成 | 5个服务接口预留 |
| Docker 部署 | ✅ 完成 | docker-compose |
| Kubernetes 部署 | ✅ 完成 | YAML 编排 |
| Handler 实现 | 🟡 部分 | 基础路由已完成，部分功能为 stub |
| NLP 感知引擎 | 🔲 规划 | 新闻情感分析 |
| AI 策略生成 | 🔲 规划 | LLM 生成策略 |
| 真实交易接口 | 🔲 规划 | 对接券商 API |

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                        统一接入层                            │
│              REST API (port 8888) + gRPC (预留)             │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                      应用服务层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  用户管理 │  │  策略工坊 │  │ AI决策   │  │ 智能执行  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │股票数据  │  │ 市场分析 │  │ 交易服务 │  │专项分析  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                      数据持久层                              │
│         MySQL (GORM)  +  Redis (缓存)  +  Pulsar (MQ)     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 方式一：Docker 一键启动（推荐）

```bash
cd quantos

# 1. 配置环境
cp .env.example .env
# 编辑 .env 填入实际值（至少修改 DB_PASSWORD 和 JWT_SECRET）

# 2. 启动基础设施
make dev

# 3. 执行数据库迁移
make migrate-up

# 4. 启动 API 服务
make run-api

# 5. 验证
curl http://localhost:8888/health
```

### 方式二：本地开发

```bash
# 1. 安装 Go 1.22+, Docker, MySQL 8.0, Redis
brew install go mysql redis  # macOS
# 或 apt install golang mysql-server redis-server  # Ubuntu

# 2. 克隆并进入项目
cd quantos

# 3. 安装依赖
go mod download
pip install akshare pandas numpy  # 市场数据脚本需要

# 4. 配置（参考上面）

# 5. 启动 MySQL + Redis，创建数据库
mysql -u root -p -e "CREATE DATABASE quantos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 6. 迁移 + 启动
make migrate-up
make run-api
```

### 方式三：模拟盘快速体验

无需启动数据库，直接体验模拟交易功能：

```bash
cd quantos

# 安装 Python 依赖（必需）
pip install akshare pandas numpy

# 模拟盘 CLI
go run app/command/console.go paper --help

# 查看状态
go run app/command/console.go paper status

# 买入
go run app/command/console.go paper buy 600036 35.50 300 "MA多头+RSI=45"

# 选股信号
go run app/command/console.go paper signal

# 自主进化分析
go run app/command/console.go paper evolve
```

---

## 📂 项目结构

```
QuantSaaS/
├── README.md              # 本文件
├── .env.example          # 环境变量模板
├── quantos/              # 主应用 (Go)
│   ├── app/
│   │   ├── api/          # REST API 服务
│   │   ├── command/      # 命令行工具 (模拟盘)
│   │   └── model/        # 数据模型
│   ├── pb/               # gRPC Proto 定义
│   ├── common/           # 通用工具
│   ├── constant/         # 常量
│   ├── scripts/           # Python 数据脚本
│   └── deploy/           # Docker / K8s 部署
└── docs/
    ├── API.md            # API 接口文档
    ├── DEVELOPER.md      # 开发者指南
    └── PAPERTRADING.md   # 模拟盘使用文档
```

---

## 🛠️ 核心功能

### 1. 模拟盘交易系统 ✅
- 文件/数据库双存储
- 止损止盈自动执行
- 每日持仓状态更新
- 历史交易记录

### 2. 选股信号系统 ✅
- 趋势跟踪策略（MA20>MA60）
- RSI 区间筛选（35-65）
- 成交额过滤（>3亿）
- 综合评分输出

### 3. 自主进化引擎 ✅
- RSI 区间胜率分析
- 均线策略效果分析
- 持仓时长与盈亏关系
- 自动参数调优

### 4. 股票数据服务 ✅
- 实时行情（东方财富）
- 历史 K 线数据
- 技术指标计算（MA/RSI/MACD）
- 涨停板/强势股池

### 5. 策略管理 🟡
- 策略 CRUD
- 模板超市
- AI 生成策略（stub）
- 回测引擎（stub）

### 6. 新闻政策感知 🔲
- 多源新闻接入
- NLP 情感分析
- 事件提取
- 影响传导图谱

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| [API.md](docs/API.md) | 完整的 API 接口文档 |
| [DEVELOPER.md](docs/DEVELOPER.md) | 开发者指南（含添加 Handler 教程） |
| [PAPERTRADING.md](docs/PAPERTRADING.md) | 模拟盘详细使用手册 |

---

## 🛠️ 常用命令

```bash
cd quantos

make run-api          # 启动 API 服务
make migrate-up       # 执行数据库迁移
make migrate-down     # 回滚迁移
make test             # 运行测试
make lint             # 代码检查
make build            # 构建
make fmt              # 代码格式化
make swagger          # 生成 Swagger 文档
make docker-build     # 构建 Docker 镜像
make deploy-k8s       # 部署到 K8s
make security-check    # 安全检查
```

---

## 🧩 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| 后端框架 | go-zero | 1.6.4+ |
| 编程语言 | Go | 1.22+ |
| 数据库 | MySQL | 8.0+ |
| 缓存 | Redis | 6.0+ |
| ORM | GORM | v2 |
| 消息队列 | Apache Pulsar | 2.10+ |
| 数据获取 | akshare | - |
| 数据分析 | pandas/numpy | - |
| 容器化 | Docker | 20.0+ |
| 编排 | Kubernetes | 1.24+ |

---

## 🔜 开发路线

### Phase 1 - 基础平台 ✅ (已完成)
- [x] go-zero 框架搭建
- [x] 用户认证系统
- [x] 数据库迁移
- [x] 模拟盘交易系统
- [x] 市场数据获取
- [x] Docker/K8s 部署

### Phase 2 - 核心功能 🟡 (进行中)
- [ ] 完整 Handler 实现
- [ ] 策略回测引擎
- [ ] 实时行情 WebSocket
- [ ] 邮件/短信通知

### Phase 3 - AI 增强 🔲 (规划中)
- [ ] NLP 新闻感知引擎
- [ ] LLM 策略生成
- [ ] 机器学习选股
- [ ] AI 风控系统

### Phase 4 - 生态完善 🔲 (规划中)
- [ ] 移动端 App
- [ ] 第三方数据源集成
- [ ] 策略市场与跟投
- [ ] 真实交易对接

---

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支: `git checkout -b feature/your-feature`
3. 提交更改: `git commit -m 'Add some feature'`
4. 推送: `git push origin feature/your-feature`
5. 发起 Pull Request

**注意：**
- 提交前运行 `make fmt` 和 `make lint`
- 新增 Handler 需要同步更新 `docs/API.md`
- 遵守 Go 官方代码规范

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件。

---

## 📞 联系我们

- **GitHub**: https://github.com/tangpanpan23
- **邮箱**: tangpan23@126.com

---

<p align="center">
  <strong>让量化投资不再是少数人的游戏</strong><br>
  <em>QuantSaaS - 量化投资的未来</em>
</p>

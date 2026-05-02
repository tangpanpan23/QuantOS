# QuantSaaS - Go 主应用

> 本目录是 QuantSaaS 平台的 Go 后端主应用，基于 go-zero 微服务框架。

## 📖 快速开始

```bash
# 1. 安装依赖
go mod download

# 2. 配置环境
cp .env.example .env
# 编辑 .env 填入实际值

# 3. 启动基础设施
make dev

# 4. 数据库迁移
make migrate-up

# 5. 启动 API
make run-api

# 6. 验证
curl http://localhost:8888/health
```

## 📁 目录结构

```
quantos/
├── app/
│   ├── api/               # REST API 服务
│   │   ├── api.go         # 程序入口
│   │   └── internal/
│   │       ├── config/    # 配置结构体
│   │       ├── handler/   # HTTP Handler（路由在此注册）
│   │       ├── logic/     # 业务逻辑层
│   │       ├── middleware/# JWT 等中间件
│   │       ├── svc/       # 服务上下文
│   │       └── types/     # 请求/响应类型
│   ├── command/           # 命令行工具
│   │   ├── console.go     # 数据库迁移工具
│   │   └── paper.go      # 模拟盘 CLI
│   └── model/             # 数据模型
│       ├── user/
│       └── market/
│           └── papertrading/  # 模拟交易核心
├── pb/                    # gRPC Proto 定义
├── common/                # 通用工具（DB/Redis 初始化）
├── constant/              # 全局常量
├── scripts/               # 辅助脚本
│   └── fetch_market_data.py  # 市场数据获取（Python）
├── deploy/                # Docker / Kubernetes 配置
├── Makefile               # 构建工具
├── go.mod / go.sum        # Go 依赖
└── .env.example           # 环境变量模板
```

## 🛠️ 常用命令

```bash
make run-api          # 启动 API 服务 (go run)
make build            # 构建到 bin/
make test             # 运行测试
make migrate-up       # 执行数据库迁移
make migrate-down     # 回滚迁移
make fmt              # 格式化代码
make lint             # 代码检查
make swagger          # 生成 Swagger 文档
make clean            # 清理构建产物
make dev              # Docker 启动基础设施
```

## 🧩 模拟盘 CLI

```bash
# 查看所有命令
go run app/command/console.go paper --help

# 基本操作
go run app/command/console.go paper status      # 账户状态
go run app/command/console.go paper buy 600036 35.50 300 "MA多头"
go run app/command/console.go paper sell 600036 38.50 "止盈"
go run app/command/console.go paper signal        # 选股扫描
go run app/command/console.go paper evolve         # 自主进化
go run app/command/console.go paper report today  # 生成报告
go run app/command/console.go paper simulate       # 历史回测
go run app/command/console.go paper daily          # 每日更新
```

## 📊 数据模型

### 主要表结构

| 表名 | 说明 |
|------|------|
| `q_paper_account` | 模拟账户 |
| `q_paper_position` | 持仓记录 |
| `q_paper_trade` | 交易流水 |
| `q_strategy_params` | 策略参数（含进化历史） |
| `q_daily_stats` | 每日统计数据 |
| `q_evolution_log` | 进化历史记录 |

### 模拟盘策略参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 初始资金 | ¥100,000 | - |
| 保留现金 | ¥40,000 | 不用于交易 |
| 单只最大持仓 | ¥15,000 | - |
| 最多持仓 | 4 只 | - |
| 止损线 | 3% | 亏损 3% 触发 |
| 第一止盈 | 5% | 概率触发 |
| 第二止盈 | 8% | 触发后清仓 |
| RSI 买入区间 | 35-65 | 可通过进化优化 |

## 🛡️ API 安全

- 所有业务 API 需要 JWT Token 认证
- Token 在 `/api/v1/user/login` 获取
- 放入 Header: `Authorization: Bearer <token>`
- Token 有效期：`JWT_ACCESS_EXPIRE`（默认 24 小时）

## 📝 开发指南

详细开发指南请参考 [docs/DEVELOPER.md](docs/DEVELOPER.md)。

添加新的 Handler 流程：

```
1. 在 types/types.go 添加请求/响应结构体
2. 在 handler/ 创建 Handler 函数
3. 在 logic/ 创建 Logic 业务逻辑
4. 在 routes.go 注册路由
```

## 📚 相关文档

- [API 接口文档](docs/API.md)
- [开发者指南](docs/DEVELOPER.md)
- [模拟盘使用手册](docs/PAPERTRADING.md)

## 🤝 贡献

1. Fork → 特性分支 → PR
2. 提交前运行 `make fmt && make lint`
3. 新增 Handler 同步更新 `docs/API.md`

## 📄 许可证

MIT License

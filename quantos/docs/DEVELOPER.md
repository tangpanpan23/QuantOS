# QuantSaaS 开发者指南

> 让量化投资不再是少数人的游戏 🚀

---

## 📁 项目结构

```
QuantSaaS/
├── README.md              # 项目概述
├── docs/
│   ├── API.md             # API 接口文档
│   ├── DEVELOPER.md       # 本文件
│   └── PAPERTRADING.md   # 模拟盘使用指南
├── quantos/              # 主应用
│   ├── app/
│   │   ├── api/          # REST API 服务 ✅
│   │   │   ├── api.go                 # 入口
│   │   │   ├── internal/
│   │   │   │   ├── config/           # 配置
│   │   │   │   ├── handler/          # HTTP Handler（路由在此注册）
│   │   │   │   ├── logic/            # 业务逻辑层
│   │   │   │   ├── middleware/       # 中间件（JWT）
│   │   │   │   ├── svc/              # 服务上下文
│   │   │   │   └── types/            # 请求/响应结构体
│   │   │   └── etc/api.yaml          # 配置文件
│   │   ├── command/      # 命令行工具 ✅
│   │   │   ├── console.go            # 数据库迁移
│   │   │   └── paper.go              # 模拟盘 CLI
│   │   └── model/        # 数据模型层 ✅
│   │       ├── user/                 # 用户模型
│   │       └── market/
│   │           ├── papertrading/      # 模拟交易系统
│   │           ├── market.go
│   │           ├── realtime/
│   │           └── kline/
│   ├── pb/               # Proto 定义（gRPC 预留）
│   │   ├── stock.proto
│   │   ├── market_analysis.proto
│   │   ├── strategy.proto
│   │   ├── trading.proto
│   │   └── special_analysis.proto
│   ├── common/           # 通用工具 ✅
│   ├── constant/          # 常量定义 ✅
│   ├── scripts/           # 辅助脚本
│   │   ├── fetch_market_data.py       # 市场数据获取（Python）
│   │   └── setup-secrets.sh           # K8s Secrets 配置
│   ├── Makefile          # 构建工具
│   ├── go.mod / go.sum   # 依赖管理
│   └── deploy/           # 部署配置
│       ├── docker/
│       └── kubernetes/
├── .env.example          # 环境变量模板
└── SECURITY.md           # 安全配置
```

---

## 🚀 本地开发

### 1. 环境要求

```bash
Go 1.22+
Docker & Docker Compose
MySQL 8.0+
Redis 7+
Python 3.9+ (用于市场数据脚本)
```

### 2. 安装依赖

```bash
cd quantos

# Go 依赖
go mod download

# Python 依赖（用于数据脚本）
pip install akshare pandas numpy
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入实际值
```

关键配置项：
```bash
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
JWT_ACCESS_SECRET=your_32_char_secret
```

### 4. 启动基础设施

```bash
# 使用 Docker 启动 MySQL 和 Redis
make dev

# 或手动启动
docker run -d --name quantos-mysql \
  -e MYSQL_ROOT_PASSWORD=quantos123 \
  -p 3306:3306 mysql:8.0

docker run -d --name quantos-redis \
  -p 6379:6379 redis:7-alpine
```

### 5. 数据库迁移

```bash
make migrate-up
```

### 6. 启动服务

```bash
make run-api
# 或
go run app/api/api.go -f app/api/etc/api.yaml
```

服务启动在：`http://localhost:8888`

### 7. 验证

```bash
curl http://localhost:8888/health
# {"status":"ok","service":"quantos-api"}
```

---

## 🛠️ 开发指南

### 添加新的 API Handler

**步骤 1：定义类型**

在 `app/api/internal/types/types.go` 添加请求/响应结构体：

```go
// 获取用户策略列表请求
type GetUserStrategiesReq struct {
    UserID uint64 `form:"user_id"`
    Type   int8   `form:"type"`
    Page   int64  `form:"page,default=1"`
    Size   int64  `form:"page_size,default=20"`
}
```

**步骤 2：编写 Handler**

在 `app/api/internal/handler/` 创建或添加 handler：

```go
func getUserStrategiesHandler(ctx *svc.ServiceContext) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        var req types.GetUserStrategiesReq
        if err := httpx.Parse(r, &req); err != nil {
            httpx.Error(w, err)
            return
        }

        l := logic.NewGetUserStrategiesLogic(r.Context(), ctx)
        resp, err := l.GetUserStrategies(&req)
        if err != nil {
            httpx.Error(w, err)
        } else {
            httpx.OkJson(w, resp)
        }
    }
}
```

**步骤 3：编写 Logic**

在 `app/api/internal/logic/` 创建 logic 文件：

```go
package logic

type GetUserStrategiesLogic struct {
    ctx context.Context
    svc *svc.ServiceContext
}

func NewGetUserStrategiesLogic(ctx context.Context, svc *svc.ServiceContext) *GetUserStrategiesLogic {
    return &GetUserStrategiesLogic{ctx: ctx, svc: svc}
}

func (l *GetUserStrategiesLogic) GetUserStrategies(req *types.GetUserStrategiesReq) (interface{}, error) {
    // 业务逻辑
    strategies := []types.Strategy{}
    return types.GetStrategiesResp{
        List:     strategies,
        Total:    0,
        Page:     req.Page,
        PageSize: req.Size,
    }, nil
}
```

**步骤 4：注册路由**

在 `app/api/internal/handler/routes.go` 添加路由：

```go
server.AddRoutes([]rest.Route{
    {
        Method:  http.MethodGet,
        Path:    "/api/v1/user/strategies",
        Handler: getUserStrategiesHandler(ctx),
    },
}, rest.WithJwt(ctx.JwtAuthMiddleware))
```

### 添加数据模型

在 `app/model/` 下创建新的模型文件：

```go
package yourmodel

type YourModel struct {
    ID        uint64    `gorm:"primaryKey;autoIncrement" json:"id"`
    Name      string    `gorm:"column:name;type:varchar(100)" json:"name"`
    CreatedAt time.Time `gorm:"column:created_at" json:"created_at"`
}

func (YourModel) TableName() string {
    return "your_table_name"
}
```

然后在 `common/common.go` 的 `autoMigrate()` 中注册。

### 市场数据脚本扩展

Python 脚本位于 `scripts/fetch_market_data.py`，基于 akshare 封装。

添加新接口（如板块数据）：

```python
def get_sector_data(sector_name):
    """获取板块行情数据"""
    try:
        df = ak.stock_board_industry_name_em()
        return df.to_dict('records')
    except Exception as e:
        print(f"获取板块数据失败: {e}")
        return []
```

---

## 🧪 测试

```bash
# 运行所有测试
make test

# 带覆盖率
make test-coverage

# 单个包测试
go test ./app/model/... -v
```

---

## 📦 构建与部署

```bash
# 本地构建
make build

# Docker 构建
make docker-build

# 生产环境构建（Linux）
make prod

# Kubernetes 部署
make deploy-k8s

# 检查部署状态
make deploy-k8s-check
```

---

## 🔐 安全配置

```bash
# 检查安全配置
make security-check

# 设置 K8s Secrets
make secrets-setup

# 验证 Secrets
make secrets-verify
```

**重要：**
- 生产环境务必修改 `JWT_ACCESS_SECRET`
- 数据库密码使用强密码
- 不要将 `.env` 提交到版本库

---

## 📊 模拟盘使用

```bash
# 进入项目目录
cd quantos

# 启动服务（如需要API）
make run-api

# 模拟盘 CLI（在另一个终端）
go run app/command/console.go paper --help

# 查看账户状态
go run app/command/console.go paper status

# 买入股票
go run app/command/console.go paper buy 600036 35.50 300 "MA多头排列"

# 卖出股票
go run app/command/console.go paper sell 600036 38.50 "止盈"

# 选股信号扫描
go run app/command/console.go paper signal

# 单只股票分析
go run app/command/console.go paper signal 600036

# 运行自主进化
go run app/command/console.go paper evolve

# 生成报告
go run app/command/console.go paper report today

# 每日更新（建议 cron）
go run app/command/console.go paper daily

# 历史模拟回测
go run app/command/console.go paper simulate
```

---

## 🔄 代码质量

```bash
# 格式化代码
make fmt

# 代码检查
make lint

# go vet
make vet
```

---

## 📝 代码规范

- 遵循 Go 官方 [Effective Go](https://go.dev/doc/effective_go)
- 命名：驼峰式，包名简短
- 错误处理：优先使用 `fmt.Errorf("doing something: %w", err)` 包装错误
- Context：每个入口函数传递 `context.Context`
- 日志：使用 `logx`（go-zero 内置）

---

## 🆘 常见问题

### 1. 数据库连接失败

```bash
# 检查 MySQL 是否运行
docker ps | grep mysql

# 检查端口
lsof -i :3306

# 查看日志
docker logs quantos-mysql
```

### 2. JWT Token 过期

检查 `.env` 中的 `JWT_ACCESS_SECRET` 是否配置，`JWT_ACCESS_EXPIRE` 是否过小。

### 3. akshare 获取数据失败

```bash
# 确认安装
pip show akshare

# 更新到最新版本
pip install akshare --upgrade

# 检查网络（部分数据源需要直连）
```

### 4. 编译错误

```bash
# 清理缓存
go clean -cache

# 重新下载依赖
go mod tidy
```

---

## 📞 联系方式

- **GitHub**: https://github.com/tangpanpan23
- **邮箱**: tangpan23@126.com
- **项目主页**: https://github.com/tangpanpan23/quantos

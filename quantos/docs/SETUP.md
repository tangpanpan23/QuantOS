# QuantSaaS 快速上手指南

> 10 分钟内启动你的量化策略 SaaS 平台 🚀

---

## 前置要求

| 工具 | 最低版本 | 安装方式 |
|------|---------|---------|
| Go | 1.22+ | [go.dev/dl](https://go.dev/dl) |
| MySQL | 8.0+ | `brew install mysql` / `apt install mysql-server` |
| Redis | 6.0+ | `brew install redis` / `apt install redis` |
| Docker | 20.0+ | [docker.com](https://docker.com) |
| Python | 3.9+ | `brew install python3` |

---

## 方式一：Docker 一键启动（推荐）

### 1. 克隆项目

```bash
git clone https://github.com/tangpanpan23/quantos.git
cd quantos
```

### 2. 配置环境变量

```bash
cp ../.env.example .env
```

编辑 `.env`，至少配置：

```bash
DB_PASSWORD=your_mysql_password    # MySQL 密码
JWT_ACCESS_SECRET=change_me_32chars  # JWT 密钥（生产必改）
```

### 3. 启动基础设施

```bash
make dev
```

这会启动 MySQL + Redis 容器。

### 4. 配置数据库

```bash
# 创建数据库（用你的密码）
mysql -h localhost -u root -p -e "CREATE DATABASE quantos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 执行迁移
make migrate-up
```

### 5. 启动服务

```bash
make run-api
```

服务运行在：`http://localhost:8888`

### 6. 验证

```bash
curl http://localhost:8888/health
# {"status":"ok","service":"quantos-api"}
```

---

## 方式二：本地开发

### 1. 安装 Go 依赖

```bash
cd quantos
go mod download
```

### 2. 安装 Python 依赖（市场数据脚本需要）

```bash
pip install akshare pandas numpy
```

### 3. 配置环境变量

```bash
cp ../.env.example .env
# 编辑 .env 填入实际值
```

### 4. 启动 MySQL

```bash
# macOS
brew services start mysql

# Ubuntu
sudo systemctl start mysql

# 创建数据库
mysql -u root -p -e "CREATE DATABASE quantos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 5. 启动 Redis

```bash
# macOS
brew services start redis

# Ubuntu
sudo systemctl start redis
```

### 6. 执行数据库迁移

```bash
make migrate-up
```

### 7. 启动服务

```bash
make run-api
```

---

## 方式三：模拟盘独立体验（无需数据库）

不需要 MySQL，直接体验模拟交易功能：

```bash
cd quantos

# 安装 Python 依赖
pip install akshare pandas numpy

# 模拟盘 CLI
go run app/command/console.go paper status      # 账户状态
go run app/command/console.go paper buy 600036 35.50 300 "MA多头+RSI=45"
go run app/command/console.go paper signal        # 选股信号
go run app/command/console.go paper evolve        # 自主进化
```

---

## 目录结构速查

```
quantos/
├── app/
│   ├── api/                    # REST API 服务
│   │   └── internal/
│   │       ├── config/         # 配置结构体
│   │       ├── handler/         # HTTP Handler（含未实现的 stub）
│   │       ├── logic/           # 业务逻辑
│   │       ├── middleware/      # JWT 中间件
│   │       ├── svc/              # 服务上下文
│   │       └── types/            # 请求/响应类型
│   ├── command/                # CLI 工具
│   │   ├── console.go          # 数据库迁移
│   │   └── paper.go            # 模拟盘 CLI
│   └── model/                  # 数据模型
│       ├── user/               # 用户/策略/组合模型
│       └── market/papertrading/ # 模拟交易模型
├── common/                     # 通用工具
├── constant/                   # 常量
├── pb/                         # gRPC Proto（预留）
├── scripts/                    # Python 数据脚本
├── deploy/                    # Docker / K8s 配置
└── docs/                       # 文档
    ├── API.md                 # API 完整文档
    ├── DEVELOPER.md           # 开发者指南
    ├── PAPERTRADING.md        # 模拟盘手册
    └── SETUP.md               # 本文件
```

---

## 常用命令

```bash
cd quantos

make run-api          # 启动 API（开发模式）
make build            # 构建二进制
make test             # 运行测试
make migrate-up       # 数据库迁移
make migrate-down     # 回滚迁移
make fmt              # 格式化代码
make lint             # 代码检查
make dev              # Docker 启动基础设施
make dev-stop         # 停止 Docker 基础设施
```

---

## 模拟盘 CLI 快速参考

```bash
# 账户
go run app/command/console.go paper status      # 查看账户
go run app/command/console.go paper reset       # 重置账户

# 交易
go run app/command/console.go paper buy 600036 35.50 300 "MA多头+RSI=45"
go run app/command/console.go paper sell 600036 38.50 "止盈1"

# 选股
go run app/command/console.go paper signal        # 扫描全市场
go run app/command/console.go paper signal 600036 # 分析单只

# 分析
go run app/command/console.go paper evolve        # 自主进化
go run app/command/console.go paper report today  # 今日报告
go run app/command/console.go paper simulate       # 历史回测

# 每日
go run app/command/console.go paper daily         # 每日更新
```

---

## API 测试

### 注册用户

```bash
curl -X POST http://localhost:8888/api/v1/user/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@126.com",
    "password": "password123"
  }'
```

### 登录

```bash
curl -X POST http://localhost:8888/api/v1/user/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```

### 使用 Token 访问受保护接口

```bash
curl http://localhost:8888/api/v1/strategies \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## 常见问题

### 1. MySQL 连接失败

```bash
# 检查 MySQL 是否运行
mysql -u root -p -e "SELECT 1"

# macOS 重启
brew services restart mysql

# 查看端口占用
lsof -i :3306
```

### 2. Redis 连接失败

```bash
# 检查 Redis
redis-cli ping

# macOS 重启
brew services restart redis
```

### 3. akshare 数据获取失败

```bash
# 更新 akshare
pip install akshare --upgrade

# 检查网络
curl -I https://push2his.eastmoney.com
```

### 4. 编译报错

```bash
# 清理缓存
go clean -cache

# 重新下载依赖
go mod tidy

# 检查 Go 版本
go version
```

### 5. JWT Token 无效

确保 `.env` 中的 `JWT_ACCESS_SECRET` 至少 32 字符。

### 6. 端口被占用

```bash
# 查找占用端口的进程
lsof -i :8888

# 杀死进程
kill -9 <PID>
```

---

## 下一步

- 📖 阅读 [API.md](API.md) 了解完整接口
- 👨‍💻 阅读 [DEVELOPER.md](DEVELOPER.md) 学习如何添加新功能
- 📊 阅读 [PAPERTRADING.md](PAPERTRADING.md) 深入模拟盘系统

# QuantSaaS

基于感知-决策智能的量化策略平台

## 📖 项目简介

QuantSaaS 是首个将宏观政策感知、AI辅助决策与用户自主创造深度融合的量化策略SaaS平台，实现量化投资的"技术民主化"。

## ✨ 核心特性

### 🎯 新闻政策感知引擎
- 多源数据接入：新华社、央行、交易所等官方数据
- NLP情感分析：情感打分、事件提取、影响传导图谱
- 因子工厂：自动生成量化投资因子

### 🏭 策略工坊
- 三层架构：AI生成层 → 策略超市层 → 用户定制层
- 多模式支持：自然语言、流程图、专业代码IDE
- 智能协同：AI启发，人类决策

### 🤖 AI辅助决策中心
- 策略优化建议和逻辑分析
- 行业轮动信号和趋势预测
- 收益归因解读和风险评估

### ⚡ 智能执行与风控
- 合规前置检查和实时审核
- 个性化风控规则和熔断机制
- 策略托管和自动执行

## 🏗️ 技术架构

```
数据源层          计算中台层          应用服务层          接入层
├── 行情数据      ├── 流处理引擎    ├── API服务        ├── WebSocket
├── 新闻政策      ├── 批量计算      ├── 感知引擎       ├── REST API
└── 基本面数据    ├── AI模型服务    ├── 策略工坊       └── 移动端
                   ├── 策略运行时    ├── AI决策中心
                   └── 风控引擎      └── 执行服务
```

## 🚀 快速开始

### Docker环境（推荐）
```bash
make dev          # 启动开发环境
make migrate-up   # 执行数据库迁移
make dev-logs     # 查看服务状态
```

### 本地环境
```bash
go mod download
docker run -d --name mysql -e MYSQL_ROOT_PASSWORD=quantos123 -p 3306:3306 mysql:8.0
docker run -d --name redis -p 6379:6379 redis:7-alpine
go run app/command/console.go migrate up
make run-api
```

### 验证服务
```bash
curl http://localhost:8888/health
# {"status":"ok","service":"quantos-api"}
```

## 📋 API示例

### 用户注册
```bash
curl -X POST http://localhost:8888/api/v1/user/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","email":"demo@tal.com","password":"demo123"}'
```

### 获取Token
```bash
curl -X POST http://localhost:8888/api/v1/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo123"}'
```

## 💼 商业模式

### Freemium订阅体系
- **免费版**：基础行情、新闻摘要、简易回测
- **专业版**：全量数据、高级因子、无限制回测
- **机构版**：私有部署、专属数据源、独立风控

### 增值服务
- 📊 数据超市：第三方特色数据购买
- 🤝 策略托管：优秀策略分享与收益分成
- 👨‍💼 专家咨询：行业分析师一对一服务

## 🛠️ 技术栈

- **框架**：go-zero 微服务框架
- **语言**：Go 1.22
- **存储**：MySQL + Redis
- **消息**：Apache Pulsar
- **部署**：Docker + Kubernetes

## 📁 项目结构

```
quantos/
├── app/                    # 应用服务层
│   ├── api/               # REST API服务 ✅
│   ├── newsPolicyEngine/  # 新闻政策感知引擎 🟡
│   ├── strategyWorkshop/  # 策略工坊 🟡
│   ├── aiAssistant/       # AI决策中心 🟡
│   ├── smartExecution/    # 智能执行服务 🟡
│   ├── command/           # 命令行工具 ✅
│   └── model/             # 数据模型 ✅
├── common/                # 通用工具 ✅
├── pkg/                   # 业务包 (预留)
├── constant/              # 常量定义 ✅
├── database/migrations/   # 数据库迁移 ✅
└── deploy/               # 部署配置 ✅
```

## 🔄 开发进度

- ✅ 基础架构和API服务
- ✅ 用户管理和数据模型
- ✅ 数据库迁移和部署配置
- 🟡 RPC服务层 (架构预留)
- 🟡 核心业务功能 (待开发)

## 📞 联系我们

- **项目主页**: https://github.com/tal-tech/quantos
- **技术文档**: https://docs.tal.com/quantos
- **邮箱**: quantos@tal.com
- **内部论坛**: https://forum.tal.com/c/quantos

---

*"让量化投资不再是少数人的游戏"* 🚀
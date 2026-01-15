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
  -d '{"username":"demo","email":"demo@126.com","password":"demo123"}'
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
│   ├── stockData/         # 股票数据服务 🆕
│   ├── marketAnalysis/    # 市场分析服务 🆕
│   ├── trading/           # 交易服务 🆕
│   ├── specialAnalysis/   # 专项分析服务 🆕
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
- ✅ StockApi数据服务集成 (架构设计 + Proto定义)
- 🟡 RPC服务层 (架构预留)
- 🟡 核心业务功能 (待开发)

## 📊 StockApi 数据服务功能

### 🎯 已集成功能 (架构设计)

#### 1. 股票数据服务 (StockData)
- **实时行情**: Level2实时数据、实时报价推送
- **历史数据**: 股票/板块日K线行情数据
- **基础数据**: A股列表、大盘指数信息
- **技术指标**: 实时技术指标计算和分析

#### 2. 市场分析服务 (MarketAnalysis)
- **AI智能选股**: 基于机器学习的智能选股系统
- **情绪周期分析**: 市场情绪周期和趋势分析
- **技术指标**: 专业技术指标分析 (MA/MACD/RSI/KDJ/BOLL)
- **板块龙头股**: 行业板块龙头股票分析
- **涨停股池**: 涨停股票实时监控和分析
- **板块概念**: 概念板块热度和趋势分析
- **异动数据**: 股票异动实时监控
- **游资数据**: 游资动向和资金流入流出分析

#### 3. 策略服务 (Strategy)
- **大模型策略**: AI大模型生成交易策略
- **策略精选**: 优质策略推荐和评分系统
- **策略回测**: 专业策略回测引擎和绩效分析
- **收益回测**: 详细的收益归因和风险分析

#### 4. 交易服务 (Trading)
- **下单买卖**: 股票交易委托和执行
- **订单管理**: 订单查询、撤单、状态跟踪
- **账户管理**: 多账户管理和资金查询
- **持仓管理**: 实时持仓和盈亏计算
- **风控检查**: 交易前的风险控制和合规检查

#### 5. 专项分析服务 (SpecialAnalysis)
- **竞价专题**: 集合竞价数据分析和机会识别
- **风险预警**: 实时风险监控和预警系统
- **竞价抢筹**: 竞价阶段资金抢筹分析
- **基础数据增强**: 财务数据和基本面深度分析
- **交易日历**: 交易日程和重要事件提醒
- **ST股列表**: ST股实时监控和风险提示
- **龙虎榜单**: 机构席位和龙虎榜数据分析
- **资金流向**: 板块和个股资金流向分析

### 🚀 API接口示例

#### 实时行情查询
```bash
# 获取股票实时行情
curl -X GET "http://localhost:8888/api/v1/stock/quote?symbols=000001,600000" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### AI智能选股
```bash
# 获取AI推荐股票
curl -X GET "http://localhost:8888/api/v1/market/ai-selection?strategy_type=growth&limit=10" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 策略回测
```bash
# 执行策略回测
curl -X POST "http://localhost:8888/api/v1/strategy/backtest" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "strategy_001",
    "symbol": "000001",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "initial_capital": 100000
  }'
```

#### 股票交易
```bash
# 下单买入
curl -X POST "http://localhost:8888/api/v1/trading/order" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "000001",
    "direction": "BUY",
    "order_type": "LIMIT",
    "price": 10.50,
    "quantity": 100
  }'
```

### 🏗️ 技术实现

#### Proto文件定义
- `pb/stock.proto`: 股票数据服务接口
- `pb/market_analysis.proto`: 市场分析服务接口
- `pb/strategy.proto`: 策略服务接口
- `pb/trading.proto`: 交易服务接口
- `pb/special_analysis.proto`: 专项分析服务接口

#### API路由集成
- `/api/v1/stock/*`: 股票数据相关接口
- `/api/v1/market/*`: 市场分析相关接口
- `/api/v1/strategy/*`: 策略相关接口
- `/api/v1/trading/*`: 交易相关接口
- `/api/v1/analysis/*`: 专项分析相关接口

#### 服务架构
```
API Gateway (8888)
├── StockData Service (8085)
├── MarketAnalysis Service (8086)
├── Strategy Service (8087)
├── Trading Service (8088)
└── SpecialAnalysis Service (8089)
```

## 📞 联系我们

- **项目主页**: https://github.com/tangpanpan23
- **邮箱**: tangpan23@126.com

---

*"让量化投资不再是少数人的游戏"* 🚀
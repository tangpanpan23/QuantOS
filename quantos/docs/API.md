# QuantSaaS API 文档

> 版本：v1.0 | Base URL：`http://localhost:8888` | 认证：JWT Bearer Token

---

## 认证

所有 API（除 `/health` 和 `/api/v1/user/register`、`/api/v1/user/login` 外）均需要 JWT Token。

```
Authorization: Bearer <your_jwt_token>
```

---

## 健康检查

### GET /health

服务健康检查。

**响应示例：**
```json
{
  "status": "ok",
  "service": "quantos-api"
}
```

---

## 用户管理

### POST /api/v1/user/register

用户注册。

**请求体：**
```json
{
  "username": "quant_trader",
  "email": "trader@126.com",
  "password": "secure_password"
}
```

**响应示例：**
```json
{
  "code": 0,
  "message": "注册成功",
  "data": {
    "id": 1,
    "username": "quant_trader",
    "email": "trader@126.com"
  }
}
```

---

### POST /api/v1/user/login

用户登录。

**请求体：**
```json
{
  "username": "quant_trader",
  "password": "secure_password"
}
```

**响应示例：**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access_expire": 86400,
  "user": {
    "id": 1,
    "username": "quant_trader",
    "email": "trader@126.com",
    "role": 1
  }
}
```

---

### GET /api/v1/user/:user_id

获取用户信息。

**路径参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| user_id | uint64 | 用户ID |

**响应示例：**
```json
{
  "id": 1,
  "username": "quant_trader",
  "email": "trader@126.com",
  "total_assets": 200000,
  "total_returns": 5.2,
  "win_rate": 62.5,
  "subscription": 1
}
```

---

### PUT /api/v1/user/:user_id

更新用户信息。

**请求体：**
```json
{
  "phone": "13800138000",
  "nickname": "量化新手",
  "risk_tolerance": 0.7,
  "time_horizon": 2
}
```

---

## 策略管理

### POST /api/v1/strategies

创建策略。

**请求体：**
```json
{
  "name": "新能源轮动策略",
  "description": "基于政策情感的行业轮动策略",
  "code": "func Strategy() { ... }",
  "type": 2,
  "category": "sector_rotation"
}
```

| type | 说明 |
|------|------|
| 1 | 手动策略 |
| 2 | AI生成策略 |
| 3 | 模板策略 |

---

### GET /api/v1/strategies

获取策略列表。

**查询参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| user_id | uint64 | - | 按用户筛选 |
| type | int8 | - | 策略类型 |
| status | int8 | - | 状态 |
| category | string | - | 分类 |
| page | int64 | 1 | 页码 |
| page_size | int64 | 20 | 每页数量 |

---

### POST /api/v1/strategies/:strategy_id/run

运行策略回测。

**响应示例：**
```json
{
  "task_id": "task_abc123",
  "status": "running",
  "message": "策略回测任务已提交"
}
```

---

## 投资组合

### POST /api/v1/portfolios

创建投资组合。

**请求体：**
```json
{
  "name": "我的模拟组合",
  "description": "趋势跟踪组合",
  "initial_cash": 100000
}
```

---

### GET /api/v1/portfolios

获取投资组合列表。

---

### GET /api/v1/portfolios/:portfolio_id

获取投资组合详情（含持仓）。

**响应示例：**
```json
{
  "id": 1,
  "name": "我的模拟组合",
  "status": 1,
  "initial_cash": 100000,
  "total_value": 105200,
  "total_return": 5.2,
  "positions": [
    {
      "symbol": "600036",
      "symbol_name": "招商银行",
      "quantity": 300,
      "avg_cost": 35.50,
      "current_price": 37.20,
      "market_value": 11160,
      "unrealized_pnl": 510
    }
  ]
}
```

---

## 市场数据

### GET /api/v1/market/data

获取K线数据。

**查询参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| symbol | string | ✅ | 股票代码，如 `600036` |
| date | string | - | 日期 `YYYY-MM-DD` |
| limit | int64 | - | 数量，默认100 |

**响应示例：**
```json
{
  "list": [
    {
      "symbol": "600036",
      "symbol_name": "招商银行",
      "open_price": 35.00,
      "high_price": 35.80,
      "low_price": 34.90,
      "close_price": 35.50,
      "volume": 1250000,
      "trade_date": "2026-04-30",
      "ma5": 35.20,
      "ma20": 34.80,
      "rsi": 55.3
    }
  ]
}
```

---

## 新闻政策

### GET /api/v1/news

获取新闻列表。

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| category | string | 分类：`macro`、`industry`、`company` |
| sentiment | string | 情感：`positive`、`negative`、`neutral` |
| start_date | string | 开始日期 |
| end_date | string | 结束日期 |
| page | int64 | 页码 |
| page_size | int64 | 每页数量 |

---

### GET /api/v1/policy

获取政策信息列表（同 `/api/v1/news`，但专门筛选政策类）。

---

## 因子数据

### GET /api/v1/market/factors

获取量化因子数据。

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| factor_code | string | 因子代码 |
| symbol | string | 股票代码 |
| type | int8 | 因子类型 |
| start_date | string | 开始日期 |
| end_date | string | 结束日期 |
| limit | int64 | 数量限制 |

---

## 策略工坊

### POST /api/v1/workshop/generate

AI 生成策略。

**请求体：**
```json
{
  "prompt": "基于新能源板块的均值回归策略",
  "category": "mean_reversion"
}
```

---

### GET /api/v1/workshop/templates

获取策略模板列表。

---

### POST /api/v1/workshop/backtest

策略回测。

---

## AI 决策

### POST /api/v1/ai/analyze

AI 分析策略。

**请求体：**
```json
{
  "strategy_id": 1,
  "content": "策略代码或描述"
}
```

---

### GET /api/v1/ai/suggestions

获取AI优化建议。

---

## 股票数据（StockApi）

### GET /api/v1/stock/list

获取A股股票列表。

---

### GET /api/v1/stock/quote

获取股票实时行情。

**查询参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| symbols | string | ✅ | 股票代码，多个用逗号分隔，如 `600036,600900` |

**响应示例：**
```json
{
  "data": {
    "600036": {
      "symbol": "600036",
      "name": "招商银行",
      "price": 35.50,
      "change_pct": 1.25,
      "volume": 3500000,
      "amount": 1234567890
    }
  }
}
```

---

### GET /api/v1/stock/kline

获取K线数据。

**查询参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| symbol | string | ✅ | 股票代码 |
| period | string | - | 周期：`daily`、`weekly`、`monthly`，默认 `daily` |
| adjust | string | - | 复权：`qfq`（前复权）、`hfqf`（后复权）、`none`，默认 `qfq` |
| limit | int64 | - | 数据条数，默认 60 |

---

### GET /api/v1/stock/index

获取大盘指数。

---

### GET /api/v1/stock/level2

获取Level2行情数据（需要专业版权限）。

---

## 市场分析

### GET /api/v1/market/ai-selection

AI智能选股。

**查询参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| strategy_type | string | 策略类型：`growth`（成长）、`value`（价值）、`momentum`（动量） |
| limit | int64 | 返回数量，默认10 |

---

### GET /api/v1/market/sentiment

市场情绪周期分析。

---

### GET /api/v1/market/technical

技术指标分析。

**查询参数：**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| symbol | string | ✅ | 股票代码 |

---

### GET /api/v1/market/sector-leaders

行业板块龙头股。

---

### GET /api/v1/market/limit-up-pool

涨停股池。

---

### GET /api/v1/market/sector-concepts

概念板块热度。

---

### GET /api/v1/market/hot-money

游资数据。

---

## 策略（增强版）

### POST /api/v1/strategy/generate-ai

AI生成交易策略。

### POST /api/v1/strategy/backtest

策略回测。

**请求体：**
```json
{
  "strategy_id": "strategy_001",
  "symbol": "000001",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 100000
}
```

### GET /api/v1/strategy/performance

获取策略表现分析。

### GET /api/v1/strategy/featured

获取精选策略列表。

---

## 交易

### POST /api/v1/trading/order

下单。

**请求体：**
```json
{
  "symbol": "600036",
  "direction": "BUY",
  "order_type": "LIMIT",
  "price": 35.50,
  "quantity": 100
}
```

| direction | 说明 |
|-----------|------|
| BUY | 买入 |
| SELL | 卖出 |

| order_type | 说明 |
|-------------|------|
| LIMIT | 限价单 |
| MARKET | 市价单 |

---

### DELETE /api/v1/trading/order/:order_id

撤单。

---

### GET /api/v1/trading/orders

获取订单列表。

---

### GET /api/v1/trading/account

获取账户信息。

**响应示例：**
```json
{
  "account_id": 1,
  "cash": 60000,
  "total_value": 105200,
  "positions_count": 3,
  "total_pnl": 5200,
  "today_pnl": 350
}
```

---

### GET /api/v1/trading/positions

获取持仓列表。

---

### POST /api/v1/trading/risk-check

交易前风险检查。

---

## 专项分析

### GET /api/v1/analysis/auction

竞价数据专题。

### GET /api/v1/analysis/risk-warnings

风险预警。

### GET /api/v1/analysis/st-stocks

ST股列表。

### GET /api/v1/analysis/dragon-tiger

龙虎榜单。

### GET /api/v1/analysis/capital-flow

资金流向。

### GET /api/v1/analysis/trading-calendar

交易日历。

---

## 错误码

| code | 说明 |
|------|------|
| 0 | 成功 |
| 1001 | 参数错误 |
| 1002 | 认证失败 |
| 1003 | 权限不足 |
| 2001 | 资源不存在 |
| 3001 | 服务器内部错误 |
| 4001 | 业务逻辑错误 |

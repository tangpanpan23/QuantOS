package constant

// 策略状态
const (
	StrategyStatusDraft     = 1 // 草稿
	StrategyStatusTesting   = 2 // 测试中
	StrategyStatusPublished = 3 // 已发布
	StrategyStatusRunning   = 4 // 运行中
	StrategyStatusPaused    = 5 // 已暂停
	StrategyStatusStopped   = 6 // 已停止
)

// 策略类型
const (
	StrategyTypeManual   = 1 // 手动创建
	StrategyTypeAIGen    = 2 // AI生成
	StrategyTypeTemplate = 3 // 模板创建
)

// 用户角色
const (
	UserRoleAdmin    = 1 // 管理员
	UserRoleTrader   = 2 // 交易员
	UserRoleAnalyst  = 3 // 分析师
	UserRoleInvestor = 4 // 投资者
)

// 数据源类型
const (
	DataSourceTypeMarket    = 1 // 行情数据
	DataSourceTypeNews      = 2 // 新闻数据
	DataSourceTypePolicy    = 3 // 政策数据
	DataSourceTypeFinancial = 4 // 财务数据
	DataSourceTypeAlternative = 5 // 另类数据
)

// 因子类型
const (
	FactorTypeTechnical = 1 // 技术因子
	FactorTypeFundamental = 2 // 基本面因子
	FactorTypeSentiment  = 3 // 情感因子
	FactorTypeMacro      = 4 // 宏观因子
	FactorTypeCustom     = 5 // 自定义因子
)

// 交易信号
const (
	TradeSignalBuy  = 1 // 买入
	TradeSignalSell = 2 // 卖出
	TradeSignalHold = 3 // 持有
)

// 风控级别
const (
	RiskLevelLow    = 1 // 低风险
	RiskLevelMedium = 2 // 中风险
	RiskLevelHigh   = 3 // 高风险
)

// 订阅计划
const (
	SubscriptionFree     = 1 // 免费版
	SubscriptionPro      = 2 // 专业版
	SubscriptionEnterprise = 3 // 企业版
)

// 消息队列主题
const (
	TopicMarketData    = "market.data"
	TopicNewsData      = "news.data"
	TopicPolicyData    = "policy.data"
	TopicTradeSignal   = "trade.signal"
	TopicStrategyEvent = "strategy.event"
)

// 缓存键前缀
const (
	CacheKeyUser        = "user:"
	CacheKeyStrategy    = "strategy:"
	CacheKeyMarketData  = "market:"
	CacheKeyFactor      = "factor:"
	CacheKeyToken       = "token:"
)

// 时间格式
const (
	DateFormat     = "2006-01-02"
	TimeFormat     = "15:04:05"
	DateTimeFormat = "2006-01-02 15:04:05"
)

// 默认分页参数
const (
	DefaultPageSize = 20
	MaxPageSize     = 100
)

// 情感分析结果
const (
	SentimentNegative = -1.0 // 负面
	SentimentNeutral  = 0.0  // 中性
	SentimentPositive = 1.0  // 正面
)

// 市场状态
const (
	MarketStatusNormal     = 1 // 正常
	MarketStatusPreOpen    = 2 // 盘前
	MarketStatusOpen       = 3 // 开盘
	MarketStatusBreak      = 4 // 休市
	MarketStatusClose      = 5 // 收盘
	MarketStatusAfterClose = 6 // 盘后
)

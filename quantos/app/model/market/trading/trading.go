package trading

import (
	"quantos/app/model"
)

// TradeOrder 交易订单模型
type TradeOrder struct {
	model.BaseModel

	UserID       uint64  `gorm:"column:user_id;not null;index:idx_user_id;comment:用户ID"`
	StrategyID   uint64  `gorm:"column:strategy_id;index:idx_strategy_id;comment:策略ID"`
	PortfolioID  uint64  `gorm:"column:portfolio_id;not null;index:idx_portfolio_id;comment:投资组合ID"`

	// 订单信息
	OrderID      string  `gorm:"column:order_id;type:varchar(50);uniqueIndex:uk_order_id;comment:订单号"`
	Symbol       string  `gorm:"column:symbol;type:varchar(20);not null;comment:股票代码"`
	SymbolName   string  `gorm:"column:symbol_name;type:varchar(100);comment:股票名称"`

	// 交易方向和类型
	Side         string  `gorm:"column:side;type:varchar(10);not null;comment:买卖方向: buy,sell"`
	OrderType    string  `gorm:"column:order_type;type:varchar(20);not null;comment:订单类型: market,limit,stop"`

	// 数量和价格
	Quantity     float64 `gorm:"column:quantity;type:decimal(20,4);not null;comment:委托数量"`
	Price        float64 `gorm:"column:price;type:decimal(10,4);comment:委托价格"`
	Amount       float64 `gorm:"column:amount;type:decimal(20,2);comment:委托金额"`

	// 订单状态
	Status       string  `gorm:"column:status;type:varchar(20);not null;default:'pending';comment:订单状态: pending,submitted,partial,completed,cancelled,rejected"`
	FilledQty    float64 `gorm:"column:filled_qty;type:decimal(20,4);default:0.0000;comment:已成交数量"`
	AvgFillPrice float64 `gorm:"column:avg_fill_price;type:decimal(10,4);comment:平均成交价"`

	// 时间信息
	SubmitTime   string  `gorm:"column:submit_time;type:datetime;comment:提交时间"`
	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`

	// 交易所信息
	Exchange     string  `gorm:"column:exchange;type:varchar(20);comment:交易所"`
	BrokerID     string  `gorm:"column:broker_id;type:varchar(20);comment:券商ID"`

	// 备注信息
	Notes        string  `gorm:"column:notes;type:text;comment:备注"`
	ErrorMsg     string  `gorm:"column:error_msg;type:varchar(500);comment:错误信息"`
}

// TableName 指定表名
func (TradeOrder) TableName() string {
	return "q_trade_orders"
}

// TradeExecution 交易执行记录模型
type TradeExecution struct {
	model.BaseModel

	OrderID      string  `gorm:"column:order_id;type:varchar(50);not null;index:idx_order_id;comment:订单ID"`
	ExecutionID  string  `gorm:"column:execution_id;type:varchar(50);uniqueIndex:uk_execution_id;comment:执行ID"`

	UserID       uint64  `gorm:"column:user_id;not null;comment:用户ID"`
	Symbol       string  `gorm:"column:symbol;type:varchar(20);not null;comment:股票代码"`

	// 执行信息
	Side         string  `gorm:"column:side;type:varchar(10);not null;comment:买卖方向"`
	Quantity     float64 `gorm:"column:quantity;type:decimal(20,4);not null;comment:执行数量"`
	Price        float64 `gorm:"column:price;type:decimal(10,4);not null;comment:执行价格"`
	Amount       float64 `gorm:"column:amount;type:decimal(20,2);not null;comment:执行金额"`

	// 费用信息
	Commission   float64 `gorm:"column:commission;type:decimal(10,2);default:0.00;comment:佣金"`
	StampTax     float64 `gorm:"column:stamp_tax;type:decimal(10,2);default:0.00;comment:印花税"`
	TransferFee  float64 `gorm:"column:transfer_fee;type:decimal(10,2);default:0.00;comment:过户费"`

	// 时间信息
	ExecutionTime string `gorm:"column:execution_time;type:datetime;not null;comment:执行时间"`

	// 交易所信息
	Exchange     string  `gorm:"column:exchange;type:varchar(20);comment:交易所"`
	BrokerID     string  `gorm:"column:broker_id;type:varchar(20);comment:券商ID"`
}

// TableName 指定表名
func (TradeExecution) TableName() string {
	return "q_trade_executions"
}

// AccountBalance 账户余额模型
type AccountBalance struct {
	model.BaseModel

	UserID       uint64  `gorm:"column:user_id;not null;uniqueIndex:uk_user_currency;comment:用户ID"`
	Currency     string  `gorm:"column:currency;type:varchar(10);not null;uniqueIndex:uk_user_currency;default:'CNY';comment:货币类型"`

	// 余额信息
	TotalBalance float64 `gorm:"column:total_balance;type:decimal(20,2);default:0.00;comment:总余额"`
	AvailableBalance float64 `gorm:"column:available_balance;type:decimal(20,2);default:0.00;comment:可用余额"`
	FrozenBalance float64 `gorm:"column:frozen_balance;type:decimal(20,2);default:0.00;comment:冻结余额"`

	// 市值信息
	TotalMarketValue float64 `gorm:"column:total_market_value;type:decimal(20,2);default:0.00;comment:总市值"`
	TotalEquity   float64 `gorm:"column:total_equity;type:decimal(20,2);default:0.00;comment:总资产"`

	// 盈亏信息
	TotalPnL      float64 `gorm:"column:total_pnl;type:decimal(20,2);default:0.00;comment:总盈亏"`
	DayPnL        float64 `gorm:"column:day_pnl;type:decimal(20,2);default:0.00;comment:当日盈亏"`

	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`
}

// TableName 指定表名
func (AccountBalance) TableName() string {
	return "q_account_balance"
}

// RiskControl 风险控制模型
type RiskControl struct {
	model.BaseModel

	UserID       uint64  `gorm:"column:user_id;not null;uniqueIndex:uk_user_type;comment:用户ID"`
	ControlType  string  `gorm:"column:control_type;type:varchar(20);not null;uniqueIndex:uk_user_type;comment:控制类型: position_size,max_drawdown,daily_loss等"`

	// 控制参数
	MaxValue     float64 `gorm:"column:max_value;type:decimal(10,4);comment:最大值"`
	MinValue     float64 `gorm:"column:min_value;type:decimal(10,4);comment:最小值"`
	Threshold    float64 `gorm:"column:threshold;type:decimal(10,4);comment:阈值"`

	// 控制状态
	IsEnabled    int8    `gorm:"column:is_enabled;type:tinyint(4);default:1;comment:是否启用"`
	ViolationCount int   `gorm:"column:violation_count;type:int;default:0;comment:违规次数"`

	LastViolationTime string `gorm:"column:last_violation_time;type:datetime;comment:最后违规时间"`

	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`
}

// TableName 指定表名
func (RiskControl) TableName() string {
	return "q_risk_control"
}

// AuctionData 竞价数据模型
type AuctionData struct {
	model.BaseModel

	Symbol       string  `gorm:"column:symbol;type:varchar(20);not null;index:idx_symbol_date;comment:股票代码"`
	TradeDate    string  `gorm:"column:trade_date;type:date;not null;index:idx_symbol_date;comment:交易日期"`

	// 竞价阶段
	AuctionPhase string  `gorm:"column:auction_phase;type:varchar(20);comment:竞价阶段: call_auction,continuous"`

	// 竞价数据
	BidVolume    int64   `gorm:"column:bid_volume;type:bigint;comment:买单总量"`
	AskVolume    int64   `gorm:"column:ask_volume;type:bigint;comment:卖单总量"`
	BidAmount    float64 `gorm:"column:bid_amount;type:decimal(20,2);comment:买单总金额"`
	AskAmount    float64 `gorm:"column:ask_amount;type:decimal(20,2);comment:卖单总金额"`

	// 匹配结果
	MatchPrice   float64 `gorm:"column:match_price;type:decimal(10,4);comment:匹配价格"`
	MatchVolume  int64   `gorm:"column:match_volume;type:bigint;comment:匹配数量"`
	MatchAmount  float64 `gorm:"column:match_amount;type:decimal(20,2);comment:匹配金额"`

	// 价位分布 (JSON格式存储)
	PriceDistribution string `gorm:"column:price_distribution;type:json;comment:价位分布数据"`

	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`
}

// TableName 指定表名
func (AuctionData) TableName() string {
	return "q_auction_data"
}

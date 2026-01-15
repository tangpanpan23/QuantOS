package realtime

import (
	"quantos/app/model"
)

// RealTimeQuote 实时报价模型
type RealTimeQuote struct {
	model.BaseModel

	Symbol       string  `gorm:"column:symbol;type:varchar(20);not null;index:idx_symbol_time;comment:股票代码"`
	Name         string  `gorm:"column:name;type:varchar(100);comment:股票名称"`

	// 价格信息
	Price        float64 `gorm:"column:price;type:decimal(10,4);not null;comment:最新价"`
	OpenPrice    float64 `gorm:"column:open_price;type:decimal(10,4);comment:开盘价"`
	HighPrice    float64 `gorm:"column:high_price;type:decimal(10,4);comment:最高价"`
	LowPrice     float64 `gorm:"column:low_price;type:decimal(10,4);comment:最低价"`
	PreClose     float64 `gorm:"column:pre_close;type:decimal(10,4);comment:昨收价"`

	// 交易信息
	Volume       int64   `gorm:"column:volume;type:bigint;comment:成交量"`
	Amount       float64 `gorm:"column:amount;type:decimal(20,2);comment:成交额"`

	// 涨跌幅
	Change       float64 `gorm:"column:change;type:decimal(10,4);comment:涨跌额"`
	ChangePct    float64 `gorm:"column:change_pct;type:decimal(7,4);comment:涨跌幅"`

	// 买卖五档
	BidPrice1    float64 `gorm:"column:bid_price1;type:decimal(10,4);comment:买一价"`
	BidVolume1   int64   `gorm:"column:bid_volume1;type:bigint;comment:买一量"`
	BidPrice2    float64 `gorm:"column:bid_price2;type:decimal(10,4);comment:买二价"`
	BidVolume2   int64   `gorm:"column:bid_volume2;type:bigint;comment:买二量"`
	BidPrice3    float64 `gorm:"column:bid_price3;type:decimal(10,4);comment:买三价"`
	BidVolume3   int64   `gorm:"column:bid_volume3;type:bigint;comment:买三量"`
	BidPrice4    float64 `gorm:"column:bid_price4;type:decimal(10,4);comment:买四价"`
	BidVolume4   int64   `gorm:"column:bid_volume4;type:bigint;comment:买四量"`
	BidPrice5    float64 `gorm:"column:bid_price5;type:decimal(10,4);comment:买五价"`
	BidVolume5   int64   `gorm:"column:bid_volume5;type:bigint;comment:买五量"`

	AskPrice1    float64 `gorm:"column:ask_price1;type:decimal(10,4);comment:卖一价"`
	AskVolume1   int64   `gorm:"column:ask_volume1;type:bigint;comment:卖一量"`
	AskPrice2    float64 `gorm:"column:ask_price2;type:decimal(10,4);comment:卖二价"`
	AskVolume2   int64   `gorm:"column:ask_volume2;type:bigint;comment:卖二量"`
	AskPrice3    float64 `gorm:"column:ask_price3;type:decimal(10,4);comment:卖三价"`
	AskVolume3   int64   `gorm:"column:ask_volume3;type:bigint;comment:卖三量"`
	AskPrice4    float64 `gorm:"column:ask_price4;type:decimal(10,4);comment:卖四价"`
	AskVolume4   int64   `gorm:"column:ask_volume4;type:bigint;comment:卖四量"`
	AskPrice5    float64 `gorm:"column:ask_price5;type:decimal(10,4);comment:卖五价"`
	AskVolume5   int64   `gorm:"column:ask_volume5;type:bigint;comment:卖五量"`

	// 时间信息
	TradeTime    string  `gorm:"column:trade_time;type:datetime;not null;index:idx_symbol_time;comment:交易时间"`
	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`

	// 市场状态
	Status       int8    `gorm:"column:status;type:tinyint(4);default:1;comment:状态: 1-正常, 2-停牌"`
	Market       string  `gorm:"column:market;type:varchar(10);comment:市场"`
}

// TableName 指定表名
func (RealTimeQuote) TableName() string {
	return "q_realtime_quote"
}

// Level2Data Level2深度数据模型
type Level2Data struct {
	model.BaseModel

	Symbol       string  `gorm:"column:symbol;type:varchar(20);not null;index:idx_symbol_time;comment:股票代码"`

	// 逐笔成交
	TradePrice   float64 `gorm:"column:trade_price;type:decimal(10,4);comment:成交价"`
	TradeVolume  int64   `gorm:"column:trade_volume;type:bigint;comment:成交量"`
	TradeTime    string  `gorm:"column:trade_time;type:datetime;not null;index:idx_symbol_time;comment:成交时间"`
	TradeType    string  `gorm:"column:trade_type;type:varchar(10);comment:成交类型"`

	// 买卖队列 (前10档)
	BuyOrders    string  `gorm:"column:buy_orders;type:json;comment:买单队列JSON"`
	SellOrders   string  `gorm:"column:sell_orders;type:json;comment:卖单队列JSON"`

	// 市场统计
	TotalBidVolume int64 `gorm:"column:total_bid_volume;type:bigint;comment:总买单量"`
	TotalAskVolume int64 `gorm:"column:total_ask_volume;type:bigint;comment:总卖单量"`

	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`
}

// TableName 指定表名
func (Level2Data) TableName() string {
	return "q_level2_data"
}

// MarketCapitalFlow 市场资金流向模型
type MarketCapitalFlow struct {
	model.BaseModel

	TradeDate    string  `gorm:"column:trade_date;type:date;not null;uniqueIndex:uk_date;comment:交易日期"`

	// 主力资金
	MainInflow   float64 `gorm:"column:main_inflow;type:decimal(20,2);comment:主力净流入"`
	MainOutflow  float64 `gorm:"column:main_outflow;type:decimal(20,2);comment:主力净流出"`
	MainNet      float64 `gorm:"column:main_net;type:decimal(20,2);comment:主力净额"`

	// 超大单
	LargeInflow  float64 `gorm:"column:large_inflow;type:decimal(20,2);comment:超大单净流入"`
	LargeOutflow float64 `gorm:"column:large_outflow;type:decimal(20,2);comment:超大单净流出"`
	LargeNet     float64 `gorm:"column:large_net;type:decimal(20,2);comment:超大单净额"`

	// 大单
	BigInflow    float64 `gorm:"column:big_inflow;type:decimal(20,2);comment:大单净流入"`
	BigOutflow   float64 `gorm:"column:big_outflow;type:decimal(20,2);comment:大单净流出"`
	BigNet       float64 `gorm:"column:big_net;type:decimal(20,2);comment:大单净额"`

	// 中单
	MediumInflow float64 `gorm:"column:medium_inflow;type:decimal(20,2);comment:中单净流入"`
	MediumOutflow float64 `gorm:"column:medium_outflow;type:decimal(20,2);comment:中单净流出"`
	MediumNet    float64 `gorm:"column:medium_net;type:decimal(20,2);comment:中单净额"`

	// 小单
	SmallInflow  float64 `gorm:"column:small_inflow;type:decimal(20,2);comment:小单净流入"`
	SmallOutflow float64 `gorm:"column:small_outflow;type:decimal(20,2);comment:小单净流出"`
	SmallNet     float64 `gorm:"column:small_net;type:decimal(20,2);comment:小单净额"`

	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`
}

// TableName 指定表名
func (MarketCapitalFlow) TableName() string {
	return "q_market_capital_flow"
}

// TradingCalendar 交易日历模型
type TradingCalendar struct {
	model.BaseModel

	TradeDate    string `gorm:"column:trade_date;type:date;not null;uniqueIndex:uk_date;comment:交易日期"`
	IsTradingDay int8   `gorm:"column:is_trading_day;type:tinyint(4);not null;default:1;comment:是否交易日: 1-是, 0-否"`
	Market       string `gorm:"column:market;type:varchar(10);not null;comment:市场代码"`

	// 特殊标记
	IsHoliday    int8   `gorm:"column:is_holiday;type:tinyint(4);default:0;comment:是否节假日"`
	IsHalfDay    int8   `gorm:"column:is_half_day;type:tinyint(4);default:0;comment:是否半日交易"`
	HolidayName  string `gorm:"column:holiday_name;type:varchar(50);comment:节假日名称"`

	// 时间信息
	PreTradeDate string `gorm:"column:pre_trade_date;type:date;comment:上一交易日"`
	NextTradeDate string `gorm:"column:next_trade_date;type:date;comment:下一交易日"`
}

// TableName 指定表名
func (TradingCalendar) TableName() string {
	return "q_trading_calendar"
}

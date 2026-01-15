package kline

import (
	"quantos/app/model"
)

// KlineData K线数据模型
type KlineData struct {
	model.BaseModel

	Symbol       string  `gorm:"column:symbol;type:varchar(20);not null;index:idx_symbol_period_time;comment:股票代码"`
	Name         string  `gorm:"column:name;type:varchar(100);comment:股票名称"`

	// 时间信息
	Period       string  `gorm:"column:period;type:varchar(10);not null;index:idx_symbol_period_time;comment:周期: 1m,5m,15m,30m,1h,1d,1w,1M"`
	StartTime    string  `gorm:"column:start_time;type:datetime;not null;index:idx_symbol_period_time;comment:开始时间"`
	EndTime      string  `gorm:"column:end_time;type:datetime;not null;comment:结束时间"`

	// 价格数据 (OHLC)
	OpenPrice    float64 `gorm:"column:open_price;type:decimal(10,4);not null;comment:开盘价"`
	HighPrice    float64 `gorm:"column:high_price;type:decimal(10,4);not null;comment:最高价"`
	LowPrice     float64 `gorm:"column:low_price;type:decimal(10,4);not null;comment:最低价"`
	ClosePrice   float64 `gorm:"column:close_price;type:decimal(10,4);not null;comment:收盘价"`

	// 成交数据
	Volume       int64   `gorm:"column:volume;type:bigint;comment:成交量"`
	Amount       float64 `gorm:"column:amount;type:decimal(20,2);comment:成交额"`

	// 技术指标
	MA5          float64 `gorm:"column:ma5;type:decimal(10,4);comment:5日均线"`
	MA10         float64 `gorm:"column:ma10;type:decimal(10,4);comment:10日均线"`
	MA20         float64 `gorm:"column:ma20;type:decimal(10,4);comment:20日均线"`
	MA30         float64 `gorm:"column:ma30;type:decimal(10,4);comment:30日均线"`
	MA60         float64 `gorm:"column:ma60;type:decimal(10,4);comment:60日均线"`

	EMA12        float64 `gorm:"column:ema12;type:decimal(10,4);comment:12日指数均线"`
	EMA26        float64 `gorm:"column:ema26;type:decimal(10,4);comment:26日指数均线"`

	MACD         float64 `gorm:"column:macd;type:decimal(10,6);comment:MACD指标"`
	MACD_SIGNAL  float64 `gorm:"column:macd_signal;type:decimal(10,6);comment:MACD信号线"`
	MACD_HIST    float64 `gorm:"column:macd_hist;type:decimal(10,6);comment:MACD柱状图"`

	RSI          float64 `gorm:"column:rsi;type:decimal(7,4);comment:RSI指标"`
	RSI6         float64 `gorm:"column:rsi6;type:decimal(7,4);comment:6日RSI"`
	RSI12        float64 `gorm:"column:rsi12;type:decimal(7,4);comment:12日RSI"`
	RSI24        float64 `gorm:"column:rsi24;type:decimal(7,4);comment:24日RSI"`

	KDJ_K        float64 `gorm:"column:kdj_k;type:decimal(7,4);comment:KDJ-K值"`
	KDJ_D        float64 `gorm:"column:kdj_d;type:decimal(7,4);comment:KDJ-D值"`
	KDJ_J        float64 `gorm:"column:kdj_j;type:decimal(7,4);comment:KDJ-J值"`

	BOLL_UPPER   float64 `gorm:"column:boll_upper;type:decimal(10,4);comment:布林线上轨"`
	BOLL_MIDDLE  float64 `gorm:"column:boll_middle;type:decimal(10,4);comment:布林线中轨"`
	BOLL_LOWER   float64 `gorm:"column:boll_lower;type:decimal(10,4);comment:布林线下轨"`

	// 波动率指标
	ATR          float64 `gorm:"column:atr;type:decimal(10,4);comment:ATR指标"`
	CCI          float64 `gorm:"column:cci;type:decimal(10,4);comment:CCI指标"`
	WILLR        float64 `gorm:"column:willr;type:decimal(10,4);comment:WILLR指标"`

	// 数据质量
	DataQuality  int8    `gorm:"column:data_quality;type:tinyint(4);default:1;comment:数据质量: 1-完整, 2-部分缺失, 3-异常"`

	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`
}

// TableName 指定表名
func (KlineData) TableName() string {
	return "q_kline_data"
}

// SectorKlineData 板块K线数据模型
type SectorKlineData struct {
	model.BaseModel

	SectorCode   string  `gorm:"column:sector_code;type:varchar(20);not null;index:idx_sector_period_time;comment:板块代码"`
	SectorName   string  `gorm:"column:sector_name;type:varchar(100);comment:板块名称"`

	// 时间信息
	Period       string  `gorm:"column:period;type:varchar(10);not null;index:idx_sector_period_time;comment:周期"`
	StartTime    string  `gorm:"column:start_time;type:datetime;not null;index:idx_sector_period_time;comment:开始时间"`
	EndTime      string  `gorm:"column:end_time;type:datetime;not null;comment:结束时间"`

	// 价格数据
	OpenPrice    float64 `gorm:"column:open_price;type:decimal(10,4);not null;comment:开盘价"`
	HighPrice    float64 `gorm:"column:high_price;type:decimal(10,4);not null;comment:最高价"`
	LowPrice     float64 `gorm:"column:low_price;type:decimal(10,4);not null;comment:最低价"`
	ClosePrice   float64 `gorm:"column:close_price;type:decimal(10,4);not null;comment:收盘价"`

	// 成交数据
	Volume       int64   `gorm:"column:volume;type:bigint;comment:成交量"`
	Amount       float64 `gorm:"column:amount;type:decimal(20,2);comment:成交额"`

	// 技术指标 (简版)
	MA5          float64 `gorm:"column:ma5;type:decimal(10,4);comment:5日均线"`
	MA10         float64 `gorm:"column:ma10;type:decimal(10,4);comment:10日均线"`
	MA20         float64 `gorm:"column:ma20;type:decimal(10,4);comment:20日均线"`

	ChangePct    float64 `gorm:"column:change_pct;type:decimal(7,4);comment:涨跌幅"`

	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`
}

// TableName 指定表名
func (SectorKlineData) TableName() string {
	return "q_sector_kline_data"
}

// IndexKlineData 指数K线数据模型
type IndexKlineData struct {
	model.BaseModel

	IndexCode    string  `gorm:"column:index_code;type:varchar(20);not null;index:idx_index_period_time;comment:指数代码"`
	IndexName    string  `gorm:"column:index_name;type:varchar(100);comment:指数名称"`

	// 时间信息
	Period       string  `gorm:"column:period;type:varchar(10);not null;index:idx_index_period_time;comment:周期"`
	StartTime    string  `gorm:"column:start_time;type:datetime;not null;index:idx_index_period_time;comment:开始时间"`
	EndTime      string  `gorm:"column:end_time;type:datetime;not null;comment:结束时间"`

	// 价格数据
	OpenValue    float64 `gorm:"column:open_value;type:decimal(12,4);not null;comment:开盘值"`
	HighValue    float64 `gorm:"column:high_value;type:decimal(12,4);not null;comment:最高值"`
	LowValue     float64 `gorm:"column:low_value;type:decimal(12,4);not null;comment:最低值"`
	CloseValue   float64 `gorm:"column:close_value;type:decimal(12,4);not null;comment:收盘值"`

	// 成交数据
	Volume       int64   `gorm:"column:volume;type:bigint;comment:成交量"`
	Amount       float64 `gorm:"column:amount;type:decimal(20,2);comment:成交额"`

	// 涨跌幅
	ChangePct    float64 `gorm:"column:change_pct;type:decimal(7,4);comment:涨跌幅"`

	// 技术指标
	MA5          float64 `gorm:"column:ma5;type:decimal(10,4);comment:5日均线"`
	MA10         float64 `gorm:"column:ma10;type:decimal(10,4);comment:10日均线"`
	MA20         float64 `gorm:"column:ma20;type:decimal(10,4);comment:20日均线"`

	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`
}

// TableName 指定表名
func (IndexKlineData) TableName() string {
	return "q_index_kline_data"
}

package market

import (
	"quantos/app/model"
)

// MarketData 市场行情数据模型
type MarketData struct {
	model.BaseModel

	Symbol       string  `gorm:"column:symbol;type:varchar(20);not null;index:idx_symbol_time;comment:证券代码"`
	SymbolName   string  `gorm:"column:symbol_name;type:varchar(100);comment:证券名称"`

	// 价格数据
	OpenPrice    float64 `gorm:"column:open_price;type:decimal(10,4);comment:开盘价"`
	HighPrice    float64 `gorm:"column:high_price;type:decimal(10,4);comment:最高价"`
	LowPrice     float64 `gorm:"column:low_price;type:decimal(10,4);comment:最低价"`
	ClosePrice   float64 `gorm:"column:close_price;type:decimal(10,4);not null;comment:收盘价"`
	Volume       int64   `gorm:"column:volume;type:bigint;comment:成交量"`
	Amount       float64 `gorm:"column:amount;type:decimal(20,2);comment:成交额"`

	// 交易时间
	TradeDate    string  `gorm:"column:trade_date;type:date;not null;index:idx_symbol_time;comment:交易日期"`
	TradeTime    string  `gorm:"column:trade_time;type:time;comment:交易时间"`

	// 市场信息
	Market       string  `gorm:"column:market;type:varchar(10);not null;comment:市场代码"`
	DataSource   int8    `gorm:"column:data_source;type:tinyint(4);not null;default:1;comment:数据源: 1-实时, 2-历史"`

	// 技术指标 (可选)
	MA5          float64 `gorm:"column:ma5;type:decimal(10,4);comment:5日均线"`
	MA10         float64 `gorm:"column:ma10;type:decimal(10,4);comment:10日均线"`
	MA20         float64 `gorm:"column:ma20;type:decimal(10,4);comment:20日均线"`
	RSI          float64 `gorm:"column:rsi;type:decimal(7,4);comment:RSI指标"`
	MACD         float64 `gorm:"column:macd;type:decimal(10,6);comment:MACD指标"`
}

// TableName 指定表名
func (MarketData) TableName() string {
	return "q_market_data"
}

// NewsData 新闻数据模型
type NewsData struct {
	model.BaseModel

	Title        string  `gorm:"column:title;type:varchar(500);not null;comment:新闻标题"`
	Content      string  `gorm:"column:content;type:longtext;comment:新闻内容"`
	Summary      string  `gorm:"column:summary;type:text;comment:新闻摘要"`

	// 来源信息
	Source       string  `gorm:"column:source;type:varchar(100);not null;comment:新闻来源"`
	SourceURL    string  `gorm:"column:source_url;type:varchar(1000);comment:原文链接"`
	Author       string  `gorm:"column:author;type:varchar(100);comment:作者"`

	// 发布时间
	PublishTime  string  `gorm:"column:publish_time;type:datetime;not null;index:idx_publish_time;comment:发布时间"`

	// 情感分析结果
	SentimentScore float64 `gorm:"column:sentiment_score;type:decimal(5,4);default:0.0000;comment:情感得分(-1到1)"`
	SentimentLabel string  `gorm:"column:sentiment_label;type:varchar(20);comment:情感标签"`

	// 实体识别
	Entities     string  `gorm:"column:entities;type:json;comment:识别的实体(JSON)"`

	// 分类信息
	Category     string  `gorm:"column:category;type:varchar(50);comment:新闻分类"`
	Tags         string  `gorm:"column:tags;type:json;comment:标签(JSON)"`

	// 处理状态
	IsProcessed  int8    `gorm:"column:is_processed;type:tinyint(4);default:0;comment:是否已处理: 0-未处理, 1-已处理"`
	ProcessTime  *string `gorm:"column:process_time;type:datetime;comment:处理时间"`
}

// TableName 指定表名
func (NewsData) TableName() string {
	return "q_news_data"
}

// PolicyData 政策数据模型
type PolicyData struct {
	model.BaseModel

	Title        string  `gorm:"column:title;type:varchar(500);not null;comment:政策标题"`
	Content      string  `gorm:"column:content;type:longtext;comment:政策内容"`
	Summary      string  `gorm:"column:summary;type:text;comment:政策摘要"`

	// 来源信息
	Source       string  `gorm:"column:source;type:varchar(100);not null;comment:政策来源"`
	SourceURL    string  `gorm:"column:source_url;type:varchar(1000);comment:原文链接"`
	Issuer       string  `gorm:"column:issuer;type:varchar(100);comment:发布机构"`

	// 发布时间
	PublishTime  string  `gorm:"column:publish_time;type:datetime;not null;index:idx_publish_time;comment:发布时间"`

	// 政策分类
	Category     string  `gorm:"column:category;type:varchar(50);comment:政策分类"`
	SubCategory  string  `gorm:"column:sub_category;type:varchar(50);comment:政策子分类"`

	// 影响分析
	ImpactLevel  int8    `gorm:"column:impact_level;type:tinyint(4);default:1;comment:影响级别: 1-低, 2-中, 3-高"`
	ImpactScope  string  `gorm:"column:impact_scope;type:varchar(200);comment:影响范围"`

	// 情感分析
	SentimentScore float64 `gorm:"column:sentiment_score;type:decimal(5,4);default:0.0000;comment:政策情感得分"`

	// 关联实体
	RelatedEntities string `gorm:"column:related_entities;type:json;comment:相关实体(JSON)"`

	// 处理状态
	IsProcessed  int8    `gorm:"column:is_processed;type:tinyint(4);default:0;comment:是否已处理"`
	ProcessTime  *string `gorm:"column:process_time;type:datetime;comment:处理时间"`
}

// TableName 指定表名
func (PolicyData) TableName() string {
	return "q_policy_data"
}

// FactorData 因子数据模型
type FactorData struct {
	model.BaseModel

	FactorCode   string  `gorm:"column:factor_code;type:varchar(50);not null;index:idx_factor_code_time;comment:因子代码"`
	FactorName   string  `gorm:"column:factor_name;type:varchar(100);not null;comment:因子名称"`

	// 因子值
	Value        float64 `gorm:"column:value;type:decimal(15,8);not null;comment:因子值"`

	// 时间信息
	Date         string  `gorm:"column:date;type:date;not null;index:idx_factor_code_time;comment:日期"`
	Time         string  `gorm:"column:time;type:time;comment:时间"`

	// 因子分类
	Type         int8    `gorm:"column:type;type:tinyint(4);not null;comment:因子类型: 1-技术, 2-基本面, 3-情感, 4-宏观, 5-自定义"`
	Category     string  `gorm:"column:category;type:varchar(50);comment:因子分类"`

	// 关联信息
	Symbol       string  `gorm:"column:symbol;type:varchar(20);index:idx_symbol;comment:关联证券代码"`
	Sector       string  `gorm:"column:sector;type:varchar(50);comment:关联行业"`

	// 元数据
	Parameters   string  `gorm:"column:parameters;type:json;comment:计算参数(JSON)"`
	Description  string  `gorm:"column:description;type:text;comment:因子描述"`

	// 数据质量
	DataQuality  int8    `gorm:"column:data_quality;type:tinyint(4);default:1;comment:数据质量: 1-低, 2-中, 3-高"`
}

// TableName 指定表名
func (FactorData) TableName() string {
	return "q_factor_data"
}

// IndexData 指数数据模型
type IndexData struct {
	model.BaseModel

	IndexCode    string  `gorm:"column:index_code;type:varchar(20);not null;index:idx_index_code_time;comment:指数代码"`
	IndexName    string  `gorm:"column:index_name;type:varchar(100);not null;comment:指数名称"`

	// 价格数据
	OpenValue    float64 `gorm:"column:open_value;type:decimal(12,4);comment:开盘值"`
	HighValue    float64 `gorm:"column:high_value;type:decimal(12,4);comment:最高值"`
	LowValue     float64 `gorm:"column:low_value;type:decimal(12,4);comment:最低值"`
	CloseValue   float64 `gorm:"column:close_value;type:decimal(12,4);not null;comment:收盘值"`

	// 交易数据
	Volume       int64   `gorm:"column:volume;type:bigint;comment:成交量"`
	Amount       float64 `gorm:"column:amount;type:decimal(20,2);comment:成交额"`

	// 时间信息
	TradeDate    string  `gorm:"column:trade_date;type:date;not null;index:idx_index_code_time;comment:交易日期"`

	// 市场信息
	Market       string  `gorm:"column:market;type:varchar(10);not null;comment:市场代码"`
	DataSource   int8    `gorm:"column:data_source;type:tinyint(4);not null;default:1;comment:数据源"`
}

// TableName 指定表名
func (IndexData) TableName() string {
	return "q_index_data"
}

// StockBasic 股票基础信息模型
type StockBasic struct {
	model.BaseModel

	Symbol       string `gorm:"column:symbol;type:varchar(20);not null;uniqueIndex:uk_symbol;comment:股票代码"`
	Name         string `gorm:"column:name;type:varchar(100);not null;comment:股票名称"`
	FullName     string `gorm:"column:full_name;type:varchar(200);comment:股票全称"`

	// 基本信息
	Market       string `gorm:"column:market;type:varchar(10);not null;comment:市场代码"`
	Exchange     string `gorm:"column:exchange;type:varchar(20);comment:交易所"`
	Board        string `gorm:"column:board;type:varchar(50);comment:板块"`
	Industry     string `gorm:"column:industry;type:varchar(100);comment:行业"`
	Sector       string `gorm:"column:sector;type:varchar(100);comment:板块"`

	// 财务信息
	ListDate     string  `gorm:"column:list_date;type:date;comment:上市日期"`
	TotalShare   float64 `gorm:"column:total_share;type:decimal(20,4);comment:总股本"`
	FloatShare   float64 `gorm:"column:float_share;type:decimal(20,4);comment:流通股本"`

	// 状态信息
	Status       int8    `gorm:"column:status;type:tinyint(4);not null;default:1;comment:状态: 1-正常, 2-ST, 3-停牌"`
	IsSt         int8    `gorm:"column:is_st;type:tinyint(4);default:0;comment:是否ST股"`
	IsSuspended  int8    `gorm:"column:is_suspended;type:tinyint(4);default:0;comment:是否停牌"`

	// 更新信息
	UpdateDate   string  `gorm:"column:update_date;type:date;comment:更新日期"`
}

// TableName 指定表名
func (StockBasic) TableName() string {
	return "q_stock_basic"
}

// FundBasic 基金基础信息模型
type FundBasic struct {
	model.BaseModel

	FundCode     string  `gorm:"column:fund_code;type:varchar(20);not null;uniqueIndex:uk_fund_code;comment:基金代码"`
	Name         string  `gorm:"column:name;type:varchar(100);not null;comment:基金名称"`
	ShortName    string  `gorm:"column:short_name;type:varchar(50);comment:基金简称"`

	// 基本信息
	Type         string  `gorm:"column:type;type:varchar(20);comment:基金类型"`
	Management   string  `gorm:"column:management;type:varchar(100);comment:基金管理人"`
	Custodian    string  `gorm:"column:custodian;type:varchar(100);comment:基金托管人"`

	// 规模信息
	TotalAsset   float64 `gorm:"column:total_asset;type:decimal(20,4);comment:基金规模"`
	ShareSize    float64 `gorm:"column:share_size;type:decimal(20,4);comment:份额规模"`

	// 时间信息
	EstablishDate string `gorm:"column:establish_date;type:date;comment:成立日期"`
	UpdateDate    string `gorm:"column:update_date;type:date;comment:更新日期"`

	// 状态
	Status       int8    `gorm:"column:status;type:tinyint(4);default:1;comment:状态: 1-正常, 2-停止"`
}

// TableName 指定表名
func (FundBasic) TableName() string {
	return "q_fund_basic"
}

// LimitUpPool 涨停股池模型
type LimitUpPool struct {
	model.BaseModel

	Symbol       string  `gorm:"column:symbol;type:varchar(20);not null;index:idx_symbol_date;comment:股票代码"`
	Name         string  `gorm:"column:name;type:varchar(100);comment:股票名称"`

	// 涨停信息
	TradeDate    string  `gorm:"column:trade_date;type:date;not null;index:idx_symbol_date;comment:交易日期"`
	LimitUpPrice float64 `gorm:"column:limit_up_price;type:decimal(10,4);comment:涨停价"`
	ClosePrice   float64 `gorm:"column:close_price;type:decimal(10,4);comment:收盘价"`

	// 封单信息
	LimitUpAmount float64 `gorm:"column:limit_up_amount;type:decimal(20,2);comment:封单金额"`
	LimitUpVolume int64   `gorm:"column:limit_up_volume;type:bigint;comment:封单量"`

	// 统计信息
	FirstLimitUpTime string `gorm:"column:first_limit_up_time;type:datetime;comment:首次涨停时间"`
	OpenTimes     int8    `gorm:"column:open_times;type:tinyint(4);default:0;comment:打开次数"`
	OpenAmount    float64 `gorm:"column:open_amount;type:decimal(20,2);comment:打开金额"`

	// 原因分类
	Reason       string  `gorm:"column:reason;type:varchar(200);comment:涨停原因"`
	Category     string  `gorm:"column:category;type:varchar(50);comment:涨停类型"`

	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`
}

// TableName 指定表名
func (LimitUpPool) TableName() string {
	return "q_limit_up_pool"
}

// DragonTigerList 龙虎榜模型
type DragonTigerList struct {
	model.BaseModel

	Symbol       string  `gorm:"column:symbol;type:varchar(20);not null;index:idx_symbol_date;comment:股票代码"`
	Name         string  `gorm:"column:name;type:varchar(100);comment:股票名称"`
	TradeDate    string  `gorm:"column:trade_date;type:date;not null;index:idx_symbol_date;comment:交易日期"`

	// 龙虎榜信息
	RankType     string  `gorm:"column:rank_type;type:varchar(20);comment:榜单类型"`
	RankPosition int8    `gorm:"column:rank_position;type:tinyint(4);comment:排名"`

	// 买入信息
	BuyAmount    float64 `gorm:"column:buy_amount;type:decimal(20,2);comment:买入金额"`
	BuyVolume    int64   `gorm:"column:buy_volume;type:bigint;comment:买入量"`
	SellAmount   float64 `gorm:"column:sell_amount;type:decimal(20,2);comment:卖出金额"`
	SellVolume   int64   `gorm:"column:sell_volume;type:bigint;comment:卖出量"`

	// 营业部信息
	BrokerName   string  `gorm:"column:broker_name;type:varchar(200);comment:营业部名称"`
	BrokerCode   string  `gorm:"column:broker_code;type:varchar(20);comment:营业部代码"`

	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`
}

// TableName 指定表名
func (DragonTigerList) TableName() string {
	return "q_dragon_tiger_list"
}

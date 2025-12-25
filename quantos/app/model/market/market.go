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

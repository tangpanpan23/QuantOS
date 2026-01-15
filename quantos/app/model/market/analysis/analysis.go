package analysis

import (
	"quantos/app/model"
)

// MarketSentiment 市场情绪模型
type MarketSentiment struct {
	model.BaseModel

	TradeDate    string  `gorm:"column:trade_date;type:date;not null;uniqueIndex:uk_date;comment:交易日期"`

	// 情绪指标
	BullishPct   float64 `gorm:"column:bullish_pct;type:decimal(5,4);comment:看涨比例"`
	BearishPct   float64 `gorm:"column:bearish_pct;type:decimal(5,4);comment:看跌比例"`
	NeutralPct   float64 `gorm:"column:neutral_pct;type:decimal(5,4);comment:中性比例"`

	// 恐慌贪婪指数
	FearGreedIndex float64 `gorm:"column:fear_greed_index;type:decimal(7,4);comment:恐慌贪婪指数(0-100)"`

	// 市场热度
	MarketHeat   float64 `gorm:"column:market_heat;type:decimal(7,4);comment:市场热度"`

	// 新闻情绪
	NewsSentiment float64 `gorm:"column:news_sentiment;type:decimal(5,4);comment:新闻情绪得分(-1到1)"`

	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`
}

// TableName 指定表名
func (MarketSentiment) TableName() string {
	return "q_market_sentiment"
}

// StockSentiment 股票情绪模型
type StockSentiment struct {
	model.BaseModel

	Symbol       string  `gorm:"column:symbol;type:varchar(20);not null;index:idx_symbol_date;comment:股票代码"`
	TradeDate    string  `gorm:"column:trade_date;type:date;not null;index:idx_symbol_date;comment:交易日期"`

	// 情绪指标
	SentimentScore float64 `gorm:"column:sentiment_score;type:decimal(5,4);comment:情绪得分(-1到1)"`
	AttentionScore float64 `gorm:"column:attention_score;type:decimal(7,4);comment:关注度得分"`

	// 新闻分析
	NewsCount    int     `gorm:"column:news_count;type:int;comment:相关新闻数量"`
	PositiveNews int     `gorm:"column:positive_news;type:int;comment:正面新闻数"`
	NegativeNews int     `gorm:"column:negative_news;type:int;comment:负面新闻数"`

	// 社交媒体情绪
	SocialSentiment float64 `gorm:"column:social_sentiment;type:decimal(5,4);comment:社交媒体情绪"`

	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`
}

// TableName 指定表名
func (StockSentiment) TableName() string {
	return "q_stock_sentiment"
}

// SectorAnalysis 板块分析模型
type SectorAnalysis struct {
	model.BaseModel

	SectorCode   string  `gorm:"column:sector_code;type:varchar(20);not null;index:idx_sector_date;comment:板块代码"`
	SectorName   string  `gorm:"column:sector_name;type:varchar(100);comment:板块名称"`
	TradeDate    string  `gorm:"column:trade_date;type:date;not null;index:idx_sector_date;comment:交易日期"`

	// 板块表现
	AvgChangePct float64 `gorm:"column:avg_change_pct;type:decimal(7,4);comment:平均涨跌幅"`
	TotalVolume  int64   `gorm:"column:total_volume;type:bigint;comment:总成交量"`
	TotalAmount  float64 `gorm:"column:total_amount;type:decimal(20,2);comment:总成交额"`

	// 领涨股
	LeaderSymbol string  `gorm:"column:leader_symbol;type:varchar(20);comment:领涨股代码"`
	LeaderChange float64 `gorm:"column:leader_change;type:decimal(7,4);comment:领涨股涨跌幅"`

	// 资金流向
	MainInflow   float64 `gorm:"column:main_inflow;type:decimal(20,2);comment:主力净流入"`
	RetailInflow float64 `gorm:"column:retail_inflow;type:decimal(20,2);comment:散户净流入"`

	// 热度指标
	HeatScore    float64 `gorm:"column:heat_score;type:decimal(7,4);comment:热度得分"`

	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`
}

// TableName 指定表名
func (SectorAnalysis) TableName() string {
	return "q_sector_analysis"
}

// TechnicalIndicator 技术指标模型
type TechnicalIndicator struct {
	model.BaseModel

	Symbol       string  `gorm:"column:symbol;type:varchar(20);not null;index:idx_symbol_date;comment:股票代码"`
	TradeDate    string  `gorm:"column:trade_date;type:date;not null;index:idx_symbol_date;comment:交易日期"`

	// 趋势指标
	MA5          float64 `gorm:"column:ma5;type:decimal(10,4);comment:5日均线"`
	MA10         float64 `gorm:"column:ma10;type:decimal(10,4);comment:10日均线"`
	MA20         float64 `gorm:"column:ma20;type:decimal(10,4);comment:20日均线"`
	MA30         float64 `gorm:"column:ma30;type:decimal(10,4);comment:30日均线"`
	MA60         float64 `gorm:"column:ma60;type:decimal(10,4);comment:60日均线"`

	EMA12        float64 `gorm:"column:ema12;type:decimal(10,4);comment:12日指数均线"`
	EMA26        float64 `gorm:"column:ema26;type:decimal(10,4);comment:26日指数均线"`

	// 动量指标
	MACD         float64 `gorm:"column:macd;type:decimal(10,6);comment:MACD指标"`
	MACD_SIGNAL  float64 `gorm:"column:macd_signal;type:decimal(10,6);comment:MACD信号线"`
	MACD_HIST    float64 `gorm:"column:macd_hist;type:decimal(10,6);comment:MACD柱状图"`

	RSI          float64 `gorm:"column:rsi;type:decimal(7,4);comment:RSI指标"`
	RSI6         float64 `gorm:"column:rsi6;type:decimal(7,4);comment:6日RSI"`
	RSI12        float64 `gorm:"column:rsi12;type:decimal(7,4);comment:12日RSI"`

	// 超买超卖指标
	KDJ_K        float64 `gorm:"column:kdj_k;type:decimal(7,4);comment:KDJ-K值"`
	KDJ_D        float64 `gorm:"column:kdj_d;type:decimal(7,4);comment:KDJ-D值"`
	KDJ_J        float64 `gorm:"column:kdj_j;type:decimal(7,4);comment:KDJ-J值"`

	// 波动率指标
	ATR          float64 `gorm:"column:atr;type:decimal(10,4);comment:ATR指标"`
	CCI          float64 `gorm:"column:cci;type:decimal(10,4);comment:CCI指标"`
	WILLR        float64 `gorm:"column:willr;type:decimal(10,4);comment:WILLR指标"`

	// 布林带
	BOLL_UPPER   float64 `gorm:"column:boll_upper;type:decimal(10,4);comment:布林线上轨"`
	BOLL_MIDDLE  float64 `gorm:"column:boll_middle;type:decimal(10,4);comment:布林线中轨"`
	BOLL_LOWER   float64 `gorm:"column:boll_lower;type:decimal(10,4);comment:布林线下轨"`

	// 信号
	BuySignal    int8    `gorm:"column:buy_signal;type:tinyint(4);default:0;comment:买入信号强度(0-5)"`
	SellSignal   int8    `gorm:"column:sell_signal;type:tinyint(4);default:0;comment:卖出信号强度(0-5)"`

	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`
}

// TableName 指定表名
func (TechnicalIndicator) TableName() string {
	return "q_technical_indicator"
}

// StockRanking 股票排名模型
type StockRanking struct {
	model.BaseModel

	Symbol       string  `gorm:"column:symbol;type:varchar(20);not null;index:idx_date_type;comment:股票代码"`
	Name         string  `gorm:"column:name;type:varchar(100);comment:股票名称"`
	TradeDate    string  `gorm:"column:trade_date;type:date;not null;index:idx_date_type;comment:交易日期"`

	// 排名类型
	RankType     string  `gorm:"column:rank_type;type:varchar(20);not null;index:idx_date_type;comment:排名类型: volume,amount,change,gainers,losers等"`
	RankPosition int     `gorm:"column:rank_position;type:int;comment:排名位置"`

	// 排名依据数据
	Volume       int64   `gorm:"column:volume;type:bigint;comment:成交量"`
	Amount       float64 `gorm:"column:amount;type:decimal(20,2);comment:成交额"`
	ChangePct    float64 `gorm:"column:change_pct;type:decimal(7,4);comment:涨跌幅"`

	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`
}

// TableName 指定表名
func (StockRanking) TableName() string {
	return "q_stock_ranking"
}

// AbnormalMovement 异动数据模型
type AbnormalMovement struct {
	model.BaseModel

	Symbol       string  `gorm:"column:symbol;type:varchar(20);not null;index:idx_symbol_date;comment:股票代码"`
	Name         string  `gorm:"column:name;type:varchar(100);comment:股票名称"`
	TradeDate    string  `gorm:"column:trade_date;type:date;not null;index:idx_symbol_date;comment:交易日期"`
	TradeTime    string  `gorm:"column:trade_time;type:datetime;comment:异动时间"`

	// 异动类型
	MovementType string  `gorm:"column:movement_type;type:varchar(50);comment:异动类型: 涨停,跌停,炸板,龙虎榜等"`
	MovementDesc string  `gorm:"column:movement_desc;type:varchar(200);comment:异动描述"`

	// 异动数据
	Price        float64 `gorm:"column:price;type:decimal(10,4);comment:异动价格"`
	Volume       int64   `gorm:"column:volume;type:bigint;comment:成交量"`
	Amount       float64 `gorm:"column:amount;type:decimal(20,2);comment:成交额"`

	// 异动强度
	Intensity    float64 `gorm:"column:intensity;type:decimal(7,4);comment:异动强度"`

	UpdateTime   string  `gorm:"column:update_time;type:datetime;comment:更新时间"`
}

// TableName 指定表名
func (AbnormalMovement) TableName() string {
	return "q_abnormal_movement"
}

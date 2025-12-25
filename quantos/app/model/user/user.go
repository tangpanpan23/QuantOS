package user

import (
	"quantos/app/model"
)

// User 用户模型
type User struct {
	model.BaseModel

	// 基础信息
	Username     string `gorm:"column:username;type:varchar(50);not null;uniqueIndex:uk_username;comment:用户名"`
	Email        string `gorm:"column:email;type:varchar(100);not null;uniqueIndex:uk_email;comment:邮箱地址"`
	Password     string `gorm:"column:password;type:varchar(255);not null;comment:密码哈希"`
	Phone        string `gorm:"column:phone;type:varchar(20);comment:手机号"`
	Avatar       string `gorm:"column:avatar;type:varchar(500);comment:头像URL"`
	Nickname     string `gorm:"column:nickname;type:varchar(50);comment:昵称"`

	// 账户状态
	Status       int8   `gorm:"column:status;type:tinyint(4);not null;default:1;comment:状态: 1-正常, 2-禁用"`
	Role         int8   `gorm:"column:role;type:tinyint(4);not null;default:4;comment:角色: 1-管理员, 2-交易员, 3-分析师, 4-投资者"`
	Subscription int8   `gorm:"column:subscription;type:tinyint(4);not null;default:1;comment:订阅计划: 1-免费, 2-专业, 3-企业"`

	// 认证信息
	LastLoginAt  *string `gorm:"column:last_login_at;type:datetime;comment:最后登录时间"`
	LastLoginIP  string  `gorm:"column:last_login_ip;type:varchar(45);comment:最后登录IP"`

	// 风险偏好
	RiskTolerance float64 `gorm:"column:risk_tolerance;type:decimal(5,4);default:0.5000;comment:风险容忍度(0-1)"`
	TimeHorizon   int8    `gorm:"column:time_horizon;type:tinyint(4);default:2;comment:投资期限: 1-短期, 2-中期, 3-长期"`

	// 统计信息
	TotalAssets   float64 `gorm:"column:total_assets;type:decimal(20,2);default:0.00;comment:总资产"`
	TotalReturns  float64 `gorm:"column:total_returns;type:decimal(10,4);default:0.0000;comment:总收益率"`
	WinRate       float64 `gorm:"column:win_rate;type:decimal(5,4);default:0.0000;comment:胜率"`

	// 关联关系
	Strategies   []Strategy `gorm:"foreignKey:UserID"`
	Portfolios   []Portfolio `gorm:"foreignKey:UserID"`
}

// TableName 指定表名
func (User) TableName() string {
	return "q_users"
}

// Strategy 用户策略模型
type Strategy struct {
	model.BaseModel

	UserID       uint64 `gorm:"column:user_id;not null;index:idx_user_id;comment:用户ID"`
	Name         string `gorm:"column:name;type:varchar(100);not null;comment:策略名称"`
	Description  string `gorm:"column:description;type:text;comment:策略描述"`
	Code         string `gorm:"column:code;type:longtext;comment:策略代码"`

	// 策略配置
	Status       int8    `gorm:"column:status;type:tinyint(4);not null;default:1;comment:状态: 1-草稿, 2-测试, 3-发布, 4-运行, 5-暂停, 6-停止"`
	Type         int8    `gorm:"column:type;type:tinyint(4);not null;default:1;comment:类型: 1-手动, 2-AI生成, 3-模板"`
	Category     string  `gorm:"column:category;type:varchar(50);comment:策略分类"`

	// 风险指标
	MaxDrawdown     float64 `gorm:"column:max_drawdown;type:decimal(7,4);default:0.0000;comment:最大回撤"`
	SharpeRatio     float64 `gorm:"column:sharpe_ratio;type:decimal(7,4);default:0.0000;comment:夏普比率"`
	AnnualReturn    float64 `gorm:"column:annual_return;type:decimal(7,4);default:0.0000;comment:年化收益率"`
	Volatility      float64 `gorm:"column:volatility;type:decimal(7,4);default:0.0000;comment:波动率"`

	// 策略参数 (JSON格式存储)
	Parameters  string  `gorm:"column:parameters;type:json;comment:策略参数"`

	// 执行信息
	LastRunAt   *string `gorm:"column:last_run_at;type:datetime;comment:最后运行时间"`
	RunCount    int64   `gorm:"column:run_count;type:int;default:0;comment:运行次数"`

	// 关联关系
	User        *User   `gorm:"foreignKey:UserID"`
}

// TableName 指定表名
func (Strategy) TableName() string {
	return "q_strategies"
}

// Portfolio 用户投资组合模型
type Portfolio struct {
	model.BaseModel

	UserID       uint64  `gorm:"column:user_id;not null;index:idx_user_id;comment:用户ID"`
	Name         string  `gorm:"column:name;type:varchar(100);not null;comment:组合名称"`
	Description  string  `gorm:"column:description;type:text;comment:组合描述"`

	// 组合配置
	Status       int8    `gorm:"column:status;type:tinyint(4);not null;default:1;comment:状态: 1-正常, 2-暂停, 3-清盘"`
	InitialCash  float64 `gorm:"column:initial_cash;type:decimal(20,2);not null;comment:初始资金"`

	// 绩效指标
	TotalValue   float64 `gorm:"column:total_value;type:decimal(20,2);default:0.00;comment:总价值"`
	TotalReturn  float64 `gorm:"column:total_return;type:decimal(10,4);default:0.0000;comment:总收益率"`
	MaxDrawdown  float64 `gorm:"column:max_drawdown;type:decimal(7,4);default:0.0000;comment:最大回撤"`

	// 关联关系
	User         *User   `gorm:"foreignKey:UserID"`
	Positions    []Position `gorm:"foreignKey:PortfolioID"`
}

// TableName 指定表名
func (Portfolio) TableName() string {
	return "q_portfolios"
}

// Position 持仓模型
type Position struct {
	model.BaseModel

	PortfolioID  uint64  `gorm:"column:portfolio_id;not null;index:idx_portfolio_id;comment:组合ID"`
	Symbol       string  `gorm:"column:symbol;type:varchar(20);not null;comment:证券代码"`
	SymbolName   string  `gorm:"column:symbol_name;type:varchar(100);comment:证券名称"`

	// 持仓信息
	Quantity     float64 `gorm:"column:quantity;type:decimal(20,4);not null;comment:持仓数量"`
	AvgCost      float64 `gorm:"column:avg_cost;type:decimal(10,4);not null;comment:平均成本"`
	CurrentPrice float64 `gorm:"column:current_price;type:decimal(10,4);default:0.0000;comment:当前价格"`
	MarketValue  float64 `gorm:"column:market_value;type:decimal(20,2);default:0.00;comment:市值"`

	// 盈亏信息
	UnrealizedPnL float64 `gorm:"column:unrealized_pnl;type:decimal(20,2);default:0.00;comment:未实现盈亏"`
	RealizedPnL   float64 `gorm:"column:realized_pnl;type:decimal(20,2);default:0.00;comment:已实现盈亏"`

	// 关联关系
	Portfolio    *Portfolio `gorm:"foreignKey:PortfolioID"`
}

// TableName 指定表名
func (Position) TableName() string {
	return "q_positions"
}

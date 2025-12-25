package types

// 用户相关请求/响应
type (
	// 用户注册请求
	UserRegisterReq struct {
		Username string `json:"username" validate:"required,min=3,max=50"`
		Email    string `json:"email" validate:"required,email"`
		Password string `json:"password" validate:"required,min=6,max=50"`
		Phone    string `json:"phone,omitempty"`
	}

	// 用户登录请求
	UserLoginReq struct {
		Username string `json:"username" validate:"required"`
		Password string `json:"password" validate:"required"`
	}

	// 用户登录响应
	UserLoginResp struct {
		AccessToken  string `json:"access_token"`
		AccessExpire int64  `json:"access_expire"`
		User         *User  `json:"user"`
	}

	// 用户信息
	User struct {
		ID           uint64  `json:"id"`
		Username     string  `json:"username"`
		Email        string  `json:"email"`
		Phone        string  `json:"phone,omitempty"`
		Avatar       string  `json:"avatar,omitempty"`
		Nickname     string  `json:"nickname,omitempty"`
		Status       int8    `json:"status"`
		Role         int8    `json:"role"`
		Subscription int8    `json:"subscription"`
		RiskTolerance float64 `json:"risk_tolerance"`
		TimeHorizon  int8    `json:"time_horizon"`
		TotalAssets  float64 `json:"total_assets"`
		TotalReturns float64 `json:"total_returns"`
		WinRate      float64 `json:"win_rate"`
		CreatedAt    *string `json:"created_at"`
	}

	// 获取用户信息请求
	GetUserReq struct {
		UserID uint64 `path:"user_id"`
	}

	// 更新用户信息请求
	UpdateUserReq struct {
		UserID       uint64   `path:"user_id"`
		Phone        *string  `json:"phone,omitempty"`
		Avatar       *string  `json:"avatar,omitempty"`
		Nickname     *string  `json:"nickname,omitempty"`
		RiskTolerance *float64 `json:"risk_tolerance,omitempty"`
		TimeHorizon  *int8    `json:"time_horizon,omitempty"`
	}
)

// 策略相关请求/响应
type (
	// 创建策略请求
	CreateStrategyReq struct {
		Name        string  `json:"name" validate:"required,max=100"`
		Description string  `json:"description,omitempty"`
		Code        string  `json:"code,omitempty"`
		Type        int8    `json:"type,omitempty"` // 1-手动, 2-AI生成, 3-模板
		Category    string  `json:"category,omitempty"`
	}

	// 更新策略请求
	UpdateStrategyReq struct {
		StrategyID  uint64  `path:"strategy_id"`
		Name        *string `json:"name,omitempty"`
		Description *string `json:"description,omitempty"`
		Code        *string `json:"code,omitempty"`
		Category    *string `json:"category,omitempty"`
	}

	// 获取策略列表请求
	GetStrategiesReq struct {
		UserID   uint64 `form:"user_id,omitempty"`
		Type     int8   `form:"type,omitempty"`
		Status   int8   `form:"status,omitempty"`
		Category string `form:"category,omitempty"`
		Page     int64  `form:"page,default=1"`
		PageSize int64  `form:"page_size,default=20"`
	}

	// 策略列表响应
	GetStrategiesResp struct {
		List     []Strategy `json:"list"`
		Total    int64      `json:"total"`
		Page     int64      `json:"page"`
		PageSize int64      `json:"page_size"`
	}

	// 策略信息
	Strategy struct {
		ID            uint64   `json:"id"`
		UserID        uint64   `json:"user_id"`
		Name          string   `json:"name"`
		Description   string   `json:"description,omitempty"`
		Code          string   `json:"code,omitempty"`
		Status        int8     `json:"status"`
		Type          int8     `json:"type"`
		Category      string   `json:"category,omitempty"`
		MaxDrawdown   float64  `json:"max_drawdown"`
		SharpeRatio   float64  `json:"sharpe_ratio"`
		AnnualReturn  float64  `json:"annual_return"`
		Volatility    float64  `json:"volatility"`
		Parameters    string   `json:"parameters,omitempty"`
		LastRunAt     *string  `json:"last_run_at,omitempty"`
		RunCount      int64    `json:"run_count"`
		CreatedAt     *string  `json:"created_at"`
		UpdatedAt     *string  `json:"updated_at"`
	}

	// 运行策略请求
	RunStrategyReq struct {
		StrategyID uint64 `path:"strategy_id"`
	}

	// 策略运行响应
	RunStrategyResp struct {
		TaskID    string `json:"task_id"`
		Status    string `json:"status"`
		Message   string `json:"message"`
	}
)

// 投资组合相关请求/响应
type (
	// 创建投资组合请求
	CreatePortfolioReq struct {
		Name        string  `json:"name" validate:"required,max=100"`
		Description string  `json:"description,omitempty"`
		InitialCash float64 `json:"initial_cash" validate:"required,min=0"`
	}

	// 获取投资组合列表请求
	GetPortfoliosReq struct {
		UserID   uint64 `form:"user_id,omitempty"`
		Status   int8   `form:"status,omitempty"`
		Page     int64  `form:"page,default=1"`
		PageSize int64  `form:"page_size,default=20"`
	}

	// 投资组合列表响应
	GetPortfoliosResp struct {
		List     []Portfolio `json:"list"`
		Total    int64       `json:"total"`
		Page     int64       `json:"page"`
		PageSize int64       `json:"page_size"`
	}

	// 投资组合信息
	Portfolio struct {
		ID          uint64      `json:"id"`
		UserID      uint64      `json:"user_id"`
		Name        string      `json:"name"`
		Description string      `json:"description,omitempty"`
		Status      int8        `json:"status"`
		InitialCash float64     `json:"initial_cash"`
		TotalValue  float64     `json:"total_value"`
		TotalReturn float64     `json:"total_return"`
		MaxDrawdown float64     `json:"max_drawdown"`
		Positions   []Position  `json:"positions,omitempty"`
		CreatedAt   *string     `json:"created_at"`
		UpdatedAt   *string     `json:"updated_at"`
	}

	// 持仓信息
	Position struct {
		ID            uint64  `json:"id"`
		PortfolioID   uint64  `json:"portfolio_id"`
		Symbol        string  `json:"symbol"`
		SymbolName    string  `json:"symbol_name,omitempty"`
		Quantity      float64 `json:"quantity"`
		AvgCost       float64 `json:"avg_cost"`
		CurrentPrice  float64 `json:"current_price"`
		MarketValue   float64 `json:"market_value"`
		UnrealizedPnL float64 `json:"unrealized_pnl"`
		RealizedPnL   float64 `json:"realized_pnl"`
		CreatedAt     *string `json:"created_at"`
	}
)

// 市场数据相关请求/响应
type (
	// 获取市场数据请求
	GetMarketDataReq struct {
		Symbol string `form:"symbol" validate:"required"`
		Date   string `form:"date,omitempty"` // YYYY-MM-DD格式
		Limit  int64  `form:"limit,default=100"`
	}

	// 市场数据响应
	GetMarketDataResp struct {
		List []MarketData `json:"list"`
	}

	// 市场数据
	MarketData struct {
		Symbol     string  `json:"symbol"`
		SymbolName string  `json:"symbol_name,omitempty"`
		OpenPrice  float64 `json:"open_price,omitempty"`
		HighPrice  float64 `json:"high_price,omitempty"`
		LowPrice   float64 `json:"low_price,omitempty"`
		ClosePrice float64 `json:"close_price"`
		Volume     int64   `json:"volume,omitempty"`
		Amount     float64 `json:"amount,omitempty"`
		TradeDate  string  `json:"trade_date"`
		TradeTime  string  `json:"trade_time,omitempty"`
		MA5        float64 `json:"ma5,omitempty"`
		MA10       float64 `json:"ma10,omitempty"`
		MA20       float64 `json:"ma20,omitempty"`
		RSI        float64 `json:"rsi,omitempty"`
		MACD       float64 `json:"macd,omitempty"`
	}
)

// 新闻数据相关请求/响应
type (
	// 获取新闻列表请求
	GetNewsReq struct {
		Category   string `form:"category,omitempty"`
		Sentiment  string `form:"sentiment,omitempty"` // positive, negative, neutral
		StartDate  string `form:"start_date,omitempty"`
		EndDate    string `form:"end_date,omitempty"`
		Page       int64  `form:"page,default=1"`
		PageSize   int64  `form:"page_size,default=20"`
	}

	// 新闻列表响应
	GetNewsResp struct {
		List     []News `json:"list"`
		Total    int64  `json:"total"`
		Page     int64  `json:"page"`
		PageSize int64  `json:"page_size"`
	}

	// 新闻信息
	News struct {
		ID             uint64  `json:"id"`
		Title          string  `json:"title"`
		Content        string  `json:"content,omitempty"`
		Summary        string  `json:"summary,omitempty"`
		Source         string  `json:"source"`
		SourceURL      string  `json:"source_url,omitempty"`
		Author         string  `json:"author,omitempty"`
		PublishTime    string  `json:"publish_time"`
		SentimentScore float64 `json:"sentiment_score"`
		SentimentLabel string  `json:"sentiment_label,omitempty"`
		Entities       string  `json:"entities,omitempty"`
		Category       string  `json:"category,omitempty"`
		Tags           string  `json:"tags,omitempty"`
	}
)

// 因子数据相关请求/响应
type (
	// 获取因子数据请求
	GetFactorsReq struct {
		FactorCode string `form:"factor_code,omitempty"`
		Symbol     string `form:"symbol,omitempty"`
		Type       int8   `form:"type,omitempty"`
		StartDate  string `form:"start_date,omitempty"`
		EndDate    string `form:"end_date,omitempty"`
		Limit      int64  `form:"limit,default=100"`
	}

	// 因子数据响应
	GetFactorsResp struct {
		List []Factor `json:"list"`
	}

	// 因子信息
	Factor struct {
		ID          uint64  `json:"id"`
		FactorCode  string  `json:"factor_code"`
		FactorName  string  `json:"factor_name"`
		Value       float64 `json:"value"`
		Date        string  `json:"date"`
		Time        string  `json:"time,omitempty"`
		Type        int8    `json:"type"`
		Category    string  `json:"category,omitempty"`
		Symbol      string  `json:"symbol,omitempty"`
		Sector      string  `json:"sector,omitempty"`
		Parameters  string  `json:"parameters,omitempty"`
		Description string  `json:"description,omitempty"`
		DataQuality int8    `json:"data_quality"`
	}
)

// 通用响应
type (
	// 通用响应
	CommonResp struct {
		Code    int    `json:"code"`
		Message string `json:"message"`
		Data    any    `json:"data,omitempty"`
	}

	// 分页响应
	PageResp struct {
		List     any    `json:"list"`
		Total    int64  `json:"total"`
		Page     int64  `json:"page"`
		PageSize int64  `json:"page_size"`
	}

	// 错误响应
	ErrorResponse struct {
		Code    int    `json:"code"`
		Message string `json:"message"`
	}
)

func (e *ErrorResponse) Error() string {
	return e.Message
}

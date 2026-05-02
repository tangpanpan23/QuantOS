package handler

import (
	"net/http"

	"quantos/app/api/internal/svc"

	"github.com/zeromicro/go-zero/rest"
)

func RegisterHandlers(server *rest.Server, ctx *svc.ServiceContext) {
	// 健康检查（公开，无需认证）
	server.AddRoutes([]rest.Route{
		{
			Method:  http.MethodGet,
			Path:    "/health",
			Handler: healthHandler(ctx),
		},
	})

	// 用户相关路由（公开，无需认证）
	server.AddRoutes([]rest.Route{
		{
			Method:  http.MethodPost,
			Path:    "/api/v1/user/register",
			Handler: userRegisterHandler(ctx),
		},
		{
			Method:  http.MethodPost,
			Path:    "/api/v1/user/login",
			Handler: userLoginHandler(ctx),
		},
	})

	// 用户详情（需认证）
	server.AddRoutes([]rest.Route{
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/user/:user_id",
			Handler: getUserHandler(ctx),
		},
		{
			Method:  http.MethodPut,
			Path:    "/api/v1/user/:user_id",
			Handler: updateUserHandler(ctx),
		},
	}, rest.WithJwt(ctx.JwtAuthMiddleware))

	// 策略管理（需认证）
	server.AddRoutes([]rest.Route{
		{
			Method:  http.MethodPost,
			Path:    "/api/v1/strategies",
			Handler: createStrategyHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/strategies",
			Handler: getStrategiesHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/strategies/:strategy_id",
			Handler: getStrategyHandler(ctx),
		},
		{
			Method:  http.MethodPut,
			Path:    "/api/v1/strategies/:strategy_id",
			Handler: updateStrategyHandler(ctx),
		},
		{
			Method:  http.MethodDelete,
			Path:    "/api/v1/strategies/:strategy_id",
			Handler: deleteStrategyHandler(ctx),
		},
		{
			Method:  http.MethodPost,
			Path:    "/api/v1/strategies/:strategy_id/run",
			Handler: runStrategyHandler(ctx),
		},
	}, rest.WithJwt(ctx.JwtAuthMiddleware))

	// 投资组合（需认证）
	server.AddRoutes([]rest.Route{
		{
			Method:  http.MethodPost,
			Path:    "/api/v1/portfolios",
			Handler: createPortfolioHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/portfolios",
			Handler: getPortfoliosHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/portfolios/:portfolio_id",
			Handler: getPortfolioHandler(ctx),
		},
	}, rest.WithJwt(ctx.JwtAuthMiddleware))

	// 市场数据（需认证）
	server.AddRoutes([]rest.Route{
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/market/data",
			Handler: getMarketDataHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/market/factors",
			Handler: getFactorsHandler(ctx),
		},
	}, rest.WithJwt(ctx.JwtAuthMiddleware))

	// 新闻政策（需认证）
	server.AddRoutes([]rest.Route{
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/news",
			Handler: getNewsHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/policy",
			Handler: getPolicyHandler(ctx),
		},
	}, rest.WithJwt(ctx.JwtAuthMiddleware))

	// 策略工坊（需认证）
	server.AddRoutes([]rest.Route{
		{
			Method:  http.MethodPost,
			Path:    "/api/v1/workshop/generate",
			Handler: generateStrategyHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/workshop/templates",
			Handler: getStrategyTemplatesHandler(ctx),
		},
		{
			Method:  http.MethodPost,
			Path:    "/api/v1/workshop/backtest",
			Handler: backtestStrategyHandler(ctx),
		},
	}, rest.WithJwt(ctx.JwtAuthMiddleware))

	// AI 助手（需认证）
	server.AddRoutes([]rest.Route{
		{
			Method:  http.MethodPost,
			Path:    "/api/v1/ai/analyze",
			Handler: analyzeStrategyHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/ai/suggestions",
			Handler: getAISuggestionsHandler(ctx),
		},
	}, rest.WithJwt(ctx.JwtAuthMiddleware))

	// StockApi 股票数据（需认证）
	server.AddRoutes([]rest.Route{
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/stock/list",
			Handler: getStockListHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/stock/quote",
			Handler: getRealTimeQuoteHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/stock/kline",
			Handler: getKLineDataHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/stock/level2",
			Handler: getLevel2DataHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/stock/index",
			Handler: getIndexDataHandler(ctx),
		},
	}, rest.WithJwt(ctx.JwtAuthMiddleware))

	// 市场分析（需认证）
	server.AddRoutes([]rest.Route{
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/market/ai-selection",
			Handler: getAISmartSelectionHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/market/sentiment",
			Handler: getSentimentCycleHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/market/technical",
			Handler: getTechnicalIndicatorsHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/market/sector-leaders",
			Handler: getSectorLeadersHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/market/limit-up-pool",
			Handler: getLimitUpPoolHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/market/sector-concepts",
			Handler: getSectorConceptsHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/market/abnormal-movements",
			Handler: getAbnormalMovementsHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/market/hot-money",
			Handler: getHotMoneyDataHandler(ctx),
		},
	}, rest.WithJwt(ctx.JwtAuthMiddleware))

	// 策略（增强版，需认证）
	server.AddRoutes([]rest.Route{
		{
			Method:  http.MethodPost,
			Path:    "/api/v1/strategy/generate-ai",
			Handler: generateAIStrategyHandler(ctx),
		},
		{
			Method:  http.MethodPost,
			Path:    "/api/v1/strategy/backtest",
			Handler: runBacktestHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/strategy/performance",
			Handler: getPerformanceAnalysisHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/strategy/featured",
			Handler: getFeaturedStrategiesHandler(ctx),
		},
	}, rest.WithJwt(ctx.JwtAuthMiddleware))

	// 交易（需认证）
	server.AddRoutes([]rest.Route{
		{
			Method:  http.MethodPost,
			Path:    "/api/v1/trading/order",
			Handler: placeOrderHandler(ctx),
		},
		{
			Method:  http.MethodDelete,
			Path:    "/api/v1/trading/order/:order_id",
			Handler: cancelOrderHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/trading/orders",
			Handler: getOrdersHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/trading/trades",
			Handler: getTradesHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/trading/account",
			Handler: getAccountHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/trading/positions",
			Handler: getPositionsHandler(ctx),
		},
		{
			Method:  http.MethodPost,
			Path:    "/api/v1/trading/risk-check",
			Handler: riskCheckHandler(ctx),
		},
	}, rest.WithJwt(ctx.JwtAuthMiddleware))

	// 专项分析（需认证）
	server.AddRoutes([]rest.Route{
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/analysis/auction",
			Handler: getAuctionDataHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/analysis/risk-warnings",
			Handler: getRiskWarningsHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/analysis/auction-advanced",
			Handler: getAuctionAdvancedHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/analysis/basic-data-enhanced",
			Handler: getBasicDataEnhancedHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/analysis/trading-calendar",
			Handler: getTradingCalendarHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/analysis/st-stocks",
			Handler: getSTStocksHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/analysis/dragon-tiger",
			Handler: getDragonTigerListHandler(ctx),
		},
		{
			Method:  http.MethodGet,
			Path:    "/api/v1/analysis/capital-flow",
			Handler: getCapitalFlowHandler(ctx),
		},
	}, rest.WithJwt(ctx.JwtAuthMiddleware))
}

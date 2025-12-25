package handler

import (
	"net/http"

	"quantos/app/api/internal/svc"

	"github.com/zeromicro/go-zero/rest"
)

func RegisterHandlers(server *rest.Server, ctx *svc.ServiceContext) {
	// 健康检查
	server.AddRoutes([]rest.Route{
		{
			Method:  http.MethodGet,
			Path:    "/health",
			Handler: healthHandler(ctx),
		},
	}, rest.WithJwt(ctx.JwtAuthMiddleware))

	// 用户相关路由
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
	}, rest.WithJwt(ctx.JwtAuthMiddleware))

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

	// 策略相关路由
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

	// 投资组合相关路由
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

	// 市场数据相关路由
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

	// 新闻数据相关路由
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

	// 策略工坊相关路由
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

	// AI助手相关路由
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
}

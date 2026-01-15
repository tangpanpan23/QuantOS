package svc

import (
	"quantos/app/api/internal/config"
	"quantos/app/api/internal/middleware"
	"quantos/common"

	"github.com/zeromicro/go-zero/core/stores/cache"
	"github.com/zeromicro/go-zero/rest"
	"github.com/zeromicro/go-zero/zrpc"
)

type ServiceContext struct {
	Config            config.Config
	Cache             cache.Cache
	JwtAuthMiddleware rest.Middleware
	// RPC客户端
	NewsPolicyEngineRpc zrpc.Client
	StrategyWorkshopRpc zrpc.Client
	AiAssistantRpc       zrpc.Client
	SmartExecutionRpc    zrpc.Client

	// 新增的stockApi RPC客户端
	StockDataRpc       zrpc.Client
	MarketAnalysisRpc  zrpc.Client
	StrategyRpc        zrpc.Client
	TradingRpc         zrpc.Client
	SpecialAnalysisRpc zrpc.Client
	// 通用组件
	Common *common.Common
}

func NewServiceContext(c config.Config) *ServiceContext {
	// 初始化缓存
	cache := cache.NewCache(c.Redis, nil)

	return &ServiceContext{
		Config: c,
		Cache:  cache,
		JwtAuthMiddleware: middleware.NewJwtAuthMiddleware(
			c.JwtAuth.AccessSecret,
			c.JwtAuth.AccessExpire,
		).Handle,
		// 初始化RPC客户端
		NewsPolicyEngineRpc: zrpc.MustNewClient(c.NewsPolicyEngine),
		StrategyWorkshopRpc: zrpc.MustNewClient(c.StrategyWorkshop),
		AiAssistantRpc:       zrpc.MustNewClient(c.AiAssistant),
		SmartExecutionRpc:    zrpc.MustNewClient(c.SmartExecution),

		// 初始化新增的stockApi RPC客户端
		StockDataRpc:       zrpc.MustNewClient(c.StockData),
		MarketAnalysisRpc:  zrpc.MustNewClient(c.MarketAnalysis),
		StrategyRpc:        zrpc.MustNewClient(c.Strategy),
		TradingRpc:         zrpc.MustNewClient(c.Trading),
		SpecialAnalysisRpc: zrpc.MustNewClient(c.SpecialAnalysis),
		// 初始化通用组件 - 使用安全的数据库连接池配置
		Common: common.NewCommon(
			c.DB.Host,
			c.DB.Port,
			c.DB.User,
			c.DB.Password,
			c.DB.Database,
			c.DB.MaxIdleConns,
			c.DB.MaxOpenConns,
			c.DB.ConnMaxLifetime,
		),
	}
}

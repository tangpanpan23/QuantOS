package svc

import (
	"log"
	"quantos/app/api/internal/config"
	"quantos/app/api/internal/middleware"
	"quantos/common"

	"github.com/zeromicro/go-zero/core/stores/cache"
	"github.com/zeromicro/go-zero/rest"
	"github.com/zeromicro/go-zero/zrpc"
)

// ServiceContext 服务上下文
// 所有 API Handler 和 Logic 共享此上下文
type ServiceContext struct {
	Config            config.Config
	Cache             cache.Cache
	JwtAuthMiddleware rest.Middleware

	// RPC 客户端（可选，未实现时为 nil）
	// TODO: 随着各微服务实现，逐步启用
	NewsPolicyEngineRpc  zrpc.Client
	StrategyWorkshopRpc  zrpc.Client
	AiAssistantRpc       zrpc.Client
	SmartExecutionRpc    zrpc.Client
	StockDataRpc         zrpc.Client
	MarketAnalysisRpc    zrpc.Client
	StrategyRpc          zrpc.Client
	TradingRpc           zrpc.Client
	SpecialAnalysisRpc   zrpc.Client

	// 通用组件
	Common *common.Common
}

// NewServiceContext 创建服务上下文
func NewServiceContext(c config.Config) *ServiceContext {
	// 初始化缓存
	var cacheClient cache.Cache
	cacheClient = cache.NewCache(c.Redis, nil)

	// JWT 中间件
	jwtMiddleware := middleware.NewJwtAuthMiddleware(
		c.JwtAuth.AccessSecret,
		c.JwtAuth.AccessExpire,
	).Handle

	// 初始化通用组件（数据库）
	var dbCommon *common.Common
	dbCommon = common.NewCommon(
		c.DB.Host,
		c.DB.Port,
		c.DB.User,
		c.DB.Password,
		c.DB.Database,
		c.DB.MaxIdleConns,
		c.DB.MaxOpenConns,
		c.DB.ConnMaxLifetime,
	)

	ctx := &ServiceContext{
		Config:             c,
		Cache:              cacheClient,
		JwtAuthMiddleware:  jwtMiddleware,
		Common:             dbCommon,
		// RPC 客户端初始化为 nil，按需启用
	}

	// 初始化 RPC 客户端（非阻塞，如果服务不存在会记录警告）
	ctx.initRpcClients(c)

	return ctx
}

// initRpcClients 初始化 RPC 客户端（不阻塞启动）
func (ctx *ServiceContext) initRpcClients(c config.Config) {
	// 所有 RPC 服务目前均为 stub 实现
	// 注释掉自动初始化，避免启动时 panic
	// TODO: 随着各服务实现，逐步取消注释

	/*
	ctx.NewsPolicyEngineRpc = ctx.newRpcClientSafe(c.NewsPolicyEngine, "NewsPolicyEngine")
	ctx.StrategyWorkshopRpc = ctx.newRpcClientSafe(c.StrategyWorkshop, "StrategyWorkshop")
	ctx.AiAssistantRpc = ctx.newRpcClientSafe(c.AiAssistant, "AiAssistant")
	ctx.SmartExecutionRpc = ctx.newRpcClientSafe(c.SmartExecution, "SmartExecution")
	ctx.StockDataRpc = ctx.newRpcClientSafe(c.StockData, "StockData")
	ctx.MarketAnalysisRpc = ctx.newRpcClientSafe(c.MarketAnalysis, "MarketAnalysis")
	ctx.StrategyRpc = ctx.newRpcClientSafe(c.Strategy, "Strategy")
	ctx.TradingRpc = ctx.newRpcClientSafe(c.Trading, "Trading")
	ctx.SpecialAnalysisRpc = ctx.newRpcClientSafe(c.SpecialAnalysis, "SpecialAnalysis")
	*/
}

// newRpcClientSafe 安全创建 RPC 客户端（不阻塞）
func (ctx *ServiceContext) newRpcClientSafe(conf zrpc.RpcClientConf, name string) zrpc.Client {
	if !ctx.isRpcConfigured(conf) {
		log.Printf("[WARN] RPC client %s 未配置，跳过初始化", name)
		return nil
	}
	client, err := zrpc.NewClient(conf)
	if err != nil {
		log.Printf("[WARN] RPC 客户端 %s 初始化失败: %v（服务可能未启动）", name, err)
		return nil
	}
	log.Printf("[INFO] RPC 客户端 %s 初始化成功", name)
	return client
}

// isRpcConfigured 检查 RPC 配置是否有效
func (ctx *ServiceContext) isRpcConfigured(conf zrpc.RpcClientConf) bool {
	return conf.Endpoints != nil && len(conf.Endpoints) > 0 && conf.Endpoints[0] != ""
}

package svc

import (
	"context"
	"fmt"
	"log"
	"quantos/app/api/internal/config"
	"quantos/common"

	"github.com/redis/go-redis/v9"
	"github.com/zeromicro/go-zero/zrpc"
)

type ServiceContext struct {
	Config config.Config

	Redis *redis.Client

	NewsPolicyEngineRpc zrpc.Client
	StrategyWorkshopRpc zrpc.Client
	AiAssistantRpc      zrpc.Client
	SmartExecutionRpc   zrpc.Client
	StockDataRpc        zrpc.Client
	MarketAnalysisRpc   zrpc.Client
	StrategyRpc         zrpc.Client
	TradingRpc          zrpc.Client
	SpecialAnalysisRpc  zrpc.Client

	Common *common.Common
}

func NewServiceContext(c config.Config) *ServiceContext {
	dbCommon := common.NewCommon(
		c.DB.Host, c.DB.Port, c.DB.User, c.DB.Password,
		c.DB.Database, c.DB.MaxIdleConns, c.DB.MaxOpenConns, c.DB.ConnMaxLifetime,
	)

	// 初始化 Redis 客户端
	rdb := redis.NewClient(&redis.Options{
		Addr: fmt.Sprintf("%s:%d", c.Redis.Host, c.Redis.Port),
	})
	// 连接测试
	ctx := context.Background()
	if err := rdb.Ping(ctx).Err(); err != nil {
		log.Printf("[WARN] Redis 连接失败: %v", err)
	} else {
		log.Printf("[INFO] Redis 连接成功: %s:%d", c.Redis.Host, c.Redis.Port)
	}

	return &ServiceContext{
		Config: c,
		Redis:  rdb,
		Common: dbCommon,
	}
}

func (ctx *ServiceContext) initRpcClients(c config.Config) {}

func (ctx *ServiceContext) newRpcClientSafe(conf zrpc.RpcClientConf, name string) zrpc.Client {
	if !ctx.isRpcConfigured(conf) {
		log.Printf("[WARN] RPC client %s 未配置，跳过初始化", name)
		return nil
	}
	client, err := zrpc.NewClient(conf)
	if err != nil {
		log.Printf("[WARN] RPC 客户端 %s 初始化失败: %v", name, err)
		return nil
	}
	log.Printf("[INFO] RPC 客户端 %s 初始化成功", name)
	return client
}

func (ctx *ServiceContext) isRpcConfigured(conf zrpc.RpcClientConf) bool {
	return conf.Endpoints != nil && len(conf.Endpoints) > 0 && conf.Endpoints[0] != ""
}

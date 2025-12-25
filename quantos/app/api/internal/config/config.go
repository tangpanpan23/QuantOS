package config

import (
	"github.com/zeromicro/go-zero/core/stores/cache"
	"github.com/zeromicro/go-zero/rest"
	"github.com/zeromicro/go-zero/zrpc"
)

type Config struct {
	rest.RestConf

	// JWT 配置
	JwtAuth struct {
		AccessSecret string
		AccessExpire int64
	}

	// 数据库配置
	DB struct {
		Host     string
		Port     int
		User     string
		Password string
		Database string
		Charset  string
	}

	// Redis 配置
	Redis cache.CacheConf

	// RPC服务配置
	NewsPolicyEngine zrpc.RpcClientConf
	StrategyWorkshop zrpc.RpcClientConf
	AiAssistant      zrpc.RpcClientConf
	SmartExecution   zrpc.RpcClientConf

	// 其他配置
	Log       LogConf
	Telemetry TelemetryConf
}

type LogConf struct {
	ServiceName string
	Level       string
	Mode        string
}

type TelemetryConf struct {
	Name     string
	Endpoint string
	Sampler  float64
}

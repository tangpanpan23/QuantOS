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

	// 数据库配置 - 增强安全性
	DB struct {
		Host            string
		Port            int
		User            string
		Password        string
		Database        string
		Charset         string
		MaxIdleConns    int `yaml:"MaxIdleConns"`
		MaxOpenConns    int `yaml:"MaxOpenConns"`
		ConnMaxLifetime int `yaml:"ConnMaxLifetime"`
	}

	// Redis 配置
	Redis cache.CacheConf

	// RPC服务配置
	NewsPolicyEngine zrpc.RpcClientConf
	StrategyWorkshop zrpc.RpcClientConf
	AiAssistant      zrpc.RpcClientConf
	SmartExecution   zrpc.RpcClientConf

	// 新增的stockApi服务配置
	StockData       zrpc.RpcClientConf
	MarketAnalysis  zrpc.RpcClientConf
	Strategy        zrpc.RpcClientConf
	Trading         zrpc.RpcClientConf
	SpecialAnalysis zrpc.RpcClientConf

	// 其他配置
	Log       LogConf
	Telemetry TelemetryConf

	// 安全配置
	Security SecurityConf

	// 功能开关
	Features FeatureConf
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

type SecurityConf struct {
	CorsAllowedOrigins string `yaml:"CorsAllowedOrigins"`
	RateLimitPerMinute int    `yaml:"RateLimitPerMinute"`
}

type FeatureConf struct {
	EnableSwagger bool `yaml:"EnableSwagger"`
	EnableMetrics bool `yaml:"EnableMetrics"`
	EnableTracing bool `yaml:"EnableTracing"`
	EnableCache   bool `yaml:"EnableCache"`
	DebugMode     bool `yaml:"DebugMode"`
	AutoMigrate   bool `yaml:"AutoMigrate"`
}

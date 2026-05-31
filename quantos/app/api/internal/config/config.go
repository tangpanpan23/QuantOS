package config

import (
	"github.com/zeromicro/go-zero/rest"
	"github.com/zeromicro/go-zero/zrpc"
)

type Config struct {
	rest.RestConf

	JwtAuth struct {
		AccessSecret string
		AccessExpire int64
	}

	DB struct {
		Host            string
		Port            int
		User            string
		Password        string
		Database        string
		Charset         string
		MaxIdleConns    int
		MaxOpenConns    int
		ConnMaxLifetime int
	}

	Redis struct {
		Host string
		Port int
		Type string
	}

	NewsPolicyEngine zrpc.RpcClientConf
	StrategyWorkshop zrpc.RpcClientConf
	AiAssistant      zrpc.RpcClientConf
	SmartExecution   zrpc.RpcClientConf
	StockData        zrpc.RpcClientConf
	MarketAnalysis   zrpc.RpcClientConf
	Strategy         zrpc.RpcClientConf
	Trading          zrpc.RpcClientConf
	SpecialAnalysis  zrpc.RpcClientConf
}

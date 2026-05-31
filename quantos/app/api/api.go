package main

import (
	"flag"
	"fmt"
	"net/http"
	"os"
	"path/filepath"

	"quantos/app/api/internal/config"
	"quantos/app/api/internal/handler"
	"quantos/app/api/internal/svc"

	"github.com/zeromicro/go-zero/core/conf"
	"github.com/zeromicro/go-zero/rest"
)

var configFile = flag.String("f", "etc/api.yaml", "the config file")

func main() {
	flag.Parse()

	var c config.Config
	conf.MustLoad(*configFile, &c)

	ctx := svc.NewServiceContext(c)
	server := rest.MustNewServer(c.RestConf)
	defer server.Stop()

	handler.RegisterHandlers(server, ctx)

	// 静态文件服务
	dir, _ := os.Getwd()
	staticDir := filepath.Join(dir, "dashboard")
	if info, err := os.Stat(staticDir); err == nil && info.IsDir() {
		staticHandler := http.StripPrefix("/", http.FileServer(http.Dir(staticDir)))
		server.AddRoutes([]rest.Route{{
			Method:  http.MethodGet,
			Path:    "/",
			Handler: staticHandler.ServeHTTP,
		}})
	}

	fmt.Printf("Starting server at %s:%d...\n", c.Host, c.Port)
	server.Start()
}

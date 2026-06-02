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

	// 静态文件服务（SPA）
	staticDir := "/Users/tank/Code/quantos-dashboard/dist"
	if info, err := os.Stat(staticDir); err == nil && info.IsDir() {
		fs := http.Dir(staticDir)
		fileServer := http.FileServer(fs)
		spaHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			fp := filepath.Join(staticDir, r.URL.Path)
			if _, err := os.Stat(fp); os.IsNotExist(err) {
				http.ServeFile(w, r, filepath.Join(staticDir, "index.html"))
			} else {
				fileServer.ServeHTTP(w, r)
			}
		})
		rest.WithNotFoundHandler(spaHandler)(server)
		fmt.Printf("Static files enabled (SPA): %s\n", staticDir)
	} else {
		fmt.Printf("WARNING: dist not found at %s\n", staticDir)
	}

	fmt.Printf("Starting server at %s:%d...\n", c.Host, c.Port)
	server.Start()
}

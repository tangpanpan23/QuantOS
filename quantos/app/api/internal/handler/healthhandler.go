package handler

import (
	"net/http"

	"quantos/app/api/internal/svc"

	"github.com/zeromicro/go-zero/rest/httpx"
)

func healthHandler(ctx *svc.ServiceContext) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		httpx.OkJson(w, map[string]string{
			"status": "ok",
			"service": "quantos-api",
		})
	}
}

package middleware

import (
	"net/http"
	"strings"

	"github.com/golang-jwt/jwt/v4"
	"github.com/zeromicro/go-zero/rest/httpx"
)

type JwtAuthMiddleware struct {
	secret     string
	expireTime int64
}

func NewJwtAuthMiddleware(secret string, expireTime int64) *JwtAuthMiddleware {
	return &JwtAuthMiddleware{
		secret:     secret,
		expireTime: expireTime,
	}
}

func (m *JwtAuthMiddleware) Handle(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// 从请求头获取token
		authHeader := r.Header.Get("Authorization")
		if authHeader == "" {
			httpx.Error(w, &ErrorResponse{
				Code:    401,
				Message: "Authorization header is required",
			})
			return
		}

		// 检查Bearer token格式
		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || parts[0] != "Bearer" {
			httpx.Error(w, &ErrorResponse{
				Code:    401,
				Message: "Invalid authorization format",
			})
			return
		}

		tokenString := parts[1]

		// 解析token
		token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
			if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, jwt.ErrSignatureInvalid
			}
			return []byte(m.secret), nil
		})

		if err != nil || !token.Valid {
			httpx.Error(w, &ErrorResponse{
				Code:    401,
				Message: "Invalid token",
			})
			return
		}

		// 将用户信息存储到请求上下文中
		if claims, ok := token.Claims.(jwt.MapClaims); ok {
			// 可以在这里添加用户ID到上下文
			r.Header.Set("X-User-ID", claims["user_id"].(string))
		}

		next(w, r)
	}
}

type ErrorResponse struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

func (e *ErrorResponse) Error() string {
	return e.Message
}

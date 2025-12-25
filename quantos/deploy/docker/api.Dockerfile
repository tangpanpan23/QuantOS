# QuantSaaS API Service Dockerfile
FROM golang:1.22-alpine AS builder

# 设置工作目录
WORKDIR /app

# 安装构建依赖
RUN apk add --no-cache git ca-certificates

# 复制go mod文件
COPY go.mod go.sum ./

# 下载依赖
RUN go mod download

# 复制源代码
COPY . .

# 构建API服务
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o api ./app/api

# 运行时镜像
FROM alpine:latest

# 安装ca-certificates用于HTTPS请求
RUN apk --no-cache add ca-certificates

WORKDIR /root/

# 从构建阶段复制二进制文件
COPY --from=builder /app/api .

# 复制配置文件
COPY --from=builder /app/app/api/etc/api.yaml ./etc/

# 暴露端口
EXPOSE 8888

# 启动服务
CMD ["./api", "-f", "etc/api.yaml"]

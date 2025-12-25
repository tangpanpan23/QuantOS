# QuantSaaS Makefile
# 用于构建、测试和部署QuantSaaS平台

.PHONY: help build test clean docker-build docker-push deploy dev prod

# 默认目标
help: ## 显示帮助信息
	@echo "QuantSaaS 构建和部署工具"
	@echo ""
	@echo "可用命令:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# 开发环境命令
dev: ## 启动开发环境 (Docker Compose)
	cd deploy/docker && docker-compose up -d

dev-logs: ## 查看开发环境日志
	cd deploy/docker && docker-compose logs -f

dev-stop: ## 停止开发环境
	cd deploy/docker && docker-compose down

# 构建命令
build: ## 构建所有服务
	go mod tidy
	go build -o bin/api ./app/api
	@echo "构建完成"

build-api: ## 构建API服务
	go build -o bin/api ./app/api

# 测试命令
test: ## 运行所有测试
	go test ./...

test-coverage: ## 运行测试并生成覆盖率报告
	go test -coverprofile=coverage.out ./...
	go tool cover -html=coverage.out -o coverage.html

# Docker 命令
docker-build: ## 构建Docker镜像
	docker build -f deploy/docker/api.Dockerfile -t quantos/api:latest .

docker-push: ## 推送Docker镜像 (需要先登录Docker Hub)
	docker tag quantos/api:latest your-registry/quantos/api:latest
	docker push your-registry/quantos/api:latest

# 生产环境部署命令
prod: ## 生产环境构建 (交叉编译)
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -installsuffix cgo -o bin/api-linux ./app/api

deploy-k8s: ## 部署到Kubernetes
	kubectl apply -f deploy/kubernetes/namespace.yaml
	kubectl apply -f deploy/kubernetes/mysql.yaml
	kubectl apply -f deploy/kubernetes/redis.yaml
	kubectl apply -f deploy/kubernetes/api.yaml

deploy-k8s-check: ## 检查Kubernetes部署状态
	kubectl get pods -n quantos
	kubectl get services -n quantos
	kubectl get ingress -n quantos

# 数据库命令
migrate-up: ## 执行数据库迁移
	go run app/command/console.go migrate up

migrate-down: ## 回滚数据库迁移
	go run app/command/console.go migrate down

migrate-status: ## 查看迁移状态
	go run app/command/console.go migrate status

# 代码质量检查
lint: ## 运行代码质量检查
	golangci-lint run

fmt: ## 格式化代码
	go fmt ./...
	goimports -w .

vet: ## 运行go vet
	go vet ./...

# 清理命令
clean: ## 清理构建产物
	rm -rf bin/
	rm -f coverage.out coverage.html

clean-docker: ## 清理Docker镜像和容器
	docker-compose -f deploy/docker/docker-compose.yml down --volumes --remove-orphans
	docker system prune -f

# 快速开发命令
run-api: ## 直接运行API服务 (开发模式)
	go run app/api/api.go -f app/api/etc/api.yaml

swagger: ## 生成Swagger文档
	goctl api plugin -plugin goctl-swagger="swagger -filename api.json -host 127.0.0.1:8888" -api app/api/desc/api.api -dir .

# 安全相关命令
secrets-setup: ## 设置Kubernetes Secrets
	./scripts/setup-secrets.sh quantos

secrets-verify: ## 验证Kubernetes Secrets
	./scripts/setup-secrets.sh -v quantos

secrets-clean: ## 清理Kubernetes Secrets（危险操作）
	./scripts/setup-secrets.sh -d quantos

security-check: ## 安全检查
	@echo "检查安全配置..."
	@test -f .env && echo "✓ 环境变量文件存在" || (echo "✗ 缺少 .env 文件"; exit 1)
	@grep -q "JWT_ACCESS_SECRET=your_" .env && echo "⚠️  JWT密钥未配置" || echo "✓ JWT密钥已配置"
	@grep -q "DB_PASSWORD=your_" .env && echo "⚠️  数据库密码未配置" || echo "✓ 数据库密码已配置"
	@echo "安全检查完成"

# 生产环境部署
deploy-secure: secrets-setup deploy-k8s ## 安全部署到生产环境

# CI/CD 相关
ci: security-check lint test build ## CI流水线命令（包含安全检查）

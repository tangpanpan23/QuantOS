# QuantSaaS 安全配置指南

## 📋 概述

本文档详细说明QuantSaaS的安全配置和最佳实践，确保生产环境的安全部署。

## 🔐 安全架构

### 环境变量管理
- ✅ 使用 `.env` 文件管理敏感配置
- ✅ 生产环境使用环境变量注入
- ✅ 敏感信息不提交到版本控制

### 数据库安全
- ✅ 强密码策略（32位随机密码）
- ✅ 连接池限制（最大连接数、超时控制）
- ✅ SQL注入防护（使用ORM参数化查询）
- ✅ 审计日志记录

### API安全
- ✅ JWT Token认证
- ✅ 请求频率限制
- ✅ CORS策略配置
- ✅ HTTPS传输加密

### 容器安全
- ✅ 非root用户运行
- ✅ 只读根文件系统
- ✅ 最小权限原则
- ✅ 资源限制配置

## 🚀 快速开始

### 1. 环境准备

```bash
# 复制环境变量模板
cp env.example .env

# 编辑环境变量（设置安全的密码）
vim .env
```

### 2. 生成安全密钥

```bash
# 使用安全脚本生成密码
./scripts/setup-secrets.sh quantos
```

### 3. Docker部署

```bash
# 启动安全配置的服务
./scripts/start.sh
```

### 4. Kubernetes部署

```bash
# 创建安全的Secrets
./scripts/setup-secrets.sh quantos

# 部署到Kubernetes
kubectl apply -f deploy/kubernetes/
```

## 🔑 密钥管理

### 自动生成密钥

使用提供的脚本自动生成安全的随机密码：

```bash
# 生成所有Secrets
./scripts/setup-secrets.sh quantos

# 验证Secrets
./scripts/setup-secrets.sh -v quantos

# 删除Secrets（危险操作）
./scripts/setup-secrets.sh -d quantos
```

### 手动配置

对于生产环境，建议使用外部密钥管理工具：

```bash
# 示例：使用外部密码管理器
export DB_PASSWORD=$(vault kv get -field=password secret/quantos/db)
export JWT_SECRET=$(vault kv get -field=secret secret/quantos/jwt)
```

## 🗄️ 数据库安全配置

### MySQL安全设置

```sql
-- 启用严格SQL模式
SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO';

-- 创建最小权限用户
CREATE USER 'quantos'@'%' IDENTIFIED BY 'strong_password_here';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER ON quantos.* TO 'quantos'@'%';

-- 创建只读用户（用于报表）
CREATE USER 'quantos_readonly'@'%' IDENTIFIED BY 'another_strong_password';
GRANT SELECT ON quantos.* TO 'quantos_readonly'@'%';
```

### 连接池配置

```yaml
DB:
  MaxIdleConns: 10          # 最大空闲连接
  MaxOpenConns: 100         # 最大打开连接
  ConnMaxLifetime: 300      # 连接最大生存时间(秒)
```

## 🔒 API安全配置

### JWT配置

```yaml
JwtAuth:
  AccessSecret: "your_64_char_jwt_secret_here"
  AccessExpire: 86400  # 24小时
```

### 安全中间件

```go
// CORS配置
Security:
  CorsAllowedOrigins: "http://localhost:3000,http://localhost:8080"
  RateLimitPerMinute: 1000

// 功能开关
Features:
  EnableSwagger: false     # 生产环境关闭
  EnableMetrics: true
  EnableTracing: true
  DebugMode: false         # 生产环境关闭
```

## 🐳 Docker安全配置

### Dockerfile安全实践

```dockerfile
# 使用官方镜像
FROM golang:1.22-alpine

# 创建非root用户
RUN addgroup -g 1001 -S appuser && \
    adduser -u 1001 -S appuser -G appuser

# 复制应用
COPY --chown=appuser:appuser . /app

# 切换到非root用户
USER appuser

# 运行应用
CMD ["./app"]
```

### Docker Compose安全配置

```yaml
services:
  mysql:
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
      MYSQL_PASSWORD: ${DB_PASSWORD}
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
```

## ☸️ Kubernetes安全配置

### Pod安全上下文

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1001
    runAsGroup: 1001
    fsGroup: 1001
  containers:
  - securityContext:
      readOnlyRootFilesystem: true
      allowPrivilegeEscalation: false
      capabilities:
        drop:
          - ALL
```

### Network Policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: ingress
    ports:
    - protocol: TCP
      port: 8888
```

### Secrets管理

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
data:
  jwt-secret: <base64-encoded-secret>
  db-password: <base64-encoded-password>
```

## 📊 监控和审计

### 日志配置

```yaml
Log:
  ServiceName: quantos-api
  Level: info
  Mode: json  # 结构化日志

Telemetry:
  Name: quantos-api
  Endpoint: http://jaeger-collector:14268/api/traces
  Sampler: 0.1
```

### 健康检查

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8888
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8888
  initialDelaySeconds: 5
  periodSeconds: 5
```

## 🚨 安全检查清单

### 部署前检查

- [ ] 所有密码都已更改为强密码
- [ ] JWT密钥长度至少64字符
- [ ] 数据库用户使用最小权限原则
- [ ] 防火墙规则正确配置
- [ ] SSL/TLS证书有效
- [ ] 日志记录启用
- [ ] 监控告警配置

### 定期维护

- [ ] 定期轮换密码和密钥
- [ ] 监控异常访问
- [ ] 更新安全补丁
- [ ] 审查访问日志
- [ ] 备份验证

## 🔧 故障排除

### 常见问题

#### 数据库连接失败
```bash
# 检查环境变量
echo $DB_PASSWORD

# 测试数据库连接
mysql -h mysql-service -u quantos -p
```

#### JWT认证失败
```bash
# 检查JWT密钥
kubectl get secret api-secrets -o yaml

# 验证密钥长度
echo $JWT_ACCESS_SECRET | wc -c
```

#### Secrets未注入
```bash
# 检查Pod环境变量
kubectl exec -it <pod-name> -- env | grep -E "(JWT|DB_)"
```

## 📞 安全报告

如果发现安全漏洞，请通过以下方式报告：

- 📧 邮箱: tangpan23@126.com
- 🐛 GitHub Issues: [安全问题模板](.github/ISSUE_TEMPLATE/security.md)

我们承诺在收到报告后24小时内响应，并在90天内发布修复方案。

## 📚 相关文档

- [部署指南](./README.md)
- [API文档](./docs/api.md)
- [开发规范](./docs/development.md)
- [监控指南](./docs/monitoring.md)

---

*"安全不是目的，而是一种持续的过程"* 🛡️

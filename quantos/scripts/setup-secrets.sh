#!/bin/bash

# QuantSaaS Secrets 安全管理脚本
# 用于生成和管理Kubernetes Secrets

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 生成安全随机密码
generate_password() {
    local length=${1:-32}
    openssl rand -base64 "$length" | tr -d "=+/" | cut -c1-"$length"
}

# 生成JWT密钥
generate_jwt_secret() {
    generate_password 64
}

# base64编码
encode_base64() {
    echo -n "$1" | base64
}

# 检查kubectl是否可用
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl 未安装或不在PATH中"
        exit 1
    fi
}

# 检查命名空间是否存在
ensure_namespace() {
    local namespace=$1
    if ! kubectl get namespace "$namespace" &> /dev/null; then
        log_info "创建命名空间: $namespace"
        kubectl create namespace "$namespace"
    else
        log_info "命名空间已存在: $namespace"
    fi
}

# 创建MySQL Secrets
create_mysql_secrets() {
    local namespace=$1
    log_step "创建MySQL Secrets"

    # 生成密码
    local root_pass=$(generate_password)
    local user_pass=$(generate_password)
    local readonly_pass=$(generate_password)

    log_info "生成的MySQL密码:"
    echo "  Root Password: $root_pass"
    echo "  User Password: $user_pass"
    echo "  ReadOnly Password: $readonly_pass"

    # 创建Secret
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: mysql-secret
  namespace: $namespace
  labels:
    app: mysql
    component: database
  annotations:
    security.alpha.kubernetes.io/secret-type: "database"
type: Opaque
data:
  mysql-root-password: $(encode_base64 "$root_pass")
  mysql-user-password: $(encode_base64 "$user_pass")
  mysql-readonly-password: $(encode_base64 "$readonly_pass")
EOF

    log_info "MySQL Secrets创建成功"

    # 保存密码到本地文件（用于备份）
    mkdir -p secrets
    cat > "secrets/mysql-$namespace.txt" << EOF
MySQL Secrets for namespace: $namespace
Generated at: $(date)

Root Password: $root_pass
User Password: $user_pass
ReadOnly Password: $readonly_pass

请妥善保存这些密码！
EOF

    log_warn "密码已保存到 secrets/mysql-$namespace.txt，请妥善保管！"
}

# 创建Redis Secrets
create_redis_secrets() {
    local namespace=$1
    log_step "创建Redis Secrets"

    local redis_pass=$(generate_password)

    log_info "生成的Redis密码: $redis_pass"

    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: redis-secret
  namespace: $namespace
  labels:
    app: redis
    component: cache
  annotations:
    security.alpha.kubernetes.io/secret-type: "database"
type: Opaque
data:
  redis-password: $(encode_base64 "$redis_pass")
EOF

    log_info "Redis Secrets创建成功"

    # 保存密码
    cat >> "secrets/mysql-$namespace.txt" << EOF

Redis Password: $redis_pass
EOF
}

# 创建API Secrets
create_api_secrets() {
    local namespace=$1
    log_step "创建API Secrets"

    local jwt_secret=$(generate_jwt_secret)

    log_info "生成的JWT密钥: $jwt_secret"

    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: api-secrets
  namespace: $namespace
  labels:
    app: api
    component: application
  annotations:
    security.alpha.kubernetes.io/secret-type: "application"
type: Opaque
data:
  jwt-access-secret: $(encode_base64 "$jwt_secret")
EOF

    log_info "API Secrets创建成功"

    # 保存密钥
    cat >> "secrets/mysql-$namespace.txt" << EOF

JWT Access Secret: $jwt_secret
EOF
}

# 验证Secrets
verify_secrets() {
    local namespace=$1
    log_step "验证Secrets创建"

    local secrets=("mysql-secret" "redis-secret" "api-secrets")
    for secret in "${secrets[@]}"; do
        if kubectl get secret "$secret" -n "$namespace" &> /dev/null; then
            log_info "✓ Secret $secret 存在"
        else
            log_error "✗ Secret $secret 不存在"
            return 1
        fi
    done

    log_info "所有Secrets验证通过"
}

# 显示使用帮助
show_help() {
    echo "QuantSaaS Secrets 管理脚本"
    echo ""
    echo "用法:"
    echo "  $0 [选项] [命名空间]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示此帮助信息"
    echo "  -c, --create   创建Secrets (默认)"
    echo "  -v, --verify   验证Secrets"
    echo "  -d, --delete   删除Secrets"
    echo ""
    echo "示例:"
    echo "  $0 quantos                    # 在quantos命名空间创建Secrets"
    echo "  $0 -v quantos                 # 验证quantos命名空间的Secrets"
    echo "  $0 -d quantos                 # 删除quantos命名空间的Secrets"
    echo ""
    echo "注意:"
    echo "  生成的密码会保存到 secrets/ 目录中，请妥善保管！"
}

# 删除Secrets
delete_secrets() {
    local namespace=$1
    log_step "删除Secrets"

    local secrets=("mysql-secret" "redis-secret" "api-secrets")
    for secret in "${secrets[@]}"; do
        if kubectl get secret "$secret" -n "$namespace" &> /dev/null; then
            kubectl delete secret "$secret" -n "$namespace"
            log_info "已删除Secret: $secret"
        else
            log_info "Secret不存在: $secret"
        fi
    done
}

# 主函数
main() {
    local action="create"
    local namespace=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -c|--create)
                action="create"
                shift
                ;;
            -v|--verify)
                action="verify"
                shift
                ;;
            -d|--delete)
                action="delete"
                shift
                ;;
            *)
                namespace="$1"
                shift
                ;;
        esac
    done

    # 默认命名空间
    if [ -z "$namespace" ]; then
        namespace="quantos"
    fi

    log_info "QuantSaaS Secrets管理 - 命名空间: $namespace"

    case $action in
        create)
            check_kubectl
            ensure_namespace "$namespace"
            create_mysql_secrets "$namespace"
            create_redis_secrets "$namespace"
            create_api_secrets "$namespace"
            verify_secrets "$namespace"
            log_info "Secrets创建完成！"
            log_warn "重要提醒："
            echo "  1. 密码已保存到 secrets/ 目录"
            echo "  2. 请妥善保管这些敏感信息"
            echo "  3. 生产环境建议使用外部密钥管理工具"
            ;;
        verify)
            check_kubectl
            verify_secrets "$namespace"
            ;;
        delete)
            check_kubectl
            delete_secrets "$namespace"
            log_info "Secrets删除完成"
            ;;
        *)
            log_error "未知操作: $action"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"

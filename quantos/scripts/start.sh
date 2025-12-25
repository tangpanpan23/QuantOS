#!/bin/bash

# QuantSaaS 安全启动脚本
# 此脚本用于安全地启动QuantSaaS服务

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# 检查环境变量文件
check_env_file() {
    if [ ! -f ".env" ]; then
        log_error "环境变量文件 .env 不存在！"
        log_info "请复制 env.example 到 .env 并配置你的实际值："
        echo "  cp env.example .env"
        echo "  # 然后编辑 .env 文件设置安全密码和其他配置"
        exit 1
    fi

    # 检查关键的环境变量
    local required_vars=("DB_PASSWORD" "JWT_ACCESS_SECRET")
    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" .env || grep -q "^${var}=your_\|${var}=change_this" .env; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -ne 0 ]; then
        log_error "以下环境变量未正确配置："
        printf '  - %s\n' "${missing_vars[@]}"
        log_info "请在 .env 文件中设置这些变量的安全值"
        exit 1
    fi
}

# 生成安全的随机密码
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

# 设置默认环境变量
setup_default_env() {
    local env_file=".env"

    # 如果.env不存在，从env.example复制
    if [ ! -f "$env_file" ]; then
        cp env.example "$env_file"
        log_info "已从 env.example 复制环境变量文件"
    fi

    # 检查并设置关键变量的默认值
    if ! grep -q "^DB_ROOT_PASSWORD=" "$env_file" || grep -q "^DB_ROOT_PASSWORD=change_this" "$env_file"; then
        local db_root_pass=$(generate_password)
        sed -i.bak "s|^DB_ROOT_PASSWORD=.*|DB_ROOT_PASSWORD=$db_root_pass|" "$env_file"
        log_info "已生成安全的数据库root密码"
    fi

    if ! grep -q "^DB_PASSWORD=" "$env_file" || grep -q "^DB_PASSWORD=your_secure_password_here" "$env_file"; then
        local db_pass=$(generate_password)
        sed -i.bak "s|^DB_PASSWORD=.*|DB_PASSWORD=$db_pass|" "$env_file"
        log_info "已生成安全的数据库用户密码"
    fi

    if ! grep -q "^JWT_ACCESS_SECRET=" "$env_file" || grep -q "^JWT_ACCESS_SECRET=your_jwt_secret_key_here" "$env_file"; then
        local jwt_secret=$(generate_password)
        sed -i.bak "s|^JWT_ACCESS_SECRET=.*|JWT_ACCESS_SECRET=$jwt_secret|" "$env_file"
        log_info "已生成安全的JWT密钥"
    fi

    if ! grep -q "^REDIS_PASSWORD=" "$env_file" || [ "$(grep '^REDIS_PASSWORD=' "$env_file" | cut -d'=' -f2)" = "" ]; then
        local redis_pass=$(generate_password)
        sed -i.bak "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=$redis_pass|" "$env_file"
        log_info "已生成安全的Redis密码"
    fi

    # 清理备份文件
    rm -f "${env_file}.bak"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
}

# 清理之前的容器
cleanup_containers() {
    log_info "清理之前的容器..."
    docker-compose -f deploy/docker/docker-compose.yml down --volumes --remove-orphans 2>/dev/null || true
}

# 启动服务
start_services() {
    log_info "启动 QuantSaaS 服务..."

    # 切换到正确的目录
    cd "$(dirname "$0")/.." || exit 1

    # 启动服务
    docker-compose -f deploy/docker/docker-compose.yml up -d

    log_info "服务启动中，请稍候..."

    # 等待服务就绪
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f deploy/docker/docker-compose.yml ps | grep -q "healthy"; then
            log_info "所有服务已启动并运行正常！"
            echo ""
            echo "========================================"
            echo "🎉 QuantSaaS 启动成功！"
            echo "========================================"
            echo "📊 API服务: http://localhost:${APP_PORT:-8888}"
            echo "🏥 健康检查: http://localhost:${APP_PORT:-8888}/health"
            echo "📝 API文档: http://localhost:${APP_PORT:-8888}/swagger/"
            echo "========================================"
            return 0
        fi

        echo "等待服务启动... ($attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done

    log_error "服务启动超时，请检查日志："
    echo "  docker-compose -f deploy/docker/docker-compose.yml logs"
    exit 1
}

# 显示使用帮助
show_help() {
    echo "QuantSaaS 安全启动脚本"
    echo ""
    echo "用法:"
    echo "  $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示此帮助信息"
    echo "  -c, --clean    清理并重新启动"
    echo "  -s, --stop     停止所有服务"
    echo "  -l, --logs     查看服务日志"
    echo ""
    echo "示例:"
    echo "  $0              # 正常启动"
    echo "  $0 -c           # 清理并重新启动"
    echo "  $0 -s           # 停止服务"
    echo "  $0 -l           # 查看日志"
}

# 主函数
main() {
    case "${1:-}" in
        -h|--help)
            show_help
            exit 0
            ;;
        -c|--clean)
            log_info "执行清理启动..."
            cleanup_containers
            check_env_file
            start_services
            ;;
        -s|--stop)
            log_info "停止所有服务..."
            cd "$(dirname "$0")/.." || exit 1
            docker-compose -f deploy/docker/docker-compose.yml down
            log_info "服务已停止"
            ;;
        -l|--logs)
            log_info "查看服务日志..."
            cd "$(dirname "$0")/.." || exit 1
            docker-compose -f deploy/docker/docker-compose.yml logs -f
            ;;
        *)
            log_info "启动 QuantSaaS 服务..."
            check_docker
            setup_default_env
            check_env_file
            start_services
            ;;
    esac
}

# 执行主函数
main "$@"
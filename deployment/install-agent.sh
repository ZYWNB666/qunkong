#!/bin/bash
#
# Qunkong Agent 安装脚本
# 用法: ./install-agent.sh --server <服务器地址> --port <端口> [--binary-path <二进制文件路径>]
#

set -e

# 默认值
INSTALL_DIR="/opt/qunkong-agent"
SERVICE_FILE="/etc/systemd/system/qunkong-agent.service"
BINARY_NAME="qunkong-agent"
SERVER_HOST="localhost"
SERVER_PORT="8765"
BINARY_PATH=""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印信息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        print_error "请使用root权限运行此脚本"
        exit 1
    fi
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --server|-s)
                SERVER_HOST="$2"
                shift 2
                ;;
            --port|-p)
                SERVER_PORT="$2"
                shift 2
                ;;
            --binary-path|-b)
                BINARY_PATH="$2"
                shift 2
                ;;
            --install-dir|-d)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --help|-h)
                echo "用法: $0 --server <服务器地址> --port <端口> [选项]"
                echo ""
                echo "选项:"
                echo "  --server, -s        服务器地址 (必需)"
                echo "  --port, -p          服务器端口 (必需)"
                echo "  --binary-path, -b   二进制文件路径 (可选，不指定则从当前目录查找)"
                echo "  --install-dir, -d   安装目录 (默认: /opt/qunkong-agent)"
                echo "  --help, -h          显示帮助信息"
                exit 0
                ;;
            *)
                print_error "未知参数: $1"
                exit 1
                ;;
        esac
    done
}

# 查找二进制文件
find_binary() {
    if [ -n "$BINARY_PATH" ]; then
        if [ ! -f "$BINARY_PATH" ]; then
            print_error "指定的二进制文件不存在: $BINARY_PATH"
            exit 1
        fi
        print_info "使用指定的二进制文件: $BINARY_PATH"
        return
    fi
    
    # 在当前目录查找
    if [ -f "./$BINARY_NAME" ]; then
        BINARY_PATH="./$BINARY_NAME"
        print_info "找到二进制文件: $BINARY_PATH"
        return
    fi
    
    # 在上级目录查找
    if [ -f "../$BINARY_NAME" ]; then
        BINARY_PATH="../$BINARY_NAME"
        print_info "找到二进制文件: $BINARY_PATH"
        return
    fi
    
    print_error "未找到二进制文件: $BINARY_NAME"
    print_error "请使用 --binary-path 参数指定二进制文件路径"
    exit 1
}

# 停止现有服务
stop_service() {
    if systemctl is-active --quiet qunkong-agent; then
        print_info "停止现有服务..."
        systemctl stop qunkong-agent
    fi
}

# 创建安装目录
create_install_dir() {
    print_info "创建安装目录: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
}

# 安装二进制文件
install_binary() {
    print_info "安装二进制文件..."
    cp "$BINARY_PATH" "$INSTALL_DIR/$BINARY_NAME"
    chmod +x "$INSTALL_DIR/$BINARY_NAME"
    
    # 创建版本信息文件
    echo "$(date '+%Y-%m-%d %H:%M:%S')" > "$INSTALL_DIR/version.txt"
}

# 创建systemd服务文件
create_service_file() {
    print_info "创建systemd服务文件..."
    
    cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Qunkong Agent - Distributed Script Execution System
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/$BINARY_NAME --server $SERVER_HOST --port $SERVER_PORT
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# 环境变量
Environment="PATH=/usr/local/bin:/usr/bin:/bin"

# 资源限制
LimitNOFILE=65536

# 安全设置
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
}

# 启动服务
start_service() {
    print_info "重新加载systemd配置..."
    systemctl daemon-reload
    
    print_info "启用服务..."
    systemctl enable qunkong-agent
    
    print_info "启动服务..."
    systemctl start qunkong-agent
    
    # 等待服务启动
    sleep 2
    
    # 检查服务状态
    if systemctl is-active --quiet qunkong-agent; then
        print_info "服务启动成功！"
    else
        print_error "服务启动失败！"
        print_error "请查看日志: journalctl -u qunkong-agent -f"
        exit 1
    fi
}

# 显示状态
show_status() {
    echo ""
    print_info "========== 安装完成 =========="
    print_info "服务名称: qunkong-agent"
    print_info "安装目录: $INSTALL_DIR"
    print_info "服务器地址: $SERVER_HOST:$SERVER_PORT"
    echo ""
    print_info "常用命令:"
    echo "  查看状态: systemctl status qunkong-agent"
    echo "  启动服务: systemctl start qunkong-agent"
    echo "  停止服务: systemctl stop qunkong-agent"
    echo "  重启服务: systemctl restart qunkong-agent"
    echo "  查看日志: journalctl -u qunkong-agent -f"
    echo "  禁用服务: systemctl disable qunkong-agent"
    echo ""
}

# 主函数
main() {
    print_info "Qunkong Agent 安装脚本"
    echo ""
    
    check_root
    parse_args "$@"
    
    if [ -z "$SERVER_HOST" ] || [ -z "$SERVER_PORT" ]; then
        print_error "请指定服务器地址和端口"
        print_error "用法: $0 --server <服务器地址> --port <端口>"
        exit 1
    fi
    
    find_binary
    stop_service
    create_install_dir
    install_binary
    create_service_file
    start_service
    show_status
}

main "$@"


#!/bin/bash
#
# Qunkong Agent 安装脚本
# 用法: 
#   从URL安装: ./install-agent.sh --server <服务器地址> --port <端口> --download-url <下载地址> [--md5 <MD5值>]
#   从本地安装: ./install-agent.sh --server <服务器地址> --port <端口> --binary-path <二进制文件路径>
#

set -e

# 默认值
INSTALL_DIR="/opt/qunkong-agent"
SERVICE_FILE="/etc/systemd/system/qunkong-agent.service"
BINARY_NAME="qunkong-agent"
SERVER_HOST="101.133.149.155"
SERVER_PORT="18765"
BINARY_PATH=""
DOWNLOAD_URL="https://oss.zywjjj.vip/test/qunkong-agent"
MD5_EXPECTED="0c2aabd808858ad3fa5b9b1d12711e4e"

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
            --download-url|-u)
                DOWNLOAD_URL="$2"
                shift 2
                ;;
            --md5|-m)
                MD5_EXPECTED="$2"
                shift 2
                ;;
            --install-dir|-d)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --help|-h)
                echo "用法："
                echo "  从URL安装:"
                echo "    $0 --server <地址> --port <端口> --download-url <URL> [--md5 <MD5>]"
                echo ""
                echo "  从本地文件安装:"
                echo "    $0 --server <地址> --port <端口> --binary-path <文件路径>"
                echo ""
                echo "选项:"
                echo "  --server, -s        Qunkong服务器地址 (必需)"
                echo "  --port, -p          Qunkong服务器端口 (必需)"
                echo "  --download-url, -u  下载URL (与--binary-path二选一)"
                echo "  --md5, -m           文件MD5值 (与--download-url配合使用，推荐)"
                echo "  --binary-path, -b   本地二进制文件路径 (与--download-url二选一)"
                echo "  --install-dir, -d   安装目录 (默认: /opt/qunkong-agent)"
                echo "  --help, -h          显示帮助信息"
                echo ""
                echo "示例:"
                echo "  从URL安装:"
                echo "    $0 --server 192.168.1.100 --port 8765 \\"
                echo "       --download-url http://192.168.1.100:8000/qunkong-agent \\"
                echo "       --md5 a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
                echo ""
                echo "  从本地文件安装:"
                echo "    $0 --server 192.168.1.100 --port 8765 \\"
                echo "       --binary-path ./qunkong-agent"
                exit 0
                ;;
            *)
                print_error "未知参数: $1"
                exit 1
                ;;
        esac
    done
}

# 下载二进制文件
download_binary() {
    print_info "从URL下载: $DOWNLOAD_URL"
    
    # 创建临时目录
    TEMP_DIR=$(mktemp -d)
    TEMP_FILE="$TEMP_DIR/$BINARY_NAME"
    
    # 检查下载工具
    if command -v wget &> /dev/null; then
        print_info "使用 wget 下载..."
        wget -O "$TEMP_FILE" "$DOWNLOAD_URL"
    elif command -v curl &> /dev/null; then
        print_info "使用 curl 下载..."
        curl -L -o "$TEMP_FILE" "$DOWNLOAD_URL"
    else
        print_error "未找到下载工具 (wget 或 curl)"
        print_error "请安装: apt-get install wget 或 yum install wget"
        exit 1
    fi
    
    if [ ! -f "$TEMP_FILE" ]; then
        print_error "下载失败"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    print_info "下载完成"
    
    # MD5校验
    if [ -n "$MD5_EXPECTED" ]; then
        print_info "开始MD5校验..."
        
        # 计算MD5
        if command -v md5sum &> /dev/null; then
            MD5_ACTUAL=$(md5sum "$TEMP_FILE" | awk '{print $1}')
        elif command -v md5 &> /dev/null; then
            MD5_ACTUAL=$(md5 -q "$TEMP_FILE")
        else
            print_warn "未找到MD5工具，跳过校验"
            BINARY_PATH="$TEMP_FILE"
            return
        fi
        
        # 转换为小写比较
        MD5_ACTUAL=$(echo "$MD5_ACTUAL" | tr '[:upper:]' '[:lower:]')
        MD5_EXPECTED_LOWER=$(echo "$MD5_EXPECTED" | tr '[:upper:]' '[:lower:]')
        
        print_info "文件MD5: $MD5_ACTUAL"
        print_info "期望MD5: $MD5_EXPECTED_LOWER"
        
        if [ "$MD5_ACTUAL" != "$MD5_EXPECTED_LOWER" ]; then
            print_error "MD5校验失败！"
            print_error "期望: $MD5_EXPECTED_LOWER"
            print_error "实际: $MD5_ACTUAL"
            rm -rf "$TEMP_DIR"
            exit 1
        fi
        
        print_info "MD5校验通过"
    else
        print_warn "未提供MD5值，跳过校验（不推荐）"
    fi
    
    BINARY_PATH="$TEMP_FILE"
}

# 准备二进制文件
prepare_binary() {
    # 优先使用下载URL
    if [ -n "$DOWNLOAD_URL" ]; then
        download_binary
        return
    fi
    
    # 使用本地文件
    if [ -n "$BINARY_PATH" ]; then
        if [ ! -f "$BINARY_PATH" ]; then
            print_error "指定的二进制文件不存在: $BINARY_PATH"
            exit 1
        fi
        print_info "使用本地二进制文件: $BINARY_PATH"
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
    
    print_error "未找到二进制文件"
    print_error "请使用 --download-url 或 --binary-path 参数"
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

# 清理临时文件
cleanup() {
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
}

# 主函数
main() {
    print_info "========== Qunkong Agent 安装脚本 =========="
    echo ""
    
    check_root
    parse_args "$@"
    
    # 验证必需参数
    if [ -z "$SERVER_HOST" ] || [ -z "$SERVER_PORT" ]; then
        print_error "请指定服务器地址和端口"
        echo ""
        echo "用法："
        echo "  从URL安装: $0 --server <地址> --port <端口> --download-url <URL> [--md5 <MD5>]"
        echo "  从本地安装: $0 --server <地址> --port <端口> --binary-path <路径>"
        echo ""
        echo "使用 --help 查看详细帮助"
        exit 1
    fi
    
    # 设置清理函数（失败时清理）
    trap cleanup EXIT
    
    # 1. 下载或准备二进制文件
    prepare_binary
    
    # 2. 停止现有服务
    stop_service
    
    # 3. 创建安装目录
    create_install_dir
    
    # 4. 安装二进制文件
    install_binary
    
    # 5. 配置systemd服务
    create_service_file
    
    # 6. 启动服务
    start_service
    
    # 7. 显示状态
    show_status
    
    # 清理临时文件
    cleanup
}

main "$@"


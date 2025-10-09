#!/bin/bash
#
# Qunkong Agent 卸载脚本
#

set -e

# 默认值
INSTALL_DIR="/opt/qunkong-agent"
SERVICE_FILE="/etc/systemd/system/qunkong-agent.service"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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
if [ "$EUID" -ne 0 ]; then 
    print_error "请使用root权限运行此脚本"
    exit 1
fi

print_info "Qunkong Agent 卸载脚本"
echo ""

# 停止服务
if systemctl is-active --quiet qunkong-agent; then
    print_info "停止服务..."
    systemctl stop qunkong-agent
fi

# 禁用服务
if systemctl is-enabled --quiet qunkong-agent; then
    print_info "禁用服务..."
    systemctl disable qunkong-agent
fi

# 删除服务文件
if [ -f "$SERVICE_FILE" ]; then
    print_info "删除服务文件..."
    rm -f "$SERVICE_FILE"
fi

# 重新加载systemd
print_info "重新加载systemd配置..."
systemctl daemon-reload

# 删除安装目录
if [ -d "$INSTALL_DIR" ]; then
    print_warn "是否删除安装目录 $INSTALL_DIR ? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_info "删除安装目录..."
        rm -rf "$INSTALL_DIR"
    else
        print_info "保留安装目录"
    fi
fi

echo ""
print_info "========== 卸载完成 =========="


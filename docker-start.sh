#!/bin/bash

# QueenBee 项目 Docker 启动脚本

echo "QueenBee 项目容器化启动"
echo "========================"

# 检查 Docker 和 Docker Compose 是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "错误: Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 创建必要的目录
mkdir -p logs config/mysql

# 检查数据库配置文件
if [ ! -f "config/database.conf" ]; then
    echo "创建数据库配置文件..."
    cp config/database.conf.docker config/database.conf
    echo "请编辑 config/database.conf 填写数据库连接信息"
fi

echo "正在启动服务..."
echo "前端地址: http://localhost:3000"
echo "后端API地址: http://localhost:5000"
echo "WebSocket地址: ws://localhost:8765"
echo ""
echo "注意: 请确保外部MySQL服务器已启动并可访问"
echo "数据库配置请检查 config/database.conf 文件"
echo ""

# 启动服务
if docker compose version &> /dev/null; then
    docker compose up --build
else
    docker-compose up --build
fi

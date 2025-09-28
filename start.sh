#!/bin/bash

echo "正在启动 QueenBee 前端项目..."
echo

echo "检查 Node.js 环境..."
if ! command -v node &> /dev/null; then
    echo "错误: 未检测到 Node.js，请先安装 Node.js"
    echo "下载地址: https://nodejs.org/"
    exit 1
fi

echo "检查依赖包..."
if [ ! -d "node_modules" ]; then
    echo "正在安装依赖包..."
    npm install
    if [ $? -ne 0 ]; then
        echo "错误: 依赖包安装失败"
        exit 1
    fi
fi

echo "启动开发服务器..."
echo "前端地址: http://localhost:3000"
echo "请确保后端服务运行在 http://localhost:5000"
echo
npm run dev

@echo off
echo 正在启动 QueenBee 前端项目...
echo.

echo 检查 Node.js 环境...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未检测到 Node.js，请先安装 Node.js
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

echo 检查依赖包...
if not exist "node_modules" (
    echo 正在安装依赖包...
    npm install
    if %errorlevel% neq 0 (
        echo 错误: 依赖包安装失败
        pause
        exit /b 1
    )
)

echo 启动开发服务器...
echo 前端地址: http://localhost:3000
echo 请确保后端服务运行在 http://localhost:5000
echo.
npm run dev

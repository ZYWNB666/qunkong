# QueenBee 项目容器化部署指南

## 概述

本项目已经容器化，包含以下服务：
- **前端服务**: Vue.js + Vite (端口 3000)
- **后端服务**: Flask + WebSocket (端口 5000 + 8765)

**注意**: 此配置不包含MySQL数据库服务，需要使用外部MySQL服务器。

## 快速启动

### 前置条件
1. **MySQL服务器**: 确保MySQL服务器已启动并可访问
2. **数据库配置**: 编辑 `config/database.conf` 配置数据库连接信息

### 方法一：使用启动脚本 (推荐)
```bash
# 给启动脚本执行权限
chmod +x docker-start.sh

# 运行启动脚本
./docker-start.sh
```

### 方法二：手动启动
```bash
# 确保配置文件存在
cp config/database.conf.docker config/database.conf
# 编辑 config/database.conf 填写实际数据库信息

# 构建并启动所有服务
docker-compose up --build

# 或者在后台运行
docker-compose up --build -d
```

## 访问地址

启动成功后，可以通过以下地址访问：

- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:5000
- **WebSocket**: ws://localhost:8765

**数据库要求**: 需要外部MySQL服务器，请在 `config/database.conf` 中配置连接信息。

## 项目结构

```
├── Dockerfile.frontend          # 前端容器构建文件
├── Dockerfile.backend           # 后端容器构建文件  
├── docker-compose.yml           # 服务编排文件
├── docker-start.sh              # 启动脚本
├── .dockerignore               # Docker忽略文件
├── config/
│   └── database.conf.docker    # 数据库配置模板
└── logs/                       # 日志目录
```

## 常用操作

### 查看服务状态
```bash
docker-compose ps
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs frontend
docker-compose logs backend
```

### 停止服务
```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

### 重启服务
```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
```

### 进入容器
```bash
# 进入后端容器
docker-compose exec backend bash

# 进入前端容器
docker-compose exec frontend sh

# 连接外部数据库（需要安装MySQL客户端）
mysql -h localhost -u your_username -p
```

## 开发模式

### 前端热重载
前端容器已配置为开发模式，修改 `src/` 目录下的文件会自动重新构建。

### 后端调试
如需调试后端代码，可以：
1. 修改 `docker-compose.yml` 中的后端服务配置
2. 添加调试端口映射
3. 使用 VS Code 的远程调试功能

## 生产环境部署

对于生产环境，建议：

1. **安全配置**: 修改 `config/database.conf` 中的数据库密码
2. **反向代理**: 使用 Nginx 作为反向代理
3. **SSL证书**: 添加 HTTPS 支持
4. **监控**: 添加容器监控和日志收集
5. **备份**: 定期备份数据库和配置文件

## 故障排除

### 常见问题

1. **端口占用**
   ```bash
   # 检查端口占用
   netstat -tlnp | grep :3000
   netstat -tlnp | grep :5000
   netstat -tlnp | grep :8765
   ```

2. **数据库连接失败**
   ```bash
   # 检查外部MySQL服务状态
   systemctl status mysql  # Linux
   # 或
   brew services list | grep mysql  # macOS
   
   # 测试数据库连接
   mysql -h localhost -u your_username -p
   
   # 检查后端日志中的数据库错误
   docker-compose logs backend
   ```

3. **前端构建失败**
   ```bash
   # 清理并重新构建
   docker-compose down
   docker-compose build --no-cache frontend
   docker-compose up frontend
   ```

4. **后端服务启动失败**
   ```bash
   # 检查后端日志
   docker-compose logs backend
   
   # 重新构建后端
   docker-compose build --no-cache backend
   ```

### 清理Docker资源
```bash
# 清理未使用的容器和镜像
docker system prune -a

# 清理未使用的数据卷
docker volume prune
```

## 配置文件说明

### docker-compose.yml 主要配置

- **网络模式**: 后端服务使用主机网络模式访问外部MySQL
- **数据卷**: 配置和日志目录挂载到主机
- **健康检查**: 包含后端服务的健康检查
- **依赖关系**: 前端依赖后端服务

### 数据库配置

数据库配置通过 `config/database.conf` 文件设置：

```ini
[mysql]
host = localhost          # MySQL服务器地址
port = 3306              # MySQL服务器端口
database = queenbee      # 数据库名称
username = your_username # 数据库用户名
password = your_password # 数据库密码
charset = utf8mb4        # 字符集

[connection]
max_connections = 20     # 最大连接数
timeout = 30             # 连接超时时间
```

### 前端环境变量

前端服务的环境变量（在docker-compose.yml中设置）：
- `VITE_API_URL`: 后端API地址
- `VITE_WS_URL`: WebSocket地址

## 更新日志

- v1.1.0: 简化配置管理
  - 移除环境变量复杂配置，统一使用配置文件
  - 简化部署流程
  - 优化文档说明

- v1.0.0: 初始容器化配置
  - 前端、后端服务容器化
  - 外部MySQL数据库支持
  - 包含健康检查和依赖管理

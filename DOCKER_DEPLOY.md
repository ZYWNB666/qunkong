# Qunkong Docker 部署指南

## 生产环境部署

### 前端特性
- ✅ 多阶段构建，优化镜像大小
- ✅ 使用 nginx 服务静态文件
- ✅ 启用 gzip 压缩
- ✅ 支持 React Router
- ✅ 静态资源缓存优化
- ✅ 健康检查

### 快速启动

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重新构建前端
docker-compose build frontend

# 仅启动前端
docker-compose up -d frontend
```

### 访问地址

- **前端**: http://localhost:3000
- **后端API**: http://localhost:5000
- **WebSocket**: ws://localhost:8765

### 环境变量配置

在 `docker-compose.yml` 中修改：

```yaml
frontend:
  build:
    args:
      - VITE_API_URL=http://your-api-url:5000
      - VITE_WS_URL=ws://your-ws-url:8765
```

### 健康检查

```bash
# 检查前端健康状态
curl http://localhost:3000/health

# 检查后端健康状态
curl http://localhost:5000/api/health
```

### 生产环境优化建议

1. **使用反向代理**
   ```nginx
   # 在外层nginx配置
   upstream qunkong_frontend {
       server localhost:3000;
   }
   
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://qunkong_frontend;
       }
   }
   ```

2. **配置HTTPS**
   - 使用Let's Encrypt获取免费SSL证书
   - 配置nginx SSL

3. **数据持久化**
   - 在docker-compose.yml中添加数据库volume

4. **日志管理**
   - 配置日志轮转
   - 使用日志收集工具（如ELK）

### 故障排查

```bash
# 查看容器状态
docker-compose ps

# 查看特定服务日志
docker-compose logs frontend
docker-compose logs backend

# 进入容器调试
docker-compose exec frontend sh
docker-compose exec backend bash

# 检查nginx配置
docker-compose exec frontend nginx -t
```

### 镜像大小优化

当前配置已经使用：
- ✅ Alpine Linux基础镜像
- ✅ 多阶段构建
- ✅ .dockerignore排除无关文件
- ✅ npm ci安装依赖

### 更新部署

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build

# 清理旧镜像
docker image prune -f
```


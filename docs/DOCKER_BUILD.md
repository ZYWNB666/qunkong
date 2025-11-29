# GitHub Actions Docker 镜像构建说明

## 配置 GitHub Secrets

在您的 GitHub 仓库中设置以下 Secrets（Settings → Secrets and variables → Actions → New repository secret）：

### 必需的 Secrets

1. **ALIYUN_USERNAME**: `youwei886`
2. **ALIYUN_PASSWORD**: `zhangyouwei886123`

### 可选的 Secrets

3. **VITE_API_URL**: 前端 API 地址（默认：`http://localhost:5000`）
4. **VITE_WS_URL**: WebSocket 地址（默认：`ws://localhost:8765`）

## 镜像命名规则

构建后的镜像会自动推送到阿里云镜像仓库：

### 镜像仓库
- **仓库地址**: `registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong`

### 标签规则
- **Backend 镜像**:
  - `backend-{时间戳}` - 带时间戳的版本（格式：YYYYMMDDHHmmss，精确到秒）
  - `backend-latest` - 最新版本

- **Frontend 镜像**:
  - `frontend-{时间戳}` - 带时间戳的版本（格式：YYYYMMDDHHmmss，精确到秒）
  - `frontend-latest` - 最新版本

### 示例
```
registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:backend-20251129053012
registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:backend-latest
registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:frontend-20251129053012
registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:frontend-latest
```

## 触发构建

以下操作会触发 Docker 镜像构建：

1. **推送代码到 main/master 分支**
   ```bash
   git push origin main
   ```

2. **创建版本标签**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. **手动触发**
   - 在 GitHub 仓库页面：Actions → Build and Push Docker Images → Run workflow

## 拉取镜像

构建完成后，可以使用以下命令拉取镜像：

```bash
# 登录阿里云镜像仓库
docker login --username=youwei886 --password=zhangyouwei886123 registry.cn-shanghai.aliyuncs.com

# 拉取最新版本
docker pull registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:backend-latest
docker pull registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:frontend-latest

# 拉取特定时间戳版本
docker pull registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:backend-20251129053012
docker pull registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:frontend-20251129053012
```

## 使用镜像部署

### 方式 1: 直接运行

```bash
# 运行 Backend
docker run -d \
  --name qunkong-backend \
  -p 5000:5000 \
  -p 8765:8765 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:backend-latest

# 运行 Frontend
docker run -d \
  --name qunkong-frontend \
  -p 3000:80 \
  registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:frontend-latest
```

### 方式 2: 使用 docker-compose

使用项目中的 `docker-compose.prod.yml` 文件：

```bash
# 登录阿里云
docker login --username=youwei886 --password=zhangyouwei886123 registry.cn-shanghai.aliyuncs.com

# 拉取最新镜像
docker-compose -f docker-compose.prod.yml pull

# 启动服务
docker-compose -f docker-compose.prod.yml up -d
```

## 查看构建状态

在 GitHub 仓库页面：Actions → Build and Push Docker Images

每次构建会显示：
- 构建状态（成功/失败）
- 构建时间
- 生成的镜像标签
- 构建日志

## 镜像平台

当前配置构建 `linux/amd64` 平台镜像。如需支持多平台（如 ARM），可以在工作流中修改 `platforms` 配置：

```yaml
platforms: linux/amd64,linux/arm64
```

## 构建缓存

工作流使用 GitHub Actions Cache 来加速构建：
- 首次构建较慢
- 后续构建会使用缓存，速度显著提升

## 常见问题

### 1. 构建失败：认证错误
检查 Secrets 中的用户名和密码是否正确。

### 2. 镜像推送失败
确保在阿里云容器镜像服务中已创建命名空间 `zywdockers/images`。

### 3. Frontend 镜像缺少文件
确保 Dockerfile.frontend 的 context 正确指向 `./web` 目录。


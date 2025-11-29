# 镜像构建配置总结

## ✅ 已完成配置

### 镜像仓库信息
- **仓库地址**: `registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong`
- **仓库类型**: 统一仓库，通过标签区分 Backend 和 Frontend

### 镜像标签命名规则

每次构建会生成两个标签：

**Backend**:
- `backend-{时间戳}` - 例如：`backend-20251129053012`（精确到秒）
- `backend-latest` - 最新版本

**Frontend**:
- `frontend-{时间戳}` - 例如：`frontend-20251129053012`（精确到秒）
- `frontend-latest` - 最新版本

### 完整镜像地址示例
```
registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:backend-20251129053012
registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:backend-latest
registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:frontend-20251129053012
registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:frontend-latest
```

---

## 🚀 构建触发方式

代码已推送到 GitHub，GitHub Actions 会自动构建镜像。

### 查看构建状态
访问：https://github.com/ZYWNB666/qunkong/actions

### 手动触发构建
1. 进入 Actions 页面
2. 选择 **Build and Push Docker Images**
3. 点击 **Run workflow** → **Run workflow**

---

## 📦 拉取和使用镜像

### 登录阿里云镜像仓库
```bash
docker login --username=youwei886 --password=zhangyouwei886123 registry.cn-shanghai.aliyuncs.com
```

### 拉取镜像
```bash
# 拉取最新版本
docker pull registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:backend-latest
docker pull registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:frontend-latest

# 拉取特定时间戳版本
docker pull registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:backend-20251129053012
docker pull registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong:frontend-20251129053012
```

### 使用 docker-compose 部署
```bash
# 拉取最新镜像
docker-compose -f docker-compose.prod.yml pull

# 启动服务（包含 MySQL、Backend、Frontend）
docker-compose -f docker-compose.prod.yml up -d

# 查看运行状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 📝 相关文件

- `.github/workflows/docker-build.yml` - GitHub Actions 工作流配置
- `docker-compose.prod.yml` - 生产环境部署配置
- `Dockerfile.backend` - Backend 镜像构建文件
- `Dockerfile.frontend` - Frontend 镜像构建文件
- `web/nginx.conf` - Frontend Nginx 配置
- `docs/DOCKER_BUILD.md` - 详细使用文档

---

## 🎯 优势

1. **统一仓库管理** - 所有镜像在一个仓库中，便于管理
2. **时间戳版本** - 精确到秒的时间戳，方便回溯和追���
3. **Latest 标签** - 始终可以拉取最新版本
4. **自动构建** - 推送代码即自动构建和推送镜像
5. **完整部署方案** - 提供 docker-compose 一键部署

---

构建完成后，可以在阿里云镜像仓库查看所有版本：
https://cr.console.aliyun.com/repository/cn-shanghai/zywdockers/qunkong/details


# GitHub Actions 构建错误修复说明

## 遇到的错误

### 1. Backend 推送失败
```
push access denied, repository does not exist or may require authorization
```

**原因**：阿里云镜像仓库中不存在对应的仓库

**解决方案**：需要在阿里云容器镜像服务中手动创建仓库

### 2. Frontend 构建失败
```
"/nginx.conf": not found
```

**原因**：nginx.conf 文件未提交到 Git 仓库

**解决方案**：提交 nginx.conf 文件

---

## 立即修复步骤

### 步骤 1：在阿里云创建镜像仓库

1. 登录阿里云控制台：https://cr.console.aliyun.com/
2. 选择 **上海** 区域
3. 进入 **个人实例** → **命名空间**
4. 如果没有 `zywdockers` 命名空间，创建一个
5. 进入 **镜像仓库** → **创建镜像仓库**
6. 创建两个仓库：
   - 仓库名称：`images/qunkong-backend`
   - 仓库名称：`images/qunkong-frontend`
   - 仓库类型：公开或私有（推荐私有）
   - 代码源：本地仓库

### 步骤 2：提交缺失的文件到 Git

在本地项目目录执行：

```bash
# 添加新创建的文件
git add .github/workflows/docker-build.yml
git add Dockerfile.frontend
git add web/nginx.conf
git add web/.dockerignore
git add docker-compose.prod.yml
git add docs/DOCKER_BUILD.md
git add docs/GITHUB_ACTIONS_FIX.md

# 提交更改
git commit -m "fix: 添加 nginx.conf 和修复 Docker 构建配置"

# 推送到 GitHub
git push origin main
```

### 步骤 3：重新触发 GitHub Actions

推送后会自动触发构建，或者手动触发：

1. 访问：https://github.com/ZYWNB666/qunkong/actions
2. 选择 **Build and Push Docker Images**
3. 点击 **Run workflow** → **Run workflow**

---

## 替代方案：修改镜像仓库路径

如果您的阿里云镜像仓库命名空间不是 `zywdockers/images`，需要修改工作流配置：

编辑 `.github/workflows/docker-build.yml`：

```yaml
env:
  REGISTRY: registry.cn-shanghai.aliyuncs.com
  NAMESPACE: 你的命名空间/你的仓库前缀  # 修改这里
  BACKEND_IMAGE: qunkong-backend
  FRONTEND_IMAGE: qunkong-frontend
```

例如，如果您的命名空间是 `youwei886`，仓库直接叫 `qunkong-backend`：

```yaml
env:
  REGISTRY: registry.cn-shanghai.aliyuncs.com
  NAMESPACE: youwei886  # 只写命名空间
  BACKEND_IMAGE: qunkong-backend
  FRONTEND_IMAGE: qunkong-frontend
```

---

## 验证修复

提交并推送后：

1. 查看 GitHub Actions 运行状态
2. 确认两个 Job 都显示绿色 ✓
3. 检查阿里云镜像仓库是否有新镜像

## 拉取镜像测试

```bash
# 登录
docker login --username=youwei886 --password=zhangyouwei886123 registry.cn-shanghai.aliyuncs.com

# 拉取镜像
docker pull registry.cn-shanghai.aliyuncs.com/zywdockers/images/qunkong-backend:latest
docker pull registry.cn-shanghai.aliyuncs.com/zywdockers/images/qunkong-frontend:latest
```

如果拉取成功，说明构建和推送都正常工作了！


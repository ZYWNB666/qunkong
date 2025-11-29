# Qunkong - 分布式运维管理平台

<div align="center">

一个轻量级、高效的分布式运维管理平台，支持远程脚本执行、Web终端、文件传输等功能。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18.2-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

</div>

## ✨ 主要特性

### 🚀 脚本执行
- 在线编辑器（Monaco Editor）支持语法高亮
- 支持Shell、Python等多种脚本语言
- 批量执行脚本到多个Agent
- 实时查看执行输出
- 支持脚本参数传递
- 执行超时控制

### 💻 Web终端（PTY模式）
- 基于xterm.js的全功能Web终端
- 真实PTY终端体验，完整支持交互式命令
- 支持sz/rz文件传输（ZMODEM协议）
- 多标签页管理，同时连接多个Agent
- 支持终端大小动态调整
- 支持256色显示
- 跨平台支持（Linux优先，Windows部分支持）

### 📊 任务编排
- 作业管理和调度
- 支持多步骤作业编排
- 主机组管理，批量执行
- 执行历史记录查询
- 支持任务状态追踪
- 任务结果详细展示
- 支持按项目隔离

### 🖥️ Agent管理
- Agent自动注册和心跳检测（每3秒自动刷新）
- 实时查看Agent状态（在线/离线）
- 实时系统资源监控（CPU、内存、磁盘、网络）
- 显示公网IP和内网IP
- 支持Linux系统（Windows实验性支持）
- WebSocket实时通信
- Agent远程重启功能
- 主机远程重启功能
- Agent在线更新功能

### 👥 多租户 & 项目隔离
- 租户管理（管理员功能）
- 项目级别的资源隔离
- 灵活的权限控制（管理员/读写/只读）
- 项目成员管理
- 跨项目资源共享控制
- 项目切换器，快速切换工作环境

### 🔐 用户管理
- 用户注册和登录（JWT认证）
- 角色权限管理（超级管理员/租户管理员/普通用户）
- 个人资料设置
- 密码修改
- 用户状态管理

### 🌐 集群模式（可选）
- 基于Redis的分布式架构
- 多节点负载均衡
- Agent跨节点访问
- 会话状态共享
- 自动故障转移

## 📦 技术栈

### 前端
- **框架**: React 18.2 + React Router 6
- **UI库**: Ant Design 5.8
- **构建工具**: Vite 4.4
- **编辑器**: Monaco Editor（VS Code同款）
- **终端**: @xterm/xterm 5.5
- **文件传输**: zmodem.js（sz/rz协议）
- **HTTP客户端**: Axios 1.5

### 后端
- **框架**: FastAPI 0.104+
- **ASGI服务器**: Uvicorn（支持Gunicorn多进程）
- **WebSocket**: websockets 11.0
- **数据库**: MySQL 8.0+（通过PyMySQL + DBUtils连接池）
- **认证**: JWT（PyJWT 2.8）
- **系统信息**: psutil 5.9
- **集群支持**: Redis 4.5+（可选）
- **数据验证**: Pydantic 2.0

### 部署
- **容器化**: Docker + docker-compose
- **镜像仓库**: 阿里云容器镜像服务
- **CI/CD**: GitHub Actions（自动构建镜像和Agent）
- **Web服务器**: nginx（前端静态文件服务）
- **多阶段构建**: 优化镜像大小
- **进程管理**: systemd（Agent服务）

## 🚀 快速开始

### 方式一：Docker部署（推荐）

#### 1. 克隆项目
```bash
git clone https://github.com/ZYWNB666/qunkong.git
cd qunkong
```

#### 2. 使用生产镜像部署
```bash
# 拉取最新镜像并启动服务（包含MySQL、Backend、Frontend）
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

#### 3. 访问系统
- **前端**: http://localhost （端口80）
- **后端API**: http://localhost:5000
- **API文档**: http://localhost:5000/api/docs

### 方式二：本地开发部署

#### 前置要求
- Python 3.8+
- Node.js 18+
- MySQL 8.0+

#### 1. 克隆项目
```bash
git clone https://github.com/ZYWNB666/qunkong.git
cd qunkong
```

#### 2. 配置数据库
```bash
# 复制数据库配置模板
cp config/database.conf.template config/database.conf

# 编辑配置文件
vim config/database.conf
```

配置文件示例：
```ini
[database]
host = localhost
port = 3306
user = qunkong
password = your_password
database = qunkong

[server]
api_port = 5000
websocket_port = 8765

[cluster]
enabled = false
node_id = 

[redis]
enabled = false
host = localhost
port = 6379
db = 0
password = 
max_connections = 10
```

#### 3. 初始化数据库
```bash
python scripts/init_database.py
```

#### 4. 启动后端
```bash
# 安装Python依赖
pip install -r requirements.txt

# 开发模式启动
python start_backend.py

# 或生产模式启动（Uvicorn）
python start_production.py --mode uvicorn --workers 1

# 或生产模式启动（Gunicorn，仅Linux/Mac）
python start_production.py --mode gunicorn --workers 4
```

#### 5. 启动前端
```bash
# 进入前端目录
cd web

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

### 部署Agent

#### 方式一：使用二进制文件（推荐）

从GitHub Releases下载预编译的Agent二进制文件（自动构建）：

```bash
# 下载Agent（以Linux为例）
wget https://github.com/ZYWNB666/qunkong/releases/latest/download/qunkong-agent

# 添加执行权限
chmod +x qunkong-agent

# 启动Agent
./qunkong-agent --server SERVER_IP --port 8765

# 详细日志模式
./qunkong-agent --server SERVER_IP --port 8765 --verbose

# 指定Agent ID
./qunkong-agent --server SERVER_IP --port 8765 --agent-id my-agent-001
```

#### 方式二：使用Python脚本

```bash
# 复制Agent客户端
scp app/client.py user@target-server:/opt/qunkong/

# 安装依赖
pip install -r requirements-client.txt

# 启动Agent
python3 client.py --server SERVER_IP --port 8765
```

#### 方式三：使用systemd服务（推荐生产环境）

```bash
# 使用部署脚本
cd deployment
sudo ./install-agent.sh

# 查看服务状态
sudo systemctl status qunkong-agent

# 启动服务
sudo systemctl start qunkong-agent

# 停止服务
sudo systemctl stop qunkong-agent

# 查看日志
sudo journalctl -u qunkong-agent -f
```

## 📖 使用指南

### 访问地址
- **前端**: http://localhost:3000（开发模式）或 http://localhost（生产模式）
- **后端API**: http://localhost:5000
- **API文档**: http://localhost:5000/api/docs（Swagger UI）
- **WebSocket**: ws://localhost:8765

### 默认账号
- **用户名**: admin
- **密码**: admin123

⚠️ 首次登录后建议立即修改密码！

### 使用流程

1. **登录系统** → 选择或创建项目
2. **部署Agent** → 在目标服务器上安装Agent
3. **管理Agent** → 查看Agent状态，确认在线（每3秒自动刷新）
4. **创建作业** → 配置主机组和执行步骤
5. **执行脚本** → 编写脚本并选择目标Agent执行
6. **Web终端** → 直接在浏览器中操作远程服务器
7. **文件传输** → 使用sz/rz命令上传下载文件
8. **查看历史** → 查看执行历史和结果详情

### sz/rz文件传输

在Web终端中：
```bash
# 下载文件到本地
sz filename

# 上传文件到服务器
rz
```

## 📁 项目结构

```
qunkong/
├── .github/
│   └── workflows/
│       ├── docker-build.yml         # Docker镜像自动构建
│       └── build-agent.yml          # Agent二进制自动打包
├── app/                             # 后端应用
│   ├── routers/                     # FastAPI路由
│   │   ├── auth.py                  # 认证路由
│   │   ├── agents.py                # Agent管理路由
│   │   ├── tasks.py                 # 任务管理路由
│   │   ├── simple_jobs.py           # 简单作业路由
│   │   ├── users.py                 # 用户管理路由
│   │   ├── projects.py              # 项目管理路由
│   │   └── tenants.py               # 租户管理路由
│   ├── models/                      # 数据模型
│   │   ├── __init__.py              # 数据库管理器
│   │   ├── auth.py                  # 认证模型
│   │   ├── simple_jobs.py           # 作业模型
│   │   ├── project.py               # 项目模型
│   │   └── tenant.py                # 租户模型
│   ├── middleware/                  # 中间件
│   ├── client.py                    # Agent客户端
│   ├── server_core.py               # WebSocket服务核心
│   ├── cluster.py                   # 集群管理
│   ├── cache.py                     # 缓存管理
│   ├── main.py                      # FastAPI应用入口
│   └── fastapi_app.py               # FastAPI应用工厂
├── web/                             # 前端源码
│   ├── src/
│   │   ├── pages/                   # 页面组件
│   │   │   ├── AgentManagement.jsx      # Agent管理
│   │   │   ├── ScriptExecution.jsx      # 脚本执行
│   │   │   ├── ExecutionHistory.jsx     # 执行历史
│   │   │   ├── Terminal.jsx             # Web终端
│   │   │   ├── SimpleJobs.jsx           # 作业管理
│   │   │   ├── ProjectManagement.jsx    # 项目管理
│   │   │   ├── UserManagement.jsx       # 用户管理
│   │   │   ├── TenantManagement.jsx     # 租户管理
│   │   │   ├── UserProfile.jsx          # 个人设置
│   │   │   ├── Login.jsx                # 登录页面
│   │   │   └── ProjectSelector.jsx      # 项目选择器
│   │   ├── utils/                   # 工具函数
│   │   │   └── api.js               # API封装
│   │   ├── App.jsx                  # 应用入口
│   │   └── main.jsx                 # React入口
│   ├── nginx.conf                   # Nginx配置
│   ├── package.json                 # 前端依赖
│   └── vite.config.js               # Vite配置
├── config/                          # 配置文件
│   ├── database.conf.template       # 数据库配置模板
│   └── database.conf                # 数据库配置（需创建）
├── scripts/                         # 数据库脚本
│   ├── init_database.py             # 数据库初始化
│   ├── init_complete.sql            # 完整SQL脚本
│   └── optimize_indexes.sql         # 索引优化脚本
├── deployment/                      # 部署脚本
│   ├── install-agent.sh             # Agent安装脚本
│   ├── uninstall-agent.sh           # Agent卸载脚本
│   └── qunkong-agent.service        # systemd服务文件
├── test/                            # 测试和工具
│   ├── build_client.py              # Agent打包脚本
│   └── requirements-build.txt       # 打包依赖
├── docs/                            # 文档
│   ├── DOCKER_BUILD.md              # Docker构建文档
│   ├── IMAGE_BUILD_SUMMARY.md       # 镜像构建总结
│   └── SQL_OPTIMIZATION.md          # SQL优化文档
├── releases/                        # Agent发布目录
│   ├── qunkong-agent-latest         # 最新Agent二进制
│   └── README.md                    # 发布说明
├── docker-compose.yml               # Docker编排（开发）
├── docker-compose.prod.yml          # Docker编排（生产）
├── Dockerfile.frontend              # 前端镜像
├── Dockerfile.backend               # 后端镜像
├── start_backend.py                 # 后端启动脚本
├── start_production.py              # 生产环境启动脚本
├── requirements.txt                 # Python依赖
└── requirements-client.txt          # Agent依赖
```

## 🔧 配置说明

### 环境变量

**前端**（构建时）:
```bash
VITE_API_URL=http://localhost:5000
VITE_WS_URL=ws://localhost:8765
```

**后端**:
```bash
# 数据库配置文件路径
DATABASE_CONFIG=./config/database.conf
```

### Agent配置

使用命令行参数启动Agent：
```bash
# 基本启动
./qunkong-agent --server SERVER_IP --port 8765

# 详细日志
./qunkong-agent --server SERVER_IP --port 8765 --verbose

# 指定Agent ID
./qunkong-agent --server SERVER_IP --port 8765 --agent-id my-agent-001

# 指定日志级别
./qunkong-agent --server SERVER_IP --port 8765 --log-level DEBUG
```

## 📊 系统要求

### 服务器端
- CPU: 2核+
- 内存: 2GB+
- 磁盘: 10GB+
- 系统: Linux/Windows/macOS
- Docker: 20.10+（如使用Docker部署）

### Agent节点
- CPU: 1核+
- 内存: 512MB+
- 系统: Linux（推荐Ubuntu 20.04+/CentOS 7+）
- Python: 3.8+（如使用Python脚本方式）

## 🐳 Docker镜像

### 镜像仓库
- **地址**: `registry.cn-shanghai.aliyuncs.com/zywdockers/qunkong`
- **标签规则**:
  - `backend-latest` - Backend最新版本
  - `backend-{时间戳}` - Backend带时间戳版本（精确到秒）
  - `frontend-latest` - Frontend最新版本
  - `frontend-{时间戳}` - Frontend带时间戳版本（精确到秒）

### 自动构建
每次代码推送到main分支，GitHub Actions会自动构建并推送镜像到阿里云。

详细说明请查看：[docs/IMAGE_BUILD_SUMMARY.md](docs/IMAGE_BUILD_SUMMARY.md)

## 🔒 安全建议

1. **修改默认密码**：首次登录后立即修改admin密码
2. **修改默认端口**：避免使用默认的5000和8765端口
3. **启用HTTPS**：生产环境必须使用SSL/TLS
4. **数据库安全**：使用强密码，限制远程访问
5. **防火墙配置**：只开放必要端口（80/443/5000/8765）
6. **JWT密钥**：修改为复杂的随机字符串
7. **定期更新**：及时更新依赖包版本
8. **Agent认证**：使用Agent ID验证机制

## 🐛 故障排查

### Agent无法连接
```bash
# 检查网络连通性
telnet server-ip 8765

# 查看Agent日志
journalctl -u qunkong-agent -f

# 检查防火墙
sudo firewall-cmd --list-all  # CentOS/RHEL
sudo ufw status                # Ubuntu
```

### 终端无法打开
- 检查WebSocket连接状态（浏览器开发者工具 → Network → WS）
- 确认Agent在线（Agent管理页面）
- 查看浏览器控制台错误信息
- 确认服务器防火墙已开放8765端口

### 文件传输失败
- 确认服务器已安装lrzsz：
  ```bash
  # CentOS/RHEL
  yum install lrzsz
  
  # Ubuntu/Debian
  apt-get install lrzsz
  ```
- 检查网络稳定性
- 查看浏览器控制台日志
- 确认文件大小（建议单个文件<100MB）

### 数据库连接失败
- 检查MySQL服务状态
- 确认database.conf配置正确
- 检查数据库用户权限
- 查看后端日志

## 📝 开发指南

### 本地开发

```bash
# 后端开发（带热重载）
python start_backend.py

# 前端开发
cd web
npm run dev
```

### API文档

启动后端服务后访问：
- Swagger UI: http://localhost:5000/api/docs
- ReDoc: http://localhost:5000/api/redoc
- OpenAPI JSON: http://localhost:5000/api/openapi.json

### 代码规范
- Python: PEP 8
- JavaScript: ESLint + Prettier
- 提交信息: 遵循 Conventional Commits 规范

### Agent打包

#### 自动构建（推荐）

每次 `app/client.py` 文件更新时，GitHub Actions 会自动构建Linux平台的Agent二进制文件并发布到Releases。

从 [Releases](https://github.com/ZYWNB666/qunkong/releases) 页面下载最新版本。

#### 手动打包

使用PyInstaller打包Agent为独立可执行文件：

```bash
# 安装打包依赖
pip install -r test/requirements-build.txt

# 执行打包脚本
python test/build_client.py

# 打包后的文件位于
dist/qunkong-agent
```

打包后的二进制文件大小约 15-20MB，包含所有依赖，无需安装Python环境即可运行。

## 🤝 贡献

欢迎提交Issue和Pull Request！

贡献指南：
1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交Pull Request

## 📄 License

[MIT License](LICENSE)

## 💬 联系方式

- Issue: [GitHub Issues](https://github.com/ZYWNB666/qunkong/issues)
- Repository: https://github.com/ZYWNB666/qunkong

---

<div align="center">

Made with ❤️ by Qunkong Team

**Star ⭐ this repository if you find it helpful!**

</div>


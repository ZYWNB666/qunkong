# Qunkong - 分布式运维管理平台

<div align="center">

![Qunkong](./public/logo.svg)

一个轻量级、高效的分布式运维管理平台，支持远程脚本执行、Web终端、文件传输等功能。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18.2-blue.svg)](https://reactjs.org/)

</div>

## ✨ 主要特性

### 🚀 脚本执行
- 在线编辑器（Monaco Editor）支持语法高亮
- 支持Shell、Python等多种脚本语言
- 批量执行脚本到多个Agent
- 实时查看执行输出

### 💻 Web终端
- 基于xterm.js的全功能Web终端
- 支持sz/rz文件传输（ZMODEM协议）
- 多标签页管理，同时连接多个Agent
- 支持终端大小调整

### 📊 任务编排
- 作业管理和调度
- 执行历史记录查询
- 支持任务状态追踪

### 🖥️ Agent管理
- Agent自动注册和心跳检测
- 实时查看Agent状态（在线/离线）
- 支持Linux系统（可扩展其他平台）
- WebSocket实时通信

### 👥 多租户 & 项目隔离
- 租户管理（管理员功能）
- 项目级别的资源隔离
- 灵活的权限控制（管理员/读写/只读）
- 项目成员管理

### 🔐 用户管理
- 用户注册和登录（JWT认证）
- 角色权限管理
- 个人资料设置
- 密码修改

## 📦 技术栈

### 前端
- **框架**: React 18.2 + React Router 6
- **UI库**: Ant Design 5.8
- **构建工具**: Vite 4.4
- **编辑器**: Monaco Editor（VS Code同款）
- **终端**: xterm.js 5.5
- **文件传输**: zmodem.js（sz/rz协议）

### 后端
- **框架**: Flask 2.3
- **WebSocket**: websockets 11.0
- **数据库**: MySQL（通过PyMySQL）
- **认证**: JWT（PyJWT 2.8）
- **系统信息**: psutil 5.9

### 部署
- **容器化**: Docker + docker-compose
- **Web服务器**: nginx（生产环境）
- **多阶段构建**: 优化镜像大小（~50MB）

## 🚀 快速开始

### 前置要求
- Docker & Docker Compose
- MySQL 5.7+（或使用Docker部署）

### 1. 克隆项目
```bash
git clone https://github.com/your-org/qunkong.git
cd qunkong
```

### 2. 配置数据库
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
```

### 3. 初始化数据库
```bash
python scripts/init_database.py
```

### 4. Docker部署（推荐）
```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看日志
docker-compose logs -f
```

### 5. 手动部署

#### 后端
```bash
# 安装Python依赖
pip install -r requirements.txt

# 启动后端服务
python start_backend.py
```

#### 前端
```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

### 6. 部署Agent

在目标服务器上：

```bash
# 复制Agent客户端
scp app/client.py user@target-server:/opt/qunkong/

# 安装依赖
pip install -r requirements-client.txt

# 使用systemd服务（推荐）
cd deployment
sudo ./install-agent.sh

# 或手动启动
python3 client.py
```

## 📖 使用指南

### 访问地址
- **前端**: http://localhost:3000
- **后端API**: http://localhost:5000
- **WebSocket**: ws://localhost:8765

### 默认账号
首次运行后，通过界面注册管理员账号。

### 使用流程

1. **登录系统** → 创建或选择项目
2. **部署Agent** → 在目标服务器上安装Agent
3. **管理Agent** → 查看Agent状态，确认在线
4. **执行脚本** → 编写脚本并选择目标Agent执行
5. **Web终端** → 直接在浏览器中操作远程服务器
6. **文件传输** → 使用sz/rz命令上传下载文件

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
├── app/                      # 后端应用
│   ├── api/                  # API路由
│   │   ├── auth.py          # 认证API
│   │   ├── routes.py        # Agent管理API
│   │   ├── jobs.py          # 作业管理API
│   │   ├── projects.py      # 项目管理API
│   │   ├── tenants.py       # 租户管理API
│   │   └── users.py         # 用户管理API
│   ├── models/              # 数据模型
│   ├── client.py            # Agent客户端
│   ├── server_core.py       # WebSocket服务核心
│   └── main.py              # Flask应用入口
├── src/                      # 前端源码
│   ├── pages/               # 页面组件
│   │   ├── AgentManagement.jsx      # Agent管理
│   │   ├── ScriptExecution.jsx      # 脚本执行
│   │   ├── ExecutionHistory.jsx     # 执行历史
│   │   ├── Terminal.jsx             # Web终端
│   │   ├── SimpleJobs.jsx           # 作业管理
│   │   ├── ProjectManagement.jsx    # 项目管理
│   │   ├── UserManagement.jsx       # 用户管理
│   │   ├── TenantManagement.jsx     # 租户管理
│   │   └── UserProfile.jsx          # 个人设置
│   ├── utils/               # 工具函数
│   └── App.jsx              # 应用入口
├── config/                   # 配置文件
├── scripts/                  # 数据库脚本
├── deployment/              # 部署脚本
├── docker-compose.yml       # Docker编排
├── Dockerfile.frontend      # 前端镜像
├── Dockerfile.backend       # 后端镜像
└── nginx.conf               # Nginx配置
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
FLASK_ENV=production
DATABASE_CONFIG=./config/database.conf
```

### Agent配置

编辑 `client.py` 中的服务器地址：
```python
SERVER_URL = "ws://your-server:8765"
```

## 📊 系统要求

### 服务器端
- CPU: 2核+
- 内存: 2GB+
- 磁盘: 10GB+
- 系统: Linux/Windows/macOS

### Agent节点
- CPU: 1核+
- 内存: 512MB+
- 系统: Linux（推荐Ubuntu/CentOS）

## 🔒 安全建议

1. **修改默认端口**：避免使用默认的5000和8765端口
2. **启用HTTPS**：生产环境必须使用SSL/TLS
3. **数据库安全**：使用强密码，限制远程访问
4. **防火墙配置**：只开放必要端口
5. **JWT密钥**：修改为复杂的随机字符串
6. **定期更新**：及时更新依赖包版本

## 🐛 故障排查

### Agent无法连接
```bash
# 检查网络连通性
telnet server-ip 8765

# 查看Agent日志
journalctl -u qunkong-agent -f

# 检查防火墙
sudo firewall-cmd --list-all
```

### 终端无法打开
- 检查WebSocket连接状态
- 确认Agent在线
- 查看浏览器控制台错误信息

### 文件传输失败
- 确认服务器已安装lrzsz：`yum install lrzsz` 或 `apt-get install lrzsz`
- 检查网络稳定性
- 查看浏览器控制台日志

## 📝 开发指南

### 本地开发

```bash
# 后端开发
cd app
python main.py

# 前端开发
npm run dev
```

### 代码规范
- Python: PEP 8
- JavaScript: ESLint + Prettier（推荐）
- 提交信息: 使用有意义的commit message

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 License

[MIT License](LICENSE)

## 💬 联系方式

- Issue: [GitHub Issues](https://github.com/your-org/qunkong/issues)
- Email: your-email@example.com

---

<div align="center">
Made with ❤️ by Qunkong Team
</div>


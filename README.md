# QueenBee 分布式脚本执行系统

一个基于 WebSocket 的分布式脚本执行系统，支持多主机批量脚本执行和实时监控。

## 快速开始

### 1. 环境要求

- Python 3.7+
- MySQL 5.7+ 或 8.0+
- Node.js 16+ (前端开发)

### 2. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装前端依赖（开发时需要）
npm install
```

### 3. 配置数据库

```bash
# 复制配置模板
cp config/database.conf.template config/database.conf

# 编辑配置文件，填写数据库连接信息
vim config/database.conf

# 初始化数据库
python scripts/init_database.py
```

### 4. 启动服务

```bash
# 启动后端服务（包含Web界面）
python start_backend.py
```

服务启动后：
- Web界面: http://localhost:5000
- WebSocket服务: ws://localhost:8765

### 5. 部署Agent

在需要执行脚本的目标主机上运行：

```bash
# 启动Agent客户端
python app/client.py --server <服务器IP> --port 8765
```

## 功能特性

- 🚀 **分布式执行**: 支持多主机并发脚本执行
- 📊 **实时监控**: WebSocket实时状态更新
- 🔄 **自动重连**: Agent断线自动重连机制
- 📝 **执行历史**: 完整的执行记录和结果查看
- 🔧 **Agent管理**: 主机状态监控和远程重启
- 🎯 **批量操作**: 支持多主机批量脚本执行
- 🔒 **安全可靠**: MySQL数据持久化存储

## 项目结构

```
├── app/                    # 后端应用
│   ├── main.py            # 主服务入口
│   ├── server_core.py     # WebSocket服务核心
│   ├── client.py          # Agent客户端
│   ├── models/            # 数据库模型
│   └── api/               # REST API
├── src/                   # 前端源码
│   ├── views/             # 页面组件
│   └── api/               # API接口
├── config/                # 配置文件
├── scripts/               # 工具脚本
└── docs/                  # 文档
```

## 详细文档

- [数据库配置指南](docs/DATABASE_SETUP.md)
- [项目总结](PROJECT_SUMMARY.md)
- [快速开始](QUICKSTART.md)
- [使用说明](USAGE.md)

## 许可证

MIT License
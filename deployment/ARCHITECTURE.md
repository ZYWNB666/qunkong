# Qunkong Agent Systemd 管理架构

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      管理界面 (Web UI)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │Agent管理 │  │脚本执行  │  │执行历史  │  │终端管理  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP/WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Qunkong Server                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │API服务   │  │WebSocket │  │任务管理  │  │数据库    │    │
│  │ (Flask)  │  │  (WS)    │  │ (Tasks)  │  │(MySQL)   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ WebSocket 连接
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Agent 节点（多台）                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  systemd (qunkong-agent.service)                      │  │
│  │    ├─ 自动启动                                         │  │
│  │    ├─ 失败重启                                         │  │
│  │    ├─ 日志管理                                         │  │
│  │    └─ 资源限制                                         │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                 │
│                            ▼                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  qunkong-agent (二进制程序)                            │  │
│  │    ├─ 心跳保活                                         │  │
│  │    ├─ 任务执行                                         │  │
│  │    ├─ 终端管理                                         │  │
│  │    └─ 自动更新                                         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. Systemd 服务管理

**服务文件**：`/etc/systemd/system/qunkong-agent.service`

**功能**：
- 自动启动：系统启动时自动运行 Agent
- 失败重启：Agent 崩溃后自动重启（RestartSec=10）
- 日志管理：统一输出到 journald
- 资源限制：CPU、内存、文件句柄限制

**优势**：
- ✅ 可靠性高：systemd 保证进程存活
- ✅ 日志统一：journalctl 查看所有日志
- ✅ 易于管理：标准 systemctl 命令
- ✅ 开机自启：无需额外配置

### 2. Agent 二进制文件

**位置**：`/opt/qunkong-agent/qunkong-agent`

**打包方式**：PyInstaller 打包为单文件可执行程序

**功能模块**：

1. **WebSocket 客户端**
   - 连接到 Qunkong Server
   - 心跳保活（5秒一次）
   - 自动重连（断线重连）

2. **任务执行引擎**
   - 接收执行任务
   - Shell/Python 脚本执行
   - 结果实时上报

3. **PTY 终端管理**
   - 完整的终端模拟
   - 支持交互式命令
   - 多会话管理

4. **自动更新模块**
   - 下载新版本
   - 备份旧版本
   - 原子替换
   - 自动重启

### 3. 更新机制

**流程**：

```
1. Web UI 发起更新请求
   ├─ 指定版本号
   └─ 提供下载 URL

2. Server 转发更新命令
   └─ 通过 WebSocket 发送到 Agent

3. Agent 执行更新
   ├─ 下载新版本文件
   ├─ 验证文件完整性
   ├─ 备份当前版本 (.backup)
   ├─ 替换可执行文件
   └─ 写入版本信息 (version.txt)

4. Agent 退出
   └─ systemd 检测到进程退出

5. Systemd 自动重启
   ├─ 使用新版本启动
   └─ Agent 重新连接到 Server

6. 更新完成
   └─ Web UI 显示更新结果
```

**安全机制**：

- 🔒 备份旧版本：更新前自动备份
- 🔒 原子替换：使用 `mv` 原子操作
- 🔒 权限检查：确保文件权限正确
- 🔒 失败恢复：更新失败可回滚

## 部署流程

### 开发阶段

```bash
# 1. 开发 Agent 代码
app/client.py

# 2. 本地测试
python3 app/client.py --server localhost --port 8765
```

### 打包阶段

```bash
# 3. 打包为二进制文件
cd deployment
./build-agent.sh

# 输出：deployment/dist/qunkong-agent
```

### 部署阶段

```bash
# 4. 上传到目标机器
scp dist/qunkong-agent install-agent.sh root@目标机器:/tmp/

# 5. 安装为 systemd 服务
ssh root@目标机器
cd /tmp
./install-agent.sh --server 服务器IP --port 8765 --binary-path ./qunkong-agent

# 6. 验证部署
systemctl status qunkong-agent
```

### 更新阶段

```bash
# 7. 打包新版本
./build-agent.sh

# 8. 上传到 Web 服务器
cp dist/qunkong-agent /var/www/html/downloads/

# 9. 在 Web UI 批量更新
# 选择 Agent → 批量管理 → 更新版本
# 填写版本号和 URL → 执行
```

## 通信协议

### WebSocket 消息格式

#### Agent → Server

**注册消息**：
```json
{
  "type": "register",
  "agent_id": "abc123...",
  "hostname": "server01",
  "ip": "192.168.1.101",
  "external_ip": "1.2.3.4",
  "platform": "Linux",
  "system_info": { ... }
}
```

**心跳消息**：
```json
{
  "type": "heartbeat",
  "agent_id": "abc123...",
  "timestamp": "2025-10-09T10:00:00"
}
```

**任务结果**：
```json
{
  "type": "task_result",
  "task_id": "task123",
  "agent_id": "abc123...",
  "result": {
    "exit_code": 0,
    "stdout": "...",
    "stderr": "...",
    "execution_time": 1.23
  }
}
```

#### Server → Agent

**执行任务**：
```json
{
  "type": "execute_task",
  "task_id": "task123",
  "script": "#!/bin/bash\necho 'Hello'",
  "script_params": "",
  "timeout": 7200
}
```

**重启 Agent**：
```json
{
  "type": "restart_agent"
}
```

**更新 Agent**：
```json
{
  "type": "update_agent",
  "version": "v1.0.2",
  "download_url": "http://server/qunkong-agent"
}
```

**更新响应**：
```json
{
  "type": "update_agent_response",
  "agent_id": "abc123...",
  "status": "success|downloading|installing|failed",
  "version": "v1.0.2",
  "message": "更新成功"
}
```

## 目录结构

```
qunkong/
├── app/
│   ├── client.py              # Agent 源代码
│   ├── server_core.py         # Server 核心
│   └── api/
│       └── routes.py          # API 路由
├── deployment/
│   ├── README.md              # 详细文档
│   ├── QUICKSTART.md          # 快速开始
│   ├── ARCHITECTURE.md        # 本文档
│   ├── qunkong-agent.service  # systemd 模板
│   ├── build-agent.sh         # 打包脚本
│   ├── install-agent.sh       # 安装脚本
│   └── uninstall-agent.sh     # 卸载脚本
└── src/
    └── views/
        └── AgentManagement.vue # Agent 管理界面
```

## 安装后的目录结构

```
/opt/qunkong-agent/
├── qunkong-agent           # 主程序
├── qunkong-agent.backup    # 备份文件（更新后生成）
└── version.txt             # 版本信息

/etc/systemd/system/
└── qunkong-agent.service   # systemd 服务文件

/var/log/journal/
└── ...                     # systemd 日志
```

## 日志管理

### 查看日志

```bash
# 实时日志
sudo journalctl -u qunkong-agent -f

# 最近 100 条
sudo journalctl -u qunkong-agent -n 100

# 指定时间范围
sudo journalctl -u qunkong-agent --since "2025-10-09 10:00:00" --until "2025-10-09 11:00:00"

# 导出日志
sudo journalctl -u qunkong-agent > agent.log
```

### 日志级别

- **INFO**：正常运行日志
- **DEBUG**：详细调试信息（使用 `-v` 参数启用）
- **WARNING**：警告信息
- **ERROR**：错误信息

## 性能优化

### 资源限制

编辑 `/etc/systemd/system/qunkong-agent.service`：

```ini
[Service]
# 限制内存（512MB）
MemoryLimit=512M

# 限制CPU（50%）
CPUQuota=50%

# 限制文件句柄
LimitNOFILE=65536
```

### 心跳优化

默认 5 秒一次心跳，可以根据网络情况调整：

```python
# app/client.py 第 1195 行
await asyncio.sleep(5)  # 心跳间隔
```

## 安全考虑

### 1. 网络安全

- ✅ 使用内网传输
- ✅ 配置防火墙规则
- ✅ 限制 WebSocket 端口访问

### 2. 文件安全

- ✅ 下载文件权限检查
- ✅ 可执行文件签名验证（可选）
- ✅ HTTPS 传输（生产环境）

### 3. 权限控制

- ✅ 管理界面身份验证
- ✅ 操作权限控制
- ✅ 审计日志记录

## 故障恢复

### Agent 崩溃

- systemd 自动重启（RestartSec=10）
- 最多重启次数：无限制
- 重启间隔：10 秒

### 更新失败

```bash
# 恢复备份版本
cd /opt/qunkong-agent
sudo mv qunkong-agent.backup qunkong-agent
sudo systemctl restart qunkong-agent
```

### 网络断开

- Agent 自动重连
- 重连间隔：指数退避（5s → 10s → 20s → ... → 60s）
- 最大重试次数：10 次

## 监控指标

### 系统指标

- Agent 在线数量
- CPU 使用率
- 内存使用率
- 磁盘使用率

### 业务指标

- 任务执行成功率
- 任务执行时长
- 更新成功率
- 心跳延迟

## 扩展性

### 水平扩展

- ✅ 无状态设计
- ✅ 支持多 Server 负载均衡
- ✅ Agent 数量无限制

### 功能扩展

- 插件系统（待实现）
- 自定义命令（待实现）
- 监控集成（待实现）

---

**架构版本**：v1.0.0  
**更新日期**：2025-10-09


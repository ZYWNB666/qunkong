# Qunkong Agent Systemd 部署指南

本指南详细说明如何将 Qunkong Agent 部署为 systemd 服务，以及如何实现远程批量更新。

## 目录结构

```
deployment/
├── README.md                   # 本文档
├── qunkong-agent.service       # systemd 服务模板
├── install-agent.sh            # 安装脚本
├── uninstall-agent.sh          # 卸载脚本
└── build-agent.sh              # 打包脚本（生成二进制文件）
```

## 前置要求

- Linux 系统（支持 systemd）
- root 权限
- Python 3.8+（用于打包）
- PyInstaller（用于打包）

## 第一步：打包 Agent 为二进制文件

### 安装打包工具

```bash
pip install pyinstaller
```

### 使用打包脚本

```bash
cd deployment
chmod +x build-agent.sh
./build-agent.sh
```

打包完成后，会在 `deployment/dist/` 目录下生成 `qunkong-agent` 二进制文件。

### 手动打包（可选）

如果不使用打包脚本，可以手动执行：

```bash
cd app
pyinstaller --onefile \
    --name qunkong-agent \
    --add-data "client.py:." \
    client.py
```

## 第二步：部署 Agent

### 方法一：使用安装脚本（推荐）

```bash
# 基本用法
sudo ./install-agent.sh --server <服务器地址> --port <端口>

# 示例
sudo ./install-agent.sh --server 192.168.1.100 --port 8765

# 指定二进制文件路径
sudo ./install-agent.sh --server 192.168.1.100 --port 8765 --binary-path ./dist/qunkong-agent

# 自定义安装目录
sudo ./install-agent.sh --server 192.168.1.100 --port 8765 --install-dir /usr/local/qunkong-agent
```

安装脚本会自动完成以下操作：

1. 创建安装目录（默认：`/opt/qunkong-agent`）
2. 复制二进制文件
3. 创建 systemd 服务文件
4. 启动并启用服务

### 方法二：手动部署

#### 1. 创建安装目录

```bash
sudo mkdir -p /opt/qunkong-agent
```

#### 2. 复制二进制文件

```bash
sudo cp dist/qunkong-agent /opt/qunkong-agent/
sudo chmod +x /opt/qunkong-agent/qunkong-agent
```

#### 3. 创建 systemd 服务文件

```bash
sudo nano /etc/systemd/system/qunkong-agent.service
```

内容如下（替换 SERVER_HOST 和 SERVER_PORT）：

```ini
[Unit]
Description=Qunkong Agent - Distributed Script Execution System
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/qunkong-agent
ExecStart=/opt/qunkong-agent/qunkong-agent --server <SERVER_HOST> --port <SERVER_PORT>
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# 环境变量
Environment="PATH=/usr/local/bin:/usr/bin:/bin"

# 资源限制
LimitNOFILE=65536

# 安全设置
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

#### 4. 启动服务

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 启用服务（开机自启）
sudo systemctl enable qunkong-agent

# 启动服务
sudo systemctl start qunkong-agent

# 查看状态
sudo systemctl status qunkong-agent
```

## 第三步：管理服务

### 常用命令

```bash
# 查看服务状态
sudo systemctl status qunkong-agent

# 启动服务
sudo systemctl start qunkong-agent

# 停止服务
sudo systemctl stop qunkong-agent

# 重启服务
sudo systemctl restart qunkong-agent

# 查看日志（实时）
sudo journalctl -u qunkong-agent -f

# 查看最近的日志
sudo journalctl -u qunkong-agent -n 100

# 禁用服务（取消开机自启）
sudo systemctl disable qunkong-agent

# 启用服务（开机自启）
sudo systemctl enable qunkong-agent
```

## 第四步：远程批量更新

### 准备更新文件

1. **打包新版本**

```bash
./build-agent.sh
```

2. **上传到 Web 服务器**

将 `dist/qunkong-agent` 上传到一个可访问的 HTTP/HTTPS 服务器，例如：

```bash
# 使用 Nginx
sudo cp dist/qunkong-agent /var/www/html/downloads/

# 或使用 Python 简单 HTTP 服务器（测试用）
cd dist
python3 -m http.server 8000
```

### 在 Web UI 中批量更新

1. 登录 Qunkong 管理界面
2. 进入 "Agent 管理" 页面
3. 选择要更新的 Agent（可以多选）
4. 点击 "批量管理" 按钮
5. 选择 "更新版本"
6. 填写信息：
   - **目标版本**：例如 `v1.0.2`
   - **下载URL**：例如 `http://192.168.1.100:8000/qunkong-agent`
7. 点击 "执行"

### 更新流程说明

1. 服务器向选中的 Agent 发送更新命令
2. Agent 从指定 URL 下载新版本
3. Agent 备份当前版本到 `.backup` 文件
4. Agent 替换可执行文件
5. Agent 自动重启（由 systemd 管理）
6. Agent 重新连接到服务器

### 更新失败恢复

如果更新失败，可以手动恢复备份：

```bash
cd /opt/qunkong-agent
sudo mv qunkong-agent.backup qunkong-agent
sudo systemctl restart qunkong-agent
```

## 卸载服务

使用卸载脚本：

```bash
sudo ./uninstall-agent.sh
```

或手动卸载：

```bash
# 停止服务
sudo systemctl stop qunkong-agent

# 禁用服务
sudo systemctl disable qunkong-agent

# 删除服务文件
sudo rm /etc/systemd/system/qunkong-agent.service

# 重新加载 systemd
sudo systemctl daemon-reload

# 删除安装目录（可选）
sudo rm -rf /opt/qunkong-agent
```

## 批量部署脚本示例

如果需要在多台机器上部署，可以使用以下脚本：

```bash
#!/bin/bash
# batch-deploy.sh

# 配置
SERVER_HOST="192.168.1.100"
SERVER_PORT="8765"
AGENT_HOSTS=(
    "192.168.1.101"
    "192.168.1.102"
    "192.168.1.103"
)

# 部署到每台机器
for host in "${AGENT_HOSTS[@]}"; do
    echo "部署到 $host ..."
    
    # 复制文件
    scp install-agent.sh dist/qunkong-agent root@$host:/tmp/
    
    # 远程执行安装
    ssh root@$host "cd /tmp && ./install-agent.sh --server $SERVER_HOST --port $SERVER_PORT --binary-path ./qunkong-agent"
    
    echo "完成：$host"
    echo ""
done

echo "批量部署完成！"
```

## 故障排查

### Agent 无法启动

```bash
# 查看详细日志
sudo journalctl -u qunkong-agent -n 100 --no-pager

# 检查文件权限
ls -l /opt/qunkong-agent/qunkong-agent

# 手动运行（测试）
sudo /opt/qunkong-agent/qunkong-agent --server <服务器> --port <端口>
```

### Agent 无法连接服务器

1. 检查服务器地址和端口是否正确
2. 检查防火墙规则
3. 检查网络连接
4. 查看服务器日志

### 更新失败

1. 检查下载 URL 是否可访问
2. 检查磁盘空间
3. 检查文件权限
4. 查看 Agent 日志：`sudo journalctl -u qunkong-agent -f`

## 安全建议

1. **限制下载 URL**：建议使用内网地址或配置访问控制
2. **使用 HTTPS**：生产环境建议使用 HTTPS 传输文件
3. **文件校验**：可以添加 MD5/SHA256 校验功能
4. **权限控制**：确保只有授权用户能执行更新操作
5. **备份策略**：定期备份 Agent 配置和版本

## 高级配置

### 自定义日志级别

编辑服务文件，添加 `-v` 参数启用详细日志：

```ini
ExecStart=/opt/qunkong-agent/qunkong-agent --server <SERVER> --port <PORT> -v
```

### 设置资源限制

编辑服务文件，添加资源限制：

```ini
# 限制内存使用（512MB）
MemoryLimit=512M

# 限制CPU使用（50%）
CPUQuota=50%
```

### 配置日志保留

```bash
# 编辑 journald 配置
sudo nano /etc/systemd/journald.conf

# 设置日志保留时间
SystemMaxUse=500M
MaxRetentionSec=1month
```

然后重启 journald：

```bash
sudo systemctl restart systemd-journald
```

## 支持

如有问题，请查看：

- 项目文档
- GitHub Issues
- 服务器日志：`sudo journalctl -u qunkong-agent -f`

---

**版本**：v1.0.0  
**更新日期**：2025-10-09


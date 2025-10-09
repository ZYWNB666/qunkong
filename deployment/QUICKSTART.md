# Qunkong Agent 快速开始

## 快速部署（5分钟）

### 1. 打包 Agent

```bash
cd deployment
chmod +x build-agent.sh
./build-agent.sh
```

生成的二进制文件位于：`deployment/dist/qunkong-agent`

### 2. 部署到目标机器

```bash
# 方法一：使用安装脚本（推荐）
chmod +x install-agent.sh
sudo ./install-agent.sh --server 192.168.1.100 --port 8765

# 方法二：手动复制并运行
scp dist/qunkong-agent install-agent.sh root@目标机器:/tmp/
ssh root@目标机器 "cd /tmp && chmod +x install-agent.sh && ./install-agent.sh --server 192.168.1.100 --port 8765 --binary-path ./qunkong-agent"
```

### 3. 验证部署

```bash
# 在目标机器上检查服务状态
sudo systemctl status qunkong-agent

# 查看日志
sudo journalctl -u qunkong-agent -f
```

## 批量更新流程

### 1. 打包新版本

```bash
cd deployment
./build-agent.sh
```

### 2. 上传到 Web 服务器

```bash
# 方法一：上传到 Nginx
sudo cp dist/qunkong-agent /var/www/html/downloads/qunkong-agent

# 方法二：使用 Python HTTP 服务器（测试用）
cd dist
python3 -m http.server 8000
# 访问URL: http://你的IP:8000/qunkong-agent
```

### 3. 在 Web UI 中更新

1. 登录管理界面
2. 进入 "Agent 管理"
3. 选择要更新的 Agent
4. 点击 "批量管理"
5. 选择 "更新版本"
6. 填写：
   - 版本号：`v1.0.2`
   - 下载URL：`http://192.168.1.100:8000/qunkong-agent`
7. 点击 "执行"

### 4. 等待更新完成

Agent 会自动：
- 下载新版本
- 备份旧版本
- 替换可执行文件
- 自动重启

## 常用命令

```bash
# 查看服务状态
sudo systemctl status qunkong-agent

# 重启服务
sudo systemctl restart qunkong-agent

# 查看日志
sudo journalctl -u qunkong-agent -f

# 停止服务
sudo systemctl stop qunkong-agent

# 卸载服务
sudo ./uninstall-agent.sh
```

## 故障排查

### Agent 无法连接

```bash
# 1. 检查服务状态
sudo systemctl status qunkong-agent

# 2. 查看日志
sudo journalctl -u qunkong-agent -n 50

# 3. 检查网络
ping 服务器IP
telnet 服务器IP 8765

# 4. 手动运行测试
sudo /opt/qunkong-agent/qunkong-agent --server 服务器IP --port 8765 -v
```

### 更新失败恢复

```bash
# 恢复备份版本
cd /opt/qunkong-agent
sudo mv qunkong-agent.backup qunkong-agent
sudo systemctl restart qunkong-agent
```

## 批量部署示例

```bash
#!/bin/bash
# 批量部署到多台机器

SERVERS=("192.168.1.101" "192.168.1.102" "192.168.1.103")
SERVER_HOST="192.168.1.100"
SERVER_PORT="8765"

for host in "${SERVERS[@]}"; do
    echo "部署到 $host..."
    scp dist/qunkong-agent install-agent.sh root@$host:/tmp/
    ssh root@$host "cd /tmp && ./install-agent.sh --server $SERVER_HOST --port $SERVER_PORT --binary-path ./qunkong-agent"
done

echo "批量部署完成！"
```

## 安全建议

1. ✅ 使用内网地址传输更新文件
2. ✅ 生产环境使用 HTTPS
3. ✅ 限制管理界面访问权限
4. ✅ 定期备份配置
5. ✅ 监控更新日志

## 获取帮助

详细文档：[README.md](README.md)

---

**快速开始版本**：v1.0.0


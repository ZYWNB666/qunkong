# Agent 发布目录

此目录用于存放自动构建的 Agent 二进制文件。

## 文件说明

- `qunkong-agent-latest` - 最新版本的 Agent
- `qunkong-agent-{timestamp}` - 带时间戳的历史版本
- `VERSION-latest.txt` - 最新版本信息

## 自动构建

当 `app/client.py` 文件发生变化时，GitHub Actions 会自动：

1. 在 Linux 环境中打包 Agent
2. 创建 GitHub Release
3. 将打包好的文件提交到此目录

## 使用方法

```bash
# 下载最新版本
wget https://raw.githubusercontent.com/ZYWNB666/qunkong/main/releases/qunkong-agent-latest

# 或从 GitHub Releases 下载
# https://github.com/ZYWNB666/qunkong/releases

# 添加执行权限
chmod +x qunkong-agent-latest

# 启动 Agent
./qunkong-agent-latest --server SERVER_IP --port 8765
```

## 历史版本

所有历史版本都会保留在 GitHub Releases 中，可以按需下载特定版本。


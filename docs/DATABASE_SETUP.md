# QueenBee 数据库配置指南

## 概述

QueenBee 已从 SQLite 迁移到 MySQL，提供更好的性能和并发支持。

## 前置要求

1. **MySQL 服务器** (版本 5.7+ 或 8.0+)
2. **Python 依赖** (已包含在 requirements.txt 中)

## 快速开始

### 1. 安装 MySQL 服务器

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install mysql-server
sudo mysql_secure_installation
```

#### CentOS/RHEL
```bash
sudo yum install mysql-server
sudo systemctl start mysqld
sudo mysql_secure_installation
```

#### Windows
下载并安装 [MySQL Community Server](https://dev.mysql.com/downloads/mysql/)

#### macOS
```bash
brew install mysql
brew services start mysql
```

### 2. 创建数据库和用户

登录 MySQL：
```bash
mysql -u root -p
```

创建数据库和用户：
```sql
-- 创建数据库
CREATE DATABASE queenbee CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户（请替换为安全的密码）
CREATE USER 'queenbee'@'localhost' IDENTIFIED BY 'your_secure_password';

-- 授予权限
GRANT ALL PRIVILEGES ON queenbee.* TO 'queenbee'@'localhost';
FLUSH PRIVILEGES;

-- 退出
EXIT;
```

### 3. 配置 QueenBee

#### 3.1 安装 Python 依赖
```bash
pip install -r requirements.txt
```

#### 3.2 创建配置文件
```bash
# 复制配置模板
cp config/database.conf.template config/database.conf
```

#### 3.3 编辑配置文件
编辑 `config/database.conf`：
```ini
[mysql]
host = localhost
port = 3306
database = queenbee
username = queenbee
password = your_secure_password
charset = utf8mb4

[connection]
max_connections = 20
timeout = 30
```

#### 3.4 初始化数据库
```bash
python scripts/init_database.py
```

### 4. 启动服务

```bash
# 启动服务器
python app/main.py

# 或使用启动脚本
./start.bat  # Windows
./start.sh   # Linux/macOS
```

## 配置说明

### 数据库配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| host | MySQL 服务器地址 | localhost |
| port | MySQL 端口 | 3306 |
| database | 数据库名称 | queenbee |
| username | 数据库用户名 | - |
| password | 数据库密码 | - |
| charset | 字符集 | utf8mb4 |

### 连接池配置

| 参数 | 说明 | 默认值 |
|------|------|--------|
| max_connections | 最大连接数 | 20 |
| timeout | 连接超时时间（秒） | 30 |

## 数据库表结构

### agents 表
存储 Agent 基本信息
- `id`: Agent 唯一标识
- `hostname`: 主机名
- `ip_address`: IP 地址
- `status`: 状态 (ONLINE/OFFLINE)
- `last_heartbeat`: 最后心跳时间
- `register_time`: 注册时间

### execution_history 表
存储脚本执行历史
- `id`: 任务唯一标识
- `script_name`: 脚本名称
- `script_content`: 脚本内容
- `target_hosts`: 目标主机列表 (JSON)
- `status`: 执行状态
- `results`: 执行结果 (JSON)

### agent_system_info 表
存储 Agent 系统信息
- `agent_id`: Agent ID (外键)
- `system_info`: 系统信息 (JSON)
- `cpu_info`: CPU 信息 (JSON)
- `memory_info`: 内存信息 (JSON)
- `disk_info`: 磁盘信息 (JSON)
- `network_info`: 网络信息 (JSON)

## 故障排除

### 常见问题

1. **连接被拒绝**
   - 检查 MySQL 服务是否运行
   - 验证主机名和端口
   - 检查防火墙设置

2. **认证失败**
   - 验证用户名和密码
   - 确认用户有数据库访问权限

3. **字符集问题**
   - 确保数据库使用 utf8mb4 字符集
   - 检查配置文件中的 charset 设置

### 日志查看

```bash
# MySQL 错误日志
sudo tail -f /var/log/mysql/error.log

# QueenBee 应用日志
tail -f logs/queenbee.log
```

## 性能优化

### MySQL 配置优化

编辑 `/etc/mysql/mysql.conf.d/mysqld.cnf`：

```ini
[mysqld]
# 连接数
max_connections = 200

# 缓冲池大小（推荐为内存的 70-80%）
innodb_buffer_pool_size = 1G

# 日志文件大小
innodb_log_file_size = 256M

# 查询缓存
query_cache_size = 64M
query_cache_type = 1
```

重启 MySQL 服务：
```bash
sudo systemctl restart mysql
```

## 备份与恢复

### 备份数据库
```bash
mysqldump -u queenbee -p queenbee > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 恢复数据库
```bash
mysql -u queenbee -p queenbee < backup_20231201_120000.sql
```

## 安全建议

1. **使用强密码**：为数据库用户设置复杂密码
2. **限制访问**：只允许必要的 IP 地址访问数据库
3. **定期备份**：建立自动备份机制
4. **更新软件**：保持 MySQL 版本更新
5. **监控日志**：定期检查数据库日志

## 迁移说明

如果你从 SQLite 版本升级，旧的 `.db` 文件将不再使用。数据需要重新收集，因为表结构已优化。

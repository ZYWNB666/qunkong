"""
Uvicorn 配置文件
用于生产环境部署
"""
import multiprocessing
import os

# 从配置文件读取端口
def get_port():
    import configparser
    config = configparser.ConfigParser()
    try:
        config.read('config/database.conf', encoding='utf-8')
        return config.getint('server', 'api_port', fallback=5000)
    except:
        return 5000

# 服务器配置
bind = f"0.0.0.0:{get_port()}"
host = "0.0.0.0"
port = get_port()

# Worker 配置
# 注意：由于 WebSocket 需要共享状态，建议使用单 worker
# 如果需要多 worker，必须启用 Redis 集群模式
workers = 1

# 异步配置
loop = "uvloop"  # 高性能事件循环（需要安装 uvloop）

# 超时配置
timeout_keep_alive = 65  # Keep-alive 超时
timeout_notify = 30  # 通知超时

# 日志配置
log_level = os.getenv("LOG_LEVEL", "info")
access_log = True

# SSL 配置（如果需要）
# ssl_keyfile = "/path/to/key.pem"
# ssl_certfile = "/path/to/cert.pem"

# 限制配置
limit_concurrency = 1000  # 最大并发连接数
limit_max_requests = 10000  # 每个 worker 最大请求数（然后重启）
backlog = 2048  # 等待连接队列大小


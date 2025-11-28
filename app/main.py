"""
Qunkong 主服务器入口 - FastAPI 版本
"""
import asyncio
import threading
import configparser
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.fastapi_app import create_fastapi_app
from app.server_core import QunkongServer
from app.cluster import ClusterManager
from app.models.auth import AuthManager
from app.routers.deps import set_server_instance, set_auth_manager
from app.routers import (
    auth_router, agents_router, tasks_router, jobs_router,
    simple_jobs_router, users_router, projects_router, tenants_router
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局变量
websocket_server = None
websocket_thread = None


def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()
    try:
        config.read('config/database.conf', encoding='utf-8')
        return config
    except Exception as e:
        logger.warning(f"读取配置文件失败: {e}，使用默认配置")
        return None


def create_cluster_manager(config):
    """创建集群管理器"""
    if not config:
        logger.info("配置文件未找到，使用单节点模式")
        return None
    
    try:
        cluster_enabled = config.getboolean('cluster', 'enabled', fallback=False)
        redis_enabled = config.getboolean('redis', 'enabled', fallback=False)
        
        if not cluster_enabled or not redis_enabled:
            logger.info("集群模式未启用，使用单节点模式")
            return None
        
        try:
            import redis.asyncio as redis
        except ImportError:
            logger.error("redis包未安装，无法启用集群模式，使用单节点模式")
            return None
        
        redis_host = config.get('redis', 'host', fallback='localhost')
        redis_port = config.getint('redis', 'port', fallback=6379)
        redis_db = config.getint('redis', 'db', fallback=0)
        redis_password = config.get('redis', 'password', fallback=None)
        redis_max_connections = config.getint('redis', 'max_connections', fallback=10)
        
        if redis_password == '':
            redis_password = None
        
        redis_pool = redis.ConnectionPool(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            max_connections=redis_max_connections,
            decode_responses=True
        )
        
        redis_client = redis.Redis(connection_pool=redis_pool)
        
        node_id = config.get('cluster', 'node_id', fallback=None)
        if node_id == '':
            node_id = None
        
        cluster_manager = ClusterManager(redis_client=redis_client, node_id=node_id)
        logger.info(f"集群管理器已创建: node_id={cluster_manager.node_id}")
        
        return cluster_manager
        
    except Exception as e:
        logger.error(f"创建集群管理器失败: {e}，使用单节点模式")
        return None


def start_websocket_server(server):
    """启动WebSocket服务器"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.start())


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    global websocket_server, websocket_thread
    
    # 加载配置
    config = load_config()
    
    # 读取端口配置
    websocket_port = 8765
    api_port = 5000
    
    if config:
        try:
            websocket_port = config.getint('server', 'websocket_port', fallback=8765)
            api_port = config.getint('server', 'api_port', fallback=5000)
        except Exception as e:
            logger.warning(f"读取端口配置失败，使用默认端口: {e}")
    
    # 创建集群管理器
    cluster_manager = create_cluster_manager(config)
    
    # 创建 WebSocket 服务器
    websocket_server = QunkongServer(
        host="0.0.0.0",
        port=websocket_port,
        web_port=api_port,
        cluster_manager=cluster_manager
    )
    
    # 初始化认证管理器
    auth_manager = AuthManager(websocket_server.db)
    
    # 设置全局实例
    set_server_instance(websocket_server)
    set_auth_manager(auth_manager)
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用生命周期管理"""
        global websocket_thread
        
        # 启动时
        logger.info("=" * 60)
        logger.info(f"Web API 服务器启动在 http://0.0.0.0:{api_port}")
        logger.info(f"WebSocket 服务器启动在 ws://0.0.0.0:{websocket_port}")
        logger.info(f"API 文档: http://0.0.0.0:{api_port}/api/docs")
        if cluster_manager:
            logger.info(f"集群模式已启用 - 节点ID: {cluster_manager.node_id}")
        else:
            logger.info("单节点模式运行")
        logger.info("默认管理员账户: admin/admin123")
        logger.info("=" * 60)
        
        # 启动 WebSocket 服务器线程
        websocket_thread = threading.Thread(
            target=start_websocket_server,
            args=(websocket_server,),
            daemon=True
        )
        websocket_thread.start()
        
        yield
        
        # 关闭时
        logger.info("正在关闭服务...")
        websocket_server.running = False
    
    # 创建 FastAPI 应用
    app = FastAPI(
        title="Qunkong API",
        description="群控服务器管理平台 API",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(auth_router)
    app.include_router(agents_router)
    app.include_router(tasks_router)
    app.include_router(jobs_router)
    app.include_router(simple_jobs_router)
    app.include_router(users_router)
    app.include_router(projects_router)
    app.include_router(tenants_router)
    
    # 健康检查
    @app.get("/health", tags=["System"])
    async def health_check():
        """健康检查"""
        return {
            "status": "healthy",
            "version": "2.0.0",
            "websocket_server": "running" if websocket_server and websocket_server.running else "stopped",
            "cluster_mode": cluster_manager is not None
        }
    
    @app.get("/", tags=["System"])
    async def root():
        """根路径"""
        return {
            "name": "Qunkong API",
            "version": "2.0.0",
            "docs": "/api/docs"
        }
    
    # 静态文件服务（如果存在 web/dist 目录）
    static_dir = "web/dist"
    if os.path.exists(static_dir):
        app.mount("/assets", StaticFiles(directory=f"{static_dir}/assets"), name="assets")
        
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            """服务单页应用"""
            file_path = os.path.join(static_dir, full_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(os.path.join(static_dir, "index.html"))
    
    return app


# 创建应用实例（用于 uvicorn 启动）
app = create_app()


def main():
    """主函数"""
    config = load_config()
    
    api_port = 5000
    if config:
        try:
            api_port = config.getint('server', 'api_port', fallback=5000)
        except:
            pass
    
    # 使用 uvicorn 启动
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=api_port,
        reload=False,
        workers=1,  # 单进程模式，WebSocket 需要共享状态
        log_level="info"
    )


if __name__ == '__main__':
    main()

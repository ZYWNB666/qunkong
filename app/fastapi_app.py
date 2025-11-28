"""
FastAPI 主应用
"""
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

logger = logging.getLogger(__name__)


def create_fastapi_app(
    title: str = "Qunkong API",
    description: str = "群控服务器管理平台 API",
    version: str = "2.0.0"
) -> FastAPI:
    """创建 FastAPI 应用"""
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用生命周期管理"""
        logger.info("FastAPI 应用启动...")
        yield
        logger.info("FastAPI 应用关闭...")
    
    app = FastAPI(
        title=title,
        description=description,
        version=version,
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
    
    # 请求耗时中间件
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        # 记录慢请求
        if process_time > 1.0:
            logger.warning(f"慢请求: {request.method} {request.url.path} - {process_time:.3f}s")
        
        return response
    
    # 全局异常处理
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.detail,
                "code": exc.status_code
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"未处理的异常: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "服务器内部错误",
                "code": 500
            }
        )
    
    # 健康检查
    @app.get("/health", tags=["System"])
    async def health_check():
        """健康检查接口"""
        return {"status": "healthy", "version": version}
    
    @app.get("/", tags=["System"])
    async def root():
        """根路径"""
        return {
            "name": title,
            "version": version,
            "docs": "/api/docs"
        }
    
    return app


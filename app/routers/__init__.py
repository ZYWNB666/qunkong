"""
FastAPI 路由模块
"""
from app.routers.auth import router as auth_router
from app.routers.agents import router as agents_router
from app.routers.agent_install import router as agent_install_router
from app.routers.tasks import router as tasks_router
from app.routers.jobs import router as jobs_router
from app.routers.simple_jobs import router as simple_jobs_router
from app.routers.users import router as users_router
from app.routers.projects import router as projects_router
from app.routers.tenants import router as tenants_router

__all__ = [
    'auth_router',
    'agents_router',
    'agent_install_router',
    'tasks_router',
    'jobs_router',
    'simple_jobs_router',
    'users_router',
    'projects_router',
    'tenants_router'
]


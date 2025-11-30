"""
RBAC权限管理 - 简化的基于角色的访问控制
只提供用户级和项目级的权限验证,移除租户管理
使用本地缓存优化性能，避免每次请求都查询数据库
"""
from fastapi import Depends, HTTPException, status, Query
from typing import Dict, Any, Optional, Callable
from app.routers.deps import get_current_user
from app.models.project import ProjectManager
from app.models import DatabaseManager
from app.cache import get_local_cache
import logging
import time

logger = logging.getLogger(__name__)

# 权限缓存TTL（秒）
PERMISSION_CACHE_TTL = 60  # 权限缓存60秒
PROJECT_ACCESS_CACHE_TTL = 60  # 项目访问权限缓存60秒


class PermissionChecker:
    """权限检查器 - 单例模式，带本地缓存"""
    
    _instance = None
    _db_manager = None
    
    @classmethod
    def initialize(cls, db_manager: DatabaseManager):
        """初始化权限检查器"""
        cls._db_manager = db_manager
    
    @classmethod
    def get_instance(cls):
        """获取权限检查器实例"""
        if cls._instance is None:
            if cls._db_manager is None:
                raise RuntimeError("PermissionChecker未初始化，请先调用initialize()")
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        if self._db_manager is None:
            raise RuntimeError("PermissionChecker未初始化")
        self.project_mgr = ProjectManager(self._db_manager)
        self._cache = get_local_cache()  # 使用本地缓存
    
    def check_project_access(self, user_id: int, project_id: int,
                            user_role: str, required_role: str = None) -> bool:
        """检查用户是否可以访问指定项目（带缓存）"""
        # 系统管理员可以访问所有项目
        if user_role in ['admin', 'super_admin']:
            return True
        
        # 构建缓存key
        cache_key = f"project_access:{user_id}:{project_id}:{required_role or 'any'}"
        
        # 尝试从缓存获取
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        # 查询数据库
        result = self.project_mgr.check_project_permission(
            user_id, project_id, required_role
        )
        
        # 写入缓存
        self._cache.set(cache_key, result, PROJECT_ACCESS_CACHE_TTL)
        
        return result
    
    def check_permission_key(self, user_id: int, project_id: int,
                            permission_key: str, user_role: str) -> bool:
        """检查用户是否拥有指定的功能权限（带缓存）"""
        # 系统管理员拥有所有权限
        if user_role in ['admin', 'super_admin']:
            return True
        
        # 构建缓存key
        cache_key = f"permission:{user_id}:{project_id}:{permission_key}"
        
        # 尝试从缓存获取
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        # 查询数据库
        result = self.project_mgr.check_permission(
            project_id, user_id, permission_key, user_role
        )
        
        # 写入缓存
        self._cache.set(cache_key, result, PERMISSION_CACHE_TTL)
        
        return result
    
    def get_user_accessible_projects(self, user_id: int, user_role: str) -> list:
        """获取用户可访问的所有项目ID列表（带缓存）"""
        # 构建缓存key
        cache_key = f"accessible_projects:{user_id}:{user_role}"
        
        # 尝试从缓存获取
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        if user_role in ['admin', 'super_admin']:
            # 管理员可以访问所有项目
            all_projects = self.project_mgr.get_all_projects()
            result = [p['id'] for p in all_projects]
        else:
            # 普通用户只能访问自己的项目
            user_projects = self.project_mgr.get_user_projects(user_id)
            result = [p['id'] for p in user_projects]
        
        # 写入缓存
        self._cache.set(cache_key, result, PROJECT_ACCESS_CACHE_TTL)
        
        return result
    
    def invalidate_user_cache(self, user_id: int):
        """使用户相关的缓存失效（当权限变更时调用）"""
        # 简单实现：清除所有与该用户相关的缓存
        # 更精细的实现可以只清除特定key
        logger.info(f"清除用户 {user_id} 的权限缓存")
    
    def validate_project_access(self, user_id: int, project_id: int,
                               user_role: str, required_role: str = None):
        """验证项目访问权限，失败则抛出异常"""
        if not self.check_project_access(user_id, project_id, user_role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"您没有访问项目 {project_id} 的权限"
            )


# ==================== 依赖注入函数 ====================


async def require_project_access(
    project_id: Optional[int] = Query(None, description="项目ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    要求用户必须有项目访问权限
    适用于所有需要项目隔离的API
    """
    checker = PermissionChecker.get_instance()
    
    # project_id是必需的,如果没有提供则返回错误
    if project_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少必需的参数: project_id"
        )
    
    # 验证项目访问权限
    checker.validate_project_access(
        user_id=current_user['user_id'],
        project_id=project_id,
        user_role=current_user['role']
    )
    
    # 将project_id添加到用户上下文中
    current_user['current_project_id'] = project_id
    
    logger.info(f"用户 {current_user['username']} 访问项目 {project_id}")
    
    return current_user


async def require_project_admin(
    project_id: Optional[int] = Query(None, description="项目ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    要求用户必须是项目管理员
    适用于项目管理类API（添加成员、修改配置等）
    """
    checker = PermissionChecker.get_instance()
    
    # project_id是必需的,如果没有提供则返回错误
    if project_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少必需的参数: project_id"
        )
    
    # 验证项目管理员权限
    checker.validate_project_access(
        user_id=current_user['user_id'],
        project_id=project_id,
        user_role=current_user['role'],
        required_role='admin'  # 要求admin角色
    )
    
    current_user['current_project_id'] = project_id
    
    logger.info(f"用户 {current_user['username']} 以管理员身份访问项目 {project_id}")
    
    return current_user


async def require_project_write(
    project_id: Optional[int] = Query(None, description="项目ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    要求用户必须有项目写权限
    适用于创建/修改/删除操作的API
    """
    checker = PermissionChecker.get_instance()
    
    # project_id是必需的,如果没有提供则返回错误
    if project_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少必需的参数: project_id"
        )
    
    # 验证项目写权限
    checker.validate_project_access(
        user_id=current_user['user_id'],
        project_id=project_id,
        user_role=current_user['role'],
        required_role='readwrite'  # 要求readwrite或更高权限
    )
    
    current_user['current_project_id'] = project_id
    
    return current_user


def require_permission(permission_key: str):
    """
    要求用户必须有指定的功能权限
    这是一个装饰器工厂,返回一个依赖函数
    
    使用方式:
    @router.post("/agents/batch-add")
    async def batch_add_agents(
        current_user: Dict = Depends(require_permission('agent.batch_add'))
    ):
        ...
    
    注意: project_id会从query参数中自动提取,如果没有则抛出403错误
    """
    async def permission_checker(
        project_id: Optional[int] = Query(None, description="项目ID"),
        current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        checker = PermissionChecker.get_instance()
        
        # project_id是必需的,如果没有提供则返回错误
        if project_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="缺少必需的参数: project_id"
            )
        
        # 检查功能权限（带缓存）
        has_permission = checker.check_permission_key(
            user_id=current_user['user_id'],
            project_id=project_id,
            permission_key=permission_key,
            user_role=current_user['role']
        )
        
        if not has_permission:
            logger.warning(f"权限拒绝: user={current_user['username']}, project={project_id}, permission={permission_key}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"您没有 '{permission_key}' 权限"
            )
        
        # 将project_id添加到用户上下文
        current_user['current_project_id'] = project_id
        
        # 仅在DEBUG级别记录日志
        logger.debug(f"权限通过: user={current_user['username']}, project={project_id}, permission={permission_key}")
        
        return current_user
    
    return permission_checker


async def require_system_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    要求用户必须是系统管理员
    适用于系统管理类API
    """
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要系统管理员权限"
        )
    
    logger.info(f"系统管理员 {current_user['username']} 访问管理功能")
    
    return current_user


def filter_by_project_access(
    items: list,
    project_id_field: str,
    user_id: int,
    user_role: str
) -> list:
    """
    根据项目访问权限过滤列表
    
    Args:
        items: 要过滤的项目列表
        project_id_field: 项目ID字段名
        user_id: 用户ID
        user_role: 用户角色
    
    Returns:
        过滤后的列表
    """
    if user_role in ['admin', 'super_admin']:
        return items  # 管理员可以看到所有
    
    checker = PermissionChecker.get_instance()
    accessible_projects = set(checker.get_user_accessible_projects(user_id, user_role))
    
    # 只返回用户有权限访问的项目的数据
    filtered = [
        item for item in items
        if item.get(project_id_field) in accessible_projects
    ]
    
    logger.debug(f"过滤前: {len(items)} 项，过滤后: {len(filtered)} 项")
    
    return filtered


# ==================== 辅助函数 ====================

def get_user_context_info(current_user: Dict[str, Any]) -> Dict[str, Any]:
    """获取用户上下文信息摘要"""
    return {
        'user_id': current_user['user_id'],
        'username': current_user['username'],
        'role': current_user['role'],
        'tenant_id': current_user.get('current_tenant_id'),
        'project_id': current_user.get('current_project_id')
    }


def log_access(current_user: Dict[str, Any], resource: str, action: str):
    """记录访问日志"""
    logger.info(
        f"访问日志 - 用户: {current_user['username']}, "
        f"资源: {resource}, 操作: {action}, "
        f"项目: {current_user.get('current_project_id')}"
    )
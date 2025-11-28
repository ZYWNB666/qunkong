"""
FastAPI 依赖注入和通用模型
"""
from fastapi import Depends, HTTPException, Header, status
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ==================== Pydantic 模型 ====================

class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str = ""


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    error: str
    code: int = 400


class UserInfo(BaseModel):
    """用户信息模型"""
    user_id: int
    username: str
    email: str
    role: str


class TokenData(BaseModel):
    """令牌数据模型"""
    user_id: int
    username: str
    email: str
    role: str


# ==================== 请求模型 ====================

class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3)
    email: str
    password: str = Field(..., min_length=6)
    confirm_password: str


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    current_password: str
    new_password: str = Field(..., min_length=6)
    confirm_password: str


class ExecuteScriptRequest(BaseModel):
    """执行脚本请求"""
    script: str
    target_hosts: list[str]
    script_name: str = "未命名任务"
    script_params: str = ""
    timeout: int = 7200
    execution_user: str = "root"
    project_id: Optional[int] = None


class BatchAgentRequest(BaseModel):
    """批量管理Agent请求"""
    action: str
    agent_ids: list[str]
    version: Optional[str] = None
    download_url: Optional[str] = None
    md5: Optional[str] = None


# ==================== 响应模型 ====================

class LoginResponse(BaseModel):
    """登录响应"""
    message: str = "登录成功"
    user: UserInfo
    token: str


class AgentInfo(BaseModel):
    """Agent信息"""
    id: str
    hostname: str
    ip_address: str
    status: str
    last_heartbeat: Optional[str] = None
    register_time: Optional[str] = None


class TaskInfo(BaseModel):
    """任务信息"""
    task_id: str
    script_name: str
    status: str
    created_at: str
    agent_count: int


# ==================== 全局状态 ====================

# 服务器实例（将在 main.py 中设置）
_server_instance = None
_auth_manager = None


def set_server_instance(server):
    """设置服务器实例"""
    global _server_instance
    _server_instance = server


def get_server():
    """获取服务器实例"""
    if _server_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="服务器未就绪"
        )
    return _server_instance


def set_auth_manager(auth_manager):
    """设置认证管理器"""
    global _auth_manager
    _auth_manager = auth_manager


def get_auth_manager():
    """获取认证管理器"""
    if _auth_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="认证服务未就绪"
        )
    return _auth_manager


# ==================== 认证依赖 ====================

async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """获取当前用户（认证依赖）"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌"
        )
    
    token = authorization
    if token.startswith("Bearer "):
        token = token[7:]
    
    auth_manager = get_auth_manager()
    user = auth_manager.get_user_by_token(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌"
        )
    
    return user


async def get_optional_user(
    authorization: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    """获取可选的当前用户"""
    if not authorization:
        return None
    
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None


def require_permission(permission: str, resource: str = None):
    """权限检查依赖工厂"""
    async def permission_checker(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ):
        auth_manager = get_auth_manager()
        user_id = current_user['user_id']
        
        if not auth_manager.check_permission(user_id, permission, resource):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        
        return current_user
    
    return permission_checker


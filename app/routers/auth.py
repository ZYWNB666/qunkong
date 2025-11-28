"""
认证 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Dict, Any
from app.routers.deps import (
    LoginRequest, RegisterRequest, ChangePasswordRequest,
    LoginResponse, UserInfo, BaseResponse,
    get_current_user, get_auth_manager
)

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=BaseResponse)
async def register(data: RegisterRequest):
    """用户注册"""
    auth_manager = get_auth_manager()
    
    # 验证输入
    if '@' not in data.email:
        raise HTTPException(status_code=400, detail="请提供有效的邮箱地址")
    
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="两次输入的密码不一致")
    
    # 注册用户
    success = auth_manager.register_user(data.username, data.email, data.password)
    if not success:
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在")
    
    return BaseResponse(message="注册成功")


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, request: Request):
    """用户登录"""
    auth_manager = get_auth_manager()
    
    # 获取客户端信息
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "")
    
    # 登录验证
    user_info = auth_manager.login_user(data.username, data.password, ip_address, user_agent)
    if not user_info:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    return LoginResponse(
        message="登录成功",
        user=UserInfo(
            user_id=user_info['user_id'],
            username=user_info['username'],
            email=user_info['email'],
            role=user_info['role']
        ),
        token=user_info['token']
    )


@router.post("/logout", response_model=BaseResponse)
async def logout(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """用户登出"""
    auth_manager = get_auth_manager()
    
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        auth_manager.logout_user(token)
    
    return BaseResponse(message="登出成功")


@router.get("/profile")
async def get_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """获取用户信息"""
    return {
        "user": {
            "user_id": current_user['user_id'],
            "username": current_user['username'],
            "email": current_user['email'],
            "role": current_user['role']
        }
    }


@router.post("/change-password", response_model=BaseResponse)
async def change_password(
    data: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """修改密码"""
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="两次输入的新密码不一致")
    
    auth_manager = get_auth_manager()
    
    # 验证当前密码
    user = auth_manager.get_user_by_username(current_user['username'])
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 修改密码
    success = auth_manager.change_password(
        current_user['user_id'], 
        data.current_password, 
        data.new_password
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="当前密码错误")
    
    return BaseResponse(message="密码修改成功")


@router.post("/verify")
async def verify_token(request: Request):
    """验证令牌"""
    auth_manager = get_auth_manager()
    
    authorization = request.headers.get("Authorization", "")
    if not authorization:
        return {"valid": False, "error": "未提供令牌"}
    
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    
    user = auth_manager.get_user_by_token(token)
    if not user:
        return {"valid": False, "error": "无效令牌"}
    
    return {
        "valid": True,
        "user": {
            "user_id": user['user_id'],
            "username": user['username'],
            "email": user['email'],
            "role": user['role']
        }
    }


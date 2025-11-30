"""
用户管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.routers.deps import get_current_user, get_auth_manager, get_server

router = APIRouter(prefix="/api/users", tags=["用户管理"])


class ProjectRoleAssignment(BaseModel):
    """项目角色分配"""
    project_id: int
    role: str = "member"


class CreateUserRequest(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=3)
    email: str
    password: str = Field(..., min_length=6)
    role: str = "user"
    project_roles: Optional[List[ProjectRoleAssignment]] = Field(default=None, description="项目角色分配列表")


class UpdateUserRequest(BaseModel):
    """更新用户请求"""
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    project_roles: Optional[List[ProjectRoleAssignment]] = Field(default=None, description="项目角色分配列表")


def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)):
    """管理员权限检查"""
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="权限不足，需要管理员权限")
    return current_user


@router.get("")
async def get_users(
    role: Optional[str] = None,
    is_active: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: Optional[int] = Query(None, description="项目ID（前端自动添加，此接口忽略）"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取用户列表"""
    auth_manager = get_auth_manager()
    
    is_active_bool = None
    if is_active is not None:
        is_active_bool = is_active.lower() in ['true', '1', 'yes']
    
    offset = (page - 1) * page_size
    
    users = auth_manager.get_all_users(
        role=role,
        is_active=is_active_bool,
        search=search,
        limit=page_size,
        offset=offset
    )
    
    total = auth_manager.count_users(role=role, is_active=is_active_bool)
    
    return {
        'users': users,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size
    }


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取用户详情"""
    auth_manager = get_auth_manager()
    
    if current_user['role'] not in ['admin', 'super_admin'] and \
       current_user['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="权限不足")
    
    user = auth_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return {'user': user}


@router.post("")
async def create_user(
    data: CreateUserRequest,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """创建用户"""
    auth_manager = get_auth_manager()
    
    if '@' not in data.email:
        raise HTTPException(status_code=400, detail="请提供有效的邮箱地址")
    
    valid_roles = ['user', 'admin', 'tenant_admin', 'tenant_member']
    if data.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"无效的角色，允许的角色: {', '.join(valid_roles)}")
    
    success = auth_manager.register_user(data.username, data.email, data.password, data.role)
    if not success:
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在")
    
    user = auth_manager.get_user_by_username(data.username)
    user_id = user['id']
    
    # 如果指定了项目角色，添加用户到项目
    if data.project_roles:
        server = get_server()
        from app.models.project import ProjectManager
        project_manager = ProjectManager(server.db)
        
        for project_role in data.project_roles:
            try:
                # 验证项目是否存在
                project = project_manager.get_project_by_id(project_role.project_id)
                if not project:
                    print(f"项目 {project_role.project_id} 不存在，跳过")
                    continue
                
                # 添加用户到项目
                project_manager.add_project_member(
                    project_id=project_role.project_id,
                    user_id=user_id,
                    role=project_role.role,
                    invited_by=current_user['user_id']
                )
            except Exception as e:
                print(f"添加用户到项目 {project_role.project_id} 失败: {e}")
    
    return {'message': '用户创建成功', 'user': user}


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    data: UpdateUserRequest,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """更新用户信息"""
    auth_manager = get_auth_manager()
    
    user = auth_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    update_data = {}
    if data.email is not None:
        update_data['email'] = data.email
    if data.role is not None:
        update_data['role'] = data.role
    if data.is_active is not None:
        update_data['is_active'] = data.is_active
    
    success = auth_manager.update_user(user_id, **update_data)
    if not success:
        raise HTTPException(status_code=500, detail="更新用户失败")
    
    # 如果指定了项目角色，更新用户的项目分配
    if data.project_roles is not None:
        server = get_server()
        from app.models.project import ProjectManager
        project_manager = ProjectManager(server.db)
        
        # 先移除用户的所有项目分配
        conn = server.db._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM project_members WHERE user_id = %s", (user_id,))
        conn.commit()
        
        # 添加新的项目分配
        for project_role in data.project_roles:
            try:
                project = project_manager.get_project_by_id(project_role.project_id)
                if not project:
                    continue
                
                project_manager.add_project_member(
                    project_id=project_role.project_id,
                    user_id=user_id,
                    role=project_role.role,
                    invited_by=current_user['user_id']
                )
            except Exception as e:
                print(f"添加用户到项目 {project_role.project_id} 失败: {e}")
        
        conn.close()
    
    updated_user = auth_manager.get_user_by_id(user_id)
    return {'message': '用户更新成功', 'user': updated_user}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """删除用户"""
    auth_manager = get_auth_manager()
    
    if current_user['user_id'] == user_id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    
    user = auth_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    success = auth_manager.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除用户失败")
    
    return {'message': '用户删除成功'}


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """重置用户密码"""
    auth_manager = get_auth_manager()
    
    user = auth_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    new_password = auth_manager.reset_password(user_id)
    if not new_password:
        raise HTTPException(status_code=500, detail="重置密码失败")
    
    return {'message': '密码重置成功', 'new_password': new_password}


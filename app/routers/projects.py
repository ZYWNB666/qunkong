"""
项目管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.routers.deps import get_current_user, get_server, require_permission

router = APIRouter(prefix="/api/projects", tags=["项目管理"])


class CreateProjectRequest(BaseModel):
    """创建项目请求"""
    name: str = Field(..., min_length=1)
    description: str = ""
    tenant_id: Optional[int] = None
    project_id: Optional[int] = None  # 忽略前端自动添加的 project_id


class UpdateProjectRequest(BaseModel):
    """更新项目请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ProjectMemberRequest(BaseModel):
    """项目成员请求"""
    user_id: int
    role: str = "member"


@router.get("/my-projects")
async def get_my_projects(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取当前用户的项目列表"""
    server = get_server()
    
    from app.models.project import ProjectManager
    project_manager = ProjectManager(server.db)
    
    projects = project_manager.get_user_projects(current_user['user_id'])
    
    return {'projects': projects}


@router.get("")
async def get_projects(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取项目列表"""
    server = get_server()
    
    from app.models.project import ProjectManager
    project_manager = ProjectManager(server.db)
    
    offset = (page - 1) * page_size
    projects = project_manager.get_all_projects(
        user_id=current_user['user_id'],
        status=status,
        limit=page_size,
        offset=offset
    )
    
    return {
        'projects': projects,
        'total': len(projects),
        'page': page,
        'page_size': page_size
    }


@router.get("/{project_id}")
async def get_project(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取项目详情"""
    server = get_server()
    
    from app.models.project import ProjectManager
    project_manager = ProjectManager(server.db)
    
    project = project_manager.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    return {'project': project}


@router.post("")
async def create_project(
    data: CreateProjectRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """创建项目"""
    server = get_server()
    
    from app.models.project import ProjectManager
    project_manager = ProjectManager(server.db)
    
    # 创建项目（返回项目信息字典，不是 ID）
    project = project_manager.create_project(
        project_name=data.name,
        description=data.description,
        created_by=current_user['user_id']
    )
    
    if not project:
        raise HTTPException(status_code=500, detail="创建项目失败，项目代码可能已存在")
    
    return {'message': '项目创建成功', 'project': project}


@router.put("/{project_id}")
async def update_project(
    project_id: int,
    data: UpdateProjectRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """更新项目"""
    server = get_server()
    
    from app.models.project import ProjectManager
    project_manager = ProjectManager(server.db)
    
    project = project_manager.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 检查权限
    if not project_manager.check_project_permission(current_user['user_id'], project_id, 'admin'):
        raise HTTPException(status_code=403, detail="没有权限修改此项目")
    
    update_data = {}
    if data.name is not None:
        update_data['project_name'] = data.name
    if data.description is not None:
        update_data['description'] = data.description
    if data.status is not None:
        update_data['status'] = data.status
    
    success = project_manager.update_project(project_id, **update_data)
    if not success:
        raise HTTPException(status_code=500, detail="更新项目失败")
    
    return {'message': '项目更新成功'}


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """删除项目"""
    server = get_server()
    
    from app.models.project import ProjectManager
    project_manager = ProjectManager(server.db)
    
    project = project_manager.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 检查权限
    if not project_manager.check_project_permission(current_user['user_id'], project_id, 'admin'):
        raise HTTPException(status_code=403, detail="没有权限删除此项目")
    
    success = project_manager.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除项目失败")
    
    return {'message': '项目删除成功'}


@router.get("/{project_id}/members")
async def get_project_members(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取项目成员列表"""
    server = get_server()
    
    from app.models.project import ProjectManager
    project_manager = ProjectManager(server.db)
    
    project = project_manager.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    members = project_manager.get_project_members(project_id)
    
    return {'members': members}


@router.post("/{project_id}/members")
async def add_project_member(
    project_id: int,
    data: ProjectMemberRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """添加项目成员"""
    server = get_server()
    
    from app.models.project import ProjectManager
    project_manager = ProjectManager(server.db)
    
    project = project_manager.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 检查权限
    if not project_manager.check_project_permission(current_user['user_id'], project_id, 'admin'):
        raise HTTPException(status_code=403, detail="没有权限添加成员")
    
    success = project_manager.add_project_member(
        project_id=project_id,
        user_id=data.user_id,
        role=data.role,
        invited_by=current_user['user_id']
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="添加成员失败")
    
    return {'message': '成员添加成功'}


@router.delete("/{project_id}/members/{user_id}")
async def remove_project_member(
    project_id: int,
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """移除项目成员"""
    server = get_server()
    
    from app.models.project import ProjectManager
    project_manager = ProjectManager(server.db)
    
    project = project_manager.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 检查权限
    if not project_manager.check_project_permission(current_user['user_id'], project_id, 'admin'):
        raise HTTPException(status_code=403, detail="没有权限移除成员")
    
    success = project_manager.remove_project_member(project_id, user_id)
    if not success:
        raise HTTPException(status_code=500, detail="移除成员失败")
    
    return {'message': '成员移除成功'}


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
    project_name: str = Field(..., min_length=1, description="项目名称")
    description: str = Field(default="", description="项目描述")
    project_code: Optional[str] = Field(default=None, description="项目代码(可选,不提供则自动生成)")
    admin_ids: Optional[List[int]] = Field(default=None, description="项目管理员ID列表")
    member_ids: Optional[List[int]] = Field(default=None, description="项目成员ID列表")


class UpdateProjectRequest(BaseModel):
    """更新项目请求"""
    project_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    admin_ids: Optional[List[int]] = Field(default=None, description="项目管理员ID列表")
    member_ids: Optional[List[int]] = Field(default=None, description="项目成员ID列表")


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
    project_id: Optional[int] = Query(None, description="项目ID（前端自动添加，此接口忽略）"),
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
    
    # 检查项目名是否唯一
    conn = server.db._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM projects WHERE project_name = %s", (data.project_name,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="项目名称已存在，请使用其他名称")
    conn.close()
    
    # 创建项目（返回项目信息字典，不是 ID）
    project = project_manager.create_project(
        project_name=data.project_name,
        description=data.description,
        created_by=current_user['user_id'],
        project_code=data.project_code  # 如果提供了project_code则使用,否则自动生成
    )
    
    if not project:
        raise HTTPException(status_code=500, detail="创建项目失败，项目代码可能已存在")
    
    project_id = project['id']
    
    # 添加项目管理员
    if data.admin_ids:
        for admin_id in data.admin_ids:
            try:
                project_manager.add_project_member(
                    project_id=project_id,
                    user_id=admin_id,
                    role='admin',
                    invited_by=current_user['user_id']
                )
            except Exception as e:
                print(f"添加管理员 {admin_id} 失败: {e}")
    
    # 添加项目成员
    if data.member_ids:
        for member_id in data.member_ids:
            # 避免重复添加
            if not data.admin_ids or member_id not in data.admin_ids:
                try:
                    project_manager.add_project_member(
                        project_id=project_id,
                        user_id=member_id,
                        role='member',
                        invited_by=current_user['user_id']
                    )
                except Exception as e:
                    print(f"添加成员 {member_id} 失败: {e}")
    
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
    
    # 如果要修改项目名，检查唯一性
    if data.project_name is not None and data.project_name != project['project_name']:
        conn = server.db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM projects WHERE project_name = %s AND id != %s",
                      (data.project_name, project_id))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="项目名称已存在，请使用其他名称")
        conn.close()
    
    update_data = {}
    if data.project_name is not None:
        update_data['project_name'] = data.project_name
    if data.description is not None:
        update_data['description'] = data.description
    if data.status is not None:
        update_data['status'] = data.status
    
    success = project_manager.update_project(project_id, **update_data)
    if not success:
        raise HTTPException(status_code=500, detail="更新项目失败")
    
    # 如果指定了成员配置，更新项目成员
    if data.admin_ids is not None or data.member_ids is not None:
        conn = server.db._get_connection()
        cursor = conn.cursor()
        
        # 删除所有非创建者的成员
        cursor.execute("""
            DELETE FROM project_members
            WHERE project_id = %s AND user_id != %s
        """, (project_id, project['created_by']))
        conn.commit()
        
        # 添加新的管理员
        if data.admin_ids:
            for admin_id in data.admin_ids:
                if admin_id != project['created_by']:  # 避免重复添加创建者
                    try:
                        project_manager.add_project_member(
                            project_id=project_id,
                            user_id=admin_id,
                            role='admin',
                            invited_by=current_user['user_id']
                        )
                    except Exception as e:
                        print(f"添加管理员 {admin_id} 失败: {e}")
        
        # 添加新的成员
        if data.member_ids:
            for member_id in data.member_ids:
                # 避免重复添加
                if (member_id != project['created_by'] and
                    (not data.admin_ids or member_id not in data.admin_ids)):
                    try:
                        project_manager.add_project_member(
                            project_id=project_id,
                            user_id=member_id,
                            role='member',
                            invited_by=current_user['user_id']
                        )
                    except Exception as e:
                        print(f"添加成员 {member_id} 失败: {e}")
        
        conn.close()
    
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


@router.get("/{project_id}/permissions")
async def get_project_permissions(
    project_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取项目所有可用的功能权限列表"""
    server = get_server()
    
    from app.models.project import ProjectManager
    project_manager = ProjectManager(server.db)
    
    # 检查用户是否有权限查看
    if not project_manager.check_project_permission(current_user['user_id'], project_id):
        raise HTTPException(status_code=403, detail="没有权限访问此项目")
    
    permissions = project_manager.get_all_permission_keys()
    
    return {
        'permissions': [
            {'key': perm, 'name': _get_permission_name(perm)}
            for perm in permissions
        ]
    }


@router.get("/{project_id}/members/{user_id}/permissions")
async def get_member_permissions(
    project_id: int,
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取项目成员的权限列表"""
    server = get_server()
    
    from app.models.project import ProjectManager
    project_manager = ProjectManager(server.db)
    
    # 用户可以查看自己的权限，或者管理员可以查看任何人的权限
    is_self = current_user['user_id'] == user_id
    is_admin = project_manager.check_project_permission(current_user['user_id'], project_id, 'admin')
    
    if not is_self and not is_admin:
        raise HTTPException(status_code=403, detail="无权查看其他用户的权限")
    
    permissions = project_manager.get_user_permissions(project_id, user_id)
    
    return {'permissions': permissions}


@router.post("/{project_id}/members/{user_id}/permissions")
async def set_member_permissions(
    project_id: int,
    user_id: int,
    permissions: list,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """设置项目成员的功能权限"""
    server = get_server()
    
    from app.models.project import ProjectManager
    project_manager = ProjectManager(server.db)
    
    # 检查权限
    if not project_manager.check_project_permission(current_user['user_id'], project_id, 'admin'):
        raise HTTPException(status_code=403, detail="需要项目管理员权限")
    
    success = project_manager.set_user_permissions(
        project_id=project_id,
        user_id=user_id,
        permissions=permissions,
        granted_by=current_user['user_id']
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="设置权限失败")
    
    return {'message': '权限设置成功'}


def _get_permission_name(permission_key: str) -> str:
    """获取权限的中文名称"""
    permission_names = {
        'agent.view': '查看Agent',
        'agent.batch_add': '批量添加Agent',
        'agent.execute': '执行命令',
        'agent.terminal': '使用终端',
        'job.view': '查看作业',
        'job.create': '创建作业',
        'job.edit': '编辑作业',
        'job.delete': '删除作业',
        'job.execute': '执行作业',
        'execution.view': '查看执行历史',
        'execution.stop': '停止执行',
        'project.member_manage': '管理项目成员'
    }
    return permission_names.get(permission_key, permission_key)


"""
租户管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from app.routers.deps import get_current_user, get_server

router = APIRouter(prefix="/api/tenants", tags=["租户管理"])


class CreateTenantRequest(BaseModel):
    """创建租户请求"""
    tenant_code: str = Field(..., min_length=2)
    tenant_name: str = Field(..., min_length=1)
    description: str = ""
    max_users: int = 10
    max_agents: int = 50
    max_concurrent_jobs: int = 10
    storage_quota_gb: int = 100
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""


class UpdateTenantRequest(BaseModel):
    """更新租户请求"""
    tenant_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    max_users: Optional[int] = None
    max_agents: Optional[int] = None
    max_concurrent_jobs: Optional[int] = None
    storage_quota_gb: Optional[int] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)):
    """管理员权限检查"""
    if current_user['role'] not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="权限不足，需要管理员权限")
    return current_user


def require_super_admin(current_user: Dict[str, Any] = Depends(get_current_user)):
    """超级管理员权限检查"""
    if current_user['role'] != 'super_admin':
        raise HTTPException(status_code=403, detail="权限不足，需要超级管理员权限")
    return current_user


@router.get("")
async def get_tenants(
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """获取租户列表"""
    server = get_server()
    
    from app.models.tenant import TenantManager
    tenant_manager = TenantManager(server.db)
    
    offset = (page - 1) * page_size
    tenants = tenant_manager.get_all_tenants(
        status=status,
        limit=page_size,
        offset=offset
    )
    
    total = len(tenants)  # count_tenants不存在，使用len
    
    return {
        'tenants': tenants,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size
    }


@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: int,
    current_user: Dict[str, Any] = Depends(require_super_admin)
):
    """获取租户详情"""
    server = get_server()
    
    from app.models.tenant import TenantManager
    tenant_manager = TenantManager(server.db)
    
    tenant = tenant_manager.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    return {'tenant': tenant}


@router.post("")
async def create_tenant(
    data: CreateTenantRequest,
    current_user: Dict[str, Any] = Depends(require_super_admin)
):
    """创建租户"""
    server = get_server()
    
    from app.models.tenant import TenantManager
    tenant_manager = TenantManager(server.db)
    
    tenant_id = tenant_manager.create_tenant(
        tenant_code=data.tenant_code,
        tenant_name=data.tenant_name,
        description=data.description,
        max_users=data.max_users,
        max_agents=data.max_agents,
        max_concurrent_jobs=data.max_concurrent_jobs,
        storage_quota_gb=data.storage_quota_gb,
        contact_name=data.contact_name,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        created_by=current_user['user_id']
    )
    
    if not tenant_id:
        raise HTTPException(status_code=500, detail="创建租户失败")
    
    return {'message': '租户创建成功', 'tenant_id': tenant_id}


@router.put("/{tenant_id}")
async def update_tenant(
    tenant_id: int,
    data: UpdateTenantRequest,
    current_user: Dict[str, Any] = Depends(require_super_admin)
):
    """更新租户"""
    server = get_server()
    
    from app.models.tenant import TenantManager
    tenant_manager = TenantManager(server.db)
    
    tenant = tenant_manager.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    
    success = tenant_manager.update_tenant(tenant_id, **update_data)
    if not success:
        raise HTTPException(status_code=500, detail="更新租户失败")
    
    return {'message': '租户更新成功'}


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: int,
    current_user: Dict[str, Any] = Depends(require_super_admin)
):
    """删除租户"""
    server = get_server()
    
    from app.models.tenant import TenantManager
    tenant_manager = TenantManager(server.db)
    
    tenant = tenant_manager.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    success = tenant_manager.delete_tenant(tenant_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除租户失败")
    
    return {'message': '租户删除成功'}


@router.get("/{tenant_id}/members")
async def get_tenant_members(
    tenant_id: int,
    current_user: Dict[str, Any] = Depends(require_super_admin)
):
    """获取租户成员列表"""
    server = get_server()
    
    from app.models.tenant import TenantManager
    tenant_manager = TenantManager(server.db)
    
    tenant = tenant_manager.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    members = tenant_manager.get_tenant_members(tenant_id)
    
    return {'members': members}


@router.get("/{tenant_id}/stats")
async def get_tenant_stats(
    tenant_id: int,
    current_user: Dict[str, Any] = Depends(require_super_admin)
):
    """获取租户统计信息"""
    server = get_server()
    
    from app.models.tenant import TenantManager
    tenant_manager = TenantManager(server.db)
    
    tenant = tenant_manager.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    # 获取租户成员数量作为简单统计
    members = tenant_manager.get_tenant_members(tenant_id)
    stats = {
        'member_count': len(members),
        'tenant_id': tenant_id,
        'tenant_name': tenant.get('tenant_name', '')
    }
    
    return {'stats': stats}


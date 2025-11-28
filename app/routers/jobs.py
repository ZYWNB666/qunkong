"""
作业管理 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.routers.deps import get_current_user, get_server, require_permission

router = APIRouter(prefix="/api/jobs", tags=["作业管理"])


class JobStep(BaseModel):
    """作业步骤"""
    name: str
    type: str = "script"
    script: str
    timeout: int = 3600
    execution_user: str = "root"


class CreateJobTemplateRequest(BaseModel):
    """创建作业模板请求"""
    name: str = Field(..., min_length=1)
    description: str = ""
    project_id: int
    category: str = "custom"
    tags: List[str] = []
    steps: List[JobStep]
    default_params: dict = {}
    timeout: int = 7200


class ExecuteJobRequest(BaseModel):
    """执行作业请求"""
    template_id: str
    target_hosts: List[str]
    params: dict = {}


@router.get("/templates")
async def get_job_templates(
    project_id: int = Query(..., description="项目ID"),
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取作业模板列表"""
    server = get_server()
    
    from app.models.jobs import JobManager
    job_manager = JobManager(server.db)
    
    offset = (page - 1) * page_size
    templates = job_manager.get_templates(
        project_id=project_id,
        category=category,
        search=search,
        limit=page_size,
        offset=offset
    )
    
    total = job_manager.count_templates(
        project_id=project_id,
        category=category,
        search=search
    )
    
    return {
        'templates': templates,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size
    }


@router.get("/templates/{template_id}")
async def get_job_template(
    template_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取作业模板详情"""
    server = get_server()
    
    from app.models.jobs import JobManager
    job_manager = JobManager(server.db)
    
    template = job_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="作业模板不存在")
    
    return {'template': template}


@router.post("/templates")
async def create_job_template(
    data: CreateJobTemplateRequest,
    current_user: Dict[str, Any] = Depends(require_permission('job_management'))
):
    """创建作业模板"""
    server = get_server()
    
    from app.models.jobs import JobManager
    job_manager = JobManager(server.db)
    
    template_id = job_manager.create_template(
        name=data.name,
        description=data.description,
        project_id=data.project_id,
        category=data.category,
        tags=data.tags,
        steps=[step.dict() for step in data.steps],
        default_params=data.default_params,
        timeout=data.timeout,
        created_by=current_user['user_id']
    )
    
    if not template_id:
        raise HTTPException(status_code=500, detail="创建作业模板失败")
    
    return {'message': '作业模板创建成功', 'template_id': template_id}


@router.put("/templates/{template_id}")
async def update_job_template(
    template_id: str,
    data: CreateJobTemplateRequest,
    current_user: Dict[str, Any] = Depends(require_permission('job_management'))
):
    """更新作业模板"""
    server = get_server()
    
    from app.models.jobs import JobManager
    job_manager = JobManager(server.db)
    
    template = job_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="作业模板不存在")
    
    success = job_manager.update_template(
        template_id=template_id,
        name=data.name,
        description=data.description,
        category=data.category,
        tags=data.tags,
        steps=[step.dict() for step in data.steps],
        default_params=data.default_params,
        timeout=data.timeout
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="更新作业模板失败")
    
    return {'message': '作业模板更新成功'}


@router.delete("/templates/{template_id}")
async def delete_job_template(
    template_id: str,
    current_user: Dict[str, Any] = Depends(require_permission('job_management'))
):
    """删除作业模板"""
    server = get_server()
    
    from app.models.jobs import JobManager
    job_manager = JobManager(server.db)
    
    template = job_manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="作业模板不存在")
    
    success = job_manager.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除作业模板失败")
    
    return {'message': '作业模板删除成功'}


@router.post("/execute")
async def execute_job(
    data: ExecuteJobRequest,
    current_user: Dict[str, Any] = Depends(require_permission('job_execution'))
):
    """执行作业"""
    server = get_server()
    
    from app.models.jobs import JobManager
    job_manager = JobManager(server.db)
    
    template = job_manager.get_template(data.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="作业模板不存在")
    
    job_id = job_manager.execute_job(
        template_id=data.template_id,
        target_hosts=data.target_hosts,
        params=data.params,
        executed_by=current_user['user_id']
    )
    
    if not job_id:
        raise HTTPException(status_code=500, detail="执行作业失败")
    
    return {'message': '作业已开始执行', 'job_id': job_id}


@router.get("/instances")
async def get_job_instances(
    project_id: int = Query(..., description="项目ID"),
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取作业实例列表"""
    server = get_server()
    
    from app.models.jobs import JobManager
    job_manager = JobManager(server.db)
    
    offset = (page - 1) * page_size
    instances = job_manager.get_instances(
        project_id=project_id,
        status=status,
        limit=page_size,
        offset=offset
    )
    
    total = job_manager.count_instances(project_id=project_id, status=status)
    
    return {
        'instances': instances,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size
    }


@router.get("/instances/{job_id}")
async def get_job_instance(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取作业实例详情"""
    server = get_server()
    
    from app.models.jobs import JobManager
    job_manager = JobManager(server.db)
    
    instance = job_manager.get_instance(job_id)
    if not instance:
        raise HTTPException(status_code=404, detail="作业实例不存在")
    
    return {'instance': instance}


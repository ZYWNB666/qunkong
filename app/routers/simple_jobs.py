"""
简单作业管理 API 路由 - 支持多步骤、多主机组、多变量
"""
import asyncio
import threading
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.routers.deps import get_current_user, get_server

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/simple-jobs", tags=["简单作业"])


# ==================== Pydantic 模型 ====================

class HostGroupRequest(BaseModel):
    """主机组请求"""
    group_name: str
    host_ids: List[str]


class VariableRequest(BaseModel):
    """变量请求"""
    var_name: str
    var_value: str


class StepRequest(BaseModel):
    """步骤请求"""
    step_name: str
    script_content: str
    host_group_id: Optional[str] = None  # 绑定的主机组ID（用于已有ID的情况）
    host_group_index: Optional[int] = None  # 绑定的主机组索引（用于新建时）
    step_order: Optional[int] = None
    timeout: int = 300


class CreateJobRequest(BaseModel):
    """创建作业请求"""
    name: str = Field(..., min_length=1)
    description: str = ""
    host_groups: Optional[List[HostGroupRequest]] = None
    variables: Optional[List[VariableRequest]] = None
    steps: Optional[List[StepRequest]] = None


class UpdateJobRequest(BaseModel):
    """更新作业请求"""
    name: Optional[str] = None
    description: Optional[str] = None


class ExecuteJobRequest(BaseModel):
    """执行作业请求"""
    variables: Optional[Dict[str, str]] = None  # 运行时变量覆盖


# ==================== 作业基本操作 ====================

@router.get("/executions")
async def get_all_executions(
    project_id: int = Query(..., description="项目ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取所有作业执行历史"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    executions = job_manager.get_job_executions(
        project_id=project_id,
        limit=page_size
    )
    
    return {
        'executions': executions,
        'total': len(executions),
        'page': page,
        'page_size': page_size
    }


@router.get("/executions/{execution_id}")
async def get_execution_detail(
    execution_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取执行详情"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    execution = job_manager.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    return {'execution': execution}


@router.get("")
async def get_simple_jobs(
    project_id: int = Query(..., description="项目ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取简单作业列表"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    offset = (page - 1) * page_size
    jobs = job_manager.get_all_jobs(
        project_id=project_id,
        limit=page_size,
        offset=offset
    )
    
    return {
        'jobs': jobs,
        'total': len(jobs),
        'page': page,
        'page_size': page_size
    }


@router.get("/{job_id}")
async def get_simple_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取简单作业详情"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="作业不存在")
    
    return {'job': job}


@router.post("")
async def create_simple_job(
    data: CreateJobRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """创建简单作业"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    # 获取project_id
    project_id = current_user.get('current_project_id', 1)
    
    logger.info(f"创建作业: name={data.name}, project_id={project_id}")
    
    # 创建作业
    job_id = job_manager.create_job(
        name=data.name,
        description=data.description,
        project_id=project_id,
        created_by=current_user['user_id']
    )
    
    if not job_id:
        raise HTTPException(status_code=500, detail="创建作业失败")
    
    logger.info(f"作业创建成功: job_id={job_id}")
    
    # 创建主机组，保存索引到ID的映射
    host_group_ids = []  # 按索引存储主机组ID
    if data.host_groups:
        for hg in data.host_groups:
            group_id = job_manager.add_host_group(
                job_id=job_id,
                group_name=hg.group_name,
                host_ids=hg.host_ids
            )
            host_group_ids.append(group_id)
            if group_id:
                logger.info(f"主机组创建成功: {hg.group_name} -> {group_id}")
    
    # 创建变量
    if data.variables:
        for var in data.variables:
            job_manager.add_variable(
                job_id=job_id,
                var_name=var.var_name,
                var_value=var.var_value
            )
            logger.info(f"变量创建成功: {var.var_name}={var.var_value}")
    
    # 创建步骤
    steps_created = 0
    if data.steps:
        for i, step in enumerate(data.steps):
            # 根据索引获取主机组ID
            host_group_id = None
            if step.host_group_id:
                host_group_id = step.host_group_id
            elif step.host_group_index is not None and step.host_group_index < len(host_group_ids):
                host_group_id = host_group_ids[step.host_group_index]
            
            step_id = job_manager.add_step(
                job_id=job_id,
                step_name=step.step_name,
                script_content=step.script_content,
                host_group_id=host_group_id,
                step_order=step.step_order or (i + 1),
                timeout=step.timeout
            )
            if step_id:
                steps_created += 1
                logger.info(f"步骤创建成功: {step.step_name}, host_group_id={host_group_id}")
    
    logger.info(f"作业 {job_id} 创建完成: {steps_created} 个步骤")
    
    return {
        'message': '作业创建成功', 
        'job_id': job_id,
        'host_groups_created': len(host_group_ids),
        'steps_created': steps_created
    }


@router.put("/{job_id}")
async def update_simple_job(
    job_id: str,
    data: UpdateJobRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """更新简单作业基本信息"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="作业不存在")
    
    update_params = {}
    if data.name is not None:
        update_params['name'] = data.name
    if data.description is not None:
        update_params['description'] = data.description
    
    if update_params:
        success = job_manager.update_job(job_id=job_id, **update_params)
        if not success:
            raise HTTPException(status_code=500, detail="更新作业失败")
    
    return {'message': '作业更新成功'}


@router.delete("/{job_id}")
async def delete_simple_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """删除简单作业"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="作业不存在")
    
    success = job_manager.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除作业失败")
    
    return {'message': '作业删除成功'}


# ==================== 主机组操作 ====================

@router.post("/{job_id}/host-groups")
async def add_host_group(
    job_id: str,
    data: HostGroupRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """添加主机组"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="作业不存在")
    
    group_id = job_manager.add_host_group(
        job_id=job_id,
        group_name=data.group_name,
        host_ids=data.host_ids
    )
    
    if not group_id:
        raise HTTPException(status_code=500, detail="添加主机组失败")
    
    return {'message': '主机组添加成功', 'group_id': group_id}


@router.get("/{job_id}/host-groups")
async def get_host_groups(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取作业的所有主机组"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    groups = job_manager.get_host_groups(job_id)
    return {'host_groups': groups}


@router.put("/{job_id}/host-groups/{group_id}")
async def update_host_group(
    job_id: str,
    group_id: str,
    data: HostGroupRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """更新主机组"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    success = job_manager.update_host_group(
        group_id=group_id,
        group_name=data.group_name,
        host_ids=data.host_ids
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="更新主机组失败")
    
    return {'message': '主机组更新成功'}


@router.delete("/{job_id}/host-groups/{group_id}")
async def delete_host_group(
    job_id: str,
    group_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """删除主机组"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    success = job_manager.delete_host_group(group_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除主机组失败")
    
    return {'message': '主机组删除成功'}


# ==================== 变量操作 ====================

@router.post("/{job_id}/variables")
async def add_variable(
    job_id: str,
    data: VariableRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """添加变量"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="作业不存在")
    
    var_id = job_manager.add_variable(
        job_id=job_id,
        var_name=data.var_name,
        var_value=data.var_value
    )
    
    if not var_id:
        raise HTTPException(status_code=500, detail="添加变量失败")
    
    return {'message': '变量添加成功', 'var_id': var_id}


@router.get("/{job_id}/variables")
async def get_variables(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取作业的所有变量"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    variables = job_manager.get_variables(job_id)
    return {'variables': variables}


@router.put("/{job_id}/variables/{var_id}")
async def update_variable(
    job_id: str,
    var_id: str,
    data: VariableRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """更新变量"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    success = job_manager.update_variable(
        var_id=var_id,
        var_name=data.var_name,
        var_value=data.var_value
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="更新变量失败")
    
    return {'message': '变量更新成功'}


@router.delete("/{job_id}/variables/{var_id}")
async def delete_variable(
    job_id: str,
    var_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """删除变量"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    success = job_manager.delete_variable(var_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除变量失败")
    
    return {'message': '变量删除成功'}


# ==================== 步骤操作 ====================

@router.post("/{job_id}/steps")
async def add_step(
    job_id: str,
    data: StepRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """添加步骤"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="作业不存在")
    
    step_id = job_manager.add_step(
        job_id=job_id,
        step_name=data.step_name,
        script_content=data.script_content,
        host_group_id=data.host_group_id,
        step_order=data.step_order,
        timeout=data.timeout
    )
    
    if not step_id:
        raise HTTPException(status_code=500, detail="添加步骤失败")
    
    return {'message': '步骤添加成功', 'step_id': step_id}


@router.get("/{job_id}/steps")
async def get_steps(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取作业的所有步骤"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    steps = job_manager.get_steps(job_id)
    return {'steps': steps}


@router.put("/{job_id}/steps/{step_id}")
async def update_step(
    job_id: str,
    step_id: str,
    data: StepRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """更新步骤"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    success = job_manager.update_step(
        step_id=step_id,
        step_name=data.step_name,
        script_content=data.script_content,
        host_group_id=data.host_group_id,
        step_order=data.step_order,
        timeout=data.timeout
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="更新步骤失败")
    
    return {'message': '步骤更新成功'}


@router.delete("/{job_id}/steps/{step_id}")
async def delete_step(
    job_id: str,
    step_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """删除步骤"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    success = job_manager.delete_step(step_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除步骤失败")
    
    return {'message': '步骤删除成功'}


# ==================== 执行作业 ====================

@router.post("/{job_id}/execute")
async def execute_simple_job(
    job_id: str,
    data: ExecuteJobRequest = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """执行简单作业 - 只记录到作业执行历史，不创建单独的task"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="作业不存在")
    
    logger.info(f"执行作业: {job['name']}, 步骤数: {len(job.get('steps', []))}")
    
    # 检查是否有步骤
    steps = job.get('steps', [])
    if not steps:
        raise HTTPException(status_code=400, detail="作业没有步骤，无法执行")
    
    # 创建执行记录
    execution_id = job_manager.create_execution(job_id)
    if not execution_id:
        raise HTTPException(status_code=500, detail="创建执行记录失败")
    
    logger.info(f"执行记录创建成功: {execution_id}")
    
    # 合并运行时变量
    runtime_vars = {}
    for var in job.get('variables', []):
        runtime_vars[var['var_name']] = var['var_value']
    if data and data.variables:
        runtime_vars.update(data.variables)
    
    # 异步执行作业步骤
    def run_job():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            all_results = {}
            
            for i, step in enumerate(steps):
                step_num = i + 1
                logger.info(f"执行步骤 {step_num}/{len(steps)}: {step['step_name']}")
                
                # 更新当前步骤
                job_manager.update_execution(
                    execution_id,
                    current_step=step_num,
                    log_entry=f"开始执行步骤 {step_num}: {step['step_name']}"
                )
                
                # 获取主机组的主机列表
                host_group_id = step.get('host_group_id')
                target_hosts = []
                
                if host_group_id:
                    # 从主机组获取主机
                    for hg in job.get('host_groups', []):
                        if hg['id'] == host_group_id:
                            target_hosts = hg.get('host_ids', [])
                            break
                
                if not target_hosts:
                    # 如果没有指定主机组，尝试获取第一个主机组的主机
                    if job.get('host_groups'):
                        target_hosts = job['host_groups'][0].get('host_ids', [])
                
                if not target_hosts:
                    job_manager.update_execution(
                        execution_id,
                        log_entry=f"步骤 {step_num} 没有目标主机，跳过"
                    )
                    continue
                
                # 替换脚本中的变量
                script = step['script_content']
                for var_name, var_value in runtime_vars.items():
                    script = script.replace(f'${{{var_name}}}', var_value)
                    script = script.replace(f'${var_name}', var_value)
                
                # 执行脚本到所有目标主机
                step_results = {}
                for host_id in target_hosts:
                    try:
                        result = loop.run_until_complete(
                            server.execute_script_on_agent(host_id, script, step.get('timeout', 300))
                        )
                        step_results[host_id] = result
                        
                        # 记录执行结果
                        status_text = "成功" if result.get('exit_code') == 0 else "失败"
                        job_manager.update_execution(
                            execution_id,
                            log_entry=f"主机 {host_id} 执行{status_text}: exit_code={result.get('exit_code')}"
                        )
                    except Exception as e:
                        step_results[host_id] = {
                            'exit_code': -1,
                            'error': str(e)
                        }
                        job_manager.update_execution(
                            execution_id,
                            log_entry=f"主机 {host_id} 执行异常: {str(e)}"
                        )
                
                all_results[f"step_{step_num}"] = {
                    'step_name': step['step_name'],
                    'results': step_results
                }
            
            # 更新执行完成状态
            job_manager.update_execution(
                execution_id,
                status='COMPLETED',
                results=all_results,
                log_entry="作业执行完成"
            )
            logger.info(f"作业执行完成: {execution_id}")
            
        except Exception as e:
            logger.error(f"作业执行失败: {e}")
            job_manager.update_execution(
                execution_id,
                status='FAILED',
                error_message=str(e),
                log_entry=f"作业执行失败: {str(e)}"
            )
        finally:
            loop.close()
    
    # 在后台线程执行
    thread = threading.Thread(target=run_job)
    thread.daemon = True
    thread.start()
    
    return {
        'message': '作业已开始执行',
        'execution_id': execution_id,
        'job_name': job['name'],
        'total_steps': len(steps)
    }


@router.get("/{job_id}/history")
async def get_simple_job_history(
    job_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """获取作业执行历史"""
    server = get_server()
    
    from app.models.simple_jobs import SimpleJobManager
    job_manager = SimpleJobManager(server.db)
    
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="作业不存在")
    
    executions = job_manager.get_job_executions(
        job_id=job_id,
        limit=page_size
    )
    
    return {
        'history': executions,
        'total': len(executions),
        'page': page,
        'page_size': page_size
    }

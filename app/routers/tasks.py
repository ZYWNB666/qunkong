"""
任务执行 API 路由
"""
import asyncio
import threading
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
from app.routers.deps import (
    get_current_user, get_server, ExecuteScriptRequest
)
from app.routers.rbac import require_permission

router = APIRouter(prefix="/api", tags=["任务执行"])


@router.get("/tasks")
async def get_tasks(
    current_user: Dict[str, Any] = Depends(require_permission('job.view'))
):
    """获取执行历史"""
    project_id = current_user.get('current_project_id')
    server = get_server()
    
    history = server.db.get_execution_history(project_id=project_id, limit=100)
    
    running_tasks = []
    for task_id, task in server.tasks.items():
        task_exists = any(h['id'] == task_id for h in history)
        if not task_exists:
            task_data = {
                'id': task.id,
                'script_name': getattr(task, 'script_name', '未命名任务'),
                'script': task.script,
                'script_params': getattr(task, 'script_params', ''),
                'target_hosts': task.target_hosts,
                'status': task.status,
                'created_at': task.created_at,
                'started_at': task.started_at,
                'completed_at': task.completed_at,
                'timeout': task.timeout,
                'execution_user': getattr(task, 'execution_user', 'root'),
                'results': task.results,
                'error_message': getattr(task, 'error_message', '')
            }
            running_tasks.append(task_data)
    
    all_tasks = history + running_tasks
    all_tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    formatted_tasks = []
    for task in all_tasks:
        formatted_task = dict(task)
        formatted_task['task_id'] = formatted_task.pop('id', '')
        formatted_task['agent_count'] = len(formatted_task.get('target_hosts', []))
        if 'status' in formatted_task:
            formatted_task['status'] = formatted_task['status'].lower()
        formatted_tasks.append(formatted_task)
    
    return {'tasks': formatted_tasks}


@router.post("/tasks")
async def create_task(
    data: ExecuteScriptRequest,
    current_user: Dict[str, Any] = Depends(require_permission('script.execute'))
):
    """创建新任务"""
    # 从用户上下文获取project_id
    project_id = current_user.get('current_project_id')
    server = get_server()
    
    task_id = server.create_task(
        script=data.script,
        target_hosts=data.target_hosts,
        script_name=data.script_name,
        script_params=data.script_params,
        timeout=data.timeout,
        execution_user=data.execution_user,
        project_id=project_id
    )
    
    return {'task_id': task_id, 'message': 'Task created successfully'}


@router.get("/tasks/{task_id}")
async def get_task_details(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_permission('job.view'))
):
    """获取任务详细信息"""
    server = get_server()
    
    history = server.db.get_execution_history(limit=1000)
    task_info = None
    
    for task in history:
        if task['id'] == task_id:
            task_info = task
            break
    
    if not task_info:
        for task_id_key, task in server.tasks.items():
            if task_id_key == task_id:
                task_info = {
                    'id': task.id,
                    'script_name': getattr(task, 'script_name', '未命名任务'),
                    'script': task.script,
                    'script_params': getattr(task, 'script_params', ''),
                    'target_hosts': task.target_hosts,
                    'status': task.status,
                    'created_at': task.created_at,
                    'started_at': task.started_at,
                    'completed_at': task.completed_at,
                    'timeout': task.timeout,
                    'execution_user': getattr(task, 'execution_user', 'root'),
                    'results': task.results,
                    'error_message': getattr(task, 'error_message', '')
                }
                break
    
    if not task_info:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task_info


@router.post("/execute")
async def execute_script(
    data: ExecuteScriptRequest,
    current_user: Dict[str, Any] = Depends(require_permission('script.execute'))
):
    """执行脚本"""
    server = get_server()
    
    # 从用户上下文获取project_id
    project_id = current_user.get('current_project_id')
    
    task_id = server.create_task(
        script=data.script,
        target_hosts=data.target_hosts,
        script_name=data.script_name,
        script_params=data.script_params,
        timeout=data.timeout,
        execution_user=data.execution_user,
        project_id=project_id
    )
    
    def run_task():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.dispatch_task(task_id))
        loop.close()
    
    thread = threading.Thread(target=run_task)
    thread.daemon = True
    thread.start()
    
    return {'task_id': task_id, 'message': 'Task started successfully'}


@router.post("/tasks/{task_id}/retry")
async def retry_task(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_permission('script.execute'))
):
    """重试任务"""
    server = get_server()
    
    history = server.db.get_execution_history(limit=1000)
    original_task = None
    
    for task in history:
        if task['id'] == task_id:
            original_task = task
            break
    
    if not original_task:
        raise HTTPException(status_code=404, detail="Original task not found")
    
    new_task_id = server.create_task(
        script=original_task.get('script_content', original_task.get('script', '')),
        target_hosts=original_task.get('target_hosts', []),
        script_name=f"[重试] {original_task.get('script_name', '未命名任务')}",
        script_params=original_task.get('script_params', ''),
        timeout=original_task.get('timeout', 7200),
        execution_user=original_task.get('execution_user', 'root')
    )
    
    def run_task():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.dispatch_task(new_task_id))
        loop.close()
    
    thread = threading.Thread(target=run_task)
    thread.daemon = True
    thread.start()
    
    return {
        'task_id': new_task_id,
        'message': 'Task retry started successfully',
        'original_task_id': task_id
    }


@router.post("/tasks/{task_id}/stop")
async def stop_task(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_permission('script.execute'))
):
    """停止任务"""
    server = get_server()
    
    if task_id not in server.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = server.tasks[task_id]
    if task.status != 'RUNNING':
        raise HTTPException(status_code=400, detail="Task is not running")
    
    task.status = 'CANCELLED'
    task.completed_at = datetime.now().isoformat()
    task.error_message = '任务被用户手动停止'
    
    task_data = {
        'id': task.id,
        'script_name': getattr(task, 'script_name', '未命名任务'),
        'script': task.script,
        'script_params': getattr(task, 'script_params', ''),
        'target_hosts': task.target_hosts,
        'project_id': getattr(task, 'project_id', None),
        'status': task.status,
        'created_at': task.created_at,
        'started_at': task.started_at,
        'completed_at': task.completed_at,
        'timeout': task.timeout,
        'execution_user': getattr(task, 'execution_user', 'root'),
        'results': task.results,
        'error_message': task.error_message
    }
    server.db.save_execution_history(task_data)
    
    return {'message': 'Task stopped successfully'}


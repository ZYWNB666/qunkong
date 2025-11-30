"""
Agent 管理 API 路由
"""
import asyncio
import json
import logging
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from app.routers.deps import (
    get_current_user, get_server, BatchAgentRequest
)
from app.routers.rbac import (
    require_permission, require_project_access, require_system_admin
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Agent管理"])


class CleanupRequest(BaseModel):
    """清理请求"""
    offline_hours: int = 24


@router.get("/agents")
async def get_agents(
    tenant_id: Optional[int] = Query(None, description="租户ID(已废弃)"),
    current_user: Dict[str, Any] = Depends(require_permission('agent.view'))
):
    """获取Agent列表（支持项目隔离）"""
    project_id = current_user.get('current_project_id')
    server = get_server()
    user_role = current_user['role']
    user_id = current_user['user_id']
    
    # 非admin用户，只能看到自己有权限的项目的agents
    if user_role not in ['admin', 'super_admin']:
        # 如果指定了project_id，检查用户是否有该项目权限
        if project_id:
            # 检查project_members表
            conn = server.db._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT role FROM project_members
                WHERE project_id = %s AND user_id = %s AND status = 'active'
            ''', (project_id, user_id))
            if not cursor.fetchone():
                conn.close()
                raise HTTPException(status_code=403, detail="无权访问此项目")
            conn.close()
    
    # 获取Agent信息（支持租户和项目过滤）
    db_agents = server.db.get_all_agents(tenant_id=tenant_id, project_id=project_id)
    
    # 本地内存中的 Agent（当前节点连接的）
    local_agents = {agent.id: agent for agent in server.agents.values()}
    
    agents_list = []
    for db_agent in db_agents:
        agent_id = db_agent['id']
        local_agent = local_agents.get(agent_id)
        
        # 判断状态：优先使用本地实时状态，否则使用数据库状态
        if local_agent:
            # Agent 连接在当前节点
            status = local_agent.status.lower()  # 改为小写
            last_heartbeat = local_agent.last_heartbeat
        else:
            # Agent 可能连接在其他节点，或者已离线
            # 使用数据库中的状态
            status = db_agent.get('status', 'offline').lower()  # 改为小写
            last_heartbeat = db_agent.get('last_heartbeat', '')
        
        agent_dict = {
            'id': agent_id,
            'hostname': db_agent.get('hostname', 'Unknown'),
            'ip_address': db_agent.get('ip_address', ''),
            'os_type': db_agent.get('os_type', 'unknown'),
            'os_version': db_agent.get('os_version', ''),
            'agent_version': db_agent.get('agent_version', '1.0.0'),
            'status': status,
            'last_heartbeat': last_heartbeat,
            'register_time': db_agent.get('register_time', ''),
            'cpu_count': db_agent.get('cpu_count', 0),
            'memory_total': db_agent.get('memory_total', 0),
            'disk_total': db_agent.get('disk_total', 0),
            'external_ip': db_agent.get('external_ip', '')
        }
        agents_list.append(agent_dict)
    
    return {'agents': agents_list}


@router.get("/agents/{agent_id}")
async def get_agent_details(
    agent_id: str,
    current_user: Dict[str, Any] = Depends(require_permission('agent.view'))
):
    """获取Agent详细信息（包含实时资源信息）"""
    server = get_server()
    
    # 传递本地缓存实例，优先读取实时资源信息
    agent_info = server.db.get_agent_system_info(agent_id, local_cache=server.local_cache)
    if not agent_info:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent_info


@router.get("/agents/{agent_id}/tasks")
async def get_agent_tasks(
    agent_id: str,
    current_user: Dict[str, Any] = Depends(require_permission('agent.view'))
):
    """获取指定Agent的执行历史"""
    server = get_server()
    
    all_history = server.db.get_execution_history(limit=1000)
    
    agent_tasks = []
    for task in all_history:
        target_hosts = task.get('target_hosts', [])
        if agent_id in target_hosts:
            agent_tasks.append(task)
    
    return agent_tasks


@router.post("/agents/{agent_id}/restart")
async def restart_agent(
    agent_id: str,
    current_user: Dict[str, Any] = Depends(require_permission('agent.restart'))
):
    """重启Agent"""
    server = get_server()
    
    if agent_id not in server.agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = server.agents[agent_id]
    if agent.status != 'ONLINE':
        raise HTTPException(status_code=400, detail="Agent is not online")
    
    # 发送重启命令
    try:
        if server.loop:
            future = asyncio.run_coroutine_threadsafe(
                server.send_agent_restart(agent_id),
                server.loop
            )
            success, message = future.result(timeout=5)
            if not success:
                raise HTTPException(status_code=500, detail=message)
        else:
            restart_message = {
                'type': 'restart_agent',
                'agent_id': agent_id,
                'message': 'Server requested agent restart'
            }
            await agent.websocket.send(json.dumps(restart_message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重启Agent失败: {str(e)}")
    
    return {'message': f'Agent {agent_id} restart command sent successfully'}


@router.post("/agents/{agent_id}/restart-host")
async def restart_host(
    agent_id: str,
    current_user: Dict[str, Any] = Depends(require_permission('agent.restart'))
):
    """重启主机"""
    server = get_server()
    
    if agent_id not in server.agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = server.agents[agent_id]
    if agent.status != 'ONLINE':
        raise HTTPException(status_code=400, detail="Agent is not online")
    
    try:
        restart_message = {
            'type': 'restart_host',
            'agent_id': agent_id,
            'message': 'Server requested host restart'
        }
        await agent.websocket.send(json.dumps(restart_message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重启主机失败: {str(e)}")
    
    return {'message': f'Host restart command sent to agent {agent_id} successfully'}


@router.post("/agents/{agent_id}/terminal")
async def create_terminal_session(
    agent_id: str,
    current_user: Dict[str, Any] = Depends(require_permission('terminal.access'))
):
    """创建终端会话"""
    server = get_server()
    
    if agent_id not in server.agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = server.agents[agent_id]
    if agent.status != 'ONLINE':
        raise HTTPException(status_code=400, detail="Agent is not online")
    
    return {
        'agent_id': agent_id,
        'websocket_url': f'ws://localhost:{server.port}/terminal/{agent_id}',
        'message': 'Terminal session can be created'
    }


@router.post("/agents/batch")
async def batch_manage_agents(
    data: BatchAgentRequest,
    current_user: Dict[str, Any] = Depends(require_permission('agent.delete'))
):
    """批量管理Agent"""
    server = get_server()
    
    results = []
    action = data.action
    agent_ids = data.agent_ids
    
    if action in ['delete_offline', 'delete_down']:
        for agent_id in agent_ids:
            try:
                agent_status = None
                if agent_id in server.agents:
                    agent = server.agents[agent_id]
                    agent_status = agent.status
                    
                    if agent_status not in ['OFFLINE', 'DOWN']:
                        results.append({
                            'agent_id': agent_id,
                            'success': False,
                            'message': f'Agent状态为{agent_status}，只能删除OFFLINE或DOWN状态的Agent'
                        })
                        continue
                    
                    del server.agents[agent_id]
                
                conn = server.db._get_connection()
                cursor = conn.cursor()
                cursor.execute('DELETE FROM agents WHERE id = %s', (agent_id,))
                affected_rows = cursor.rowcount
                cursor.execute('DELETE FROM agent_system_info WHERE agent_id = %s', (agent_id,))
                conn.close()
                
                results.append({
                    'agent_id': agent_id,
                    'success': affected_rows > 0,
                    'message': 'Agent删除成功' if affected_rows > 0 else 'Agent不存在'
                })
            except Exception as e:
                results.append({
                    'agent_id': agent_id,
                    'success': False,
                    'message': f'删除失败: {str(e)}'
                })
    
    elif action == 'restart':
        if not server.loop:
            raise HTTPException(status_code=500, detail="服务器事件循环未就绪")
        
        for agent_id in agent_ids:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    server.send_agent_restart(agent_id),
                    server.loop
                )
                success, message = future.result(timeout=5)
                results.append({
                    'agent_id': agent_id,
                    'success': success,
                    'message': message
                })
            except FutureTimeoutError:
                results.append({
                    'agent_id': agent_id,
                    'success': False,
                    'message': '发送超时'
                })
            except Exception as e:
                results.append({
                    'agent_id': agent_id,
                    'success': False,
                    'message': f'重启失败: {str(e)}'
                })
    
    elif action == 'update':
        if not data.version:
            raise HTTPException(status_code=400, detail="请指定目标版本")
        if not data.download_url:
            raise HTTPException(status_code=400, detail="请提供下载URL")
        if not data.md5:
            raise HTTPException(status_code=400, detail="请提供MD5校验值")
        
        if not server.loop:
            raise HTTPException(status_code=500, detail="服务器事件循环未就绪")
        
        for agent_id in agent_ids:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    server.send_agent_update(agent_id, data.version, data.download_url, data.md5),
                    server.loop
                )
                success, message = future.result(timeout=5)
                results.append({
                    'agent_id': agent_id,
                    'success': success,
                    'message': message
                })
            except FutureTimeoutError:
                results.append({
                    'agent_id': agent_id,
                    'success': False,
                    'message': '发送超时'
                })
            except Exception as e:
                results.append({
                    'agent_id': agent_id,
                    'success': False,
                    'message': f'发送失败: {str(e)}'
                })
    
    else:
        raise HTTPException(status_code=400, detail=f"不支持的操作类型: {action}")
    
    success_count = sum(1 for r in results if r['success'])
    
    return {
        'message': f'批量操作完成，成功: {success_count}/{len(results)}',
        'results': results,
        'success_count': success_count,
        'total_count': len(results)
    }


@router.post("/agents/cleanup")
async def cleanup_offline_agents(
    data: CleanupRequest = None,
    current_user: Dict[str, Any] = Depends(require_permission('agent.delete'))
):
    """清理离线Agent"""
    server = get_server()
    
    offline_hours = data.offline_hours if data else 24
    
    # 获取本地内存中的在线Agent
    local_agents = {agent.id: agent for agent in server.agents.values()}
    
    all_agents = server.db.get_all_agents()
    deleted_agents = []
    
    for agent in all_agents:
        agent_id = agent['id']
        should_delete = False
        
        # 判断是否应该删除
        if offline_hours == 0:
            # offline_hours=0表示清理所有离线的agent
            # 检查agent是否在线
            local_agent = local_agents.get(agent_id)
            if local_agent:
                # Agent在本地内存中，检查状态
                is_online = local_agent.status.lower() in ['online', 'connected']
                should_delete = not is_online
            else:
                # Agent不在本地内存中，检查数据库状态
                db_status = agent.get('status', 'offline').lower()
                is_online = db_status in ['online', 'connected']
                should_delete = not is_online
        else:
            # 按时间清理
            if agent['last_heartbeat']:
                try:
                    last_heartbeat = datetime.fromisoformat(agent['last_heartbeat'])
                    threshold_time = datetime.now() - timedelta(hours=offline_hours)
                    should_delete = last_heartbeat < threshold_time
                except Exception as e:
                    logger.error(f"解析心跳时间失败 {agent['id']}: {e}")
        
        # 执行删除
        if should_delete:
            try:
                if agent_id in server.agents:
                    del server.agents[agent_id]
                
                conn = server.db._get_connection()
                cursor = conn.cursor()
                cursor.execute('DELETE FROM agents WHERE id = %s', (agent_id,))
                cursor.execute('DELETE FROM agent_system_info WHERE agent_id = %s', (agent_id,))
                conn.close()
                
                deleted_agents.append({
                    'id': agent_id,
                    'hostname': agent['hostname'],
                    'ip': agent['ip_address'],
                    'last_heartbeat': agent['last_heartbeat']
                })
            except Exception as e:
                logger.error(f"删除Agent {agent_id} 失败: {e}")
    
    message = f'清理完成，删除了 {len(deleted_agents)} 个离线的Agent' if offline_hours == 0 else f'清理完成，删除了 {len(deleted_agents)} 个超过{offline_hours}小时离线的Agent'
    
    return {
        'message': message,
        'deleted_agents': deleted_agents,
        'deleted_count': len(deleted_agents)
    }


@router.get("/servers")
async def get_servers(
    current_user: Dict[str, Any] = Depends(require_permission('agent.view'))
):
    """获取服务器列表"""
    server = get_server()
    
    agents = server.db.get_all_agents()
    servers = []
    for agent in agents:
        servers.append({
            'id': agent['id'],
            'hostname': agent['hostname'],
            'ip': agent['ip_address'],
            'external_ip': agent.get('external_ip', ''),
            'status': agent['status'],
            'last_heartbeat': agent['last_heartbeat'],
            'register_time': agent['register_time']
        })
    
    return servers


@router.get("/terminal/sessions")
async def get_terminal_sessions(
    current_user: Dict[str, Any] = Depends(require_permission('terminal.access'))
):
    """获取当前活跃的终端会话"""
    server = get_server()
    
    sessions = []
    for session_id, session in server.terminal_manager.sessions.items():
        sessions.append({
            'session_id': session_id,
            'agent_id': session.agent_id,
            'user_id': session.user_id,
            'created_at': session.created_at,
            'last_activity': session.last_activity,
            'is_active': session.is_active,
            'command_count': len(session.command_history)
        })
    
    return sessions


@router.delete("/terminal/sessions/{session_id}")
async def close_terminal_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(require_permission('terminal.access'))
):
    """关闭指定的终端会话"""
    server = get_server()
    
    session = server.terminal_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Terminal session not found")
    

@router.post("/agents/{agent_id}/assign-project")
async def assign_agent_to_project(
    agent_id: str,
    target_project_id: int = Query(..., description="目标项目ID"),
    can_execute: bool = Query(True),
    can_terminal: bool = Query(True),
    current_user: Dict[str, Any] = Depends(require_system_admin)
):
    """将Agent分配给项目（仅系统管理员）"""
    server = get_server()
    user_id = current_user['user_id']
    
    # 执行分配
    success = server.db.assign_agent_to_project(
        project_id=target_project_id,
        agent_id=agent_id,
        can_execute=can_execute,
        can_terminal=can_terminal,
        assigned_by=user_id
    )
    
    if success:
        return {'message': f'Agent {agent_id} 已分配给项目 {target_project_id}', 'success': True}
    else:
        raise HTTPException(status_code=500, detail="分配失败")


@router.delete("/agents/{agent_id}/remove-project/{target_project_id}")
async def remove_agent_from_project(
    agent_id: str,
    target_project_id: int,
    current_user: Dict[str, Any] = Depends(require_system_admin)
):
    """从项目中移除Agent（仅系统管理员）"""
    server = get_server()
    
    success = server.db.remove_agent_from_project(target_project_id, agent_id)
    
    if success:
        return {'message': f'Agent {agent_id} 已从项目 {target_project_id} 中移除', 'success': True}
    else:
        raise HTTPException(status_code=500, detail="移除失败")


@router.get("/projects/{target_project_id}/agents")
async def get_project_agents(
    target_project_id: int,
    current_user: Dict[str, Any] = Depends(require_system_admin)
):
    """获取项目的Agent列表（仅系统管理员）"""
    server = get_server()
    
    agents = server.db.get_project_agents(target_project_id)
    return {'agents': agents, 'total': len(agents)}


@router.put("/agents/{agent_id}/tenant")
async def update_agent_tenant(
    agent_id: str,
    tenant_id: int = Query(...),
    current_user: Dict[str, Any] = Depends(require_system_admin)
):
    """更新Agent的租户（已废弃，仅系统管理员）"""
    server = get_server()
    
    success = server.db.update_agent_tenant(agent_id, tenant_id)
    
    if success:
        return {'message': f'Agent {agent_id} 租户已更新', 'success': True}
    else:
        raise HTTPException(status_code=500, detail="更新失败")


@router.put("/agents/{agent_id}/project")
async def update_agent_default_project(
    agent_id: str,
    target_project_id: int = Query(..., description="目标项目ID"),
    current_user: Dict[str, Any] = Depends(require_system_admin)
):
    """更新Agent的默认项目（仅系统管理员）"""
    server = get_server()
    
    success = server.db.update_agent_project(agent_id, target_project_id)
    
    if success:
        return {'message': f'Agent {agent_id} 默认项目已更新', 'success': True}
    else:
        raise HTTPException(status_code=500, detail="更新失败")


@router.post("/agents/batch-assign")
async def batch_assign_agents(
    agent_ids: List[str] = Query(...),
    target_project_id: int = Query(..., description="目标项目ID"),
    can_execute: bool = Query(True),
    can_terminal: bool = Query(True),
    current_user: Dict[str, Any] = Depends(require_system_admin)
):
    """批量分配Agent到项目（仅系统管理员）"""
    server = get_server()
    user_id = current_user['user_id']
    
    results = []
    success_count = 0
    
    for agent_id in agent_ids:
        success = server.db.assign_agent_to_project(
            project_id=target_project_id,
            agent_id=agent_id,
            can_execute=can_execute,
            can_terminal=can_terminal,
            assigned_by=user_id
        )
        
        results.append({
            'agent_id': agent_id,
            'success': success
        })
        
        if success:
            success_count += 1
    
    return {
        'message': f'批量分配完成，成功: {success_count}/{len(agent_ids)}',
        'results': results,
        'success_count': success_count,
        'total_count': len(agent_ids)
    }

    if server.loop:
        future = asyncio.run_coroutine_threadsafe(
            server.close_terminal_session(session_id),
            server.loop
        )
        future.result(timeout=5)
    
    return {'message': 'Terminal session closed successfully'}


@router.get("/terminal/commands/allowed")
async def get_allowed_commands(
    current_user: Dict[str, Any] = Depends(require_permission('terminal.access'))
):
    """获取允许的命令列表"""
    server = get_server()
    
    return {
        'allowed_commands': server.terminal_manager.allowed_commands,
        'forbidden_commands': server.terminal_manager.forbidden_commands,
        'session_timeout': server.terminal_manager.session_timeout,
        'max_sessions_per_agent': server.terminal_manager.max_sessions_per_agent
    }


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
    get_current_user, get_server, require_permission, BatchAgentRequest
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Agent管理"])


class CleanupRequest(BaseModel):
    """清理请求"""
    offline_hours: int = 24


@router.get("/agents")
async def get_agents(
    project_id: Optional[int] = Query(None, description="项目ID")
):
    """获取Agent列表（集群模式下从数据库获取，确保所有节点数据一致）"""
    server = get_server()
    
    # 从数据库获取所有 Agent 信息（数据库是集群共享的）
    db_agents = server.db.get_all_agents()
    
    # 本地内存中的 Agent（当前节点连接的）
    local_agents = {agent.id: agent for agent in server.agents.values()}
    
    agents_list = []
    for db_agent in db_agents:
        agent_id = db_agent['id']
        local_agent = local_agents.get(agent_id)
        
        # 判断状态：优先使用本地实时状态，否则使用数据库状态
        if local_agent:
            # Agent 连接在当前节点
            status = local_agent.status.upper()
            last_heartbeat = local_agent.last_heartbeat
        else:
            # Agent 可能连接在其他节点，或者已离线
            # 使用数据库中的状态
            status = db_agent.get('status', 'OFFLINE').upper()
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
async def get_agent_details(agent_id: str):
    """获取Agent详细信息（包含实时资源信息）"""
    server = get_server()
    
    # 传递本地缓存实例，优先读取实时资源信息
    agent_info = server.db.get_agent_system_info(agent_id, local_cache=server.local_cache)
    if not agent_info:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent_info


@router.get("/agents/{agent_id}/tasks")
async def get_agent_tasks(agent_id: str):
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
    current_user: Dict[str, Any] = Depends(require_permission('agent_management'))
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
    current_user: Dict[str, Any] = Depends(require_permission('agent_management'))
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
async def create_terminal_session(agent_id: str):
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
    current_user: Dict[str, Any] = Depends(require_permission('agent_management'))
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
    current_user: Dict[str, Any] = Depends(require_permission('agent_management'))
):
    """清理离线Agent"""
    server = get_server()
    
    offline_hours = data.offline_hours if data else 24
    threshold_time = datetime.now() - timedelta(hours=offline_hours)
    
    all_agents = server.db.get_all_agents()
    deleted_agents = []
    
    for agent in all_agents:
        if agent['last_heartbeat']:
            try:
                last_heartbeat = datetime.fromisoformat(agent['last_heartbeat'])
                if last_heartbeat < threshold_time:
                    if agent['id'] in server.agents:
                        del server.agents[agent['id']]
                    
                    conn = server.db._get_connection()
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM agents WHERE id = %s', (agent['id'],))
                    cursor.execute('DELETE FROM agent_system_info WHERE agent_id = %s', (agent['id'],))
                    conn.close()
                    
                    deleted_agents.append({
                        'id': agent['id'],
                        'hostname': agent['hostname'],
                        'ip': agent['ip_address'],
                        'last_heartbeat': agent['last_heartbeat']
                    })
            except Exception as e:
                logger.error(f"删除Agent {agent['id']} 失败: {e}")
    
    return {
        'message': f'清理完成，删除了 {len(deleted_agents)} 个长时间离线的Agent',
        'deleted_agents': deleted_agents,
        'deleted_count': len(deleted_agents)
    }


@router.get("/servers")
async def get_servers():
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
async def get_terminal_sessions():
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
async def close_terminal_session(session_id: str):
    """关闭指定的终端会话"""
    server = get_server()
    
    session = server.terminal_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Terminal session not found")
    
    if server.loop:
        future = asyncio.run_coroutine_threadsafe(
            server.close_terminal_session(session_id),
            server.loop
        )
        future.result(timeout=5)
    
    return {'message': 'Terminal session closed successfully'}


@router.get("/terminal/commands/allowed")
async def get_allowed_commands():
    """获取允许的命令列表"""
    server = get_server()
    
    return {
        'allowed_commands': server.terminal_manager.allowed_commands,
        'forbidden_commands': server.terminal_manager.forbidden_commands,
        'session_timeout': server.terminal_manager.session_timeout,
        'max_sessions_per_agent': server.terminal_manager.max_sessions_per_agent
    }


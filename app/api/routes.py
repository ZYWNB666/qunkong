"""
API路由定义
"""
import json
import logging
import threading
import asyncio
from flask import Blueprint, jsonify, request
from app.models import DatabaseManager
from app.api.auth import require_auth, require_permission
from dataclasses import asdict

logger = logging.getLogger(__name__)

# 创建蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')

# 全局变量，将在应用初始化时设置
server_instance = None

def init_api(server):
    """初始化API，设置服务器实例"""
    global server_instance
    server_instance = server

@api_bp.route('/tasks', methods=['GET'])
@require_auth
def get_tasks():
    """获取执行历史"""
    if server_instance:
        # 从数据库获取执行历史
        history = server_instance.db.get_execution_history(limit=100)
        
        # 添加内存中正在执行的任务
        running_tasks = []
        for task_id, task in server_instance.tasks.items():
            # 检查是否已经在历史记录中
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
        
        # 合并历史记录和正在执行的任务，按创建时间排序
        all_tasks = history + running_tasks
        all_tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify(all_tasks)
    return jsonify([])

@api_bp.route('/tasks', methods=['POST'])
@require_auth
@require_permission('script_execution')
def create_task():
    """创建新任务"""
    if not server_instance:
        return jsonify({'error': 'Server not available'}), 500
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # 创建任务
    task_id = server_instance.create_task(
        script=data.get('script', ''),
        target_hosts=data.get('target_hosts', []),
        script_name=data.get('script_name', '未命名任务'),
        script_params=data.get('script_params', ''),
        timeout=data.get('timeout', 7200),
        execution_user=data.get('execution_user', 'root')
    )
    
    return jsonify({'task_id': task_id, 'message': 'Task created successfully'})

@api_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task_details(task_id):
    """获取任务详细信息"""
    if not server_instance:
        return jsonify({'error': 'Server not available'}), 500

    # 从数据库获取任务详情
    history = server_instance.db.get_execution_history(limit=1000)
    task_info = None
    for task in history:
        if task['id'] == task_id:
            task_info = task
            break

    if not task_info:
        # 如果数据库中没有找到，尝试从内存中的任务列表查找
        for task_id_key, task in server_instance.tasks.items():
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
        return jsonify({'error': 'Task not found'}), 404

    return jsonify(task_info)

@api_bp.route('/servers', methods=['GET'])
def get_servers():
    """获取服务器列表"""
    if not server_instance:
        return jsonify([])
    
    # 从数据库获取Agent列表
    agents = server_instance.db.get_all_agents()
    servers = []
    for agent in agents:
        servers.append({
            'id': agent['id'],
            'hostname': agent['hostname'],
            'ip': agent['ip_address'],  # 内网IP
            'external_ip': agent.get('external_ip', ''),  # 外网IP
            'status': agent['status'],
            'last_heartbeat': agent['last_heartbeat'],
            'register_time': agent['register_time']
        })
    return jsonify(servers)

@api_bp.route('/agents', methods=['GET'])
def get_agents():
    """获取Agent列表"""
    if server_instance:
        return jsonify([asdict(agent) for agent in server_instance.agents.values()])
    return jsonify([])

@api_bp.route('/agents/<agent_id>', methods=['GET'])
def get_agent_details(agent_id):
    """获取Agent详细信息"""
    if not server_instance:
        return jsonify({'error': 'Server not available'}), 500

    # 从数据库获取Agent系统信息
    agent_info = server_instance.db.get_agent_system_info(agent_id)
    
    if not agent_info:
        return jsonify({'error': 'Agent not found'}), 404
    
    return jsonify(agent_info)

@api_bp.route('/execute', methods=['POST'])
@require_auth
@require_permission('script_execution')
def execute_script():
    """执行脚本"""
    if not server_instance:
        return jsonify({'error': 'Server not available'}), 500
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        # 创建任务
        task_id = server_instance.create_task(
            script=data.get('script', ''),
            target_hosts=data.get('target_hosts', []),
            script_name=data.get('script_name', '未命名任务'),
            script_params=data.get('script_params', ''),
            timeout=data.get('timeout', 7200),
            execution_user=data.get('execution_user', 'root')
        )
        
        # 异步执行任务
        def run_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(server_instance.dispatch_task(task_id))
            loop.close()
        
        thread = threading.Thread(target=run_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({'task_id': task_id, 'message': 'Task started successfully'})
    
    except Exception as e:
        return jsonify({'error': f'执行脚本失败: {str(e)}'}), 500

@api_bp.route('/tasks/<task_id>/retry', methods=['POST'])
def retry_task(task_id):
    """重试任务"""
    if not server_instance:
        return jsonify({'error': 'Server not available'}), 500
    
    try:
        # 从数据库获取原任务信息
        history = server_instance.db.get_execution_history(limit=1000)
        original_task = None
        for task in history:
            if task['id'] == task_id:
                original_task = task
                break
        
        if not original_task:
            return jsonify({'error': 'Original task not found'}), 404
        
        # 创建新任务（重试）
        new_task_id = server_instance.create_task(
            script=original_task.get('script_content', original_task.get('script', '')),
            target_hosts=original_task.get('target_hosts', []),
            script_name=f"[重试] {original_task.get('script_name', '未命名任务')}",
            script_params=original_task.get('script_params', ''),
            timeout=original_task.get('timeout', 7200),
            execution_user=original_task.get('execution_user', 'root')
        )
        
        # 异步执行任务
        def run_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(server_instance.dispatch_task(new_task_id))
            loop.close()
        
        thread = threading.Thread(target=run_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'task_id': new_task_id, 
            'message': 'Task retry started successfully',
            'original_task_id': task_id
        })
    
    except Exception as e:
        return jsonify({'error': f'重试任务失败: {str(e)}'}), 500

@api_bp.route('/tasks/<task_id>/stop', methods=['POST'])
def stop_task(task_id):
    """停止任务"""
    if not server_instance:
        return jsonify({'error': 'Server not available'}), 500
    
    try:
        # 查找正在运行的任务
        if task_id in server_instance.tasks:
            task = server_instance.tasks[task_id]
            if task.status == 'RUNNING':
                task.status = 'CANCELLED'
                from datetime import datetime
                task.completed_at = datetime.now().isoformat()
                task.error_message = '任务被用户手动停止'
                
                # 保存到数据库
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
                    'error_message': task.error_message
                }
                server_instance.db.save_execution_history(task_data)
                
                return jsonify({'message': 'Task stopped successfully'})
            else:
                return jsonify({'error': 'Task is not running'}), 400
        else:
            return jsonify({'error': 'Task not found'}), 404
    
    except Exception as e:
        return jsonify({'error': f'停止任务失败: {str(e)}'}), 500

@api_bp.route('/agents/<agent_id>/tasks', methods=['GET'])
def get_agent_tasks(agent_id):
    """获取指定Agent的执行历史"""
    if not server_instance:
        return jsonify({'error': 'Server not available'}), 500
    
    try:
        # 从数据库获取所有执行历史
        all_history = server_instance.db.get_execution_history(limit=1000)
        
        # 筛选出该Agent相关的任务
        agent_tasks = []
        for task in all_history:
            target_hosts = task.get('target_hosts', [])
            if agent_id in target_hosts:
                agent_tasks.append(task)
        
        return jsonify(agent_tasks)
    
    except Exception as e:
        return jsonify({'error': f'获取Agent任务失败: {str(e)}'}), 500

@api_bp.route('/agents/<agent_id>/restart', methods=['POST'])
@require_auth
@require_permission('agent_management')
def restart_agent(agent_id):
    """重启Agent"""
    if not server_instance:
        return jsonify({'error': 'Server not available'}), 500
    
    try:
        # 检查Agent是否存在
        if agent_id not in server_instance.agents:
            return jsonify({'error': 'Agent not found'}), 404
        
        agent = server_instance.agents[agent_id]
        if agent.status != 'ONLINE':
            return jsonify({'error': 'Agent is not online'}), 400
        
        # 发送重启Agent命令
        def send_restart_command():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def restart_task():
                try:
                    restart_message = {
                        'type': 'restart_agent',
                        'agent_id': agent_id,
                        'message': 'Server requested agent restart'
                    }
                    await agent.websocket.send(json.dumps(restart_message))
                except Exception as e:
                    print(f"发送重启Agent命令失败: {e}")
            
            loop.run_until_complete(restart_task())
            loop.close()
        
        thread = threading.Thread(target=send_restart_command)
        thread.daemon = True
        thread.start()
        
        return jsonify({'message': f'Agent {agent_id} restart command sent successfully'})
    
    except Exception as e:
        return jsonify({'error': f'重启Agent失败: {str(e)}'}), 500

@api_bp.route('/agents/<agent_id>/restart-host', methods=['POST'])
def restart_host(agent_id):
    """重启主机"""
    if not server_instance:
        return jsonify({'error': 'Server not available'}), 500
    
    try:
        # 检查Agent是否存在
        if agent_id not in server_instance.agents:
            return jsonify({'error': 'Agent not found'}), 404
        
        agent = server_instance.agents[agent_id]
        if agent.status != 'ONLINE':
            return jsonify({'error': 'Agent is not online'}), 400
        
        # 发送重启主机命令
        def send_restart_command():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def restart_task():
                try:
                    restart_message = {
                        'type': 'restart_host',
                        'agent_id': agent_id,
                        'message': 'Server requested host restart'
                    }
                    await agent.websocket.send(json.dumps(restart_message))
                except Exception as e:
                    print(f"发送重启主机命令失败: {e}")
            
            loop.run_until_complete(restart_task())
            loop.close()
        
        thread = threading.Thread(target=send_restart_command)
        thread.daemon = True
        thread.start()
        
        return jsonify({'message': f'Host restart command sent to agent {agent_id} successfully'})
    
    except Exception as e:
        return jsonify({'error': f'重启主机失败: {str(e)}'}), 500

@api_bp.route('/agents/<agent_id>/terminal', methods=['POST'])
def create_terminal_session(agent_id):
    """创建终端会话"""
    if not server_instance:
        return jsonify({'error': 'Server not available'}), 500
    
    try:
        # 检查Agent是否在线
        if agent_id not in server_instance.agents:
            return jsonify({'error': 'Agent not found'}), 404
        
        agent = server_instance.agents[agent_id]
        if agent.status != 'ONLINE':
            return jsonify({'error': 'Agent is not online'}), 400
        
        # 创建终端会话（WebSocket连接将在前端建立）
        return jsonify({
            'agent_id': agent_id,
            'websocket_url': f'ws://localhost:{server_instance.port}/terminal/{agent_id}',
            'message': 'Terminal session can be created'
        })
    
    except Exception as e:
        return jsonify({'error': f'创建终端会话失败: {str(e)}'}), 500

@api_bp.route('/terminal/sessions', methods=['GET'])
def get_terminal_sessions():
    """获取当前活跃的终端会话"""
    if not server_instance:
        return jsonify({'error': 'Server not available'}), 500
    
    try:
        sessions = []
        for session_id, session in server_instance.terminal_manager.sessions.items():
            session_info = {
                'session_id': session_id,
                'agent_id': session.agent_id,
                'user_id': session.user_id,
                'created_at': session.created_at,
                'last_activity': session.last_activity,
                'is_active': session.is_active,
                'command_count': len(session.command_history)
            }
            sessions.append(session_info)
        
        return jsonify(sessions)
    
    except Exception as e:
        return jsonify({'error': f'获取终端会话失败: {str(e)}'}), 500

@api_bp.route('/terminal/sessions/<session_id>', methods=['DELETE'])
def close_terminal_session_api(session_id):
    """关闭指定的终端会话"""
    if not server_instance:
        return jsonify({'error': 'Server not available'}), 500
    
    try:
        session = server_instance.terminal_manager.get_session(session_id)
        if not session:
            return jsonify({'error': 'Terminal session not found'}), 404
        
        # 异步关闭会话
        def close_session():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def close_task():
                await server_instance.close_terminal_session(session_id)
            
            loop.run_until_complete(close_task())
            loop.close()
        
        thread = threading.Thread(target=close_session)
        thread.daemon = True
        thread.start()
        
        return jsonify({'message': 'Terminal session closed successfully'})
    
    except Exception as e:
        return jsonify({'error': f'关闭终端会话失败: {str(e)}'}), 500

@api_bp.route('/terminal/commands/allowed', methods=['GET'])
def get_allowed_commands():
    """获取允许的命令列表"""
    if not server_instance:
        return jsonify({'error': 'Server not available'}), 500
    
    try:
        return jsonify({
            'allowed_commands': server_instance.terminal_manager.allowed_commands,
            'forbidden_commands': server_instance.terminal_manager.forbidden_commands,
            'session_timeout': server_instance.terminal_manager.session_timeout,
            'max_sessions_per_agent': server_instance.terminal_manager.max_sessions_per_agent
        })
    
    except Exception as e:
        return jsonify({'error': f'获取命令配置失败: {str(e)}'}), 500

@api_bp.route('/agents/batch', methods=['POST'])
@require_auth
@require_permission('agent_management')
def batch_manage_agents():
    """批量管理Agent"""
    if not server_instance:
        return jsonify({'error': 'Server not available'}), 500
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供批量操作信息'}), 400
        
        action = data.get('action')
        agent_ids = data.get('agent_ids', [])
        
        if not action:
            return jsonify({'error': '请指定操作类型'}), 400
        
        if not agent_ids:
            return jsonify({'error': '请选择要操作的Agent'}), 400
        
        results = []
        
        if action == 'delete_offline' or action == 'delete_down':
            # 删除离线或DOWN状态的Agent
            for agent_id in agent_ids:
                try:
                    # 检查Agent状态
                    agent_status = None
                    if agent_id in server_instance.agents:
                        agent = server_instance.agents[agent_id]
                        agent_status = agent.status
                        
                        # 检查状态是否允许删除
                        if agent_status not in ['OFFLINE', 'DOWN']:
                            results.append({
                                'agent_id': agent_id,
                                'success': False,
                                'message': f'Agent状态为{agent_status}，只能删除OFFLINE或DOWN状态的Agent'
                            })
                            continue
                        
                        # 从内存中删除
                        del server_instance.agents[agent_id]
                    
                    # 从数据库中删除
                    conn = server_instance.db._get_connection()
                    cursor = conn.cursor()
                    
                    # 删除Agent记录
                    cursor.execute('DELETE FROM agents WHERE id = %s', (agent_id,))
                    affected_rows = cursor.rowcount
                    
                    # 删除Agent系统信息
                    cursor.execute('DELETE FROM agent_system_info WHERE agent_id = %s', (agent_id,))
                    
                    # 删除Agent相关的任务执行记录（可选，根据需求决定是否保留历史记录）
                    # cursor.execute('DELETE FROM execution_history WHERE target_hosts LIKE %s', (f'%{agent_id}%',))
                    
                    conn.close()
                    
                    if affected_rows > 0:
                        results.append({
                            'agent_id': agent_id,
                            'success': True,
                            'message': 'Agent删除成功'
                        })
                    else:
                        results.append({
                            'agent_id': agent_id,
                            'success': False,
                            'message': 'Agent不存在'
                        })
                        
                except Exception as e:
                    results.append({
                        'agent_id': agent_id,
                        'success': False,
                        'message': f'删除失败: {str(e)}'
                    })
        
        elif action == 'restart':
            # 批量重启Agent
            def batch_restart():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def restart_agents():
                    for agent_id in agent_ids:
                        try:
                            if agent_id in server_instance.agents:
                                agent = server_instance.agents[agent_id]
                                if agent.status == 'ONLINE' and agent.websocket:
                                    restart_message = {
                                        'type': 'restart_agent',
                                        'agent_id': agent_id,
                                        'message': 'Batch restart requested'
                                    }
                                    await agent.websocket.send(json.dumps(restart_message))
                                    results.append({
                                        'agent_id': agent_id,
                                        'success': True,
                                        'message': '重启命令已发送'
                                    })
                                else:
                                    results.append({
                                        'agent_id': agent_id,
                                        'success': False,
                                        'message': 'Agent不在线'
                                    })
                            else:
                                results.append({
                                    'agent_id': agent_id,
                                    'success': False,
                                    'message': 'Agent不存在'
                                })
                        except Exception as e:
                            results.append({
                                'agent_id': agent_id,
                                'success': False,
                                'message': f'重启失败: {str(e)}'
                            })
                
                loop.run_until_complete(restart_agents())
                loop.close()
            
            thread = threading.Thread(target=batch_restart)
            thread.daemon = True
            thread.start()
            thread.join(timeout=10)  # 等待最多10秒
        
        elif action == 'update':
            # 批量更新Agent版本
            version = data.get('version', '')
            download_url = data.get('download_url', '')
            md5 = data.get('md5', '')
            
            if not version:
                return jsonify({'error': '请指定目标版本'}), 400
            
            if not download_url:
                return jsonify({'error': '请提供下载URL'}), 400
            
            if not md5:
                return jsonify({'error': '请提供MD5校验值'}), 400
            
            # 实现批量更新逻辑 - 通过WebSocket发送更新命令
            def batch_update():
                loop = asyncio.new_event_loop()
                
                async def update_agents():
                    for agent_id in agent_ids:
                        try:
                            # 查找Agent
                            if agent_id not in server_instance.agents:
                                results.append({
                                    'agent_id': agent_id,
                                    'success': False,
                                    'message': 'Agent不存在'
                                })
                                continue
                            
                            agent = server_instance.agents[agent_id]
                            if agent.status != 'ONLINE' or not agent.websocket:
                                results.append({
                                    'agent_id': agent_id,
                                    'success': False,
                                    'message': 'Agent未连接'
                                })
                                continue
                            
                            # 发送更新命令
                            update_message = {
                                'type': 'update_agent',
                                'agent_id': agent_id,
                                'version': version,
                                'download_url': download_url,
                                'md5': md5
                            }
                            
                            await agent.websocket.send(json.dumps(update_message))
                            print(f"已发送更新命令到Agent: {agent_id}, 版本: {version}")
                            
                            results.append({
                                'agent_id': agent_id,
                                'success': True,
                                'message': f'已发送更新命令，版本: {version}'
                            })
                            
                        except Exception as e:
                            results.append({
                                'agent_id': agent_id,
                                'success': False,
                                'message': f'发送更新命令失败: {str(e)}'
                            })
                
                loop.run_until_complete(update_agents())
                loop.close()
            
            thread = threading.Thread(target=batch_update)
            thread.daemon = True
            thread.start()
            thread.join(timeout=10)  # 等待最多10秒
        
        else:
            return jsonify({'error': f'不支持的操作类型: {action}'}), 400
        
        success_count = sum(1 for r in results if r['success'])
        total_count = len(results)
        
        return jsonify({
            'message': f'批量操作完成，成功: {success_count}/{total_count}',
            'results': results,
            'success_count': success_count,
            'total_count': total_count
        })
        
    except Exception as e:
        return jsonify({'error': f'批量管理失败: {str(e)}'}), 500

@api_bp.route('/agents/cleanup', methods=['POST'])
@require_auth
@require_permission('agent_management')
def cleanup_offline_agents():
    """清理离线Agent"""
    if not server_instance:
        return jsonify({'error': 'Server not available'}), 500
    
    try:
        data = request.get_json()
        offline_hours = data.get('offline_hours', 24) if data else 24
        
        # 计算离线时间阈值
        from datetime import datetime, timedelta
        threshold_time = datetime.now() - timedelta(hours=offline_hours)
        
        # 获取所有Agent
        all_agents = server_instance.db.get_all_agents()
        
        deleted_agents = []
        for agent in all_agents:
            # 检查是否长时间离线
            if agent['last_heartbeat']:
                last_heartbeat = datetime.fromisoformat(agent['last_heartbeat'])
                if last_heartbeat < threshold_time:
                    try:
                        # 从内存中删除
                        if agent['id'] in server_instance.agents:
                            del server_instance.agents[agent['id']]
                        
                        # 从数据库中删除
                        conn = server_instance.db._get_connection()
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
                        print(f"删除Agent {agent['id']} 失败: {e}")
        
        return jsonify({
            'message': f'清理完成，删除了 {len(deleted_agents)} 个长时间离线的Agent',
            'deleted_agents': deleted_agents,
            'deleted_count': len(deleted_agents)
        })
        
    except Exception as e:
        return jsonify({'error': f'清理离线Agent失败: {str(e)}'}), 500
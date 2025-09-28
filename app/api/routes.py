"""
API路由定义
"""
import json
from flask import Blueprint, jsonify, request
from app.models import DatabaseManager
from dataclasses import asdict

# 创建蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')

# 全局变量，将在应用初始化时设置
server_instance = None

def init_api(server):
    """初始化API，设置服务器实例"""
    global server_instance
    server_instance = server

@api_bp.route('/tasks', methods=['GET'])
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
            'ip': agent['ip_address'],
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
        import threading
        def run_task():
            import asyncio
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
        import threading
        def run_task():
            import asyncio
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
        import asyncio
        import threading
        
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
        import asyncio
        import threading
        
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
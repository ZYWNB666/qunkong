"""
QueenBee服务器核心模块
"""
import asyncio
import websockets
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass, asdict
from app.models import DatabaseManager, generate_agent_id

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Agent:
    """Agent信息"""
    id: str
    hostname: str
    ip: str
    status: str = "ONLINE"
    last_heartbeat: str = ""
    websocket: object = None

@dataclass
class Task:
    """任务信息"""
    id: str
    script: str
    target_hosts: List[str]
    status: str = "PENDING"
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    timeout: int = 7200
    results: Dict = None
    script_name: str = "未命名任务"
    script_params: str = ""
    execution_user: str = "root"
    error_message: str = ""

    def __post_init__(self):
        if self.results is None:
            self.results = {}

class QueenBeeServer:
    """QueenBee 服务端主类"""
    
    def __init__(self, host="0.0.0.0", port=8765, web_port=5000):
        self.host = host
        self.port = port
        self.web_port = web_port
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.running = False
        self.db = DatabaseManager()  # 初始化数据库管理器
        # 心跳检查任务
        self.heartbeat_check_task = None

    async def register_agent(self, websocket, agent_info: dict):
        """注册 Agent"""
        # 使用agent_id或id字段，如果都没有则使用IP的MD5值
        agent_id = agent_info.get('agent_id') or agent_info.get('id')
        if not agent_id:
            # 获取客户端IP地址
            client_ip = agent_info.get('ip', '127.0.0.1')
            agent_id = generate_agent_id(client_ip)
        
        # 设置当前时间作为初始心跳时间
        current_time = datetime.now().isoformat()
        
        agent = Agent(
            id=agent_id,
            hostname=agent_info.get('hostname', 'Unknown'),
            ip=agent_info.get('ip', '127.0.0.1'),
            last_heartbeat=current_time,
            websocket=websocket
        )
        
        self.agents[agent.id] = agent
        logger.info(f"Agent 注册成功: {agent.hostname} ({agent.ip}) - ID: {agent.id}")

        # 保存Agent信息到数据库
        agent_data = {
            'id': agent_id,
            'hostname': agent.hostname,
            'ip_address': agent.ip,
            'status': agent.status,
            'last_heartbeat': agent.last_heartbeat,
            'register_time': datetime.now().isoformat(),
            'websocket_info': {}
        }
        self.db.save_agent(agent_data)

        # 保存Agent系统信息到数据库
        if 'system_info' in agent_info:
            system_data = {
                'agent_id': agent_id,
                'hostname': agent.hostname,
                'ip_address': agent.ip,
                'last_heartbeat': agent.last_heartbeat,
                'status': agent.status,
                'register_time': datetime.now().isoformat(),
                'system_info': agent_info['system_info']
            }
            self.db.save_agent_system_info(agent_id, system_data)

        # 发送注册确认
        response = {
            'type': 'register_confirm',
            'agent_id': agent.id,
            'message': 'Agent 注册成功'
        }
        await websocket.send(json.dumps(response))

    async def handle_agent_message(self, websocket, message: dict):
        """处理Agent消息"""
        try:
            msg_type = message.get('type')
            
            if msg_type == 'register':
                await self.register_agent(websocket, message)
            elif msg_type == 'heartbeat':
                agent_id = message.get('agent_id')
                if agent_id and agent_id in self.agents:
                    current_time = datetime.now().isoformat()
                    # 更新内存中的Agent信息
                    self.agents[agent_id].last_heartbeat = current_time
                    self.agents[agent_id].status = "ONLINE"
                    
                    # 更新数据库中的心跳时间
                    # 先获取现有的注册时间，避免覆盖
                    existing_agents = self.db.get_all_agents()
                    register_time = current_time  # 默认值
                    for existing_agent in existing_agents:
                        if existing_agent['id'] == agent_id:
                            register_time = existing_agent['register_time']
                            break
                    
                    agent_data = {
                        'id': agent_id,
                        'hostname': self.agents[agent_id].hostname,
                        'ip_address': self.agents[agent_id].ip,
                        'status': 'ONLINE',
                        'last_heartbeat': current_time,
                        'register_time': register_time,
                        'websocket_info': {}
                    }
                    self.db.save_agent(agent_data)
                    logger.debug(f"Agent {agent_id} 心跳已更新: {current_time}")
            elif msg_type == 'task_result':
                await self.handle_task_result(message)
            elif msg_type == 'restart_agent_response':
                await self.handle_restart_response(message)
            elif msg_type == 'restart_host_response':
                await self.handle_restart_response(message)
            else:
                logger.warning(f"未知消息类型: {msg_type}")
                
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")

    async def handle_task_result(self, message: dict):
        """处理任务结果"""
        task_id = message.get('task_id')
        agent_id = message.get('agent_id')
        result = message.get('result', {})
        
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.results[agent_id] = result
            
            # 检查是否所有目标主机都已完成
            completed_count = len(task.results)
            target_count = len(task.target_hosts)
            
            if completed_count >= target_count:
                task.status = "COMPLETED" if all(r.get('exit_code') == 0 for r in task.results.values()) else "FAILED"
                task.completed_at = datetime.now().isoformat()
                logger.info(f"任务 {task_id} 完成: {task.status}")

                # 保存执行历史到数据库
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
                self.db.save_execution_history(task_data)

    async def handle_restart_response(self, message: dict):
        """处理重启响应"""
        agent_id = message.get('agent_id')
        restart_type = message.get('restart_type', 'unknown')
        success = message.get('success', False)
        error_message = message.get('error_message', '')
        
        if success:
            logger.info(f"Agent {agent_id} {restart_type} 重启成功")
        else:
            logger.error(f"Agent {agent_id} {restart_type} 重启失败: {error_message}")

    async def handle_client(self, websocket, path):
        """处理客户端连接"""
        client_ip = websocket.remote_address[0]
        logger.info(f"新连接: {websocket.remote_address}")
        
        agent_id = None
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    
                    # 如果是注册消息，记录agent_id
                    if data.get('type') == 'register':
                        agent_id = data.get('agent_id') or data.get('id')
                        if not agent_id:
                            agent_id = generate_agent_id(data.get('ip', client_ip))
                    
                    await self.handle_agent_message(websocket, data)
                except json.JSONDecodeError:
                    logger.error(f"无效的JSON消息: {message}")
                except Exception as e:
                    logger.error(f"处理消息时出错: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"连接关闭: {client_ip}")
        except Exception as e:
            logger.error(f"连接错误: {e}")
        finally:
            # 清理断开连接的Agent
            await self.cleanup_disconnected_agent(agent_id, client_ip)

    async def cleanup_disconnected_agent(self, agent_id, client_ip):
        """清理断开连接的Agent"""
        try:
            if agent_id and agent_id in self.agents:
                # 更新Agent状态为离线
                self.agents[agent_id].status = "OFFLINE"
                
                # 更新数据库中的状态
                existing_agents = self.db.get_all_agents()
                for existing_agent in existing_agents:
                    if existing_agent['id'] == agent_id:
                        agent_data = {
                            'id': agent_id,
                            'hostname': existing_agent['hostname'],
                            'ip_address': existing_agent['ip_address'],
                            'status': 'OFFLINE',
                            'last_heartbeat': existing_agent['last_heartbeat'],
                            'register_time': existing_agent['register_time'],
                            'websocket_info': {}
                        }
                        self.db.save_agent(agent_data)
                        logger.info(f"Agent {agent_id} 状态已更新为离线")
                        break
                
                # 从内存中移除Agent（可选，也可以保留用于重连）
                # del self.agents[agent_id]
                
        except Exception as e:
            logger.error(f"清理断开连接的Agent时出错: {e}")

    async def check_agent_heartbeats(self):
        """检查Agent心跳，将超时的Agent标记为离线"""
        while self.running:
            try:
                current_time = datetime.now()
                timeout_agents = []
                
                for agent_id, agent in self.agents.items():
                    if agent.last_heartbeat:
                        try:
                            last_heartbeat_time = datetime.fromisoformat(agent.last_heartbeat)
                            time_diff = (current_time - last_heartbeat_time).total_seconds()
                            
                            # 如果超过15秒没有心跳，标记为离线
                            if time_diff > 15 and agent.status == "ONLINE":
                                timeout_agents.append(agent_id)
                                logger.info(f"Agent {agent_id} 心跳超时 ({time_diff:.1f}s)，标记为离线")
                        except ValueError as e:
                            logger.error(f"解析心跳时间失败 {agent.last_heartbeat}: {e}")
                
                # 更新超时的Agent状态
                for agent_id in timeout_agents:
                    if agent_id in self.agents:
                        self.agents[agent_id].status = "OFFLINE"
                        
                        # 更新数据库
                        existing_agents = self.db.get_all_agents()
                        for existing_agent in existing_agents:
                            if existing_agent['id'] == agent_id:
                                agent_data = {
                                    'id': agent_id,
                                    'hostname': existing_agent['hostname'],
                                    'ip_address': existing_agent['ip_address'],
                                    'status': 'OFFLINE',
                                    'last_heartbeat': existing_agent['last_heartbeat'],
                                    'register_time': existing_agent['register_time'],
                                    'websocket_info': {}
                                }
                                self.db.save_agent(agent_data)
                                break
                
                # 每5秒检查一次
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"检查心跳时出错: {e}")
                await asyncio.sleep(5)

    def create_task(self, script: str, target_hosts: List[str], **kwargs) -> str:
        """创建任务"""
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            script=script,
            target_hosts=target_hosts,
            created_at=datetime.now().isoformat(),
            **kwargs
        )
        self.tasks[task_id] = task
        
        # 立即保存任务初始状态到数据库
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
        self.db.save_execution_history(task_data)
        logger.info(f"任务 {task_id} 已创建并保存到数据库")
        
        return task_id

    async def dispatch_task(self, task_id: str):
        """分发任务到目标主机"""
        if task_id not in self.tasks:
            logger.error(f"任务不存在: {task_id}")
            return
        
        task = self.tasks[task_id]
        task.status = "RUNNING"
        task.started_at = datetime.now().isoformat()
        
        # 更新数据库中的任务状态
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
        self.db.save_execution_history(task_data)
        
        # 查找目标Agent
        target_agents = []
        for agent in self.agents.values():
            if agent.id in task.target_hosts or agent.ip in task.target_hosts:
                target_agents.append(agent)
        
        if not target_agents:
            logger.error(f"未找到目标Agent: {task.target_hosts}")
            task.status = "FAILED"
            task.error_message = "未找到目标Agent"
            return
        
        # 发送任务到目标Agent
        task_message = {
            'type': 'execute_task',
            'task_id': task_id,
            'script': task.script,
            'script_params': task.script_params,
            'timeout': task.timeout,
            'execution_user': task.execution_user
        }
        
        for agent in target_agents:
            try:
                await agent.websocket.send(json.dumps(task_message))
                logger.info(f"任务 {task_id} 已发送到 {agent.hostname}")
            except Exception as e:
                logger.error(f"发送任务到 {agent.hostname} 失败: {e}")
                task.results[agent.id] = {
                    'exit_code': -1,
                    'stdout': '',
                    'stderr': f'发送任务失败: {str(e)}',
                    'execution_time': 0
                }

    async def start(self):
        """启动服务器"""
        self.running = True
        logger.info(f"QueenBee 服务器启动在 ws://{self.host}:{self.port}")
        
        # 启动心跳检查任务
        self.heartbeat_check_task = asyncio.create_task(self.check_agent_heartbeats())
        logger.info("心跳检查任务已启动")
        
        # 创建包装函数来处理path参数
        async def websocket_handler(websocket, path=""):
            await self.handle_client(websocket, path)
        
        try:
            async with websockets.serve(websocket_handler, self.host, self.port):
                await asyncio.Future()  # 保持运行
        finally:
            # 服务器关闭时取消心跳检查任务
            if self.heartbeat_check_task:
                self.heartbeat_check_task.cancel()
                try:
                    await self.heartbeat_check_task
                except asyncio.CancelledError:
                    pass
                logger.info("心跳检查任务已停止")

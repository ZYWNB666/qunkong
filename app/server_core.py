"""
Qunkong服务器核心模块
"""
import asyncio
import websockets
import json
import uuid
import logging
import hashlib
import secrets
import time
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from app.models import DatabaseManager, generate_agent_id
from app.cluster import ClusterManager
from app.cache import get_local_cache

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
    started_at: Optional[str] = None  # 改为None，避免空字符串问题  
    completed_at: Optional[str] = None  # 改为None，避免空字符串问题
    timeout: int = 7200
    results: Dict = None
    script_name: str = "未命名任务"
    script_params: str = ""
    execution_user: str = "root"
    error_message: str = ""
    project_id: Optional[int] = None  # 添加 project_id 字段

    def __post_init__(self):
        if self.results is None:
            self.results = {}

@dataclass
class TerminalSession:
    """终端会话信息"""
    session_id: str
    agent_id: str
    user_id: str = "admin"  # 当前用户ID
    websocket: object = None
    agent_websocket: object = None
    created_at: str = ""
    last_activity: str = ""
    is_active: bool = True
    command_history: List[str] = None
    
    def __post_init__(self):
        if self.command_history is None:
            self.command_history = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_activity:
            self.last_activity = datetime.now().isoformat()

class TerminalManager:
    """终端会话管理器"""
    
    def __init__(self):
        self.sessions: Dict[str, TerminalSession] = {}
        self.session_timeout = 1800  # 30分钟超时
        self.max_sessions_per_agent = 3  # 每个Agent最大并发会话数
        self.allowed_commands = [
            # 基本命令
            'ls', 'pwd', 'cd', 'cat', 'head', 'tail', 'grep', 'find',
            'ps', 'top', 'htop', 'df', 'free', 'uname', 'whoami', 'id',
            'netstat', 'ss', 'ping', 'curl', 'wget', 'systemctl', 'service',
            # 文件操作
            'mkdir', 'rmdir', 'cp', 'mv', 'rm', 'chmod', 'chown',
            # 文本处理
            'awk', 'sed', 'sort', 'uniq', 'wc', 'less', 'more',
            # 网络工具
            'nslookup', 'dig', 'traceroute',
            # 系统信息
            'lscpu', 'lsmem', 'lsblk', 'mount', 'uptime', 'date',
            # 日志查看
            'journalctl', 'dmesg'
        ]
        self.forbidden_commands = [
            # 危险命令
            'rm -rf', 'mkfs', 'dd', 'format', 'fdisk',
            'shutdown', 'reboot', 'halt', 'poweroff',
            'passwd', 'su', 'sudo', 'visudo',
            # 网络危险操作
            'iptables', 'firewall-cmd', 'ufw',
            # 包管理
            'apt-get', 'yum', 'dnf', 'pacman', 'pip', 'npm'
        ]
    
    def create_session(self, agent_id: str, user_id: str, websocket) -> Optional[str]:
        """创建终端会话"""
        # 检查并发会话数限制
        active_sessions = [s for s in self.sessions.values() 
                          if s.agent_id == agent_id and s.is_active]
        if len(active_sessions) >= self.max_sessions_per_agent:
            return None
        
        session_id = secrets.token_urlsafe(32)
        session = TerminalSession(
            session_id=session_id,
            agent_id=agent_id,
            user_id=user_id,
            websocket=websocket
        )
        self.sessions[session_id] = session
        logger.info(f"创建终端会话: {session_id} for agent {agent_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[TerminalSession]:
        """获取会话信息"""
        return self.sessions.get(session_id)
    
    def close_session(self, session_id: str):
        """关闭会话"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.is_active = False
            logger.info(f"关闭终端会话: {session_id}")
            del self.sessions[session_id]
    
    def update_activity(self, session_id: str):
        """更新会话活动时间"""
        if session_id in self.sessions:
            self.sessions[session_id].last_activity = datetime.now().isoformat()
    
    def is_command_allowed(self, command: str) -> tuple[bool, str]:
        """检查命令是否允许执行"""
        command = command.strip().lower()
        
        # 检查禁用命令
        for forbidden in self.forbidden_commands:
            if forbidden in command:
                return False, f"命令被禁止: 包含危险操作 '{forbidden}'"
        
        # 提取命令的第一部分
        cmd_parts = command.split()
        if not cmd_parts:
            return False, "空命令"
        
        base_cmd = cmd_parts[0]
        
        # 检查是否在允许列表中
        if base_cmd in self.allowed_commands:
            return True, "命令允许"
        
        # 对于不在白名单中的命令，给出警告
        return False, f"命令不在允许列表中: '{base_cmd}'"
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            last_activity = datetime.fromisoformat(session.last_activity)
            if (now - last_activity).total_seconds() > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.close_session(session_id)
        
        return len(expired_sessions)

class QunkongServer:
    """Qunkong 服务端主类"""
    
    def __init__(self, host="0.0.0.0", port=8765, web_port=5000, cluster_manager=None):
        self.host = host
        self.port = port
        self.web_port = web_port
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.running = False
        self.db = DatabaseManager()  # 初始化数据库管理器
        # 集群管理器
        self.cluster = cluster_manager
        # 心跳检查任务
        self.heartbeat_check_task = None
        # 终端管理器
        self.terminal_manager = TerminalManager()
        # 会话清理任务
        self.session_cleanup_task = None
        # 主事件循环引用
        self.loop = None
        # 跨节点终端会话映射 {session_id: target_node_id}
        self.remote_terminal_sessions: Dict[str, str] = {}
        # 本地缓存（用于实时资源信息）
        self.local_cache = get_local_cache()
        # 资源信息数据库写入计数器
        self.resource_update_counters = {}  # agent_id -> counter

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
            'ip_address': agent.ip,  # 内网IP
            'external_ip': agent_info.get('external_ip', ''),  # 外网IP
            'os_type': agent_info.get('platform', 'unknown'),  # 操作系统类型
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

        # 在集群模式下注册Agent位置
        if self.cluster:
            await self.cluster.register_agent_location(agent_id, agent_info)

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
                    
                    # 如果心跳中包含资源信息，缓存到本地内存（不立即写数据库）
                    if any(k in message for k in ['cpu_usage', 'memory_usage', 'memory_total', 'disk_info']):
                        cache_key = f"agent_resource:{agent_id}"
                        resource_info = {
                            'cpu_usage': message.get('cpu_usage', 0),
                            'memory_usage': message.get('memory_usage', 0),
                            'memory_total': message.get('memory_total', 0),
                            'memory_used': message.get('memory_used', 0),
                            'memory_available': message.get('memory_available', 0),
                            'disk_info': message.get('disk_info', []),  # 添加磁盘信息
                            'last_heartbeat': current_time,  # 添加心跳时间
                            'last_update': current_time
                        }
                        # 缓存到本地内存，TTL=30秒（资源信息30秒内有效）
                        self.local_cache.set(cache_key, resource_info, ttl=30)
                        
                        # 每12次心跳（约1分钟）写一次数据库，避免频繁写入
                        if agent_id not in self.resource_update_counters:
                            self.resource_update_counters[agent_id] = 0
                        
                        self.resource_update_counters[agent_id] += 1
                        
                        # 每12次（约1分钟）或第一次时写入数据库
                        if self.resource_update_counters[agent_id] == 1 or self.resource_update_counters[agent_id] >= 12:
                            self.db.update_agent_resource_info(agent_id, resource_info)
                            self.resource_update_counters[agent_id] = 0  # 重置计数器
                            logger.debug(f"Agent {agent_id} 资源信息已写入数据库")
                    
                    # 更新数据库中的心跳时间（轻量级更新，只更新状态和时间）
                    # 先获取现有的Agent完整信息，避免覆盖其他字段
                    existing_agents = self.db.get_all_agents()
                    register_time = current_time  # 默认值
                    external_ip = ''  # 默认值
                    os_type = 'unknown'  # 默认值
                    for existing_agent in existing_agents:
                        if existing_agent['id'] == agent_id:
                            register_time = existing_agent['register_time']
                            external_ip = existing_agent.get('external_ip', '')
                            os_type = existing_agent.get('os_type', 'unknown')
                            break
                    
                    agent_data = {
                        'id': agent_id,
                        'hostname': self.agents[agent_id].hostname,
                        'ip_address': self.agents[agent_id].ip,
                        'external_ip': external_ip,  # 保持原有的外网IP
                        'os_type': os_type,  # 保持原有的操作系统类型
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
            elif msg_type == 'terminal_command':
                await self.handle_terminal_command(message)
            elif msg_type == 'terminal_output':
                await self.handle_terminal_output(message)
            elif msg_type == 'terminal_data':
                await self.handle_pty_terminal_data(message)
            elif msg_type == 'terminal_error':
                await self.handle_pty_terminal_error(message)
            elif msg_type == 'terminal_ready':
                await self.handle_pty_terminal_ready(message)
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
            
            # 添加 agent 信息到结果中
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                result['agent_hostname'] = agent.hostname
                result['agent_ip'] = agent.ip
            
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
                    'project_id': getattr(task, 'project_id', None),  # 添加 project_id
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

    async def handle_terminal_command(self, message: dict):
        """处理终端命令"""
        session_id = message.get('session_id')
        command = message.get('command', '').strip()
        
        if not session_id or not command:
            return
        
        session = self.terminal_manager.get_session(session_id)
        if not session or not session.is_active:
            logger.warning(f"终端会话不存在或已关闭: {session_id}")
            return
        
        # 更新会话活动时间
        self.terminal_manager.update_activity(session_id)
        
        # 检查命令是否允许
        allowed, reason = self.terminal_manager.is_command_allowed(command)
        if not allowed:
            error_response = {
                'type': 'terminal_output',
                'session_id': session_id,
                'output': f"❌ 命令被拒绝: {reason}\n",
                'error': True
            }
            try:
                await session.websocket.send(json.dumps(error_response))
            except:
                pass
            return
        
        # 记录命令历史
        session.command_history.append({
            'command': command,
            'timestamp': datetime.now().isoformat(),
            'user': session.user_id
        })
        
        # 转发命令到Agent
        if session.agent_id in self.agents:
            agent = self.agents[session.agent_id]
            if agent.websocket:
                try:
                    terminal_message = {
                        'type': 'terminal_execute',
                        'session_id': session_id,
                        'command': command
                    }
                    await agent.websocket.send(json.dumps(terminal_message))
                    logger.info(f"终端命令转发到Agent {session.agent_id}: {command}")
                except Exception as e:
                    logger.error(f"转发终端命令失败: {e}")
                    error_response = {
                        'type': 'terminal_output',
                        'session_id': session_id,
                        'output': f"❌ 命令执行失败: Agent连接异常\n",
                        'error': True
                    }
                    try:
                        await session.websocket.send(json.dumps(error_response))
                    except:
                        pass

    async def handle_terminal_output(self, message: dict):
        """处理终端输出"""
        session_id = message.get('session_id')
        output = message.get('output', '')
        error = message.get('error', False)
        
        if not session_id:
            return
        
        session = self.terminal_manager.get_session(session_id)
        if not session or not session.is_active:
            return
        
        # 转发输出到前端
        try:
            output_message = {
                'type': 'terminal_output',
                'session_id': session_id,
                'output': output,
                'error': error
            }
            await session.websocket.send(json.dumps(output_message))
        except Exception as e:
            logger.error(f"转发终端输出失败: {e}")

    async def create_terminal_session(self, agent_id: str, user_id: str, websocket) -> Optional[str]:
        """创建终端会话"""
        # 检查Agent是否在线
        if agent_id not in self.agents or self.agents[agent_id].status != "ONLINE":
            return None
        
        # 创建会话
        session_id = self.terminal_manager.create_session(agent_id, user_id, websocket)
        if not session_id:
            return None
        
        # 通知Agent启动终端
        agent = self.agents[agent_id]
        if agent.websocket:
            try:
                init_message = {
                    'type': 'terminal_init',
                    'session_id': session_id
                }
                await agent.websocket.send(json.dumps(init_message))
                logger.info(f"终端会话初始化消息发送到Agent {agent_id}")
            except Exception as e:
                logger.error(f"发送终端初始化消息失败: {e}")
                self.terminal_manager.close_session(session_id)
                return None
        
        return session_id

    async def close_terminal_session(self, session_id: str):
        """关闭终端会话"""
        session = self.terminal_manager.get_session(session_id)
        if not session:
            return
        
        # 通知Agent关闭终端
        if session.agent_id in self.agents:
            agent = self.agents[session.agent_id]
            if agent.websocket:
                try:
                    close_message = {
                        'type': 'terminal_close',
                        'session_id': session_id
                    }
                    await agent.websocket.send(json.dumps(close_message))
                except Exception as e:
                    logger.error(f"发送终端关闭消息失败: {e}")
        
        # 关闭会话
        self.terminal_manager.close_session(session_id)

    async def create_pty_terminal_session(self, agent_id: str, user_id: str, websocket) -> Optional[str]:
        """创建PTY终端会话"""
        try:
            # 检查Agent是否存在且在线
            if agent_id not in self.agents:
                logger.error(f"Agent {agent_id} 不存在")
                return None
            
            agent = self.agents[agent_id]
            if agent.status != 'ONLINE':
                logger.error(f"Agent {agent_id} 不在线")
                return None
            
            # 创建会话
            session_id = self.terminal_manager.create_session(agent_id, user_id, websocket)
            if session_id:
                # 向Agent发送初始化消息（包含终端大小）
                init_message = {
                    'type': 'terminal_init',
                    'session_id': session_id,
                    'cols': 80,
                    'rows': 24
                }
                try:
                    await agent.websocket.send(json.dumps(init_message))
                    logger.info(f"PTY终端会话 {session_id} 创建成功")
                    return session_id
                except Exception as e:
                    logger.error(f"向Agent发送初始化消息失败: {e}")
                    self.terminal_manager.close_session(session_id)
                    return None
            else:
                logger.error(f"创建PTY终端会话失败，可能达到最大会话数限制")
                return None
                
        except Exception as e:
            logger.error(f"创建PTY终端会话失败: {e}")
            return None

    async def handle_pty_terminal_input(self, session_id: str, input_data: str, is_binary: bool = False):
        """处理PTY终端输入"""
        try:
            session = self.terminal_manager.get_session(session_id)
            if not session:
                logger.warning(f"PTY终端会话不存在: {session_id}")
                return
            
            # 更新活动时间
            self.terminal_manager.update_activity(session_id)
            
            # 获取Agent
            agent = self.agents.get(session.agent_id)
            if not agent or agent.status != 'ONLINE':
                logger.warning(f"Agent {session.agent_id} 不在线")
                return
            
            # 转发输入到Agent
            input_message = {
                'type': 'terminal_input',
                'session_id': session_id,
                'data': input_data,
                'is_binary': is_binary
            }
            await agent.websocket.send(json.dumps(input_message))
            
        except Exception as e:
            logger.error(f"处理PTY终端输入失败: {e}")

    async def handle_pty_terminal_resize(self, session_id: str, cols: int, rows: int):
        """处理PTY终端大小调整"""
        try:
            session = self.terminal_manager.get_session(session_id)
            if not session:
                logger.warning(f"PTY终端会话不存在: {session_id}")
                return
            
            # 更新活动时间
            self.terminal_manager.update_activity(session_id)
            
            # 获取Agent
            agent = self.agents.get(session.agent_id)
            if not agent or agent.status != 'ONLINE':
                logger.warning(f"Agent {session.agent_id} 不在线")
                return
            
            # 转发大小调整到Agent
            resize_message = {
                'type': 'terminal_resize',
                'session_id': session_id,
                'cols': cols,
                'rows': rows
            }
            await agent.websocket.send(json.dumps(resize_message))
            
        except Exception as e:
            logger.error(f"处理PTY终端大小调整失败: {e}")

    async def handle_pty_terminal_data(self, message: dict):
        """处理PTY终端数据输出"""
        try:
            session_id = message.get('session_id')
            data = message.get('data', '')
            is_binary = message.get('is_binary', False)
            
            session = self.terminal_manager.get_session(session_id)
            if not session:
                logger.warning(f"PTY终端会话不存在: {session_id}")
                return
            
            # 转发数据到前端WebSocket
            if session.websocket:
                try:
                    if is_binary:
                        # 二进制数据直接发送（ZMODEM协议，Agent应该发送base64编码的数据）
                        response = {
                            'type': 'terminal_data',
                            'session_id': session_id,
                            'data': data,
                            'is_binary': True
                        }
                        await session.websocket.send(json.dumps(response))
                    else:
                        # 文本数据
                        response = {
                            'type': 'terminal_data',
                            'session_id': session_id,
                            'data': data
                        }
                        await session.websocket.send(json.dumps(response))
                except Exception as e:
                    logger.error(f"向前端发送PTY终端数据失败: {e}")
                    # 会话可能已断开，清理会话
                    await self.close_pty_terminal_session(session_id)
            
        except Exception as e:
            logger.error(f"处理PTY终端数据失败: {e}")

    async def handle_pty_terminal_error(self, message: dict):
        """处理PTY终端错误"""
        try:
            session_id = message.get('session_id')
            error = message.get('error', '')
            
            session = self.terminal_manager.get_session(session_id)
            if not session:
                logger.warning(f"PTY终端会话不存在: {session_id}")
                return
            
            # 转发错误到前端WebSocket
            if session.websocket:
                response = {
                    'type': 'terminal_error',
                    'session_id': session_id,
                    'error': error
                }
                try:
                    await session.websocket.send(json.dumps(response))
                except Exception as e:
                    logger.error(f"向前端发送PTY终端错误失败: {e}")
            
            # 记录错误日志
            logger.error(f"PTY终端错误 {session_id}: {error}")
            
        except Exception as e:
            logger.error(f"处理PTY终端错误失败: {e}")

    async def close_pty_terminal_session(self, session_id: str):
        """关闭PTY终端会话"""
        try:
            session = self.terminal_manager.get_session(session_id)
            if session:
                # 向Agent发送关闭消息
                agent = self.agents.get(session.agent_id)
                if agent and agent.status == 'ONLINE':
                    try:
                        close_message = {
                            'type': 'terminal_close',
                            'session_id': session_id
                        }
                        await agent.websocket.send(json.dumps(close_message))
                    except Exception as e:
                        logger.error(f"向Agent发送终端关闭消息失败: {e}")
            
            # 关闭会话
            self.terminal_manager.close_session(session_id)
            logger.info(f"PTY终端会话 {session_id} 已关闭")
            
        except Exception as e:
            logger.error(f"关闭PTY终端会话失败: {e}")

    async def handle_pty_terminal_ready(self, message: dict):
        """处理PTY终端就绪消息"""
        try:
            session_id = message.get('session_id')
            
            session = self.terminal_manager.get_session(session_id)
            if not session:
                logger.warning(f"PTY终端会话不存在: {session_id}")
                return
            
            # 转发就绪消息到前端WebSocket
            if session.websocket:
                response = {
                    'type': 'terminal_ready',
                    'session_id': session_id,
                    'cols': message.get('cols', 80),
                    'rows': message.get('rows', 24)
                }
                try:
                    await session.websocket.send(json.dumps(response))
                    logger.info(f"PTY终端就绪消息已转发: {session_id}")
                except Exception as e:
                    logger.error(f"向前端发送PTY终端就绪消息失败: {e}")
            
        except Exception as e:
            logger.error(f"处理PTY终端就绪消息失败: {e}")

    async def handle_terminal_websocket(self, websocket, agent_id: str):
        """处理PTY终端WebSocket连接"""
        session_id = None
        try:
            # 检查Agent是否在线 - 支持集群模式
            agent_location = None
            if self.cluster:
                agent_location = await self.cluster.get_agent_location(agent_id)
                
                if not agent_location:
                    error_msg = {
                        'type': 'terminal_error',
                        'error': f'Agent {agent_id} not found in cluster'
                    }
                    await websocket.send(json.dumps(error_msg))
                    return
                
                # 如果Agent在其他节点，建立代理会话
                if not agent_location.get('is_local', True):
                    await self._handle_remote_terminal(websocket, agent_id, agent_location)
                    return
            
            # Agent在本地或单节点模式
            if agent_id not in self.agents:
                error_msg = {
                    'type': 'terminal_error',
                    'error': f'Agent {agent_id} not found'
                }
                await websocket.send(json.dumps(error_msg))
                return
            
            agent = self.agents[agent_id]
            if agent.status != 'ONLINE':
                error_msg = {
                    'type': 'terminal_error', 
                    'error': f'Agent {agent_id} is not online'
                }
                await websocket.send(json.dumps(error_msg))
                return
            
            # 创建终端会话
            session_id = await self.create_pty_terminal_session(agent_id, "admin", websocket)
            if not session_id:
                error_msg = {
                    'type': 'terminal_error',
                    'error': 'Failed to create PTY terminal session'
                }
                await websocket.send(json.dumps(error_msg))
                return
            
            logger.info(f"PTY终端WebSocket连接已建立: session_id={session_id}, agent_id={agent_id}")
            
            # 发送连接成功消息
            success_msg = {
                'type': 'terminal_ready',
                'session_id': session_id,
                'agent_id': agent_id
            }
            await websocket.send(json.dumps(success_msg))
            
            # 处理WebSocket消息
            try:
                async for message in websocket:
                    try:
                        # 支持二进制数据（ZMODEM文件传输）
                        if isinstance(message, bytes):
                            # 处理二进制终端输入（ZMODEM数据）
                            logger.debug(f"收到二进制WebSocket消息: {len(message)} 字节")
                            input_data = base64.b64encode(message).decode('ascii')
                            await self.handle_pty_terminal_input(session_id, input_data, is_binary=True)
                        else:
                            # 尝试解析JSON消息
                            try:
                                data = json.loads(message)
                                
                                # 检查是否是字典类型（有效的JSON对象）
                                if isinstance(data, dict):
                                    msg_type = data.get('type')
                                    
                                    if msg_type == 'terminal_input':
                                        # 处理终端输入
                                        input_data = data.get('data', '')
                                        is_binary = data.get('is_binary', False)
                                        await self.handle_pty_terminal_input(session_id, input_data, is_binary=is_binary)
                                    elif msg_type == 'terminal_resize':
                                        # 调整终端大小
                                        cols = data.get('cols', 80)
                                        rows = data.get('rows', 24)
                                        await self.handle_pty_terminal_resize(session_id, cols, rows)
                                    elif msg_type == 'terminal_ping':
                                        # 心跳保持
                                        self.terminal_manager.update_activity(session_id)
                                        pong_message = {
                                            'type': 'terminal_pong',
                                            'timestamp': datetime.now().isoformat()
                                        }
                                        await websocket.send(json.dumps(pong_message))
                                else:
                                    # JSON解析成功但不是字典（比如数字、字符串），作为终端输入
                                    await self.handle_pty_terminal_input(session_id, message, is_binary=False)
                            except json.JSONDecodeError:
                                # 不是JSON格式，直接作为终端输入处理
                                await self.handle_pty_terminal_input(session_id, message, is_binary=False)
                        
                    except Exception as e:
                        logger.error(f"处理PTY终端WebSocket消息失败: {e}")
                        
            except Exception as e:
                logger.error(f"PTY终端WebSocket连接异常: {e}")
            
        except Exception as e:
            logger.error(f"处理PTY终端WebSocket连接失败: {e}")
        finally:
            # 清理会话
            if session_id:
                await self.close_pty_terminal_session(session_id)
                logger.info(f"PTY终端WebSocket连接已关闭: session_id={session_id}")
    
    async def _handle_remote_terminal(self, websocket, agent_id: str, agent_location: dict):
        """处理远程节点的终端连接（代理模式）"""
        session_id = f"remote_{agent_id}_{secrets.token_urlsafe(16)}"
        target_node = agent_location['node_id']
        
        logger.info(f"代理终端连接: session={session_id}, agent={agent_id} -> node:{target_node}")
        
        try:
            # 记录远程会话
            self.remote_terminal_sessions[session_id] = target_node
            
            # 向目标节点发送终端初始化请求
            init_message = {
                'type': 'terminal_init_request',
                'session_id': session_id,
                'agent_id': agent_id,
                'requester_node': self.cluster.node_id
            }
            await self.cluster.send_to_node(target_node, init_message)
            
            # 发送连接成功消息
            success_msg = {
                'type': 'terminal_ready',
                'session_id': session_id,
                'agent_id': agent_id,
                'remote': True
            }
            await websocket.send(json.dumps(success_msg))
            
            # 处理前端消息并转发到目标节点
            try:
                async for message in websocket:
                    try:
                        if isinstance(message, bytes):
                            # 二进制数据
                            input_data = base64.b64encode(message).decode('ascii')
                            forward_msg = {
                                'type': 'terminal_forward_input',
                                'session_id': session_id,
                                'data': input_data,
                                'is_binary': True
                            }
                            await self.cluster.send_to_node(target_node, forward_msg)
                        else:
                            # 文本/JSON数据
                            try:
                                data = json.loads(message)
                                if isinstance(data, dict):
                                    data['session_id'] = session_id
                                    forward_msg = {
                                        'type': 'terminal_forward_message',
                                        'session_id': session_id,
                                        'data': data
                                    }
                                    await self.cluster.send_to_node(target_node, forward_msg)
                            except json.JSONDecodeError:
                                forward_msg = {
                                    'type': 'terminal_forward_input',
                                    'session_id': session_id,
                                    'data': message,
                                    'is_binary': False
                                }
                                await self.cluster.send_to_node(target_node, forward_msg)
                    except Exception as e:
                        logger.error(f"转发终端消息失败: {e}")
            except Exception as e:
                logger.error(f"远程终端连接异常: {e}")
        finally:
            # 清理远程会话
            if session_id in self.remote_terminal_sessions:
                del self.remote_terminal_sessions[session_id]
            
            # 通知目标节点关闭会话
            close_msg = {
                'type': 'terminal_close_request',
                'session_id': session_id
            }
            if self.cluster:
                await self.cluster.send_to_node(target_node, close_msg)
            
            logger.info(f"远程终端连接已关闭: session={session_id}")

    async def handle_client(self, websocket, path):
        """处理客户端连接"""
        client_ip = websocket.remote_address[0]
        client_port = websocket.remote_address[1]
        logger.info(f"新连接: {client_ip}:{client_port} path: '{path}' (type: {type(path)})")
        
        # 记录连接的详细信息
        connection_start_time = datetime.now()
        logger.info(f"连接建立时间: {connection_start_time.isoformat()}")
        
        # 检查是否是终端WebSocket连接
        if path and path.startswith('/terminal/'):
            agent_id = path.split('/')[-1]  # 从路径中提取agent_id
            logger.info(f"检测到终端WebSocket连接，agent_id: {agent_id}")
            await self.handle_terminal_websocket(websocket, agent_id)
            return
        else:
            logger.info(f"普通WebSocket连接，进入Agent消息处理流程")
        
        agent_id = None
        message_count = 0
        
        try:
            async for message in websocket:
                try:
                    message_count += 1
                    data = json.loads(message)
                    msg_type = data.get('type')
                    
                    # 记录消息统计
                    if message_count % 10 == 0:  # 每10条消息记录一次
                        logger.debug(f"连接 {client_ip}:{client_port} 已处理 {message_count} 条消息")
                    
                    # 检查是否是终端消息（路径解析失败的备用方案）
                    if msg_type in ['terminal_input', 'terminal_resize', 'terminal_ping']:
                        logger.info(f"检测到终端消息但路径为空，尝试从消息中获取agent信息")
                        # 这是一个备用方案，尝试从其他地方获取agent_id
                        # 暂时使用第一个在线agent进行测试
                        online_agents = [aid for aid, agent in self.agents.items() if agent.status == 'ONLINE']
                        if online_agents:
                            target_agent_id = online_agents[0]  # 使用第一个在线agent
                            logger.info(f"使用在线Agent: {target_agent_id} 处理终端消息")
                            
                            if msg_type == 'terminal_input':
                                # 获取或创建终端会话
                                session_id = f"emergency_session_{target_agent_id}"
                                if not self.terminal_manager.get_session(session_id):
                                    # 创建临时会话
                                    temp_session_id = await self.create_pty_terminal_session(target_agent_id, "admin", websocket)
                                    if temp_session_id:
                                        session_id = temp_session_id
                                
                                input_data = data.get('data', '')
                                await self.handle_pty_terminal_input(session_id, input_data)
                                continue
                                
                            elif msg_type == 'terminal_resize':
                                # 类似处理resize
                                cols = data.get('cols', 80)
                                rows = data.get('rows', 24)
                                session_id = f"emergency_session_{target_agent_id}"
                                await self.handle_pty_terminal_resize(session_id, cols, rows)
                                continue
                    
                    # 如果是注册消息，记录agent_id
                    if msg_type == 'register':
                        agent_id = data.get('agent_id') or data.get('id')
                        if not agent_id:
                            agent_id = generate_agent_id(data.get('ip', client_ip))
                    
                    await self.handle_agent_message(websocket, data)
                except json.JSONDecodeError:
                    logger.error(f"无效的JSON消息: {message}")
                except Exception as e:
                    logger.error(f"处理消息时出错: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            connection_duration = (datetime.now() - connection_start_time).total_seconds()
            logger.info(f"连接关闭: {client_ip}:{client_port}, 持续时间: {connection_duration:.1f}秒, 处理消息数: {message_count}")
        except Exception as e:
            connection_duration = (datetime.now() - connection_start_time).total_seconds()
            logger.error(f"连接错误: {client_ip}:{client_port}, 错误: {e}, 持续时间: {connection_duration:.1f}秒")
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
                            'external_ip': existing_agent.get('external_ip', ''),  # 保持原有的外网IP
                            'status': 'OFFLINE',
                            'last_heartbeat': existing_agent['last_heartbeat'],
                            'register_time': existing_agent['register_time'],
                            'websocket_info': {}
                        }
                        self.db.save_agent(agent_data)
                        logger.info(f"Agent {agent_id} 状态已更新为离线")
                        break
                
                # 在集群模式下注销Agent位置
                if self.cluster:
                    await self.cluster.unregister_agent_location(agent_id)
                
                # 从内存中移除Agent（可选，也可以保留用于重连）
                # del self.agents[agent_id]
                
        except Exception as e:
            logger.error(f"清理断开连接的Agent时出错: {e}")
    
    async def _setup_cluster_handlers(self):
        """设置集群消息处理器"""
        if not self.cluster:
            return
        
        # 注册终端初始化请求处理器
        self.cluster.register_handler('terminal_init_request', self._handle_cluster_terminal_init)
        
        # 注册终端消息转发处理器
        self.cluster.register_handler('terminal_forward_input', self._handle_cluster_terminal_input)
        self.cluster.register_handler('terminal_forward_message', self._handle_cluster_terminal_message)
        
        # 注册终端关闭请求处理器
        self.cluster.register_handler('terminal_close_request', self._handle_cluster_terminal_close)
        
        logger.info("集群消息处理器已注册")
    
    async def _handle_cluster_terminal_init(self, data: dict):
        """处理集群终端初始化请求"""
        try:
            session_id = data.get('session_id')
            agent_id = data.get('agent_id')
            requester_node = data.get('requester_node')
            
            logger.info(f"收到远程终端初始化请求: session={session_id}, agent={agent_id}, from=node:{requester_node}")
            
            # 检查Agent是否在本地
            if agent_id not in self.agents:
                logger.error(f"Agent不在本地: {agent_id}")
                return
            
            agent = self.agents[agent_id]
            if agent.status != 'ONLINE':
                logger.error(f"Agent不在线: {agent_id}")
                return
            
            # 创建一个虚拟的WebSocket对象用于接收转发的消息
            class RemoteWebSocketProxy:
                def __init__(self, cluster, requester_node, session_id):
                    self.cluster = cluster
                    self.requester_node = requester_node
                    self.session_id = session_id
                
                async def send(self, message):
                    # 转发消息回请求节点
                    forward_msg = {
                        'type': 'terminal_response',
                        'session_id': self.session_id,
                        'data': message
                    }
                    await self.cluster.send_to_node(self.requester_node, forward_msg)
            
            proxy_ws = RemoteWebSocketProxy(self.cluster, requester_node, session_id)
            
            # 创建本地终端会话
            local_session_id = await self.create_pty_terminal_session(agent_id, "admin", proxy_ws)
            
            if local_session_id:
                # 映射远程session_id到本地session_id
                self.remote_terminal_sessions[session_id] = local_session_id
                logger.info(f"远程终端会话已创建: remote={session_id}, local={local_session_id}")
            else:
                logger.error(f"创建终端会话失败: agent={agent_id}")
                
        except Exception as e:
            logger.error(f"处理集群终端初始化请求失败: {e}")
    
    async def _handle_cluster_terminal_input(self, data: dict):
        """处理集群终端输入"""
        try:
            session_id = data.get('session_id')
            input_data = data.get('data', '')
            is_binary = data.get('is_binary', False)
            
            # 获取本地会话ID
            local_session_id = self.remote_terminal_sessions.get(session_id)
            if not local_session_id:
                logger.warning(f"远程会话不存在: {session_id}")
                return
            
            # 处理输入
            await self.handle_pty_terminal_input(local_session_id, input_data, is_binary)
            
        except Exception as e:
            logger.error(f"处理集群终端输入失败: {e}")
    
    async def _handle_cluster_terminal_message(self, data: dict):
        """处理集群终端消息"""
        try:
            session_id = data.get('session_id')
            message_data = data.get('data', {})
            
            # 获取本地会话ID
            local_session_id = self.remote_terminal_sessions.get(session_id)
            if not local_session_id:
                logger.warning(f"远程会话不存在: {session_id}")
                return
            
            # 处理消息
            msg_type = message_data.get('type')
            
            if msg_type == 'terminal_input':
                input_data = message_data.get('data', '')
                is_binary = message_data.get('is_binary', False)
                await self.handle_pty_terminal_input(local_session_id, input_data, is_binary)
            elif msg_type == 'terminal_resize':
                cols = message_data.get('cols', 80)
                rows = message_data.get('rows', 24)
                await self.handle_pty_terminal_resize(local_session_id, cols, rows)
            elif msg_type == 'terminal_ping':
                self.terminal_manager.update_activity(local_session_id)
            
        except Exception as e:
            logger.error(f"处理集群终端消息失败: {e}")
    
    async def _handle_cluster_terminal_close(self, data: dict):
        """处理集群终端关闭请求"""
        try:
            session_id = data.get('session_id')
            
            # 获取本地会话ID
            local_session_id = self.remote_terminal_sessions.get(session_id)
            if not local_session_id:
                logger.warning(f"远程会话不存在: {session_id}")
                return
            
            # 关闭本地会话
            await self.close_pty_terminal_session(local_session_id)
            
            # 清理映射
            if session_id in self.remote_terminal_sessions:
                del self.remote_terminal_sessions[session_id]
            
            logger.info(f"远程终端会话已关闭: {session_id}")
            
        except Exception as e:
            logger.error(f"处理集群终端关闭请求失败: {e}")

    async def check_agent_heartbeats(self):
        """检查Agent心跳，将超时的Agent标记为离线"""
        check_count = 0
        while self.running:
            try:
                check_count += 1
                current_time = datetime.now()
                timeout_agents = []
                
                # 每10次检查记录一次统计信息
                if check_count % 10 == 0:
                    online_count = sum(1 for agent in self.agents.values() if agent.status == "ONLINE")
                    logger.debug(f"心跳检查 #{check_count}: 在线Agent数量: {online_count}/{len(self.agents)}")
                
                for agent_id, agent in self.agents.items():
                    if agent.last_heartbeat:
                        try:
                            last_heartbeat_time = datetime.fromisoformat(agent.last_heartbeat)
                            time_diff = (current_time - last_heartbeat_time).total_seconds()
                            
                            # 如果超过30秒没有心跳，标记为离线（从15秒调整为30秒）
                            if time_diff > 30 and agent.status == "ONLINE":
                                timeout_agents.append(agent_id)
                                logger.info(f"Agent {agent_id} 心跳超时 ({time_diff:.1f}s)，标记为离线")
                            elif time_diff > 20 and agent.status == "ONLINE":
                                # 超过20秒给出警告，但不断开连接
                                logger.warning(f"Agent {agent_id} 心跳延迟 ({time_diff:.1f}s)，接近超时阈值")
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
                                    'external_ip': existing_agent.get('external_ip', ''),  # 保持原有的外网IP
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

    async def cleanup_terminal_sessions(self):
        """定期清理过期的终端会话"""
        while self.running:
            try:
                expired_count = self.terminal_manager.cleanup_expired_sessions()
                if expired_count > 0:
                    logger.info(f"清理了 {expired_count} 个过期的终端会话")
                
                # 每60秒检查一次
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"清理终端会话时出错: {e}")
                await asyncio.sleep(60)

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
            'project_id': getattr(task, 'project_id', None),  # 添加 project_id
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

    async def execute_script_on_agent(self, agent_id: str, script: str, timeout: int = 300) -> dict:
        """
        在指定agent上执行脚本并返回结果
        用于作业执行等场景
        
        Args:
            agent_id: Agent ID
            script: 要执行的脚本内容
            timeout: 超时时间（秒）
        
        Returns:
            dict: 执行结果 {
                'exit_code': int,
                'output': str,
                'error': str,
                'agent_hostname': str,
                'agent_ip': str
            }
        """
        try:
            # 查找agent
            if agent_id not in self.agents:
                return {
                    'exit_code': -1,
                    'output': '',
                    'error': f'Agent {agent_id} 不在线',
                    'agent_hostname': '未知',
                    'agent_ip': ''
                }
            
            agent = self.agents[agent_id]
            
            # 创建临时任务
            task_id = str(uuid.uuid4())
            task = Task(
                id=task_id,
                script=script,
                target_hosts=[agent_id],
                timeout=timeout,
                results={},
                status="PENDING",
                created_at=datetime.now().isoformat(),
                started_at="",
                completed_at=""
            )
            self.tasks[task_id] = task
            
            # 发送执行任务
            task_message = {
                'type': 'execute_task',
                'task_id': task_id,
                'script': script,
                'script_params': '',
                'timeout': timeout,
                'execution_user': 'root'
            }
            
            await agent.websocket.send(json.dumps(task_message))
            logger.debug(f"向Agent {agent_id} 发送脚本执行任务: {task_id}")
            
            # 等待执行结果（轮询）
            max_wait = timeout + 10
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                if agent_id in task.results:
                    result = task.results[agent_id]
                    # 添加agent信息
                    result['agent_hostname'] = agent.hostname
                    result['agent_ip'] = agent.ip
                    
                    # 清理临时任务
                    if task_id in self.tasks:
                        del self.tasks[task_id]
                    
                    return result
                
                await asyncio.sleep(0.5)
            
            # 超时
            if task_id in self.tasks:
                del self.tasks[task_id]
            
            return {
                'exit_code': -1,
                'output': '',
                'error': f'执行超时（{timeout}秒）',
                'agent_hostname': agent.hostname,
                'agent_ip': agent.ip
            }
            
        except Exception as e:
            logger.error(f"执行脚本失败: {e}")
            return {
                'exit_code': -1,
                'output': '',
                'error': str(e),
                'agent_hostname': '未知',
                'agent_ip': ''
            }

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
            'project_id': getattr(task, 'project_id', None),  # 添加 project_id
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

    async def send_agent_update(self, agent_id: str, version: str, download_url: str, md5: str):
        """发送Agent更新命令"""
        try:
            logger.info(f"开始发送更新命令: agent_id={agent_id}, version={version}")
            logger.info(f"当前事件循环: {asyncio.get_event_loop()}")
            logger.info(f"主事件循环: {self.loop}")
            
            if agent_id not in self.agents:
                logger.error(f"Agent不存在: {agent_id}")
                return False, 'Agent不存在'
            
            agent = self.agents[agent_id]
            logger.info(f"Agent状态: {agent.status}, WebSocket对象: {agent.websocket}")
            
            if agent.status != 'ONLINE' or not agent.websocket:
                logger.error(f"Agent未连接: {agent_id}")
                return False, 'Agent未连接'
            
            # 检查WebSocket状态
            ws_state = "unknown"
            if hasattr(agent.websocket, 'open'):
                ws_state = "open" if agent.websocket.open else "closed"
            elif hasattr(agent.websocket, 'closed'):
                ws_state = "closed" if agent.websocket.closed else "open"
            logger.info(f"WebSocket状态: {ws_state}")
            
            update_message = {
                'type': 'update_agent',
                'agent_id': agent_id,
                'version': version,
                'download_url': download_url,
                'md5': md5
            }
            
            logger.info(f"准备发送消息: {json.dumps(update_message)}")
            await agent.websocket.send(json.dumps(update_message))
            logger.info(f"✓ WebSocket.send() 调用完成")
            logger.info(f"✓ 已发送更新命令到Agent: {agent_id}, 版本: {version}")
            return True, f'已发送更新命令，版本: {version}'
            
        except Exception as e:
            logger.error(f"❌ 发送更新命令失败: {agent_id}, 错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, f'发送更新命令失败: {str(e)}'
    
    async def send_agent_restart(self, agent_id: str):
        """发送Agent重启命令"""
        try:
            if agent_id not in self.agents:
                logger.error(f"Agent不存在: {agent_id}")
                return False, 'Agent不存在'
            
            agent = self.agents[agent_id]
            if agent.status != 'ONLINE' or not agent.websocket:
                logger.error(f"Agent未连接: {agent_id}")
                return False, 'Agent不在线'
            
            restart_message = {
                'type': 'restart_agent',
                'agent_id': agent_id,
                'message': 'Batch restart requested'
            }
            
            await agent.websocket.send(json.dumps(restart_message))
            logger.info(f"已发送重启命令到Agent: {agent_id}")
            return True, '重启命令已发送'
            
        except Exception as e:
            logger.error(f"发送重启命令失败: {agent_id}, 错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, f'重启失败: {str(e)}'

    async def start(self):
        """启动服务器"""
        self.running = True
        # 保存当前事件循环的引用
        self.loop = asyncio.get_event_loop()
        logger.info(f"Qunkong 服务器启动在 ws://{self.host}:{self.port}")
        
        # 启动集群管理器
        if self.cluster:
            await self.cluster.start()
            await self._setup_cluster_handlers()
            logger.info(f"集群模式已启动: node_id={self.cluster.node_id}")
        else:
            logger.info("单节点模式运行")
        
        # 启动心跳检查任务
        self.heartbeat_check_task = asyncio.create_task(self.check_agent_heartbeats())
        logger.info("心跳检查任务已启动")
        
        # 启动会话清理任务
        self.session_cleanup_task = asyncio.create_task(self.cleanup_terminal_sessions())
        logger.info("终端会话清理任务已启动")
        
        # 创建包装函数来处理path参数
        async def websocket_handler(websocket, path):
            await self.handle_client(websocket, path)
        
        try:
            # 配置 WebSocket 参数以避免超时
            async with websockets.serve(
                websocket_handler, 
                self.host, 
                self.port,
                ping_interval=20,  # 每20秒发送一次ping
                ping_timeout=20,   # ping超时时间20秒
                close_timeout=10,  # 关闭超时10秒
                max_size=10 * 1024 * 1024,  # 最大消息大小10MB
                compression=None   # 禁用压缩以提高性能
            ):
                await asyncio.Future()  # 保持运行
        finally:
            # 服务器关闭时停止集群
            if self.cluster:
                await self.cluster.stop()
                logger.info("集群管理器已停止")
            
            # 服务器关闭时取消任务
            if self.heartbeat_check_task:
                self.heartbeat_check_task.cancel()
                try:
                    await self.heartbeat_check_task
                except asyncio.CancelledError:
                    pass
                logger.info("心跳检查任务已停止")
            
            if self.session_cleanup_task:
                self.session_cleanup_task.cancel()
                try:
                    await self.session_cleanup_task
                except asyncio.CancelledError:
                    pass
                logger.info("终端会话清理任务已停止")

"""
集群管理模块 - 支持多节点部署和节点间通信
"""
import asyncio
import json
import logging
import uuid
import time
from typing import Dict, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

class ClusterManager:
    """集群管理器 - 处理节点间通信和状态同步"""
    
    def __init__(self, redis_client=None, node_id=None):
        """
        初始化集群管理器
        
        Args:
            redis_client: Redis 客户端实例（可选，如果为None则运行在单节点模式）
            node_id: 节点唯一ID（可选，如果为None则自动生成）
        """
        self.redis = redis_client
        self.node_id = node_id or str(uuid.uuid4())[:8]
        self.is_cluster_mode = redis_client is not None
        
        # 消息处理回调
        self.message_handlers: Dict[str, Callable] = {}
        
        # 订阅任务
        self.pubsub_task = None
        self.heartbeat_task = None
        
        # 运行状态
        self.running = False
        
        logger.info(f"集群管理器初始化: node_id={self.node_id}, cluster_mode={self.is_cluster_mode}")
    
    def register_handler(self, message_type: str, handler: Callable):
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
        logger.info(f"注册消息处理器: {message_type}")
    
    async def start(self):
        """启动集群管理器"""
        if not self.is_cluster_mode:
            logger.info("单节点模式，跳过集群初始化")
            return
        
        self.running = True
        
        # 注册节点
        await self._register_node()
        
        # 启动心跳任务
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # 启动消息订阅任务
        self.pubsub_task = asyncio.create_task(self._pubsub_loop())
        
        logger.info(f"集群管理器已启动: node_id={self.node_id}")
    
    async def stop(self):
        """停止集群管理器"""
        if not self.is_cluster_mode:
            return
        
        self.running = False
        
        # 注销节点
        await self._unregister_node()
        
        # 取消任务
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub_task:
            self.pubsub_task.cancel()
            try:
                await self.pubsub_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"集群管理器已停止: node_id={self.node_id}")
    
    async def _register_node(self):
        """注册当前节点到Redis"""
        try:
            node_info = {
                'node_id': self.node_id,
                'registered_at': datetime.now().isoformat(),
                'last_heartbeat': datetime.now().isoformat(),
                'status': 'online'
            }
            
            # 使用 SETEX 设置节点信息，60秒过期
            await self.redis.setex(
                f'node:{self.node_id}',
                60,
                json.dumps(node_info)
            )
            
            logger.info(f"节点已注册: {self.node_id}")
        except Exception as e:
            logger.error(f"注册节点失败: {e}")
    
    async def _unregister_node(self):
        """注销当前节点"""
        try:
            await self.redis.delete(f'node:{self.node_id}')
            logger.info(f"节点已注销: {self.node_id}")
        except Exception as e:
            logger.error(f"注销节点失败: {e}")
    
    async def _heartbeat_loop(self):
        """心跳循环 - 每20秒更新一次节点状态"""
        while self.running:
            try:
                node_info = {
                    'node_id': self.node_id,
                    'last_heartbeat': datetime.now().isoformat(),
                    'status': 'online'
                }
                
                await self.redis.setex(
                    f'node:{self.node_id}',
                    60,
                    json.dumps(node_info)
                )
                
                logger.debug(f"节点心跳已更新: {self.node_id}")
                await asyncio.sleep(20)
            except Exception as e:
                logger.error(f"心跳更新失败: {e}")
                await asyncio.sleep(5)
    
    async def _pubsub_loop(self):
        """订阅循环 - 监听节点消息"""
        try:
            # 订阅当前节点的消息频道
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(f'node:{self.node_id}')
            
            logger.info(f"开始监听消息频道: node:{self.node_id}")
            
            while self.running:
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    
                    if message and message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            await self._handle_message(data)
                        except json.JSONDecodeError as e:
                            logger.error(f"消息解析失败: {e}")
                    
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"处理订阅消息失败: {e}")
                    await asyncio.sleep(1)
            
            await pubsub.unsubscribe(f'node:{self.node_id}')
            await pubsub.close()
            
        except Exception as e:
            logger.error(f"订阅循环异常: {e}")
    
    async def _handle_message(self, data: dict):
        """处理接收到的消息"""
        try:
            msg_type = data.get('type')
            
            if msg_type in self.message_handlers:
                handler = self.message_handlers[msg_type]
                await handler(data)
            else:
                logger.warning(f"未知的消息类型: {msg_type}")
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
    
    async def register_agent_location(self, agent_id: str, agent_info: dict):
        """
        注册Agent位置信息
        
        Args:
            agent_id: Agent ID
            agent_info: Agent信息字典
        """
        if not self.is_cluster_mode:
            return
        
        try:
            location_info = {
                'agent_id': agent_id,
                'node_id': self.node_id,
                'hostname': agent_info.get('hostname', 'Unknown'),
                'ip': agent_info.get('ip', ''),
                'registered_at': datetime.now().isoformat()
            }
            
            # 保存 Agent 位置信息，30分钟过期（心跳会更新）
            await self.redis.setex(
                f'agent_location:{agent_id}',
                1800,
                json.dumps(location_info)
            )
            
            logger.info(f"Agent位置已注册: {agent_id} -> node:{self.node_id}")
        except Exception as e:
            logger.error(f"注册Agent位置失败: {e}")
    
    async def unregister_agent_location(self, agent_id: str):
        """注销Agent位置信息"""
        if not self.is_cluster_mode:
            return
        
        try:
            await self.redis.delete(f'agent_location:{agent_id}')
            logger.info(f"Agent位置已注销: {agent_id}")
        except Exception as e:
            logger.error(f"注销Agent位置失败: {e}")
    
    async def get_agent_location(self, agent_id: str) -> Optional[dict]:
        """
        获取Agent所在节点信息
        
        Returns:
            节点信息字典，如果Agent不存在则返回None
        """
        if not self.is_cluster_mode:
            # 单节点模式，返回当前节点
            return {
                'agent_id': agent_id,
                'node_id': self.node_id,
                'is_local': True
            }
        
        try:
            location_data = await self.redis.get(f'agent_location:{agent_id}')
            
            if location_data:
                location_info = json.loads(location_data)
                location_info['is_local'] = location_info['node_id'] == self.node_id
                return location_info
            
            return None
        except Exception as e:
            logger.error(f"获取Agent位置失败: {e}")
            return None
    
    async def send_to_node(self, target_node_id: str, message: dict):
        """
        发送消息到指定节点
        
        Args:
            target_node_id: 目标节点ID
            message: 消息字典
        """
        if not self.is_cluster_mode:
            logger.warning("单节点模式不支持节点间通信")
            return
        
        try:
            # 添加发送者信息
            message['from_node'] = self.node_id
            message['timestamp'] = datetime.now().isoformat()
            
            # 发布消息到目标节点频道
            await self.redis.publish(
                f'node:{target_node_id}',
                json.dumps(message)
            )
            
            logger.debug(f"消息已发送: {self.node_id} -> {target_node_id}, type={message.get('type')}")
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
    
    async def broadcast(self, message: dict, exclude_self=True):
        """
        广播消息到所有节点
        
        Args:
            message: 消息字典
            exclude_self: 是否排除自己
        """
        if not self.is_cluster_mode:
            return
        
        try:
            # 获取所有在线节点
            nodes = await self.get_online_nodes()
            
            for node_id in nodes:
                if exclude_self and node_id == self.node_id:
                    continue
                
                await self.send_to_node(node_id, message)
            
            logger.debug(f"消息已广播到 {len(nodes)} 个节点")
        except Exception as e:
            logger.error(f"广播消息失败: {e}")
    
    async def get_online_nodes(self) -> list:
        """获取所有在线节点列表"""
        if not self.is_cluster_mode:
            return [self.node_id]
        
        try:
            # 扫描所有节点key
            nodes = []
            cursor = 0
            
            while True:
                cursor, keys = await self.redis.scan(cursor, match='node:*', count=100)
                
                for key in keys:
                    node_id = key.decode('utf-8').split(':')[1]
                    nodes.append(node_id)
                
                if cursor == 0:
                    break
            
            return nodes
        except Exception as e:
            logger.error(f"获取在线节点失败: {e}")
            return []
    
    async def forward_terminal_message(self, agent_id: str, session_id: str, message_data: dict):
        """
        转发终端消息到Agent所在节点
        
        Args:
            agent_id: Agent ID
            session_id: 终端会话ID
            message_data: 消息数据
        """
        if not self.is_cluster_mode:
            # 单节点模式，不需要转发
            return None
        
        try:
            # 获取Agent位置
            location = await self.get_agent_location(agent_id)
            
            if not location:
                logger.error(f"无法找到Agent位置: {agent_id}")
                return None
            
            if location['is_local']:
                # Agent在本地，不需要转发
                return None
            
            # 转发到目标节点
            forward_message = {
                'type': 'terminal_forward',
                'agent_id': agent_id,
                'session_id': session_id,
                'data': message_data
            }
            
            await self.send_to_node(location['node_id'], forward_message)
            logger.debug(f"终端消息已转发: session={session_id}, agent={agent_id} -> node:{location['node_id']}")
            
            return location['node_id']
        except Exception as e:
            logger.error(f"转发终端消息失败: {e}")
            return None


class DummyRedis:
    """虚拟Redis客户端 - 用于单节点模式"""
    
    async def setex(self, *args, **kwargs):
        pass
    
    async def delete(self, *args, **kwargs):
        pass
    
    async def get(self, *args, **kwargs):
        return None
    
    async def publish(self, *args, **kwargs):
        pass
    
    async def scan(self, *args, **kwargs):
        return 0, []
    
    def pubsub(self):
        class DummyPubSub:
            async def subscribe(self, *args): pass
            async def get_message(self, *args, **kwargs): return None
            async def unsubscribe(self, *args): pass
            async def close(self): pass
        return DummyPubSub()


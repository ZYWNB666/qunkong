"""
QueenBee 数据库模型
"""
import sqlite3
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "queenbee.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建执行历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS execution_history (
                id TEXT PRIMARY KEY,
                script_name TEXT,
                script_content TEXT,
                script_params TEXT,
                target_hosts TEXT,  -- JSON格式存储
                status TEXT,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                timeout INTEGER,
                execution_user TEXT,
                results TEXT,  -- JSON格式存储
                error_message TEXT
            )
        ''')
        
        # 创建Agent系统信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_system_info (
                agent_id TEXT PRIMARY KEY,
                hostname TEXT,
                ip_address TEXT,
                last_heartbeat TEXT,
                status TEXT,
                register_time TEXT,
                system_info TEXT,  -- JSON格式存储系统信息
                network_info TEXT,  -- JSON格式存储网卡信息
                memory_info TEXT,  -- JSON格式存储内存信息
                disk_info TEXT,    -- JSON格式存储磁盘信息
                cpu_info TEXT,     -- JSON格式存储CPU信息
                FOREIGN KEY (agent_id) REFERENCES agents (id)
            )
        ''')
        
        # 创建Agent基本信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                hostname TEXT,
                ip_address TEXT,
                status TEXT,
                last_heartbeat TEXT,
                register_time TEXT,
                websocket_info TEXT  -- JSON格式存储WebSocket连接信息
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_execution_history(self, task_data: Dict[str, Any]) -> bool:
        """保存执行历史到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO execution_history 
                (id, script_name, script_content, script_params, target_hosts, 
                 status, created_at, started_at, completed_at, timeout, 
                 execution_user, results, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_data.get('id'),
                task_data.get('script_name', '未命名任务'),
                task_data.get('script'),
                task_data.get('script_params', ''),
                json.dumps(task_data.get('target_hosts', [])),
                task_data.get('status'),
                task_data.get('created_at'),
                task_data.get('started_at'),
                task_data.get('completed_at'),
                task_data.get('timeout', 300),
                task_data.get('execution_user', 'root'),
                json.dumps(task_data.get('results', {})),
                task_data.get('error_message', '')
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"保存执行历史失败: {e}")
            return False
    
    def get_execution_history(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取执行历史"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, script_name, script_content, script_params, target_hosts,
                       status, created_at, started_at, completed_at, timeout,
                       execution_user, results, error_message
                FROM execution_history
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            rows = cursor.fetchall()
            conn.close()
            
            history = []
            for row in rows:
                history.append({
                    'id': row[0],
                    'script_name': row[1],
                    'script': row[2],  # 保持script字段名一致
                    'script_content': row[2],  # 同时提供script_content别名
                    'script_params': row[3],
                    'target_hosts': json.loads(row[4]) if row[4] else [],
                    'status': row[5],
                    'created_at': row[6],
                    'started_at': row[7],
                    'completed_at': row[8],
                    'timeout': row[9],
                    'execution_user': row[10],
                    'results': json.loads(row[11]) if row[11] else {},
                    'error_message': row[12]
                })
            
            return history
        except Exception as e:
            print(f"获取执行历史失败: {e}")
            return []
    
    def save_agent_system_info(self, agent_id: str, system_info: Dict[str, Any]) -> bool:
        """保存Agent系统信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO agent_system_info
                (agent_id, hostname, ip_address, last_heartbeat, status, register_time,
                 system_info, network_info, memory_info, disk_info, cpu_info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                agent_id,
                system_info.get('hostname', ''),
                system_info.get('ip_address', ''),
                system_info.get('last_heartbeat', ''),
                system_info.get('status', 'OFFLINE'),
                system_info.get('register_time', ''),
                json.dumps(system_info.get('system_info', {})),
                json.dumps(system_info.get('network_info', {})),
                json.dumps(system_info.get('memory_info', {})),
                json.dumps(system_info.get('disk_info', {})),
                json.dumps(system_info.get('cpu_info', {}))
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"保存Agent系统信息失败: {e}")
            return False
    
    def get_agent_system_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取Agent系统信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT agent_id, hostname, ip_address, last_heartbeat, status, register_time,
                       system_info, network_info, memory_info, disk_info, cpu_info
                FROM agent_system_info
                WHERE agent_id = ?
            ''', (agent_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'agent_id': row[0],
                    'hostname': row[1],
                    'ip_address': row[2],
                    'last_heartbeat': row[3],
                    'status': row[4],
                    'register_time': row[5],
                    'system_info': json.loads(row[6]) if row[6] else {},
                    'network_info': json.loads(row[7]) if row[7] else {},
                    'memory_info': json.loads(row[8]) if row[8] else {},
                    'disk_info': json.loads(row[9]) if row[9] else {},
                    'cpu_info': json.loads(row[10]) if row[10] else {}
                }
            return None
        except Exception as e:
            print(f"获取Agent系统信息失败: {e}")
            return None
    
    def save_agent(self, agent_data: Dict[str, Any]) -> bool:
        """保存Agent基本信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO agents
                (id, hostname, ip_address, status, last_heartbeat, register_time, websocket_info)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                agent_data.get('id'),
                agent_data.get('hostname', ''),
                agent_data.get('ip_address', ''),
                agent_data.get('status', 'OFFLINE'),
                agent_data.get('last_heartbeat', ''),
                agent_data.get('register_time', ''),
                json.dumps(agent_data.get('websocket_info', {}))
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"保存Agent信息失败: {e}")
            return False
    
    def get_all_agents(self) -> List[Dict[str, Any]]:
        """获取所有Agent信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, hostname, ip_address, status, last_heartbeat, register_time, websocket_info
                FROM agents
                ORDER BY register_time DESC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            agents = []
            for row in rows:
                agents.append({
                    'id': row[0],
                    'hostname': row[1],
                    'ip_address': row[2],
                    'status': row[3],
                    'last_heartbeat': row[4],
                    'register_time': row[5],
                    'websocket_info': json.loads(row[6]) if row[6] else {}
                })
            
            return agents
        except Exception as e:
            print(f"获取Agent列表失败: {e}")
            return []
    
    def get_current_time(self) -> str:
        """获取当前时间的ISO格式字符串"""
        return datetime.now().isoformat()

def generate_agent_id(ip_address: str) -> str:
    """根据IP地址生成Agent ID（MD5值）"""
    return hashlib.md5(ip_address.encode('utf-8')).hexdigest()

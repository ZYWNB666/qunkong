"""
Qunkong 数据库模型
"""
import pymysql
import hashlib
import configparser
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
from dbutils.pooled_db import PooledDB

class DatabaseManager:
    """数据库管理器 - 使用连接池优化性能"""
    
    _pool = None  # 类级别的连接池单例
    
    def __init__(self, config_path: str = "config/database.conf"):
        self.config_path = config_path
        self.db_config = self._load_config()
        self._init_pool()  # 初始化连接池
        self.init_database()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载数据库配置"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"数据库配置文件不存在: {self.config_path}")
        
        config = configparser.ConfigParser()
        config.read(self.config_path, encoding='utf-8')
        
        return {
            'host': config.get('mysql', 'host'),
            'port': config.getint('mysql', 'port'),
            'database': config.get('mysql', 'database'),
            'username': config.get('mysql', 'username'),
            'password': config.get('mysql', 'password'),
            'charset': config.get('mysql', 'charset', fallback='utf8mb4'),
            'max_connections': config.getint('connection', 'max_connections', fallback=20),
            'min_connections': config.getint('connection', 'min_connections', fallback=5),
            'timeout': config.getint('connection', 'timeout', fallback=30)
        }
    
    def _init_pool(self):
        """初始化数据库连接池"""
        if DatabaseManager._pool is None:
            DatabaseManager._pool = PooledDB(
                creator=pymysql,
                maxconnections=self.db_config['max_connections'],  # 最大连接数
                mincached=self.db_config.get('min_connections', 5),  # 初始化时创建的空闲连接数
                maxcached=self.db_config['max_connections'],  # 最大空闲连接数
                maxshared=0,  # 0表示所有连接都是专用的
                blocking=True,  # 连接池耗尽时阻塞等待
                maxusage=None,  # 单个连接最大复用次数，None表示无限制
                setsession=[],  # 开始会话时执行的SQL命令列表
                ping=1,  # 每次获取连接时检查连接是否可用 (0=None, 1=default, 2=always)
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['username'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                charset=self.db_config['charset'],
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor
            )
            print(f"数据库连接池已初始化: max={self.db_config['max_connections']}, min={self.db_config.get('min_connections', 5)}")
    
    def _get_connection(self):
        """从连接池获取数据库连接"""
        if DatabaseManager._pool is None:
            self._init_pool()
        return DatabaseManager._pool.connection()
    
    def init_database(self):
        """初始化数据库表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 创建Agent基本信息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS agents (
                    id VARCHAR(64) PRIMARY KEY,
                    hostname VARCHAR(255) NOT NULL,
                    ip_address VARCHAR(45) NOT NULL,
                    external_ip VARCHAR(45) DEFAULT '',
                    os_type VARCHAR(50) DEFAULT 'unknown',
                    status VARCHAR(20) DEFAULT 'OFFLINE',
                    tenant_id INT,
                    project_id INT,
                    last_heartbeat DATETIME,
                    register_time DATETIME,
                    websocket_info JSON,
                    tags JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_hostname (hostname),
                    INDEX idx_ip_address (ip_address),
                    INDEX idx_external_ip (external_ip),
                    INDEX idx_status (status),
                    INDEX idx_last_heartbeat (last_heartbeat),
                    INDEX idx_tenant_id (tenant_id),
                    INDEX idx_project_id (project_id),
                    INDEX idx_os_type (os_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 检查并添加 os_type 字段（如果表已存在但没有该字段）
            cursor.execute("SHOW COLUMNS FROM agents LIKE 'os_type'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE agents ADD COLUMN os_type VARCHAR(50) DEFAULT 'unknown' AFTER external_ip")
                cursor.execute("ALTER TABLE agents ADD INDEX idx_os_type (os_type)")
                print("数据库迁移：添加 os_type 字段到 agents 表")
            
            # 检查并添加 tags 字段（如果表已存在但没有该字段）
            cursor.execute("SHOW COLUMNS FROM agents LIKE 'tags'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE agents ADD COLUMN tags JSON AFTER websocket_info")
                print("数据库迁移：添加 tags 字段到 agents 表")
            
            # 检查并添加 tenant_id 字段
            cursor.execute("SHOW COLUMNS FROM agents LIKE 'tenant_id'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE agents ADD COLUMN tenant_id INT AFTER status")
                cursor.execute("ALTER TABLE agents ADD INDEX idx_tenant_id (tenant_id)")
                print("数据库迁移：添加 tenant_id 字段到 agents 表")
            
            # 创建项目-Agent关联表（用于权限管理）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_agents (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id INT NOT NULL,
                    agent_id VARCHAR(64) NOT NULL,
                    can_execute BOOLEAN DEFAULT TRUE,
                    can_terminal BOOLEAN DEFAULT TRUE,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    assigned_by INT,
                    status VARCHAR(20) DEFAULT 'active',
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                    FOREIGN KEY (agent_id) REFERENCES agents (id) ON DELETE CASCADE,
                    UNIQUE KEY unique_project_agent (project_id, agent_id),
                    INDEX idx_project_id (project_id),
                    INDEX idx_agent_id (agent_id),
                    INDEX idx_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            
            # 创建执行历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS execution_history (
                    id VARCHAR(64) PRIMARY KEY,
                    script_name VARCHAR(255) NOT NULL,
                    script_content LONGTEXT,
                    script_params TEXT,
                    target_hosts JSON,
                    project_id INT,
                    status VARCHAR(20) DEFAULT 'PENDING',
                    created_at DATETIME,
                    started_at DATETIME,
                    completed_at DATETIME,
                    timeout INT DEFAULT 7200,
                    execution_user VARCHAR(100) DEFAULT 'root',
                    results JSON,
                    error_message TEXT,
                    created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_script_name (script_name),
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at),
                    INDEX idx_execution_user (execution_user),
                    INDEX idx_project_id (project_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 创建Agent系统信息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS agent_system_info (
                    agent_id VARCHAR(64) PRIMARY KEY,
                    hostname VARCHAR(255) NOT NULL,
                    ip_address VARCHAR(45) NOT NULL,
                    last_heartbeat DATETIME,
                    status VARCHAR(20) DEFAULT 'OFFLINE',
                    register_time DATETIME,
                    system_info JSON,
                    network_info JSON,
                    memory_info JSON,
                    disk_info JSON,
                    cpu_info JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (agent_id) REFERENCES agents (id) ON DELETE CASCADE,
                    INDEX idx_hostname (hostname),
                    INDEX idx_ip_address (ip_address),
                    INDEX idx_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            conn.close()
            print("数据库表初始化完成")
        except Exception as e:
            print(f"数据库初始化失败: {e}")
            raise
    
    def save_execution_history(self, task_data: Dict[str, Any]) -> bool:
        """保存执行历史到数据库"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 处理日期时间字段，将空字符串转换为None
            def convert_datetime(value):
                """将空字符串或无效日期转换为None"""
                if not value or value == '':
                    return None
                return value
            
            cursor.execute('''
                INSERT INTO execution_history 
                (id, script_name, script_content, script_params, target_hosts, 
                 project_id, status, created_at, started_at, completed_at, timeout, 
                 execution_user, results, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                script_name = VALUES(script_name),
                script_content = VALUES(script_content),
                script_params = VALUES(script_params),
                target_hosts = VALUES(target_hosts),
                project_id = VALUES(project_id),
                status = VALUES(status),
                started_at = VALUES(started_at),
                completed_at = VALUES(completed_at),
                timeout = VALUES(timeout),
                execution_user = VALUES(execution_user),
                results = VALUES(results),
                error_message = VALUES(error_message)
            ''', (
                task_data.get('id'),
                task_data.get('script_name', '未命名任务'),
                task_data.get('script'),
                task_data.get('script_params', ''),
                json.dumps(task_data.get('target_hosts', [])),
                task_data.get('project_id'),  # 添加 project_id
                task_data.get('status'),
                convert_datetime(task_data.get('created_at')),
                convert_datetime(task_data.get('started_at')),
                convert_datetime(task_data.get('completed_at')),
                task_data.get('timeout', 7200),
                task_data.get('execution_user', 'root'),
                json.dumps(task_data.get('results', {})),
                task_data.get('error_message', '')
            ))
            
            conn.close()
            return True
        except Exception as e:
            print(f"保存执行历史失败: {e}")
            return False
    
    def get_execution_history(self, project_id: int = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取执行历史"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if project_id:
                cursor.execute('''
                    SELECT id, script_name, script_content, script_params, target_hosts,
                           status, created_at, started_at, completed_at, timeout,
                           execution_user, results, error_message, project_id
                    FROM execution_history
                    WHERE project_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                ''', (project_id, limit, offset))
            else:
                cursor.execute('''
                    SELECT id, script_name, script_content, script_params, target_hosts,
                           status, created_at, started_at, completed_at, timeout,
                           execution_user, results, error_message, project_id
                    FROM execution_history
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                ''', (limit, offset))
            
            rows = cursor.fetchall()
            conn.close()
            
            history = []
            for row in rows:
                # 处理JSON字段
                target_hosts = row['target_hosts'] if isinstance(row['target_hosts'], list) else json.loads(row['target_hosts']) if row['target_hosts'] else []
                results = row['results'] if isinstance(row['results'], dict) else json.loads(row['results']) if row['results'] else {}
                
                history.append({
                    'id': row['id'],
                    'script_name': row['script_name'],
                    'script': row['script_content'],  # 保持script字段名一致
                    'script_content': row['script_content'],  # 同时提供script_content别名
                    'script_params': row['script_params'],
                    'target_hosts': target_hosts,
                    'project_id': row.get('project_id'),  # 添加project_id字段
                    'status': row['status'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'started_at': row['started_at'].isoformat() if row['started_at'] else None,
                    'completed_at': row['completed_at'].isoformat() if row['completed_at'] else None,
                    'timeout': row['timeout'],
                    'execution_user': row['execution_user'],
                    'results': results,
                    'error_message': row['error_message']
                })
            
            return history
        except Exception as e:
            print(f"获取执行历史失败: {e}")
            return []
    
    def save_agent_system_info(self, agent_id: str, system_info: Dict[str, Any]) -> bool:
        """保存Agent系统信息"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 从system_info中提取各个部分 - 修复嵌套结构问题
            sys_info = system_info.get('system_info', {})
            
            # 直接提取各个组件
            system_info_json = json.dumps(sys_info.get('system_info', {}))
            network_info_json = json.dumps(sys_info.get('network_info', []))
            memory_info_json = json.dumps(sys_info.get('memory_info', {}))
            disk_info_json = json.dumps(sys_info.get('disk_info', []))
            cpu_info_json = json.dumps(sys_info.get('cpu_info', {}))
            
            cursor.execute('''
                INSERT INTO agent_system_info
                (agent_id, hostname, ip_address, last_heartbeat, status, register_time,
                 system_info, network_info, memory_info, disk_info, cpu_info)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                hostname = VALUES(hostname),
                ip_address = VALUES(ip_address),
                last_heartbeat = VALUES(last_heartbeat),
                status = VALUES(status),
                register_time = VALUES(register_time),
                system_info = VALUES(system_info),
                network_info = VALUES(network_info),
                memory_info = VALUES(memory_info),
                disk_info = VALUES(disk_info),
                cpu_info = VALUES(cpu_info)
            ''', (
                agent_id,
                system_info.get('hostname', ''),
                system_info.get('ip_address', ''),
                system_info.get('last_heartbeat', ''),
                system_info.get('status', 'OFFLINE'),
                system_info.get('register_time', ''),
                system_info_json,
                network_info_json,
                memory_info_json,
                disk_info_json,
                cpu_info_json
            ))
            
            conn.close()
            return True
        except Exception as e:
            print(f"保存Agent系统信息失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_agent_system_info(self, agent_id: str, local_cache=None) -> Optional[Dict[str, Any]]:
        """获取Agent系统信息（优先从缓存读取实时资源）"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 联表查询，同时获取agents表中的external_ip
            cursor.execute('''
                SELECT asi.agent_id, asi.hostname, asi.ip_address, asi.last_heartbeat, asi.status, asi.register_time,
                       asi.system_info, asi.network_info, asi.memory_info, asi.disk_info, asi.cpu_info,
                       a.external_ip
                FROM agent_system_info asi
                LEFT JOIN agents a ON asi.agent_id = a.id
                WHERE asi.agent_id = %s
            ''', (agent_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                # 处理JSON字段
                system_info = row['system_info'] if isinstance(row['system_info'], dict) else json.loads(row['system_info']) if row['system_info'] else {}
                network_info = row['network_info'] if isinstance(row['network_info'], dict) else json.loads(row['network_info']) if row['network_info'] else {}
                memory_info = row['memory_info'] if isinstance(row['memory_info'], dict) else json.loads(row['memory_info']) if row['memory_info'] else {}
                disk_info = row['disk_info'] if isinstance(row['disk_info'], dict) else json.loads(row['disk_info']) if row['disk_info'] else {}
                cpu_info = row['cpu_info'] if isinstance(row['cpu_info'], dict) else json.loads(row['cpu_info']) if row['cpu_info'] else {}
                
                # 如果有本地缓存，优先使用缓存中的实时资源信息
                if local_cache:
                    cache_key = f"agent_resource:{agent_id}"
                    cached_resource = local_cache.get(cache_key)
                    if cached_resource:
                        # 用缓存中的实时数据更新
                        system_info['cpu_usage'] = cached_resource.get('cpu_usage', system_info.get('cpu_usage', 0))
                        system_info['memory_usage'] = cached_resource.get('memory_usage', system_info.get('memory_usage', 0))
                        cpu_info['cpu_percent'] = cached_resource.get('cpu_usage', cpu_info.get('cpu_percent', 0))
                        memory_info['percent'] = cached_resource.get('memory_usage', memory_info.get('percent', 0))
                        memory_info['total'] = cached_resource.get('memory_total', memory_info.get('total', 0))
                        memory_info['used'] = cached_resource.get('memory_used', memory_info.get('used', 0))
                        memory_info['available'] = cached_resource.get('memory_available', memory_info.get('available', 0))
                        # 更新磁盘信息
                        if 'disk_info' in cached_resource and cached_resource['disk_info']:
                            disk_info = cached_resource['disk_info']
                
                return {
                    'agent_id': row['agent_id'],
                    'hostname': row['hostname'],
                    'ip_address': row['ip_address'],
                    'external_ip': row.get('external_ip', ''),  # 添加外网IP
                    'last_heartbeat': row['last_heartbeat'].isoformat() if row['last_heartbeat'] else None,
                    'status': row['status'],
                    'register_time': row['register_time'].isoformat() if row['register_time'] else None,
                    'system_info': system_info,
                    'network_info': network_info,
                    'memory_info': memory_info,
                    'disk_info': disk_info,
                    'cpu_info': cpu_info
                }
            
            return None
        except Exception as e:
            print(f"获取Agent系统信息失败: {e}")
            return None
    
    def update_agent_resource_info(self, agent_id: str, resource_info: Dict[str, Any]) -> bool:
        """更新Agent实时资源信息（CPU、内存、磁盘使用率等）- 优化版"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 使用JSON_SET直接更新JSON字段，避免先读取再写入
            # 构建更新语句
            update_parts = []
            params = []
            
            if 'cpu_usage' in resource_info:
                update_parts.append("""
                    system_info = JSON_SET(system_info, '$.cpu_usage', %s),
                    cpu_info = JSON_SET(cpu_info, '$.cpu_percent', %s)
                """)
                params.extend([resource_info['cpu_usage'], resource_info['cpu_usage']])
            
            if 'memory_usage' in resource_info:
                if not update_parts:
                    update_parts.append("")
                update_parts.append("""
                    system_info = JSON_SET(system_info, '$.memory_usage', %s),
                    memory_info = JSON_SET(
                        memory_info,
                        '$.percent', %s,
                        '$.total', %s,
                        '$.used', %s,
                        '$.available', %s
                    )
                """)
                params.extend([
                    resource_info['memory_usage'],
                    resource_info['memory_usage'],
                    resource_info.get('memory_total', 0),
                    resource_info.get('memory_used', 0),
                    resource_info.get('memory_available', 0)
                ])
            
            if 'disk_info' in resource_info and resource_info['disk_info']:
                if not update_parts:
                    update_parts.append("")
                update_parts.append("disk_info = %s")
                params.append(json.dumps(resource_info['disk_info']))
            
            if 'last_heartbeat' in resource_info:
                if not update_parts:
                    update_parts.append("")
                update_parts.append("last_heartbeat = %s")
                params.append(resource_info['last_heartbeat'])
            
            if not update_parts:
                conn.close()
                return True
            
            params.append(agent_id)
            
            # 执行单条UPDATE语句，无需先SELECT
            sql = f"""
                UPDATE agent_system_info
                SET {', '.join(update_parts)}
                WHERE agent_id = %s
            """
            
            cursor.execute(sql, tuple(params))
            affected_rows = cursor.rowcount
            
            conn.close()
            return affected_rows > 0
            
        except Exception as e:
            print(f"更新Agent资源信息失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_agent(self, agent_data: Dict[str, Any]) -> bool:
        """保存Agent基本信息"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO agents
                (id, hostname, ip_address, external_ip, os_type, status, tenant_id, project_id,
                 last_heartbeat, register_time, websocket_info, tags)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                hostname = VALUES(hostname),
                ip_address = VALUES(ip_address),
                external_ip = COALESCE(VALUES(external_ip), external_ip),
                os_type = VALUES(os_type),
                status = VALUES(status),
                tenant_id = COALESCE(VALUES(tenant_id), tenant_id),
                project_id = COALESCE(VALUES(project_id), project_id),
                last_heartbeat = VALUES(last_heartbeat),
                websocket_info = VALUES(websocket_info),
                tags = COALESCE(VALUES(tags), tags)
            ''', (
                agent_data.get('id'),
                agent_data.get('hostname', ''),
                agent_data.get('ip_address', ''),
                agent_data.get('external_ip', ''),
                agent_data.get('os_type', 'unknown'),
                agent_data.get('status', 'OFFLINE'),
                agent_data.get('tenant_id'),
                agent_data.get('project_id'),
                agent_data.get('last_heartbeat', ''),
                agent_data.get('register_time', ''),
                json.dumps(agent_data.get('websocket_info', {})),
                json.dumps(agent_data.get('tags', []))
            ))
            
            conn.close()
            return True
        except Exception as e:
            print(f"保存Agent信息失败: {e}")
            return False
    
    def get_all_agents(self, tenant_id: int = None, project_id: int = None) -> List[Dict[str, Any]]:
        """获取Agent信息（支持租户和项目过滤，严格隔离）"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            sql = '''
                SELECT id, hostname, ip_address, external_ip, os_type, status,
                       tenant_id, project_id, last_heartbeat, register_time, websocket_info, tags
                FROM agents
                WHERE 1=1
            '''
            params = []
            
            if tenant_id is not None:
                sql += ' AND tenant_id = %s'
                params.append(tenant_id)
            
            if project_id is not None:
                # 严格隔离：只显示明确分配给该项目的Agent
                sql += ' AND project_id = %s'
                params.append(project_id)
            
            sql += ' ORDER BY register_time DESC'
            
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            conn.close()
            
            agents = []
            for row in rows:
                # 处理JSON字段
                websocket_info = row['websocket_info'] if isinstance(row['websocket_info'], dict) else json.loads(row['websocket_info']) if row['websocket_info'] else {}
                tags = row.get('tags')
                if tags:
                    tags = tags if isinstance(tags, list) else json.loads(tags)
                else:
                    tags = []
                
                agents.append({
                    'id': row['id'],
                    'hostname': row['hostname'],
                    'ip_address': row['ip_address'],
                    'external_ip': row.get('external_ip', ''),
                    'os_type': row.get('os_type', 'unknown'),
                    'status': row['status'],
                    'tenant_id': row.get('tenant_id'),
                    'project_id': row.get('project_id'),
                    'last_heartbeat': row['last_heartbeat'].isoformat() if row['last_heartbeat'] else None,
                    'register_time': row['register_time'].isoformat() if row['register_time'] else None,
                    'websocket_info': websocket_info,
                    'tags': tags
                })
            
            return agents
        except Exception as e:
            print(f"获取Agent列表失败: {e}")
            return []
    
    def assign_agent_to_project(self, project_id: int, agent_id: str,
                                can_execute: bool = True, can_terminal: bool = True,
                                assigned_by: int = None) -> bool:
        """将Agent分配给项目"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO project_agents (project_id, agent_id, can_execute, can_terminal, assigned_by)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                can_execute = VALUES(can_execute),
                can_terminal = VALUES(can_terminal),
                status = 'active'
            ''', (project_id, agent_id, can_execute, can_terminal, assigned_by))
            
            conn.close()
            return True
        except Exception as e:
            print(f"分配Agent到项目失败: {e}")
            return False
    
    def remove_agent_from_project(self, project_id: int, agent_id: str) -> bool:
        """从项目中移除Agent"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE project_agents
                SET status = 'inactive'
                WHERE project_id = %s AND agent_id = %s
            ''', (project_id, agent_id))
            
            conn.close()
            return True
        except Exception as e:
            print(f"从项目移除Agent失败: {e}")
            return False
    
    def get_project_agents(self, project_id: int) -> List[Dict[str, Any]]:
        """获取项目的Agent列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT pa.id, pa.agent_id, pa.can_execute, pa.can_terminal, pa.assigned_at,
                       a.hostname, a.ip_address, a.status, a.os_type, a.tags
                FROM project_agents pa
                JOIN agents a ON pa.agent_id = a.id
                WHERE pa.project_id = %s AND pa.status = 'active'
                ORDER BY pa.assigned_at DESC
            ''', (project_id,))
            
            agents = cursor.fetchall()
            conn.close()
            
            result = []
            for agent in agents:
                tags = agent.get('tags')
                if tags:
                    tags = tags if isinstance(tags, list) else json.loads(tags)
                else:
                    tags = []
                
                result.append({
                    'id': agent['id'],
                    'agent_id': agent['agent_id'],
                    'hostname': agent['hostname'],
                    'ip_address': agent['ip_address'],
                    'status': agent['status'],
                    'os_type': agent['os_type'],
                    'can_execute': bool(agent['can_execute']),
                    'can_terminal': bool(agent['can_terminal']),
                    'assigned_at': agent['assigned_at'].isoformat() if agent['assigned_at'] else None,
                    'tags': tags
                })
            
            return result
        except Exception as e:
            print(f"获取项目Agent列表失败: {e}")
            return []
    
    def check_agent_project_permission(self, agent_id: str, project_id: int, 
                                      permission_type: str = 'execute') -> bool:
        """检查Agent在项目中的权限"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT can_execute, can_terminal
                FROM project_agents
                WHERE project_id = %s AND agent_id = %s AND status = 'active'
            ''', (project_id, agent_id))
            
            perm = cursor.fetchone()
            conn.close()
            
            if not perm:
                return False
            
            if permission_type == 'execute':
                return bool(perm['can_execute'])
            elif permission_type == 'terminal':
                return bool(perm['can_terminal'])
            
            return False
        except Exception as e:
            print(f"检查Agent权限失败: {e}")
            return False
    
    def update_agent_tenant(self, agent_id: str, tenant_id: int) -> bool:
        """更新Agent的租户"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE agents
                SET tenant_id = %s
                WHERE id = %s
            ''', (tenant_id, agent_id))
            
            conn.close()
            return True
        except Exception as e:
            print(f"更新Agent租户失败: {e}")
            return False
    
    def update_agent_project(self, agent_id: str, project_id: int) -> bool:
        """更新Agent的默认项目"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE agents
                SET project_id = %s
                WHERE id = %s
            ''', (project_id, agent_id))
            
            conn.close()
            return True
        except Exception as e:
            print(f"更新Agent项目失败: {e}")
            return False
    
    def get_current_time(self) -> str:
        """获取当前时间的ISO格式字符串"""
        return datetime.now().isoformat()

def generate_agent_id(ip_address: str) -> str:
    """根据IP地址生成Agent ID（MD5值）"""
    return hashlib.md5(ip_address.encode('utf-8')).hexdigest()

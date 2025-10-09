"""
简单作业管理系统
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.models import DatabaseManager


class SimpleJobManager:
    """简单作业管理器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.init_tables()
    
    def init_tables(self):
        """初始化数据库表"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # 作业表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS simple_jobs (
                    id VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    target_agent_id VARCHAR(64),
                    env_vars JSON,
                    created_by INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_name (name),
                    INDEX idx_target_agent (target_agent_id),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 作业步骤表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS simple_job_steps (
                    id VARCHAR(64) PRIMARY KEY,
                    job_id VARCHAR(64) NOT NULL,
                    step_order INT NOT NULL,
                    step_name VARCHAR(255) NOT NULL,
                    script_content TEXT NOT NULL,
                    target_agent_id VARCHAR(64),
                    timeout INT DEFAULT 300,
                    FOREIGN KEY (job_id) REFERENCES simple_jobs (id) ON DELETE CASCADE,
                    INDEX idx_job_id (job_id),
                    INDEX idx_step_order (step_order),
                    INDEX idx_target_agent (target_agent_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 作业执行历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS simple_job_executions (
                    id VARCHAR(64) PRIMARY KEY,
                    job_id VARCHAR(64) NOT NULL,
                    status VARCHAR(20) DEFAULT 'PENDING',
                    current_step INT DEFAULT 0,
                    total_steps INT DEFAULT 0,
                    started_at TIMESTAMP NULL,
                    completed_at TIMESTAMP NULL,
                    error_message TEXT,
                    execution_log JSON,
                    FOREIGN KEY (job_id) REFERENCES simple_jobs (id) ON DELETE CASCADE,
                    INDEX idx_job_id (job_id),
                    INDEX idx_status (status),
                    INDEX idx_started_at (started_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 检查并添加target_agent_id字段（用于数据库迁移）
            try:
                cursor.execute("SHOW COLUMNS FROM simple_job_steps LIKE 'target_agent_id'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE simple_job_steps ADD COLUMN target_agent_id VARCHAR(64) AFTER script_content")
                    cursor.execute("ALTER TABLE simple_job_steps ADD INDEX idx_target_agent (target_agent_id)")
                    print("数据库迁移：添加simple_job_steps.target_agent_id字段成功")
            except Exception as e:
                print(f"添加target_agent_id字段失败（可能已存在）: {e}")
            
            conn.close()
            print("简单作业表初始化成功")
            
        except Exception as e:
            print(f"初始化作业表失败: {e}")
            raise
    
    def create_job(self, name: str, description: str, target_agent_id: str, 
                   env_vars: Dict = None, created_by: int = None) -> str:
        """创建作业"""
        try:
            job_id = str(uuid.uuid4())
            
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO simple_jobs (id, name, description, target_agent_id, env_vars, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (job_id, name, description, target_agent_id, json.dumps(env_vars or {}), created_by))
            
            conn.close()
            return job_id
            
        except Exception as e:
            print(f"创建作业失败: {e}")
            return None
    
    def update_job(self, job_id: str, name: str = None, description: str = None, 
                   target_agent_id: str = None, env_vars: Dict = None) -> bool:
        """更新作业"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = %s")
                params.append(name)
            if description is not None:
                updates.append("description = %s")
                params.append(description)
            if target_agent_id is not None:
                updates.append("target_agent_id = %s")
                params.append(target_agent_id)
            if env_vars is not None:
                updates.append("env_vars = %s")
                params.append(json.dumps(env_vars))
            
            if not updates:
                return True
            
            params.append(job_id)
            sql = f"UPDATE simple_jobs SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(sql, params)
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"更新作业失败: {e}")
            return False
    
    def delete_job(self, job_id: str) -> bool:
        """删除作业"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM simple_jobs WHERE id = %s', (job_id,))
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"删除作业失败: {e}")
            return False
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """获取作业详情"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # 获取作业信息
            cursor.execute('''
                SELECT id, name, description, target_agent_id, env_vars, 
                       created_by, created_at, updated_at
                FROM simple_jobs WHERE id = %s
            ''', (job_id,))
            
            job = cursor.fetchone()
            if not job:
                conn.close()
                return None
            
            # 获取步骤列表
            cursor.execute('''
                SELECT id, step_order, step_name, script_content, target_agent_id, timeout
                FROM simple_job_steps 
                WHERE job_id = %s 
                ORDER BY step_order
            ''', (job_id,))
            
            steps = cursor.fetchall()
            
            conn.close()
            
            return {
                'id': job['id'],
                'name': job['name'],
                'description': job['description'],
                'target_agent_id': job['target_agent_id'],
                'env_vars': json.loads(job['env_vars']) if job['env_vars'] else {},
                'created_by': job['created_by'],
                'created_at': job['created_at'].isoformat() if job['created_at'] else None,
                'updated_at': job['updated_at'].isoformat() if job['updated_at'] else None,
                'steps': [
                    {
                        'id': step['id'],
                        'step_order': step['step_order'],
                        'step_name': step['step_name'],
                        'script_content': step['script_content'],
                        'timeout': step['timeout']
                    }
                    for step in steps
                ]
            }
            
        except Exception as e:
            print(f"获取作业失败: {e}")
            return None
    
    def get_all_jobs(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取所有作业"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT j.id, j.name, j.description, j.target_agent_id, j.env_vars,
                       j.created_by, j.created_at, j.updated_at,
                       COUNT(s.id) as step_count
                FROM simple_jobs j
                LEFT JOIN simple_job_steps s ON j.id = s.job_id
                GROUP BY j.id
                ORDER BY j.created_at DESC
                LIMIT %s OFFSET %s
            ''', (limit, offset))
            
            jobs = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'id': job['id'],
                    'name': job['name'],
                    'description': job['description'],
                    'target_agent_id': job['target_agent_id'],
                    'env_vars': json.loads(job['env_vars']) if job['env_vars'] else {},
                    'created_by': job['created_by'],
                    'created_at': job['created_at'].isoformat() if job['created_at'] else None,
                    'updated_at': job['updated_at'].isoformat() if job['updated_at'] else None,
                    'step_count': job['step_count']
                }
                for job in jobs
            ]
            
        except Exception as e:
            print(f"获取作业列表失败: {e}")
            return []
    
    def add_step(self, job_id: str, step_name: str, script_content: str, 
                 step_order: int = None, timeout: int = 300, target_agent_id: str = None) -> str:
        """添加作业步骤"""
        try:
            step_id = str(uuid.uuid4())
            
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # 如果没有指定顺序，自动获取最大顺序+1
            if step_order is None:
                cursor.execute('''
                    SELECT COALESCE(MAX(step_order), 0) + 1 as next_order
                    FROM simple_job_steps WHERE job_id = %s
                ''', (job_id,))
                result = cursor.fetchone()
                step_order = result['next_order']
            
            cursor.execute('''
                INSERT INTO simple_job_steps (id, job_id, step_order, step_name, script_content, target_agent_id, timeout)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (step_id, job_id, step_order, step_name, script_content, target_agent_id, timeout))
            
            conn.close()
            return step_id
            
        except Exception as e:
            print(f"添加作业步骤失败: {e}")
            return None
    
    def update_step(self, step_id: str, step_name: str = None, 
                    script_content: str = None, timeout: int = None) -> bool:
        """更新作业步骤"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if step_name is not None:
                updates.append("step_name = %s")
                params.append(step_name)
            if script_content is not None:
                updates.append("script_content = %s")
                params.append(script_content)
            if timeout is not None:
                updates.append("timeout = %s")
                params.append(timeout)
            
            if not updates:
                return True
            
            params.append(step_id)
            sql = f"UPDATE simple_job_steps SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(sql, params)
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"更新作业步骤失败: {e}")
            return False
    
    def delete_step(self, step_id: str) -> bool:
        """删除作业步骤"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM simple_job_steps WHERE id = %s', (step_id,))
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"删除作业步骤失败: {e}")
            return False
    
    def create_execution(self, job_id: str) -> str:
        """创建作业执行记录"""
        try:
            execution_id = str(uuid.uuid4())
            
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # 获取步骤数量
            cursor.execute('SELECT COUNT(*) as count FROM simple_job_steps WHERE job_id = %s', (job_id,))
            result = cursor.fetchone()
            total_steps = result['count']
            
            cursor.execute('''
                INSERT INTO simple_job_executions 
                (id, job_id, status, current_step, total_steps, execution_log)
                VALUES (%s, %s, 'PENDING', 0, %s, %s)
            ''', (execution_id, job_id, total_steps, json.dumps([])))
            
            conn.close()
            return execution_id
            
        except Exception as e:
            print(f"创建执行记录失败: {e}")
            return None
    
    def update_execution(self, execution_id: str, status: str = None, 
                        current_step: int = None, error_message: str = None,
                        log_entry: str = None) -> bool:
        """更新作业执行状态"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if status is not None:
                updates.append("status = %s")
                params.append(status)
                
                # 如果状态变为RUNNING且started_at为空，则设置开始时间
                if status == 'RUNNING':
                    updates.append("started_at = COALESCE(started_at, CURRENT_TIMESTAMP)")
                # 如果状态变为完成/失败/取消，则设置完成时间
                elif status in ['COMPLETED', 'FAILED', 'CANCELLED']:
                    updates.append("completed_at = CURRENT_TIMESTAMP")
            
            if current_step is not None:
                updates.append("current_step = %s")
                params.append(current_step)
            
            if error_message is not None:
                updates.append("error_message = %s")
                params.append(error_message)
            
            if log_entry is not None:
                # 获取当前日志
                cursor.execute('SELECT execution_log FROM simple_job_executions WHERE id = %s', (execution_id,))
                result = cursor.fetchone()
                current_log = json.loads(result['execution_log']) if result and result['execution_log'] else []
                current_log.append(log_entry)
                updates.append("execution_log = %s")
                params.append(json.dumps(current_log))
            
            if not updates:
                return True
            
            params.append(execution_id)
            sql = f"UPDATE simple_job_executions SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(sql, params)
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"更新执行状态失败: {e}")
            return False
    
    def get_execution(self, execution_id: str) -> Optional[Dict]:
        """获取执行记录"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT e.*, j.name as job_name, j.target_agent_id
                FROM simple_job_executions e
                JOIN simple_jobs j ON e.job_id = j.id
                WHERE e.id = %s
            ''', (execution_id,))
            
            execution = cursor.fetchone()
            conn.close()
            
            if not execution:
                return None
            
            return {
                'id': execution['id'],
                'job_id': execution['job_id'],
                'job_name': execution['job_name'],
                'target_agent_id': execution['target_agent_id'],
                'status': execution['status'],
                'current_step': execution['current_step'],
                'total_steps': execution['total_steps'],
                'started_at': execution['started_at'].isoformat() if execution['started_at'] else None,
                'completed_at': execution['completed_at'].isoformat() if execution['completed_at'] else None,
                'error_message': execution['error_message'],
                'execution_log': json.loads(execution['execution_log']) if execution['execution_log'] else []
            }
            
        except Exception as e:
            print(f"获取执行记录失败: {e}")
            return None
    
    def get_job_executions(self, job_id: str = None, limit: int = 100) -> List[Dict]:
        """获取作业执行历史"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            if job_id:
                cursor.execute('''
                    SELECT e.*, j.name as job_name
                    FROM simple_job_executions e
                    JOIN simple_jobs j ON e.job_id = j.id
                    WHERE e.job_id = %s
                    ORDER BY e.started_at DESC
                    LIMIT %s
                ''', (job_id, limit))
            else:
                cursor.execute('''
                    SELECT e.*, j.name as job_name
                    FROM simple_job_executions e
                    JOIN simple_jobs j ON e.job_id = j.id
                    ORDER BY e.started_at DESC
                    LIMIT %s
                ''', (limit,))
            
            executions = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'id': ex['id'],
                    'job_id': ex['job_id'],
                    'job_name': ex['job_name'],
                    'status': ex['status'],
                    'current_step': ex['current_step'],
                    'total_steps': ex['total_steps'],
                    'started_at': ex['started_at'].isoformat() if ex['started_at'] else None,
                    'completed_at': ex['completed_at'].isoformat() if ex['completed_at'] else None,
                    'error_message': ex['error_message']
                }
                for ex in executions
            ]
            
        except Exception as e:
            print(f"获取执行历史失败: {e}")
            return []

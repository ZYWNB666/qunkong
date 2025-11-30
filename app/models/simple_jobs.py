"""
简单作业管理系统 - 支持多步骤、多主机组、多变量
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
                    project_id INT NOT NULL,
                    created_by INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_name (name),
                    INDEX idx_created_at (created_at),
                    INDEX idx_project_id (project_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 作业主机组表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS simple_job_host_groups (
                    id VARCHAR(64) PRIMARY KEY,
                    job_id VARCHAR(64) NOT NULL,
                    group_name VARCHAR(255) NOT NULL,
                    host_ids JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES simple_jobs (id) ON DELETE CASCADE,
                    INDEX idx_job_id (job_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 作业变量表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS simple_job_variables (
                    id VARCHAR(64) PRIMARY KEY,
                    job_id VARCHAR(64) NOT NULL,
                    var_name VARCHAR(255) NOT NULL,
                    var_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES simple_jobs (id) ON DELETE CASCADE,
                    INDEX idx_job_id (job_id),
                    UNIQUE KEY unique_job_var (job_id, var_name)
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
                    host_group_id VARCHAR(64),
                    timeout INT DEFAULT 300,
                    FOREIGN KEY (job_id) REFERENCES simple_jobs (id) ON DELETE CASCADE,
                    FOREIGN KEY (host_group_id) REFERENCES simple_job_host_groups (id) ON DELETE SET NULL,
                    INDEX idx_job_id (job_id),
                    INDEX idx_step_order (step_order)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 作业执行历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS simple_job_executions (
                    id VARCHAR(64) PRIMARY KEY,
                    job_id VARCHAR(64) NOT NULL,
                    job_name VARCHAR(255),
                    project_id INT NOT NULL,
                    status VARCHAR(20) DEFAULT 'PENDING',
                    current_step INT DEFAULT 0,
                    total_steps INT DEFAULT 0,
                    started_at TIMESTAMP NULL,
                    completed_at TIMESTAMP NULL,
                    error_message TEXT,
                    execution_log JSON,
                    results JSON,
                    FOREIGN KEY (job_id) REFERENCES simple_jobs (id) ON DELETE CASCADE,
                    INDEX idx_job_id (job_id),
                    INDEX idx_status (status),
                    INDEX idx_started_at (started_at),
                    INDEX idx_project_id (project_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            conn.close()
            print("简单作业表初始化成功")
            
        except Exception as e:
            print(f"初始化作业表失败: {e}")
            raise
    
    # ==================== 作业管理 ====================
    
    def create_job(self, name: str, description: str, project_id: int, 
                   created_by: int = None) -> str:
        """创建作业"""
        try:
            job_id = str(uuid.uuid4())
            
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO simple_jobs (id, name, description, project_id, created_by)
                VALUES (%s, %s, %s, %s, %s)
            ''', (job_id, name, description, project_id, created_by))
            
            conn.close()
            return job_id
            
        except Exception as e:
            print(f"创建作业失败: {e}")
            return None
    
    def update_job(self, job_id: str, name: str = None, description: str = None) -> bool:
        """更新作业基本信息"""
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
        """获取作业完整信息"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # 获取作业基本信息
            cursor.execute('''
                SELECT id, name, description, project_id, created_by, created_at, updated_at
                FROM simple_jobs WHERE id = %s
            ''', (job_id,))
            
            job = cursor.fetchone()
            if not job:
                conn.close()
                return None
            
            # 获取主机组列表
            cursor.execute('''
                SELECT id, group_name, host_ids
                FROM simple_job_host_groups 
                WHERE job_id = %s
            ''', (job_id,))
            host_groups = cursor.fetchall()
            
            # 获取变量列表
            cursor.execute('''
                SELECT id, var_name, var_value
                FROM simple_job_variables 
                WHERE job_id = %s
            ''', (job_id,))
            variables = cursor.fetchall()
            
            # 获取步骤列表
            cursor.execute('''
                SELECT id, step_order, step_name, script_content, host_group_id, timeout
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
                'project_id': job['project_id'],
                'created_by': job['created_by'],
                'created_at': job['created_at'].isoformat() if job['created_at'] else None,
                'updated_at': job['updated_at'].isoformat() if job['updated_at'] else None,
                'host_groups': [
                    {
                        'id': hg['id'],
                        'group_name': hg['group_name'],
                        'host_ids': json.loads(hg['host_ids']) if hg['host_ids'] else []
                    }
                    for hg in host_groups
                ],
                'variables': [
                    {
                        'id': var['id'],
                        'var_name': var['var_name'],
                        'var_value': var['var_value']
                    }
                    for var in variables
                ],
                'steps': [
                    {
                        'id': step['id'],
                        'step_order': step['step_order'],
                        'step_name': step['step_name'],
                        'script_content': step['script_content'],
                        'host_group_id': step['host_group_id'],
                        'timeout': step['timeout']
                    }
                    for step in steps
                ]
            }
            
        except Exception as e:
            print(f"获取作业失败: {e}")
            return None
    
    def get_all_jobs(self, project_id: int = None, limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取所有作业列表"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            if project_id:
                cursor.execute('''
                    SELECT j.id, j.name, j.description, j.project_id,
                           j.created_by, j.created_at, j.updated_at,
                           COUNT(DISTINCT s.id) as step_count,
                           COUNT(DISTINCT hg.id) as host_group_count
                    FROM simple_jobs j
                    LEFT JOIN simple_job_steps s ON j.id = s.job_id
                    LEFT JOIN simple_job_host_groups hg ON j.id = hg.job_id
                    WHERE j.project_id = %s
                    GROUP BY j.id
                    ORDER BY j.created_at DESC
                    LIMIT %s OFFSET %s
                ''', (project_id, limit, offset))
            else:
                cursor.execute('''
                    SELECT j.id, j.name, j.description, j.project_id,
                           j.created_by, j.created_at, j.updated_at,
                           COUNT(DISTINCT s.id) as step_count,
                           COUNT(DISTINCT hg.id) as host_group_count
                    FROM simple_jobs j
                    LEFT JOIN simple_job_steps s ON j.id = s.job_id
                    LEFT JOIN simple_job_host_groups hg ON j.id = hg.job_id
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
                    'project_id': job['project_id'],
                    'created_by': job['created_by'],
                    'created_at': job['created_at'].isoformat() if job['created_at'] else None,
                    'updated_at': job['updated_at'].isoformat() if job['updated_at'] else None,
                    'step_count': job['step_count'],
                    'host_group_count': job['host_group_count']
                }
                for job in jobs
            ]
            
        except Exception as e:
            print(f"获取作业列表失败: {e}")
            return []
    
    # ==================== 主机组管理 ====================
    
    def add_host_group(self, job_id: str, group_name: str, host_ids: List[str]) -> str:
        """添加主机组"""
        try:
            group_id = str(uuid.uuid4())
            
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO simple_job_host_groups (id, job_id, group_name, host_ids)
                VALUES (%s, %s, %s, %s)
            ''', (group_id, job_id, group_name, json.dumps(host_ids)))
            
            conn.close()
            return group_id
            
        except Exception as e:
            print(f"添加主机组失败: {e}")
            return None
    
    def update_host_group(self, group_id: str, group_name: str = None, host_ids: List[str] = None) -> bool:
        """更新主机组"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if group_name is not None:
                updates.append("group_name = %s")
                params.append(group_name)
            if host_ids is not None:
                updates.append("host_ids = %s")
                params.append(json.dumps(host_ids))
            
            if not updates:
                return True
            
            params.append(group_id)
            sql = f"UPDATE simple_job_host_groups SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(sql, params)
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"更新主机组失败: {e}")
            return False
    
    def delete_host_group(self, group_id: str) -> bool:
        """删除主机组"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM simple_job_host_groups WHERE id = %s', (group_id,))
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"删除主机组失败: {e}")
            return False
    
    def delete_all_host_groups(self, job_id: str) -> bool:
        """删除作业的所有主机组"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM simple_job_host_groups WHERE job_id = %s', (job_id,))
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"删除所有主机组失败: {e}")
            return False
    
    def get_host_groups(self, job_id: str) -> List[Dict]:
        """获取作业的所有主机组"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, group_name, host_ids, created_at
                FROM simple_job_host_groups 
                WHERE job_id = %s
            ''', (job_id,))
            
            groups = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'id': g['id'],
                    'group_name': g['group_name'],
                    'host_ids': json.loads(g['host_ids']) if g['host_ids'] else [],
                    'created_at': g['created_at'].isoformat() if g['created_at'] else None
                }
                for g in groups
            ]
            
        except Exception as e:
            print(f"获取主机组失败: {e}")
            return []
    
    # ==================== 变量管理 ====================
    
    def add_variable(self, job_id: str, var_name: str, var_value: str) -> str:
        """添加变量"""
        try:
            var_id = str(uuid.uuid4())
            
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO simple_job_variables (id, job_id, var_name, var_value)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE var_value = VALUES(var_value)
            ''', (var_id, job_id, var_name, var_value))
            
            conn.close()
            return var_id
            
        except Exception as e:
            print(f"添加变量失败: {e}")
            return None
    
    def update_variable(self, var_id: str, var_name: str = None, var_value: str = None) -> bool:
        """更新变量"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if var_name is not None:
                updates.append("var_name = %s")
                params.append(var_name)
            if var_value is not None:
                updates.append("var_value = %s")
                params.append(var_value)
            
            if not updates:
                return True
            
            params.append(var_id)
            sql = f"UPDATE simple_job_variables SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(sql, params)
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"更新变量失败: {e}")
            return False
    
    def delete_variable(self, var_id: str) -> bool:
        """删除变量"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM simple_job_variables WHERE id = %s', (var_id,))
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"删除变量失败: {e}")
            return False
    
    def delete_all_variables(self, job_id: str) -> bool:
        """删除作业的所有变量"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM simple_job_variables WHERE job_id = %s', (job_id,))
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"删除所有变量失败: {e}")
            return False
    
    def get_variables(self, job_id: str) -> List[Dict]:
        """获取作业的所有变量"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, var_name, var_value
                FROM simple_job_variables 
                WHERE job_id = %s
            ''', (job_id,))
            
            variables = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'id': v['id'],
                    'var_name': v['var_name'],
                    'var_value': v['var_value']
                }
                for v in variables
            ]
            
        except Exception as e:
            print(f"获取变量失败: {e}")
            return []
    
    # ==================== 步骤管理 ====================
    
    def add_step(self, job_id: str, step_name: str, script_content: str, 
                 host_group_id: str = None, step_order: int = None, timeout: int = 300) -> str:
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
                INSERT INTO simple_job_steps (id, job_id, step_order, step_name, script_content, host_group_id, timeout)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (step_id, job_id, step_order, step_name, script_content, host_group_id, timeout))
            
            conn.close()
            return step_id
            
        except Exception as e:
            print(f"添加作业步骤失败: {e}")
            return None
    
    def update_step(self, step_id: str, step_name: str = None, 
                    script_content: str = None, host_group_id: str = None,
                    step_order: int = None, timeout: int = None) -> bool:
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
            if host_group_id is not None:
                updates.append("host_group_id = %s")
                params.append(host_group_id if host_group_id else None)
            if step_order is not None:
                updates.append("step_order = %s")
                params.append(step_order)
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
    
    def delete_all_steps(self, job_id: str) -> bool:
        """删除作业的所有步骤"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM simple_job_steps WHERE job_id = %s', (job_id,))
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"删除所有步骤失败: {e}")
            return False
    
    def get_steps(self, job_id: str) -> List[Dict]:
        """获取作业的所有步骤"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.id, s.step_order, s.step_name, s.script_content, 
                       s.host_group_id, s.timeout, hg.group_name as host_group_name
                FROM simple_job_steps s
                LEFT JOIN simple_job_host_groups hg ON s.host_group_id = hg.id
                WHERE s.job_id = %s 
                ORDER BY s.step_order
            ''', (job_id,))
            
            steps = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'id': step['id'],
                    'step_order': step['step_order'],
                    'step_name': step['step_name'],
                    'script_content': step['script_content'],
                    'host_group_id': step['host_group_id'],
                    'host_group_name': step['host_group_name'],
                    'timeout': step['timeout']
                }
                for step in steps
            ]
            
        except Exception as e:
            print(f"获取步骤失败: {e}")
            return []
    
    # ==================== 执行管理 ====================
    
    def create_execution(self, job_id: str) -> str:
        """创建作业执行记录"""
        try:
            execution_id = str(uuid.uuid4())
            
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # 获取作业信息
            cursor.execute('SELECT name, project_id FROM simple_jobs WHERE id = %s', (job_id,))
            job_result = cursor.fetchone()
            if not job_result:
                return None
            
            # 获取步骤数量
            cursor.execute('SELECT COUNT(*) as count FROM simple_job_steps WHERE job_id = %s', (job_id,))
            result = cursor.fetchone()
            total_steps = result['count']
            
            cursor.execute('''
                INSERT INTO simple_job_executions 
                (id, job_id, job_name, project_id, status, current_step, total_steps, execution_log, results, started_at)
                VALUES (%s, %s, %s, %s, 'RUNNING', 0, %s, %s, %s, CURRENT_TIMESTAMP)
            ''', (execution_id, job_id, job_result['name'], job_result['project_id'], total_steps, json.dumps([]), json.dumps({})))
            
            conn.commit()
            conn.close()
            return execution_id
            
        except Exception as e:
            print(f"创建执行记录失败: {e}")
            return None
    
    def update_execution(self, execution_id: str, status: str = None, 
                        current_step: int = None, error_message: str = None,
                        log_entry: str = None, results: Dict = None) -> bool:
        """更新作业执行状态"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if status is not None:
                updates.append("status = %s")
                params.append(status)
                
                # 如果状态变为完成/失败/取消，则设置完成时间
                if status in ['COMPLETED', 'FAILED', 'CANCELLED']:
                    updates.append("completed_at = CURRENT_TIMESTAMP")
            
            if current_step is not None:
                updates.append("current_step = %s")
                params.append(current_step)
            
            if error_message is not None:
                updates.append("error_message = %s")
                params.append(error_message)
            
            if log_entry is not None:
                # 获取当前日志并追加
                cursor.execute('SELECT execution_log FROM simple_job_executions WHERE id = %s', (execution_id,))
                result = cursor.fetchone()
                current_log = json.loads(result['execution_log']) if result and result['execution_log'] else []
                current_log.append({
                    'time': datetime.now().isoformat(),
                    'message': log_entry
                })
                updates.append("execution_log = %s")
                params.append(json.dumps(current_log))
            
            if results is not None:
                updates.append("results = %s")
                params.append(json.dumps(results))
            
            if not updates:
                return True
            
            params.append(execution_id)
            sql = f"UPDATE simple_job_executions SET {', '.join(updates)} WHERE id = %s"
            cursor.execute(sql, params)
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"更新执行状态失败: {e}")
            return False
    
    def get_execution(self, execution_id: str) -> Optional[Dict]:
        """获取执行记录详情"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT e.*, j.name as job_name_ref
                FROM simple_job_executions e
                LEFT JOIN simple_jobs j ON e.job_id = j.id
                WHERE e.id = %s
            ''', (execution_id,))
            
            execution = cursor.fetchone()
            conn.close()
            
            if not execution:
                return None
            
            return {
                'id': execution['id'],
                'job_id': execution['job_id'],
                'job_name': execution['job_name'] or execution['job_name_ref'],
                'project_id': execution['project_id'],
                'status': execution['status'],
                'current_step': execution['current_step'],
                'total_steps': execution['total_steps'],
                'started_at': execution['started_at'].isoformat() if execution['started_at'] else None,
                'completed_at': execution['completed_at'].isoformat() if execution['completed_at'] else None,
                'error_message': execution['error_message'],
                'execution_log': json.loads(execution['execution_log']) if execution['execution_log'] else [],
                'results': json.loads(execution['results']) if execution['results'] else {}
            }
            
        except Exception as e:
            print(f"获取执行记录失败: {e}")
            return None
    
    def get_job_executions(self, job_id: str = None, project_id: int = None, limit: int = 100) -> List[Dict]:
        """获取作业执行历史"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            if job_id:
                cursor.execute('''
                    SELECT e.id, e.job_id, e.job_name, e.project_id, e.status, 
                           e.current_step, e.total_steps, e.started_at, e.completed_at, 
                           e.error_message, e.results
                    FROM simple_job_executions e
                    WHERE e.job_id = %s
                    ORDER BY e.started_at DESC
                    LIMIT %s
                ''', (job_id, limit))
            elif project_id:
                cursor.execute('''
                    SELECT e.id, e.job_id, e.job_name, e.project_id, e.status, 
                           e.current_step, e.total_steps, e.started_at, e.completed_at, 
                           e.error_message, e.results
                    FROM simple_job_executions e
                    WHERE e.project_id = %s
                    ORDER BY e.started_at DESC
                    LIMIT %s
                ''', (project_id, limit))
            else:
                cursor.execute('''
                    SELECT e.id, e.job_id, e.job_name, e.project_id, e.status, 
                           e.current_step, e.total_steps, e.started_at, e.completed_at, 
                           e.error_message, e.results
                    FROM simple_job_executions e
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
                    'project_id': ex['project_id'],
                    'status': ex['status'],
                    'current_step': ex['current_step'],
                    'total_steps': ex['total_steps'],
                    'started_at': ex['started_at'].isoformat() if ex['started_at'] else None,
                    'completed_at': ex['completed_at'].isoformat() if ex['completed_at'] else None,
                    'error_message': ex['error_message'],
                    'results': json.loads(ex['results']) if ex['results'] else {}
                }
                for ex in executions
            ]
            
        except Exception as e:
            print(f"获取执行历史失败: {e}")
            return []

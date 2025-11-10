"""
作业管理数据库模型
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.models import DatabaseManager

class JobManager:
    """作业管理器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.init_job_tables()
    
    def init_job_tables(self):
        """初始化作业相关数据库表"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # 创建作业模板表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_templates (
                    id VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    project_id INT NOT NULL,
                    category VARCHAR(50) DEFAULT 'custom',
                    tags JSON,
                    steps JSON NOT NULL,
                    default_params JSON,
                    timeout INT DEFAULT 7200,
                    created_by INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    version INT DEFAULT 1,
                    INDEX idx_name (name),
                    INDEX idx_category (category),
                    INDEX idx_created_by (created_by),
                    INDEX idx_created_at (created_at),
                    INDEX idx_project_id (project_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 创建作业实例表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_instances (
                    id VARCHAR(64) PRIMARY KEY,
                    template_id VARCHAR(64),
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    project_id INT NOT NULL,
                    status VARCHAR(20) DEFAULT 'PENDING',
                    priority INT DEFAULT 5,
                    params JSON,
                    target_hosts JSON,
                    steps_status JSON,
                    current_step INT DEFAULT 0,
                    total_steps INT DEFAULT 0,
                    created_by INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP NULL,
                    completed_at TIMESTAMP NULL,
                    timeout INT DEFAULT 7200,
                    retry_count INT DEFAULT 0,
                    max_retries INT DEFAULT 3,
                    error_message TEXT,
                    execution_log JSON,
                    FOREIGN KEY (template_id) REFERENCES job_templates (id) ON DELETE SET NULL,
                    INDEX idx_template_id (template_id),
                    INDEX idx_status (status),
                    INDEX idx_priority (priority),
                    INDEX idx_created_by (created_by),
                    INDEX idx_created_at (created_at),
                    INDEX idx_project_id (project_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 创建作业步骤执行记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_step_executions (
                    id VARCHAR(64) PRIMARY KEY,
                    job_instance_id VARCHAR(64) NOT NULL,
                    project_id INT NOT NULL,
                    step_index INT NOT NULL,
                    step_name VARCHAR(255) NOT NULL,
                    step_type VARCHAR(50) NOT NULL,
                    status VARCHAR(20) DEFAULT 'PENDING',
                    started_at TIMESTAMP NULL,
                    completed_at TIMESTAMP NULL,
                    execution_time DECIMAL(10,3),
                    task_id VARCHAR(64),
                    results JSON,
                    error_message TEXT,
                    retry_count INT DEFAULT 0,
                    FOREIGN KEY (job_instance_id) REFERENCES job_instances (id) ON DELETE CASCADE,
                    INDEX idx_job_instance_id (job_instance_id),
                    INDEX idx_step_index (step_index),
                    INDEX idx_status (status),
                    INDEX idx_task_id (task_id),
                    INDEX idx_project_id (project_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 创建作业调度表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_schedules (
                    id VARCHAR(64) PRIMARY KEY,
                    template_id VARCHAR(64) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    cron_expression VARCHAR(100) NOT NULL,
                    timezone VARCHAR(50) DEFAULT 'Asia/Shanghai',
                    is_active BOOLEAN DEFAULT TRUE,
                    params JSON,
                    target_hosts JSON,
                    created_by INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    last_run_at TIMESTAMP NULL,
                    next_run_at TIMESTAMP NULL,
                    run_count INT DEFAULT 0,
                    FOREIGN KEY (template_id) REFERENCES job_templates (id) ON DELETE CASCADE,
                    INDEX idx_template_id (template_id),
                    INDEX idx_is_active (is_active),
                    INDEX idx_next_run_at (next_run_at),
                    INDEX idx_created_by (created_by)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            conn.close()
            
            # 注意：默认模板需要属于某个项目，暂不自动创建
            # 用户可以在创建项目后手动创建模板
            print("作业表初始化成功")
            
        except Exception as e:
            print(f"初始化作业表失败: {e}")
            raise
    
    def create_default_templates(self):
        """创建默认作业模板"""
        default_templates = [
            {
                'name': '系统健康检查',
                'description': '检查系统CPU、内存、磁盘使用情况',
                'category': 'monitoring',
                'tags': ['系统监控', '健康检查'],
                'steps': [
                    {
                        'name': '检查CPU使用率',
                        'type': 'script',
                        'script_type': 'shell',
                        'script': 'top -bn1 | grep "Cpu(s)" | awk \'{print $2}\' | awk -F\'%\' \'{print $1}\'',
                        'timeout': 30,
                        'continue_on_error': True
                    },
                    {
                        'name': '检查内存使用率',
                        'type': 'script',
                        'script_type': 'shell',
                        'script': 'free | grep Mem | awk \'{printf("%.2f", $3/$2 * 100.0)}\'',
                        'timeout': 30,
                        'continue_on_error': True
                    },
                    {
                        'name': '检查磁盘使用率',
                        'type': 'script',
                        'script_type': 'shell',
                        'script': 'df -h | grep -vE \'^Filesystem|tmpfs|cdrom\' | awk \'{ print $5 " " $1 }\'',
                        'timeout': 30,
                        'continue_on_error': True
                    }
                ],
                'default_params': {
                    'cpu_threshold': 80,
                    'memory_threshold': 85,
                    'disk_threshold': 90
                }
            },
            {
                'name': '应用部署',
                'description': '标准应用部署流程',
                'category': 'deployment',
                'tags': ['部署', '应用发布'],
                'steps': [
                    {
                        'name': '停止应用服务',
                        'type': 'script',
                        'script_type': 'shell',
                        'script': 'systemctl stop {{app_name}}',
                        'timeout': 60,
                        'continue_on_error': False
                    },
                    {
                        'name': '备份当前版本',
                        'type': 'script',
                        'script_type': 'shell',
                        'script': 'cp -r {{app_path}} {{backup_path}}/{{app_name}}_$(date +%Y%m%d_%H%M%S)',
                        'timeout': 300,
                        'continue_on_error': False
                    },
                    {
                        'name': '部署新版本',
                        'type': 'script',
                        'script_type': 'shell',
                        'script': 'tar -xzf {{package_path}} -C {{app_path}}',
                        'timeout': 300,
                        'continue_on_error': False
                    },
                    {
                        'name': '启动应用服务',
                        'type': 'script',
                        'script_type': 'shell',
                        'script': 'systemctl start {{app_name}}',
                        'timeout': 60,
                        'continue_on_error': False
                    },
                    {
                        'name': '验证服务状态',
                        'type': 'script',
                        'script_type': 'shell',
                        'script': 'systemctl is-active {{app_name}}',
                        'timeout': 30,
                        'continue_on_error': False
                    }
                ],
                'default_params': {
                    'app_name': 'myapp',
                    'app_path': '/opt/myapp',
                    'backup_path': '/opt/backup',
                    'package_path': '/tmp/myapp.tar.gz'
                }
            },
            {
                'name': '日志清理',
                'description': '清理系统和应用日志文件',
                'category': 'maintenance',
                'tags': ['日志清理', '维护'],
                'steps': [
                    {
                        'name': '清理系统日志',
                        'type': 'script',
                        'script_type': 'shell',
                        'script': 'find /var/log -name "*.log" -mtime +{{days}} -delete',
                        'timeout': 300,
                        'continue_on_error': True
                    },
                    {
                        'name': '清理应用日志',
                        'type': 'script',
                        'script_type': 'shell',
                        'script': 'find {{app_log_path}} -name "*.log" -mtime +{{days}} -delete',
                        'timeout': 300,
                        'continue_on_error': True
                    },
                    {
                        'name': '清理临时文件',
                        'type': 'script',
                        'script_type': 'shell',
                        'script': 'find /tmp -type f -mtime +{{days}} -delete',
                        'timeout': 300,
                        'continue_on_error': True
                    }
                ],
                'default_params': {
                    'days': 30,
                    'app_log_path': '/opt/app/logs'
                }
            }
        ]
        
        for template_data in default_templates:
            if not self.get_template_by_name(template_data['name']):
                self.create_template(
                    name=template_data['name'],
                    description=template_data['description'],
                    category=template_data['category'],
                    tags=template_data['tags'],
                    steps=template_data['steps'],
                    default_params=template_data['default_params'],
                    created_by=1  # 系统创建
                )
    
    def create_template(self, name: str, description: str, category: str, tags: List[str], 
                       steps: List[Dict], default_params: Dict = None, created_by: int = None) -> str:
        """创建作业模板"""
        try:
            template_id = str(uuid.uuid4())
            
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO job_templates 
                (id, name, description, category, tags, steps, default_params, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                template_id, name, description, category,
                json.dumps(tags), json.dumps(steps),
                json.dumps(default_params or {}), created_by
            ))
            
            conn.close()
            return template_id
            
        except Exception as e:
            print(f"创建作业模板失败: {e}")
            return None
    
    def get_template_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取作业模板"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, description, category, tags, steps, default_params, 
                       created_by, created_at, updated_at, is_active, version
                FROM job_templates 
                WHERE name = %s AND is_active = TRUE
            ''', (name,))
            
            template = cursor.fetchone()
            conn.close()
            
            if template:
                return {
                    'id': template['id'],
                    'name': template['name'],
                    'description': template['description'],
                    'category': template['category'],
                    'tags': json.loads(template['tags']) if template['tags'] else [],
                    'steps': json.loads(template['steps']) if template['steps'] else [],
                    'default_params': json.loads(template['default_params']) if template['default_params'] else {},
                    'created_by': template['created_by'],
                    'created_at': template['created_at'].isoformat() if template['created_at'] else None,
                    'updated_at': template['updated_at'].isoformat() if template['updated_at'] else None,
                    'is_active': template['is_active'],
                    'version': template['version']
                }
            
            return None
            
        except Exception as e:
            print(f"获取作业模板失败: {e}")
            return None
    
    def get_all_templates(self, category: str = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取所有作业模板"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            if category:
                cursor.execute('''
                    SELECT id, name, description, category, tags, steps, default_params,
                           created_by, created_at, updated_at, is_active, version
                    FROM job_templates 
                    WHERE category = %s AND is_active = TRUE
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                ''', (category, limit, offset))
            else:
                cursor.execute('''
                    SELECT id, name, description, category, tags, steps, default_params,
                           created_by, created_at, updated_at, is_active, version
                    FROM job_templates 
                    WHERE is_active = TRUE
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                ''', (limit, offset))
            
            templates = cursor.fetchall()
            conn.close()
            
            result = []
            for template in templates:
                result.append({
                    'id': template['id'],
                    'name': template['name'],
                    'description': template['description'],
                    'category': template['category'],
                    'tags': json.loads(template['tags']) if template['tags'] else [],
                    'steps': json.loads(template['steps']) if template['steps'] else [],
                    'default_params': json.loads(template['default_params']) if template['default_params'] else {},
                    'created_by': template['created_by'],
                    'created_at': template['created_at'].isoformat() if template['created_at'] else None,
                    'updated_at': template['updated_at'].isoformat() if template['updated_at'] else None,
                    'is_active': template['is_active'],
                    'version': template['version']
                })
            
            return result
            
        except Exception as e:
            print(f"获取作业模板列表失败: {e}")
            return []
    
    def create_job_instance(self, template_id: str, name: str, params: Dict, 
                           target_hosts: List[str], created_by: int = None, 
                           description: str = None, priority: int = 5) -> str:
        """创建作业实例"""
        try:
            # 获取模板信息
            template = self.get_template_by_id(template_id)
            if not template:
                raise ValueError(f"作业模板不存在: {template_id}")
            
            job_id = str(uuid.uuid4())
            steps = template['steps']
            total_steps = len(steps)
            
            # 初始化步骤状态
            steps_status = []
            for i, step in enumerate(steps):
                steps_status.append({
                    'index': i,
                    'name': step['name'],
                    'status': 'PENDING',
                    'started_at': None,
                    'completed_at': None,
                    'execution_time': None,
                    'error_message': None
                })
            
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO job_instances 
                (id, template_id, name, description, params, target_hosts, 
                 steps_status, total_steps, created_by, priority)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                job_id, template_id, name, description,
                json.dumps(params), json.dumps(target_hosts),
                json.dumps(steps_status), total_steps, created_by, priority
            ))
            
            conn.close()
            return job_id
            
        except Exception as e:
            print(f"创建作业实例失败: {e}")
            return None
    
    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取作业模板"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, description, category, tags, steps, default_params,
                       created_by, created_at, updated_at, is_active, version
                FROM job_templates 
                WHERE id = %s AND is_active = TRUE
            ''', (template_id,))
            
            template = cursor.fetchone()
            conn.close()
            
            if template:
                return {
                    'id': template['id'],
                    'name': template['name'],
                    'description': template['description'],
                    'category': template['category'],
                    'tags': json.loads(template['tags']) if template['tags'] else [],
                    'steps': json.loads(template['steps']) if template['steps'] else [],
                    'default_params': json.loads(template['default_params']) if template['default_params'] else {},
                    'created_by': template['created_by'],
                    'created_at': template['created_at'].isoformat() if template['created_at'] else None,
                    'updated_at': template['updated_at'].isoformat() if template['updated_at'] else None,
                    'is_active': template['is_active'],
                    'version': template['version']
                }
            
            return None
            
        except Exception as e:
            print(f"获取作业模板失败: {e}")
            return None
    
    def get_job_instance(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取作业实例"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, template_id, name, description, status, priority, params,
                       target_hosts, steps_status, current_step, total_steps,
                       created_by, created_at, started_at, completed_at, timeout,
                       retry_count, max_retries, error_message, execution_log
                FROM job_instances 
                WHERE id = %s
            ''', (job_id,))
            
            job = cursor.fetchone()
            conn.close()
            
            if job:
                return {
                    'id': job['id'],
                    'template_id': job['template_id'],
                    'name': job['name'],
                    'description': job['description'],
                    'status': job['status'],
                    'priority': job['priority'],
                    'params': json.loads(job['params']) if job['params'] else {},
                    'target_hosts': json.loads(job['target_hosts']) if job['target_hosts'] else [],
                    'steps_status': json.loads(job['steps_status']) if job['steps_status'] else [],
                    'current_step': job['current_step'],
                    'total_steps': job['total_steps'],
                    'created_by': job['created_by'],
                    'created_at': job['created_at'].isoformat() if job['created_at'] else None,
                    'started_at': job['started_at'].isoformat() if job['started_at'] else None,
                    'completed_at': job['completed_at'].isoformat() if job['completed_at'] else None,
                    'timeout': job['timeout'],
                    'retry_count': job['retry_count'],
                    'max_retries': job['max_retries'],
                    'error_message': job['error_message'],
                    'execution_log': json.loads(job['execution_log']) if job['execution_log'] else []
                }
            
            return None
            
        except Exception as e:
            print(f"获取作业实例失败: {e}")
            return None
    
    def get_all_job_instances(self, status: str = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取所有作业实例"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            if status:
                cursor.execute('''
                    SELECT id, template_id, name, description, status, priority, params,
                           target_hosts, steps_status, current_step, total_steps,
                           created_by, created_at, started_at, completed_at, timeout,
                           retry_count, max_retries, error_message
                    FROM job_instances 
                    WHERE status = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                ''', (status, limit, offset))
            else:
                cursor.execute('''
                    SELECT id, template_id, name, description, status, priority, params,
                           target_hosts, steps_status, current_step, total_steps,
                           created_by, created_at, started_at, completed_at, timeout,
                           retry_count, max_retries, error_message
                    FROM job_instances 
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                ''', (limit, offset))
            
            jobs = cursor.fetchall()
            conn.close()
            
            result = []
            for job in jobs:
                result.append({
                    'id': job['id'],
                    'template_id': job['template_id'],
                    'name': job['name'],
                    'description': job['description'],
                    'status': job['status'],
                    'priority': job['priority'],
                    'params': json.loads(job['params']) if job['params'] else {},
                    'target_hosts': json.loads(job['target_hosts']) if job['target_hosts'] else [],
                    'steps_status': json.loads(job['steps_status']) if job['steps_status'] else [],
                    'current_step': job['current_step'],
                    'total_steps': job['total_steps'],
                    'created_by': job['created_by'],
                    'created_at': job['created_at'].isoformat() if job['created_at'] else None,
                    'started_at': job['started_at'].isoformat() if job['started_at'] else None,
                    'completed_at': job['completed_at'].isoformat() if job['completed_at'] else None,
                    'timeout': job['timeout'],
                    'retry_count': job['retry_count'],
                    'max_retries': job['max_retries'],
                    'error_message': job['error_message']
                })
            
            return result
            
        except Exception as e:
            print(f"获取作业实例列表失败: {e}")
            return []
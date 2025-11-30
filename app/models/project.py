# -*- coding: utf-8 -*-
"""
项目管理数据库模型
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.models import DatabaseManager


class ProjectManager:
    """项目管理器"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.init_project_tables()

    def init_project_tables(self):
        """初始化项目相关数据库表"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 创建项目表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_code VARCHAR(50) UNIQUE NOT NULL,
                    project_name VARCHAR(100) NOT NULL,
                    description TEXT,
                    status VARCHAR(20) DEFAULT 'active',
                    created_by INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_project_code (project_code),
                    INDEX idx_status (status),
                    INDEX idx_created_by (created_by),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')

            # 创建项目成员表（用户与项目的多对多关系）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_members (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id INT NOT NULL,
                    user_id INT NOT NULL,
                    role VARCHAR(50) DEFAULT 'readonly',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    invited_by INT,
                    status VARCHAR(20) DEFAULT 'active',
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (invited_by) REFERENCES users (id) ON DELETE SET NULL,
                    UNIQUE KEY unique_project_user (project_id, user_id),
                    INDEX idx_project_id (project_id),
                    INDEX idx_user_id (user_id),
                    INDEX idx_role (role)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')

            conn.close()

        except Exception as e:
            print(f"初始化项目表失败: {e}")
            raise

    def generate_project_code(self) -> str:
        """生成唯一的项目代码"""
        import random
        import string
        from datetime import datetime
        
        while True:
            # 格式: PRJ + 日期 + 4位随机字符
            date_str = datetime.now().strftime('%Y%m%d')
            random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            project_code = f"PRJ{date_str}{random_str}"
            
            # 检查是否已存在
            try:
                conn = self.db._get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM projects WHERE project_code = %s', (project_code,))
                exists = cursor.fetchone()
                conn.close()
                
                if not exists:
                    return project_code
            except Exception as e:
                print(f"生成项目代码失败: {e}")
                return project_code

    def create_project(self, project_name: str,
                      description: str = None, created_by: int = None, 
                      project_code: str = None) -> Optional[Dict[str, Any]]:
        """创建项目，创建者自动成为项目管理员"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 如果没有提供项目代码，自动生成
            if not project_code:
                project_code = self.generate_project_code()

            # 检查项目代码是否已存在
            cursor.execute('SELECT id FROM projects WHERE project_code = %s', (project_code,))
            if cursor.fetchone():
                conn.close()
                return None

            # 创建项目
            cursor.execute('''
                INSERT INTO projects (project_code, project_name, description, created_by)
                VALUES (%s, %s, %s, %s)
            ''', (project_code, project_name, description, created_by))

            project_id = cursor.lastrowid

            # 创建者自动成为项目管理员
            if created_by:
                cursor.execute('''
                    INSERT INTO project_members (project_id, user_id, role, invited_by)
                    VALUES (%s, %s, 'admin', %s)
                ''', (project_id, created_by, created_by))

            conn.close()
            
            # 返回创建的项目信息
            return self.get_project_by_id(project_id)

        except Exception as e:
            print(f"创建项目失败: {e}")
            return None

    def get_project_by_id(self, project_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取项目信息"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, project_code, project_name, description, status,
                       created_by, created_at, updated_at
                FROM projects
                WHERE id = %s
            ''', (project_id,))

            project = cursor.fetchone()
            conn.close()

            if project:
                return {
                    'id': project['id'],
                    'project_code': project['project_code'],
                    'project_name': project['project_name'],
                    'description': project['description'],
                    'status': project['status'],
                    'created_by': project['created_by'],
                    'created_at': project['created_at'].isoformat() if project['created_at'] else None,
                    'updated_at': project['updated_at'].isoformat() if project['updated_at'] else None
                }

            return None

        except Exception as e:
            print(f"获取项目信息失败: {e}")
            return None

    def get_project_by_code(self, project_code: str) -> Optional[Dict[str, Any]]:
        """根据代码获取项目信息"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, project_code, project_name, description, status,
                       created_by, created_at, updated_at
                FROM projects
                WHERE project_code = %s
            ''', (project_code,))

            project = cursor.fetchone()
            conn.close()

            if project:
                return {
                    'id': project['id'],
                    'project_code': project['project_code'],
                    'project_name': project['project_name'],
                    'description': project['description'],
                    'status': project['status'],
                    'created_by': project['created_by'],
                    'created_at': project['created_at'].isoformat() if project['created_at'] else None,
                    'updated_at': project['updated_at'].isoformat() if project['updated_at'] else None
                }

            return None

        except Exception as e:
            print(f"获取项目信息失败: {e}")
            return None

    def get_all_projects(self, status: str = None, user_id: int = None,
                        limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取所有项目"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 如果指定用户ID，只返回该用户参与的项目
            if user_id:
                sql = '''
                    SELECT p.id, p.project_code, p.project_name, p.description, p.status,
                           p.created_by, p.created_at, p.updated_at,
                           pm.role as user_role,
                           COUNT(DISTINCT pm2.user_id) as member_count
                    FROM projects p
                    JOIN project_members pm ON p.id = pm.project_id
                    LEFT JOIN project_members pm2 ON p.id = pm2.project_id AND pm2.status = 'active'
                    WHERE pm.user_id = %s AND pm.status = 'active'
                '''
                params = [user_id]
            else:
                sql = '''
                    SELECT p.id, p.project_code, p.project_name, p.description, p.status,
                           p.created_by, p.created_at, p.updated_at,
                           COUNT(DISTINCT pm.user_id) as member_count
                    FROM projects p
                    LEFT JOIN project_members pm ON p.id = pm.project_id AND pm.status = 'active'
                    WHERE 1=1
                '''
                params = []

            if status:
                sql += ' AND p.status = %s'
                params.append(status)

            sql += ' GROUP BY p.id ORDER BY p.created_at DESC LIMIT %s OFFSET %s'
            params.extend([limit, offset])

            cursor.execute(sql, tuple(params))
            projects = cursor.fetchall()
            conn.close()

            result = []
            for project in projects:
                proj_dict = {
                    'id': project['id'],
                    'project_code': project['project_code'],
                    'project_name': project['project_name'],
                    'description': project['description'],
                    'status': project['status'],
                    'created_by': project['created_by'],
                    'created_at': project['created_at'].isoformat() if project['created_at'] else None,
                    'updated_at': project['updated_at'].isoformat() if project['updated_at'] else None,
                    'member_count': project['member_count']
                }
                if user_id:
                    proj_dict['user_role'] = project.get('user_role')
                result.append(proj_dict)

            return result

        except Exception as e:
            print(f"获取项目列表失败: {e}")
            return []

    def update_project(self, project_id: int, **kwargs) -> bool:
        """更新项目信息"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            update_fields = []
            update_values = []

            allowed_fields = ['project_name', 'description', 'status']

            for field in allowed_fields:
                if field in kwargs:
                    update_fields.append(f"{field} = %s")
                    update_values.append(kwargs[field])

            if not update_fields:
                conn.close()
                return False

            update_values.append(project_id)
            sql = f"UPDATE projects SET {', '.join(update_fields)} WHERE id = %s"

            cursor.execute(sql, tuple(update_values))
            conn.close()
            return True

        except Exception as e:
            print(f"更新项目信息失败: {e}")
            return False

    def delete_project(self, project_id: int) -> bool:
        """删除项目（软删除）"""
        try:
            return self.update_project(project_id, status='inactive')
        except Exception as e:
            print(f"删除项目失败: {e}")
            return False

    def add_project_member(self, project_id: int, user_id: int,
                          role: str = 'readonly', invited_by: int = None) -> bool:
        """添加项目成员"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 检查成员是否已存在
            cursor.execute('''
                SELECT id, status FROM project_members
                WHERE project_id = %s AND user_id = %s
            ''', (project_id, user_id))

            existing = cursor.fetchone()
            if existing:
                if existing['status'] == 'inactive':
                    cursor.execute('''
                        UPDATE project_members
                        SET status = 'active', role = %s, joined_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    ''', (role, existing['id']))
                conn.close()
                return True

            # 添加新成员
            cursor.execute('''
                INSERT INTO project_members (project_id, user_id, role, invited_by)
                VALUES (%s, %s, %s, %s)
            ''', (project_id, user_id, role, invited_by))

            conn.close()
            return True

        except Exception as e:
            print(f"添加项目成员失败: {e}")
            return False

    def remove_project_member(self, project_id: int, user_id: int) -> bool:
        """移除项目成员"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE project_members
                SET status = 'inactive'
                WHERE project_id = %s AND user_id = %s
            ''', (project_id, user_id))

            conn.close()
            return True

        except Exception as e:
            print(f"移除项目成员失败: {e}")
            return False

    def get_project_members(self, project_id: int) -> List[Dict[str, Any]]:
        """获取项目成员列表"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT pm.id, pm.project_id, pm.user_id, pm.role, pm.joined_at, pm.status,
                       u.username, u.email, u.role as user_role, u.is_active
                FROM project_members pm
                JOIN users u ON pm.user_id = u.id
                WHERE pm.project_id = %s AND pm.status = 'active'
                ORDER BY pm.joined_at DESC
            ''', (project_id,))

            members = cursor.fetchall()
            conn.close()

            result = []
            for member in members:
                result.append({
                    'id': member['id'],
                    'project_id': member['project_id'],
                    'user_id': member['user_id'],
                    'role': member['role'],
                    'joined_at': member['joined_at'].isoformat() if member['joined_at'] else None,
                    'status': member['status'],
                    'username': member['username'],
                    'email': member['email'],
                    'user_role': member['user_role'],
                    'is_active': member['is_active']
                })

            return result

        except Exception as e:
            print(f"获取项目成员列表失败: {e}")
            return []

    def get_user_projects(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户所属的项目列表"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT p.id, p.project_code, p.project_name, p.description, p.status,
                       pm.role, pm.joined_at,
                       COUNT(DISTINCT pm2.user_id) as member_count
                FROM projects p
                JOIN project_members pm ON p.id = pm.project_id
                LEFT JOIN project_members pm2 ON p.id = pm2.project_id AND pm2.status = 'active'
                WHERE pm.user_id = %s AND pm.status = 'active' AND p.status = 'active'
                GROUP BY p.id, pm.role, pm.joined_at
                ORDER BY pm.joined_at DESC
            ''', (user_id,))

            projects = cursor.fetchall()
            conn.close()

            result = []
            for project in projects:
                result.append({
                    'id': project['id'],
                    'project_code': project['project_code'],
                    'project_name': project['project_name'],
                    'description': project['description'],
                    'status': project['status'],
                    'role': project['role'],
                    'joined_at': project['joined_at'].isoformat() if project['joined_at'] else None,
                    'member_count': project['member_count']
                })

            return result

        except Exception as e:
            print(f"获取用户项目列表失败: {e}")
            return []

    def update_member_role(self, project_id: int, user_id: int, role: str) -> bool:
        """更新项目成员角色"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE project_members
                SET role = %s
                WHERE project_id = %s AND user_id = %s AND status = 'active'
            ''', (role, project_id, user_id))

            conn.close()
            return True

        except Exception as e:
            print(f"更新成员角色失败: {e}")
            return False

    def check_project_permission(self, user_id: int, project_id: int,
                                 required_role: str = None) -> bool:
        """检查用户在项目中的权限"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 检查用户是否是系统管理员
            cursor.execute('SELECT role FROM users WHERE id = %s', (user_id,))
            user = cursor.fetchone()

            if user and user['role'] in ['admin', 'super_admin']:
                conn.close()
                return True

            # 检查项目成员权限
            cursor.execute('''
                SELECT role FROM project_members
                WHERE project_id = %s AND user_id = %s AND status = 'active'
            ''', (project_id, user_id))

            member = cursor.fetchone()
            conn.close()

            if not member:
                return False

            if required_role is None:
                return True

            # 角色权限层级: admin > readwrite > readonly
            role_hierarchy = {
                'admin': 3,
                'readwrite': 2,
                'readonly': 1
            }

            user_role_level = role_hierarchy.get(member['role'], 0)
            required_role_level = role_hierarchy.get(required_role, 0)

            return user_role_level >= required_role_level

        except Exception as e:
            print(f"检查项目权限失败: {e}")
            return False
    
    # ==================== 功能权限管理 ====================
    
    def grant_permission(self, project_id: int, user_id: int,
                        permission_key: str, granted_by: int) -> bool:
        """授予用户功能权限"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO project_member_permissions
                (project_id, user_id, permission_key, is_allowed, granted_by)
                VALUES (%s, %s, %s, TRUE, %s)
                ON DUPLICATE KEY UPDATE
                is_allowed = TRUE,
                granted_by = %s,
                updated_at = CURRENT_TIMESTAMP
            ''', (project_id, user_id, permission_key, granted_by, granted_by))
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"授予功能权限失败: {e}")
            return False
    
    def revoke_permission(self, project_id: int, user_id: int,
                         permission_key: str) -> bool:
        """撤销用户功能权限"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE project_member_permissions
                SET is_allowed = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE project_id = %s AND user_id = %s AND permission_key = %s
            ''', (project_id, user_id, permission_key))
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"撤销功能权限失败: {e}")
            return False
    
    def check_permission(self, project_id: int, user_id: int,
                        permission_key: str, user_role: str = None) -> bool:
        """检查用户是否拥有某个功能权限"""
        try:
            # 系统admin拥有所有权限
            if user_role in ['admin', 'super_admin']:
                return True
            
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # 检查用户是否是项目成员
            cursor.execute('''
                SELECT role FROM project_members
                WHERE project_id = %s AND user_id = %s AND status = 'active'
            ''', (project_id, user_id))
            
            member = cursor.fetchone()
            if not member:
                conn.close()
                return False
            
            # 项目admin拥有所有权限
            if member['role'] == 'admin':
                conn.close()
                return True
            
            # 检查具体的功能权限
            cursor.execute('''
                SELECT is_allowed FROM project_member_permissions
                WHERE project_id = %s AND user_id = %s AND permission_key = %s
            ''', (project_id, user_id, permission_key))
            
            permission = cursor.fetchone()
            conn.close()
            
            # 如果有明确的权限设置,使用该设置
            if permission:
                return permission['is_allowed']
            
            # 如果没有明确设置,使用默认权限
            return self._get_default_permission(member['role'], permission_key)
            
        except Exception as e:
            print(f"检查功能权限失败: {e}")
            return False
    
    def _get_default_permission(self, role: str, permission_key: str) -> bool:
        """获取角色的默认权限"""
        # readwrite角色的默认权限
        readwrite_permissions = [
            'agent.view', 'agent.execute',
            'job.view', 'job.create', 'job.execute',
            'execution.view'
        ]
        
        # readonly角色的默认权限
        readonly_permissions = [
            'agent.view', 'job.view', 'execution.view'
        ]
        
        if role == 'readwrite':
            return permission_key in readwrite_permissions
        elif role == 'readonly':
            return permission_key in readonly_permissions
        
        return False
    
    def get_user_permissions(self, project_id: int, user_id: int) -> List[str]:
        """获取用户在项目中的所有权限"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # 检查用户角色
            cursor.execute('''
                SELECT u.role, pm.role as project_role
                FROM users u
                LEFT JOIN project_members pm ON u.id = pm.user_id
                WHERE u.id = %s AND (pm.project_id = %s OR u.role IN ('admin', 'super_admin'))
            ''', (user_id, project_id))
            
            user_info = cursor.fetchone()
            if not user_info:
                conn.close()
                return []
            
            # 系统admin或项目admin拥有所有权限
            if user_info['role'] in ['admin', 'super_admin'] or \
               user_info.get('project_role') == 'admin':
                conn.close()
                return ['*']  # 表示所有权限
            
            # 获取明确授予的权限
            cursor.execute('''
                SELECT permission_key FROM project_member_permissions
                WHERE project_id = %s AND user_id = %s AND is_allowed = TRUE
            ''', (project_id, user_id))
            
            explicit_permissions = [row['permission_key'] for row in cursor.fetchall()]
            conn.close()
            
            # 合并默认权限
            if user_info.get('project_role'):
                default_perms = self._get_all_default_permissions(user_info['project_role'])
                all_permissions = list(set(explicit_permissions + default_perms))
                return all_permissions
            
            return explicit_permissions
            
        except Exception as e:
            print(f"获取用户权限列表失败: {e}")
            return []
    
    def _get_all_default_permissions(self, role: str) -> List[str]:
        """获取角色的所有默认权限"""
        readwrite_permissions = [
            'agent.view', 'agent.execute',
            'job.view', 'job.create', 'job.execute',
            'execution.view'
        ]
        
        readonly_permissions = [
            'agent.view', 'job.view', 'execution.view'
        ]
        
        if role == 'readwrite':
            return readwrite_permissions
        elif role == 'readonly':
            return readonly_permissions
        
        return []
    
    def set_user_permissions(self, project_id: int, user_id: int,
                            permissions: List[str], granted_by: int) -> bool:
        """批量设置用户权限"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # 先删除该用户在该项目的所有权限设置
            cursor.execute('''
                DELETE FROM project_member_permissions
                WHERE project_id = %s AND user_id = %s
            ''', (project_id, user_id))
            
            # 批量插入新权限
            if permissions:
                values = [(project_id, user_id, perm, granted_by) for perm in permissions]
                cursor.executemany('''
                    INSERT INTO project_member_permissions
                    (project_id, user_id, permission_key, is_allowed, granted_by)
                    VALUES (%s, %s, %s, TRUE, %s)
                ''', values)
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"批量设置权限失败: {e}")
            return False
    
    def get_all_permission_keys(self) -> List[str]:
        """获取所有可用的功能权限标识"""
        return [
            'agent.view',
            'agent.batch_add',
            'agent.execute',
            'agent.terminal',
            'job.view',
            'job.create',
            'job.edit',
            'job.delete',
            'job.execute',
            'execution.view',
            'execution.stop',
            'project.member_manage'
        ]

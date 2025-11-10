# -*- coding: utf-8 -*-
"""
租户管理数据库模型
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.models import DatabaseManager


class TenantManager:
    """租户管理器"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.init_tenant_tables()

    def init_tenant_tables(self):
        """初始化租户相关数据库表"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 创建租户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tenants (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    tenant_code VARCHAR(50) UNIQUE NOT NULL,
                    tenant_name VARCHAR(100) NOT NULL,
                    description TEXT,
                    status VARCHAR(20) DEFAULT 'active',
                    max_users INT DEFAULT 10,
                    max_agents INT DEFAULT 50,
                    max_concurrent_jobs INT DEFAULT 10,
                    storage_quota_gb INT DEFAULT 100,
                    contact_name VARCHAR(100),
                    contact_email VARCHAR(100),
                    contact_phone VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    created_by INT,
                    INDEX idx_tenant_code (tenant_code),
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')

            # 创建租户成员表（用户与租户的多对多关系）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tenant_members (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    tenant_id INT NOT NULL,
                    user_id INT NOT NULL,
                    role VARCHAR(50) DEFAULT 'tenant_member',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    invited_by INT,
                    status VARCHAR(20) DEFAULT 'active',
                    FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (invited_by) REFERENCES users (id) ON DELETE SET NULL,
                    UNIQUE KEY unique_tenant_user (tenant_id, user_id),
                    INDEX idx_tenant_id (tenant_id),
                    INDEX idx_user_id (user_id),
                    INDEX idx_role (role)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')

            # 创建租户资源使用统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tenant_usage_stats (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    tenant_id INT NOT NULL,
                    stat_date DATE NOT NULL,
                    active_users INT DEFAULT 0,
                    active_agents INT DEFAULT 0,
                    total_jobs INT DEFAULT 0,
                    successful_jobs INT DEFAULT 0,
                    failed_jobs INT DEFAULT 0,
                    storage_used_gb DECIMAL(10,2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
                    UNIQUE KEY unique_tenant_date (tenant_id, stat_date),
                    INDEX idx_tenant_id (tenant_id),
                    INDEX idx_stat_date (stat_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')

            # 检查users表是否存在default_tenant_id字段
            cursor.execute("SHOW COLUMNS FROM users LIKE 'default_tenant_id'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN default_tenant_id INT DEFAULT NULL AFTER role")
                cursor.execute("ALTER TABLE users ADD INDEX idx_default_tenant_id (default_tenant_id)")
                print("数据库迁移：添加default_tenant_id字段到users表")

            conn.close()

            # 创建默认租户
            self.create_default_tenant()

        except Exception as e:
            print(f"初始化租户表失败: {e}")
            raise

    def create_default_tenant(self):
        """创建默认租户"""
        try:
            # 检查是否已存在默认租户
            if self.get_tenant_by_code('default'):
                return

            # 创建默认租户
            tenant_id = self.create_tenant(
                tenant_code='default',
                tenant_name='默认租户',
                description='系统默认租户，用于未分配租户的用户',
                max_users=100,
                max_agents=100,
                max_concurrent_jobs=50,
                created_by=1
            )

            if tenant_id:
                print(f"默认租户已创建: default (ID: {tenant_id})")

        except Exception as e:
            print(f"创建默认租户失败: {e}")

    def create_tenant(self, tenant_code: str, tenant_name: str, description: str = None,
                     max_users: int = 10, max_agents: int = 50, max_concurrent_jobs: int = 10,
                     storage_quota_gb: int = 100, contact_name: str = None,
                     contact_email: str = None, contact_phone: str = None,
                     created_by: int = None) -> Optional[int]:
        """创建租户"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 检查租户代码是否已存在
            cursor.execute('SELECT id FROM tenants WHERE tenant_code = %s', (tenant_code,))
            if cursor.fetchone():
                conn.close()
                return None

            cursor.execute('''
                INSERT INTO tenants
                (tenant_code, tenant_name, description, max_users, max_agents,
                 max_concurrent_jobs, storage_quota_gb, contact_name, contact_email,
                 contact_phone, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (tenant_code, tenant_name, description, max_users, max_agents,
                  max_concurrent_jobs, storage_quota_gb, contact_name, contact_email,
                  contact_phone, created_by))

            tenant_id = cursor.lastrowid
            conn.close()
            return tenant_id

        except Exception as e:
            print(f"创建租户失败: {e}")
            return None

    def get_tenant_by_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取租户信息"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, tenant_code, tenant_name, description, status,
                       max_users, max_agents, max_concurrent_jobs, storage_quota_gb,
                       contact_name, contact_email, contact_phone,
                       created_at, updated_at, created_by
                FROM tenants
                WHERE id = %s
            ''', (tenant_id,))

            tenant = cursor.fetchone()
            conn.close()

            if tenant:
                return {
                    'id': tenant['id'],
                    'tenant_code': tenant['tenant_code'],
                    'tenant_name': tenant['tenant_name'],
                    'description': tenant['description'],
                    'status': tenant['status'],
                    'max_users': tenant['max_users'],
                    'max_agents': tenant['max_agents'],
                    'max_concurrent_jobs': tenant['max_concurrent_jobs'],
                    'storage_quota_gb': tenant['storage_quota_gb'],
                    'contact_name': tenant['contact_name'],
                    'contact_email': tenant['contact_email'],
                    'contact_phone': tenant['contact_phone'],
                    'created_at': tenant['created_at'].isoformat() if tenant['created_at'] else None,
                    'updated_at': tenant['updated_at'].isoformat() if tenant['updated_at'] else None,
                    'created_by': tenant['created_by']
                }

            return None

        except Exception as e:
            print(f"获取租户信息失败: {e}")
            return None

    def get_tenant_by_code(self, tenant_code: str) -> Optional[Dict[str, Any]]:
        """根据代码获取租户信息"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, tenant_code, tenant_name, description, status,
                       max_users, max_agents, max_concurrent_jobs, storage_quota_gb,
                       contact_name, contact_email, contact_phone,
                       created_at, updated_at, created_by
                FROM tenants
                WHERE tenant_code = %s
            ''', (tenant_code,))

            tenant = cursor.fetchone()
            conn.close()

            if tenant:
                return {
                    'id': tenant['id'],
                    'tenant_code': tenant['tenant_code'],
                    'tenant_name': tenant['tenant_name'],
                    'description': tenant['description'],
                    'status': tenant['status'],
                    'max_users': tenant['max_users'],
                    'max_agents': tenant['max_agents'],
                    'max_concurrent_jobs': tenant['max_concurrent_jobs'],
                    'storage_quota_gb': tenant['storage_quota_gb'],
                    'contact_name': tenant['contact_name'],
                    'contact_email': tenant['contact_email'],
                    'contact_phone': tenant['contact_phone'],
                    'created_at': tenant['created_at'].isoformat() if tenant['created_at'] else None,
                    'updated_at': tenant['updated_at'].isoformat() if tenant['updated_at'] else None,
                    'created_by': tenant['created_by']
                }

            return None

        except Exception as e:
            print(f"获取租户信息失败: {e}")
            return None

    def get_all_tenants(self, status: str = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取所有租户"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            if status:
                cursor.execute('''
                    SELECT t.id, t.tenant_code, t.tenant_name, t.description, t.status,
                           t.max_users, t.max_agents, t.max_concurrent_jobs, t.storage_quota_gb,
                           t.contact_name, t.contact_email, t.contact_phone,
                           t.created_at, t.updated_at,
                           COUNT(DISTINCT tm.user_id) as member_count
                    FROM tenants t
                    LEFT JOIN tenant_members tm ON t.id = tm.tenant_id AND tm.status = 'active'
                    WHERE t.status = %s
                    GROUP BY t.id
                    ORDER BY t.created_at DESC
                    LIMIT %s OFFSET %s
                ''', (status, limit, offset))
            else:
                cursor.execute('''
                    SELECT t.id, t.tenant_code, t.tenant_name, t.description, t.status,
                           t.max_users, t.max_agents, t.max_concurrent_jobs, t.storage_quota_gb,
                           t.contact_name, t.contact_email, t.contact_phone,
                           t.created_at, t.updated_at,
                           COUNT(DISTINCT tm.user_id) as member_count
                    FROM tenants t
                    LEFT JOIN tenant_members tm ON t.id = tm.tenant_id AND tm.status = 'active'
                    GROUP BY t.id
                    ORDER BY t.created_at DESC
                    LIMIT %s OFFSET %s
                ''', (limit, offset))

            tenants = cursor.fetchall()
            conn.close()

            result = []
            for tenant in tenants:
                result.append({
                    'id': tenant['id'],
                    'tenant_code': tenant['tenant_code'],
                    'tenant_name': tenant['tenant_name'],
                    'description': tenant['description'],
                    'status': tenant['status'],
                    'max_users': tenant['max_users'],
                    'max_agents': tenant['max_agents'],
                    'max_concurrent_jobs': tenant['max_concurrent_jobs'],
                    'storage_quota_gb': tenant['storage_quota_gb'],
                    'contact_name': tenant['contact_name'],
                    'contact_email': tenant['contact_email'],
                    'contact_phone': tenant['contact_phone'],
                    'created_at': tenant['created_at'].isoformat() if tenant['created_at'] else None,
                    'updated_at': tenant['updated_at'].isoformat() if tenant['updated_at'] else None,
                    'member_count': tenant['member_count']
                })

            return result

        except Exception as e:
            print(f"获取租户列表失败: {e}")
            return []

    def update_tenant(self, tenant_id: int, **kwargs) -> bool:
        """更新租户信息"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 构建更新SQL
            update_fields = []
            update_values = []

            allowed_fields = ['tenant_name', 'description', 'status', 'max_users',
                            'max_agents', 'max_concurrent_jobs', 'storage_quota_gb',
                            'contact_name', 'contact_email', 'contact_phone']

            for field in allowed_fields:
                if field in kwargs:
                    update_fields.append(f"{field} = %s")
                    update_values.append(kwargs[field])

            if not update_fields:
                conn.close()
                return False

            update_values.append(tenant_id)
            sql = f"UPDATE tenants SET {', '.join(update_fields)} WHERE id = %s"

            cursor.execute(sql, tuple(update_values))
            conn.close()
            return True

        except Exception as e:
            print(f"更新租户信息失败: {e}")
            return False

    def delete_tenant(self, tenant_id: int) -> bool:
        """删除租户（软删除，将状态设置为inactive）"""
        try:
            return self.update_tenant(tenant_id, status='inactive')
        except Exception as e:
            print(f"删除租户失败: {e}")
            return False

    def add_tenant_member(self, tenant_id: int, user_id: int, role: str = 'tenant_member',
                         invited_by: int = None) -> bool:
        """添加租户成员"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 检查成员是否已存在
            cursor.execute('''
                SELECT id, status FROM tenant_members
                WHERE tenant_id = %s AND user_id = %s
            ''', (tenant_id, user_id))

            existing = cursor.fetchone()
            if existing:
                # 如果已存在但状态为inactive，则重新激活
                if existing['status'] == 'inactive':
                    cursor.execute('''
                        UPDATE tenant_members
                        SET status = 'active', role = %s, joined_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    ''', (role, existing['id']))
                conn.close()
                return True

            # 添加新成员
            cursor.execute('''
                INSERT INTO tenant_members (tenant_id, user_id, role, invited_by)
                VALUES (%s, %s, %s, %s)
            ''', (tenant_id, user_id, role, invited_by))

            conn.close()
            return True

        except Exception as e:
            print(f"添加租户成员失败: {e}")
            return False

    def remove_tenant_member(self, tenant_id: int, user_id: int) -> bool:
        """移除租户成员（软删除）"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE tenant_members
                SET status = 'inactive'
                WHERE tenant_id = %s AND user_id = %s
            ''', (tenant_id, user_id))

            conn.close()
            return True

        except Exception as e:
            print(f"移除租户成员失败: {e}")
            return False

    def get_tenant_members(self, tenant_id: int) -> List[Dict[str, Any]]:
        """获取租户成员列表"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT tm.id, tm.tenant_id, tm.user_id, tm.role, tm.joined_at, tm.status,
                       u.username, u.email, u.role as user_role, u.is_active
                FROM tenant_members tm
                JOIN users u ON tm.user_id = u.id
                WHERE tm.tenant_id = %s AND tm.status = 'active'
                ORDER BY tm.joined_at DESC
            ''', (tenant_id,))

            members = cursor.fetchall()
            conn.close()

            result = []
            for member in members:
                result.append({
                    'id': member['id'],
                    'tenant_id': member['tenant_id'],
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
            print(f"获取租户成员列表失败: {e}")
            return []

    def get_user_tenants(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户所属的租户列表"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT t.id, t.tenant_code, t.tenant_name, t.description, t.status,
                       tm.role, tm.joined_at
                FROM tenants t
                JOIN tenant_members tm ON t.id = tm.tenant_id
                WHERE tm.user_id = %s AND tm.status = 'active' AND t.status = 'active'
                ORDER BY tm.joined_at DESC
            ''', (user_id,))

            tenants = cursor.fetchall()
            conn.close()

            result = []
            for tenant in tenants:
                result.append({
                    'id': tenant['id'],
                    'tenant_code': tenant['tenant_code'],
                    'tenant_name': tenant['tenant_name'],
                    'description': tenant['description'],
                    'status': tenant['status'],
                    'role': tenant['role'],
                    'joined_at': tenant['joined_at'].isoformat() if tenant['joined_at'] else None
                })

            return result

        except Exception as e:
            print(f"获取用户租户列表失败: {e}")
            return []

    def update_member_role(self, tenant_id: int, user_id: int, role: str) -> bool:
        """更新租户成员角色"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE tenant_members
                SET role = %s
                WHERE tenant_id = %s AND user_id = %s AND status = 'active'
            ''', (role, tenant_id, user_id))

            conn.close()
            return True

        except Exception as e:
            print(f"更新成员角色失败: {e}")
            return False

    def check_tenant_permission(self, user_id: int, tenant_id: int,
                               required_role: str = None) -> bool:
        """检查用户在租户中的权限"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 检查用户是否是系统管理员
            cursor.execute('SELECT role FROM users WHERE id = %s', (user_id,))
            user = cursor.fetchone()

            if user and user['role'] in ['admin', 'super_admin']:
                conn.close()
                return True

            # 检查租户成员权限
            cursor.execute('''
                SELECT role FROM tenant_members
                WHERE tenant_id = %s AND user_id = %s AND status = 'active'
            ''', (tenant_id, user_id))

            member = cursor.fetchone()
            conn.close()

            if not member:
                return False

            if required_role is None:
                return True

            # 角色权限层级: tenant_admin > tenant_member
            role_hierarchy = {
                'tenant_admin': 2,
                'tenant_member': 1
            }

            user_role_level = role_hierarchy.get(member['role'], 0)
            required_role_level = role_hierarchy.get(required_role, 0)

            return user_role_level >= required_role_level

        except Exception as e:
            print(f"检查租户权限失败: {e}")
            return False

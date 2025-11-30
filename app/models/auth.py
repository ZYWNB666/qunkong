"""
用户认证相关数据库模型
"""
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from app.models import DatabaseManager

class AuthManager:
    """用户认证管理器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.secret_key = "qunkong_secret_key_2024"  # 生产环境应使用环境变量
        self.token_expire_hours = 24
        self.init_auth_tables()
    
    def init_auth_tables(self):
        """初始化认证相关数据库表"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # 创建用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    salt VARCHAR(32) NOT NULL,
                    role VARCHAR(20) DEFAULT 'user',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    last_login TIMESTAMP NULL,
                    login_count INT DEFAULT 0,
                    INDEX idx_username (username),
                    INDEX idx_email (email),
                    INDEX idx_role (role)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 创建用户会话表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    token_hash VARCHAR(255) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    INDEX idx_token_hash (token_hash),
                    INDEX idx_user_id (user_id),
                    INDEX idx_expires_at (expires_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 创建用户权限表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_permissions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    permission VARCHAR(50) NOT NULL,
                    resource VARCHAR(100),
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    granted_by INT,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (granted_by) REFERENCES users (id) ON DELETE SET NULL,
                    UNIQUE KEY unique_user_permission (user_id, permission, resource),
                    INDEX idx_user_id (user_id),
                    INDEX idx_permission (permission)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            conn.close()
            
            # 创建默认管理员账户
            self.create_default_admin()
            
        except Exception as e:
            print(f"初始化认证表失败: {e}")
            raise
    
    def create_default_admin(self):
        """创建默认管理员账户"""
        try:
            # 检查是否已存在管理员账户
            if self.get_user_by_username('admin'):
                return
            
            # 创建默认管理员
            self.register_user(
                username='admin',
                email='admin@qunkong.com',
                password='admin123',
                role='admin'
            )
            print("默认管理员账户已创建: admin/admin123")
            
        except Exception as e:
            print(f"创建默认管理员失败: {e}")
    
    def hash_password(self, password: str, salt: str = None) -> tuple:
        """密码哈希"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # 使用PBKDF2进行密码哈希
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 迭代次数
        ).hex()
        
        return password_hash, salt
    
    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """验证密码"""
        computed_hash, _ = self.hash_password(password, salt)
        return computed_hash == password_hash
    
    def generate_token(self, user_id: int, username: str) -> str:
        """生成JWT令牌"""
        payload = {
            'user_id': user_id,
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=self.token_expire_hours),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def register_user(self, username: str, email: str, password: str, role: str = 'user') -> bool:
        """用户注册"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # 检查用户名和邮箱是否已存在
            cursor.execute('SELECT id FROM users WHERE username = %s OR email = %s', (username, email))
            if cursor.fetchone():
                conn.close()
                return False
            
            # 哈希密码
            password_hash, salt = self.hash_password(password)
            
            # 插入用户记录
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, salt, role)
                VALUES (%s, %s, %s, %s, %s)
            ''', (username, email, password_hash, salt, role))
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"用户注册失败: {e}")
            return False
    
    def login_user(self, username: str, password: str, ip_address: str = None, user_agent: str = None) -> Optional[Dict[str, Any]]:
        """用户登录"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # 查找用户
            cursor.execute('''
                SELECT id, username, email, password_hash, salt, role, is_active
                FROM users 
                WHERE username = %s OR email = %s
            ''', (username, username))
            
            user = cursor.fetchone()
            if not user or not user['is_active']:
                conn.close()
                return None
            
            # 验证密码
            if not self.verify_password(password, user['password_hash'], user['salt']):
                conn.close()
                return None
            
            # 生成令牌
            token = self.generate_token(user['id'], user['username'])
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            # 保存会话
            expires_at = datetime.utcnow() + timedelta(hours=self.token_expire_hours)
            cursor.execute('''
                INSERT INTO user_sessions (user_id, token_hash, expires_at, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s)
            ''', (user['id'], token_hash, expires_at, ip_address, user_agent))
            
            # 更新登录信息
            cursor.execute('''
                UPDATE users 
                SET last_login = CURRENT_TIMESTAMP, login_count = login_count + 1
                WHERE id = %s
            ''', (user['id'],))
            
            conn.close()
            
            return {
                'user_id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role'],
                'token': token
            }
            
        except Exception as e:
            print(f"用户登录失败: {e}")
            return None
    
    def logout_user(self, token: str) -> bool:
        """用户登出"""
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_sessions 
                SET is_active = FALSE 
                WHERE token_hash = %s
            ''', (token_hash,))
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"用户登出失败: {e}")
            return False
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户信息"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, username, email, role, is_active, created_at, last_login, login_count
                FROM users 
                WHERE username = %s
            ''', (username,))
            
            user = cursor.fetchone()
            conn.close()
            
            return user
            
        except Exception as e:
            print(f"获取用户信息失败: {e}")
            return None
    
    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """根据令牌获取用户信息"""
        try:
            # 验证令牌
            payload = self.verify_token(token)
            if not payload:
                return None
            
            # 检查会话是否有效
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.id, s.user_id, u.username, u.email, u.role, u.is_active
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.token_hash = %s AND s.is_active = TRUE AND s.expires_at > NOW()
            ''', (token_hash,))
            
            session = cursor.fetchone()
            conn.close()
            
            if not session or not session['is_active']:
                return None
            
            return {
                'user_id': session['user_id'],
                'username': session['username'],
                'email': session['email'],
                'role': session['role']
            }
            
        except Exception as e:
            print(f"根据令牌获取用户信息失败: {e}")
            return None
    
    def check_permission(self, user_id: int, permission: str, resource: str = None) -> bool:
        """检查用户权限"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # 检查用户角色
            cursor.execute('SELECT role FROM users WHERE id = %s', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                return False
            
            # 管理员拥有所有权限
            if user['role'] == 'admin':
                conn.close()
                return True
            
            # 检查具体权限
            if resource:
                cursor.execute('''
                    SELECT id FROM user_permissions 
                    WHERE user_id = %s AND permission = %s AND (resource = %s OR resource IS NULL)
                ''', (user_id, permission, resource))
            else:
                cursor.execute('''
                    SELECT id FROM user_permissions 
                    WHERE user_id = %s AND permission = %s
                ''', (user_id, permission))
            
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
            
        except Exception as e:
            print(f"检查用户权限失败: {e}")
            return False
    
    def grant_permission(self, user_id: int, permission: str, resource: str = None, granted_by: int = None) -> bool:
        """授予用户权限"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT IGNORE INTO user_permissions (user_id, permission, resource, granted_by)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, permission, resource, granted_by))
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"授予用户权限失败: {e}")
            return False
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                DELETE FROM user_sessions
                WHERE expires_at < NOW() OR is_active = FALSE
            ''')

            deleted_count = cursor.rowcount
            conn.close()

            return deleted_count

        except Exception as e:
            print(f"清理过期会话失败: {e}")
            return 0

    def get_all_users(self, role: str = None, is_active: bool = None,
                     search: str = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取所有用户列表"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 构建查询条件
            where_conditions = []
            where_params = []

            if role:
                where_conditions.append('role = %s')
                where_params.append(role)

            if is_active is not None:
                where_conditions.append('is_active = %s')
                where_params.append(is_active)

            if search:
                where_conditions.append('(username LIKE %s OR email LIKE %s)')
                search_pattern = f'%{search}%'
                where_params.extend([search_pattern, search_pattern])

            where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'
            where_params.extend([limit, offset])

            cursor.execute(f'''
                SELECT id, username, email, role, is_active,
                       created_at, updated_at, last_login, login_count
                FROM users
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            ''', tuple(where_params))

            users = cursor.fetchall()
            conn.close()

            result = []
            for user in users:
                result.append({
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'role': user['role'],
                    'is_active': user['is_active'],
                    'created_at': user['created_at'].isoformat() if user['created_at'] else None,
                    'updated_at': user['updated_at'].isoformat() if user['updated_at'] else None,
                    'last_login': user['last_login'].isoformat() if user['last_login'] else None,
                    'login_count': user['login_count']
                })

            return result

        except Exception as e:
            print(f"获取用户列表失败: {e}")
            return []

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取用户信息"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, username, email, role, is_active,
                       created_at, updated_at, last_login, login_count
                FROM users
                WHERE id = %s
            ''', (user_id,))

            user = cursor.fetchone()
            conn.close()

            if user:
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'role': user['role'],
                    'is_active': user['is_active'],
                    'created_at': user['created_at'].isoformat() if user['created_at'] else None,
                    'updated_at': user['updated_at'].isoformat() if user['updated_at'] else None,
                    'last_login': user['last_login'].isoformat() if user['last_login'] else None,
                    'login_count': user['login_count']
                }

            return None

        except Exception as e:
            print(f"获取用户信息失败: {e}")
            return None

    def update_user(self, user_id: int, **kwargs) -> bool:
        """更新用户信息"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 构建更新SQL
            update_fields = []
            update_values = []

            # 允许更新的字段
            allowed_fields = ['username', 'email', 'role', 'is_active']

            for field in allowed_fields:
                if field in kwargs:
                    # 如果是更新用户名或邮箱，需要检查是否已存在
                    if field in ['username', 'email']:
                        cursor.execute(f'SELECT id FROM users WHERE {field} = %s AND id != %s',
                                      (kwargs[field], user_id))
                        if cursor.fetchone():
                            conn.close()
                            return False

                    update_fields.append(f"{field} = %s")
                    update_values.append(kwargs[field])

            if not update_fields:
                conn.close()
                return False

            update_values.append(user_id)
            sql = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"

            cursor.execute(sql, tuple(update_values))
            conn.close()
            return True

        except Exception as e:
            print(f"更新用户信息失败: {e}")
            return False

    def change_user_password(self, user_id: int, new_password: str) -> bool:
        """修改用户密码"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # 生成新的密码哈希
            password_hash, salt = self.hash_password(new_password)

            cursor.execute('''
                UPDATE users
                SET password_hash = %s, salt = %s
                WHERE id = %s
            ''', (password_hash, salt, user_id))

            conn.close()
            return True

        except Exception as e:
            print(f"修改用户密码失败: {e}")
            return False

    def delete_user(self, user_id: int) -> bool:
        """删除用户（物理删除）"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # 先删除用户的项目成员关系
            cursor.execute('DELETE FROM project_members WHERE user_id = %s', (user_id,))
            
            # 再删除用户
            cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
            conn.commit()
            cursor.close()
            
            return cursor.rowcount > 0
        except Exception as e:
            print(f"删除用户失败: {e}")
            if conn:
                conn.rollback()
            return False

    def count_users(self, role: str = None, is_active: bool = None) -> int:
        """统计用户数量"""
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            where_conditions = []
            where_params = []

            if role:
                where_conditions.append('role = %s')
                where_params.append(role)

            if is_active is not None:
                where_conditions.append('is_active = %s')
                where_params.append(is_active)

            where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'

            cursor.execute(f'''
                SELECT COUNT(*) as count
                FROM users
                WHERE {where_clause}
            ''', tuple(where_params))

            result = cursor.fetchone()
            conn.close()

            return result['count'] if result else 0

        except Exception as e:
            print(f"统计用户数量失败: {e}")
            return 0
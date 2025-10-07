"""
用户认证相关数据库模型
"""
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
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
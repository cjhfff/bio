"""
用户数据仓库：用户CRUD操作
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from backend.storage.db import get_db
from backend.core.security import get_password_hash, verify_password
from backend.core.config import Config

logger = logging.getLogger(__name__)


class UserRepository:
    """用户数据仓库"""
    
    def create_user(self, username: str, password: str, email: Optional[str] = None, role: str = 'user') -> Dict[str, Any]:
        """创建新用户"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 检查用户名是否已存在
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                raise ValueError(f"用户名 {username} 已存在")
            
            # 加密密码
            password_hash = get_password_hash(password)
            
            # 插入新用户
            cursor.execute("""
                INSERT INTO users (username, password_hash, email, role, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (username, password_hash, email, role))
            
            user_id = cursor.lastrowid
            logger.info(f"创建用户成功: username={username}, id={user_id}")
            
            return {
                'id': user_id,
                'username': username,
                'email': email,
                'role': role,
                'is_active': True
            }
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名查询用户"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, password_hash, email, role, is_active, created_at, last_login
                FROM users
                WHERE username = ?
            """, (username,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'id': row[0],
                'username': row[1],
                'password_hash': row[2],
                'email': row[3],
                'role': row[4],
                'is_active': bool(row[5]),
                'created_at': row[6],
                'last_login': row[7]
            }
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据ID查询用户（不包含密码）"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, email, role, is_active, created_at, last_login
                FROM users
                WHERE id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'role': row[3],
                'is_active': bool(row[4]),
                'created_at': row[5],
                'last_login': row[6]
            }
    
    def verify_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """验证用户登录"""
        user = self.get_user_by_username(username)
        if not user:
            return None
        
        if not user['is_active']:
            logger.warning(f"尝试登录已禁用账户: {username}")
            return None
        
        if not verify_password(password, user['password_hash']):
            logger.warning(f"密码验证失败: {username}")
            return None
        
        # 更新最后登录时间
        self.update_last_login(user['id'])
        
        # 返回用户信息（不包含密码）
        return {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'role': user['role'],
            'is_active': user['is_active']
        }
    
    def update_last_login(self, user_id: int):
        """更新最后登录时间"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET last_login = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), user_id))
    
    def update_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """更新用户密码"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        # 获取完整用户信息（包含密码哈希）
        full_user = self.get_user_by_username(user['username'])
        if not full_user:
            return False
        
        # 验证旧密码
        if not verify_password(old_password, full_user['password_hash']):
            return False
        
        # 更新密码
        new_password_hash = get_password_hash(new_password)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET password_hash = ?
                WHERE id = ?
            """, (new_password_hash, user_id))
        
        logger.info(f"用户密码更新成功: user_id={user_id}")
        return True
    
    def init_default_admin(self):
        """初始化默认管理员账户"""
        try:
            # 检查是否已存在管理员
            admin = self.get_user_by_username(Config.ADMIN_USERNAME)
            if admin:
                logger.info(f"默认管理员已存在: {Config.ADMIN_USERNAME}")
                return
            
            # 创建默认管理员
            self.create_user(
                username=Config.ADMIN_USERNAME,
                password=Config.ADMIN_PASSWORD,
                email=None,
                role='admin'
            )
            logger.info(f"默认管理员创建成功: {Config.ADMIN_USERNAME}")
        except Exception as e:
            logger.error(f"初始化默认管理员失败: {e}")
    
    def list_users(self) -> List[Dict[str, Any]]:
        """获取所有用户列表（不包含密码）"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, email, role, is_active, created_at, last_login
                FROM users
                ORDER BY created_at DESC
            """)
            
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'username': row[1],
                    'email': row[2],
                    'role': row[3],
                    'is_active': bool(row[4]),
                    'created_at': row[5],
                    'last_login': row[6]
                }
                for row in rows
            ]
    
    def set_user_active(self, user_id: int, is_active: bool) -> bool:
        """设置用户激活状态"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET is_active = ?
                WHERE id = ?
            """, (1 if is_active else 0, user_id))
            
            if cursor.rowcount > 0:
                logger.info(f"用户状态更新: user_id={user_id}, is_active={is_active}")
                return True
            return False
    
    def set_user_role(self, user_id: int, role: str) -> bool:
        """设置用户角色"""
        if role not in ['admin', 'user']:
            raise ValueError(f"无效的角色: {role}")
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET role = ?
                WHERE id = ?
            """, (role, user_id))
            
            if cursor.rowcount > 0:
                logger.info(f"用户角色更新: user_id={user_id}, role={role}")
                return True
            return False
    
    def reset_password(self, user_id: int, new_password: str) -> bool:
        """重置用户密码（管理员操作）"""
        new_password_hash = get_password_hash(new_password)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET password_hash = ?
                WHERE id = ?
            """, (new_password_hash, user_id))
            
            if cursor.rowcount > 0:
                logger.info(f"管理员重置用户密码: user_id={user_id}")
                return True
            return False


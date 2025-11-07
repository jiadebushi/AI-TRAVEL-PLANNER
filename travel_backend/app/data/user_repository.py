"""用户数据访问层"""
from supabase import Client
from app.models.db_models import User
from app.data.database import get_db
from passlib.context import CryptContext
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    """加密密码"""
    # 使用 bcrypt_sha256 方案，先对密码做SHA256后再进行bcrypt，避免72字节限制
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


class UserRepository:
    """用户数据仓库"""
    
    def __init__(self, db: Client):
        self.db = db
    
    def create_user(self, email: str, password: str, preferences: Optional[str] = None) -> User:
        """创建新用户"""
        user_id = str(uuid.uuid4())
        hashed_pwd = hash_password(password)
        
        data = {
            "user_id": user_id,
            "email": email,
            "hashed_password": hashed_pwd,
            "preferences": preferences,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        result = self.db.table("users").insert(data).execute()
        if result.data:
            user_data = result.data[0]
            user_data.pop("hashed_password", None)
            return User(**user_data)
        raise Exception("创建用户失败")
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """通过邮箱获取用户"""
        result = self.db.table("users").select("*").eq("email", email).execute()
        if result.data and len(result.data) > 0:
            return User(**result.data[0])
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """通过ID获取用户"""
        result = self.db.table("users").select("*").eq("user_id", user_id).execute()
        if result.data and len(result.data) > 0:
            user_data = result.data[0]
            user_data.pop("hashed_password", None)
            return User(**user_data)
        return None
    
    def get_user_with_password(self, email: str) -> Optional[Dict[str, Any]]:
        """获取用户信息（包含密码），用于密码验证"""
        result = self.db.table("users").select("*").eq("email", email).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    
    def verify_user_password(self, email: str, password: str) -> bool:
        """验证用户密码"""
        user_data = self.get_user_with_password(email)
        if not user_data:
            return False
        return verify_password(password, user_data["hashed_password"])
    
    def update_user_preferences(self, user_id: str, preferences: str) -> bool:
        """更新用户偏好"""
        result = self.db.table("users").update({
            "preferences": preferences,
            "updated_at": datetime.now().isoformat()
        }).eq("user_id", user_id).execute()
        return result.data is not None and len(result.data) > 0

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户档案"""
        result = self.db.table("users").select("*").eq("user_id", user_id).execute()
        if not result.data:
            return None
        row = result.data[0]
        profile = {
            "user_id": row.get("user_id"),
            "email": row.get("email"),
            "preferences": row.get("preferences"),
            "create_time": row.get("created_at"),
            "update_time": row.get("updated_at")
        }
        return profile

    def update_profile(self, user_id: str, preferences: str) -> Dict[str, Any]:
        """更新用户偏好（仅更新preferences字段）"""
        update_data = {
            "preferences": preferences,
            "updated_at": datetime.now().isoformat()
        }
        result = self.db.table("users").update(update_data).eq("user_id", user_id).execute()
        if not result.data:
            raise Exception("更新用户偏好失败")
        return self.get_profile(user_id)


def get_user_repository(db: Client = None) -> UserRepository:
    """获取用户仓库实例"""
    if db is None:
        db = get_db()
    return UserRepository(db)


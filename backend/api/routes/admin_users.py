"""
管理员用户管理路由
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import logging
from backend.storage.user_repo import UserRepository
from backend.core.security import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/users", tags=["admin"])


class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None
    role: str = 'user'


class UpdateUserRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    new_password: str


@router.get("")
async def list_users(admin: dict = Depends(require_admin)):
    """获取所有用户列表（仅管理员）"""
    try:
        repo = UserRepository()
        users = repo.list_users()
        return {
            "status": "success",
            "data": users
        }
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_user(user_data: CreateUserRequest, admin: dict = Depends(require_admin)):
    """创建新用户（仅管理员）"""
    try:
        if user_data.role not in ['admin', 'user']:
            raise HTTPException(status_code=400, detail="无效的角色，必须是 'admin' 或 'user'")
        
        repo = UserRepository()
        user = repo.create_user(
            username=user_data.username,
            password=user_data.password,
            email=user_data.email,
            role=user_data.role
        )
        
        return {
            "status": "success",
            "message": "用户创建成功",
            "data": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "role": user['role']
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建用户失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建用户失败")


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    user_data: UpdateUserRequest,
    admin: dict = Depends(require_admin)
):
    """更新用户信息（仅管理员）"""
    try:
        repo = UserRepository()
        
        # 检查用户是否存在
        user = repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 更新角色
        if user_data.role is not None:
            if user_data.role not in ['admin', 'user']:
                raise HTTPException(status_code=400, detail="无效的角色")
            repo.set_user_role(user_id, user_data.role)
        
        # 更新激活状态
        if user_data.is_active is not None:
            repo.set_user_active(user_id, user_data.is_active)
        
        # 返回更新后的用户信息
        updated_user = repo.get_user_by_id(user_id)
        return {
            "status": "success",
            "message": "用户更新成功",
            "data": updated_user
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新用户失败")


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    password_data: ResetPasswordRequest,
    admin: dict = Depends(require_admin)
):
    """重置用户密码（仅管理员）"""
    try:
        repo = UserRepository()
        
        # 检查用户是否存在
        user = repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        success = repo.reset_password(user_id, password_data.new_password)
        if not success:
            raise HTTPException(status_code=500, detail="重置密码失败")
        
        return {
            "status": "success",
            "message": "密码重置成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重置密码失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="重置密码失败")


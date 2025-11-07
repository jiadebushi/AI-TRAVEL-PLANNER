"""API 请求和响应数据模型"""
from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional


class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """注册请求"""
    email: EmailStr
    password: str
    preferences: Optional[str] = None


class UserResponse(BaseModel):
    """用户信息响应"""
    user_id: str
    email: str
    preferences: Optional[str] = None


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"


class TripInput(BaseModel):
    """行程需求输入 (用于 POST /plan/text)"""
    destination: str
    start_date: date
    end_date: date
    budget_cny: float
    people: str  # e.g., "2大1小"
    preferences: Optional[str] = None  # e.g., "喜欢美食和动漫"，可选字段


class TripInputFromText(BaseModel):
    """从已识别的文本创建行程 (用于 POST /plan/voice-text)"""
    text: str


class TripInputVoice(BaseModel):
    """语音行程输入（用于验证请求格式）"""
    audio_base64: Optional[str] = None


class ExpenseInputText(BaseModel):
    """文本开销录入"""
    trip_id: str
    text_input: str


class ExpenseInputVoice(BaseModel):
    """语音开销录入"""
    trip_id: str
    audio_base64: Optional[str] = None


class ExpenseResponse(BaseModel):
    """开销响应"""
    expense_id: str
    trip_id: str
    category: str
    amount: float
    currency: str
    description: str
    timestamp: str


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    trip_id: Optional[str] = None


class UserProfileResponse(BaseModel):
    """用户档案响应"""
    user_id: str
    email: EmailStr
    preferences: Optional[str] = None
    create_time: Optional[str] = None  # created_at
    update_time: Optional[str] = None  # updated_at


class UserProfileUpdateRequest(BaseModel):
    """更新用户资料请求"""
    preferences: str



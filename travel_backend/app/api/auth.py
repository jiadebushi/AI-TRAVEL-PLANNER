"""认证路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from config import settings
from app.models.api_models import LoginRequest, RegisterRequest, UserResponse, TokenResponse, UserProfileResponse, UserProfileUpdateRequest
from app.data.user_repository import get_user_repository, UserRepository
from app.data.database import get_db
from supabase import Client

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_access_token(data: dict, expires_delta: timedelta = None):
    """创建JWT Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: Client = Depends(get_db)) -> dict:
    """获取当前用户（从Token中解析）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user_repo = get_user_repository(db)
    user = user_repo.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    
    return {"user_id": user.user_id, "email": user.email}


@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest, db: Client = Depends(get_db)):
    """用户注册"""
    user_repo = get_user_repository(db)
    
    # 检查用户是否已存在
    existing_user = user_repo.get_user_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )
    
    # 创建新用户
    user = user_repo.create_user(
        email=request.email,
        password=request.password,
        preferences=request.preferences
    )
    
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        preferences=user.preferences
    )


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Client = Depends(get_db)):
    """用户登录"""
    user_repo = get_user_repository(db)
    
    # 验证用户密码
    if not user_repo.verify_user_password(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 获取用户信息
    user = user_repo.get_user_by_email(form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 生成Token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.user_id},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(access_token=access_token, token_type="bearer")


# 用户资料接口
users_router = APIRouter(prefix="/api/v1/users", tags=["用户资料"])


@users_router.get("/me", response_model=UserProfileResponse)
async def get_me(current_user: dict = Depends(get_current_user), db: Client = Depends(get_db)):
    """获取用户档案"""
    repo = get_user_repository(db)
    profile = repo.get_profile(current_user["user_id"])
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return UserProfileResponse(**profile)


@users_router.put("/me", response_model=UserProfileResponse)
async def update_me(payload: UserProfileUpdateRequest, current_user: dict = Depends(get_current_user), db: Client = Depends(get_db)):
    """更新用户偏好"""
    repo = get_user_repository(db)
    updated = repo.update_profile(
        user_id=current_user["user_id"],
        preferences=payload.preferences,
    )
    return UserProfileResponse(**updated)


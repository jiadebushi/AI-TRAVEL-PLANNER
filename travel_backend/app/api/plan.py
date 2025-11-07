"""行程规划路由"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from app.models.api_models import TripInput, TripInputFromText, MessageResponse
from app.services.trip_service import trip_service
from app.services.ai_service import ai_service
from app.api.auth import get_current_user
from supabase import Client
from app.data.database import get_db
from typing import Dict, Any
import base64
import tempfile
import os

router = APIRouter(prefix="/api/v1/plan", tags=["行程规划"])


@router.post("/text", response_model=MessageResponse)
async def create_plan_text(
    trip_input: TripInput,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """文本输入行程需求"""
    try:
        trip_id = await trip_service.generate_full_itinerary(
            user_id=current_user["user_id"],
            trip_input=trip_input
        )
        return MessageResponse(
            message="行程生成成功",
            trip_id=trip_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成行程失败: {str(e)}"
        )


@router.post("/voice", response_model=MessageResponse)
async def create_plan_voice(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """
    语音输入行程需求
    接收 WebM 格式音频文件，自动转换为 WAV (PCM) 格式后调用科大讯飞API
    """
    try:
        # 获取文件扩展名
        file_ext = os.path.splitext(file.filename or "")[1].lower() or ".webm"
        
        # 保存上传的音频文件到临时文件（保持原始格式）
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            trip_id = await trip_service.process_voice_input(
                user_id=current_user["user_id"],
                audio_file_path=tmp_path
            )
            return MessageResponse(
                message="行程生成成功",
                trip_id=trip_id
            )
        finally:
            # 删除临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理语音输入失败: {str(e)}"
        )


@router.post("/voice-text", response_model=MessageResponse)
async def create_plan_from_recognized_text(
    body: TripInputFromText,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """从前端识别的文本创建行程：
    1) LLM 解析文本 -> TripInput
    2) 调用生成行程主流程
    返回与 /plan/text 一致
    """
    try:
        print(f"[/plan/voice-text] 收到前端文本: {body.text}")
        parsed: TripInput = await ai_service.parse_trip_text(body.text)
        trip_id = await trip_service.generate_full_itinerary(
            user_id=current_user["user_id"],
            trip_input=parsed
        )
        return MessageResponse(message="行程生成成功", trip_id=trip_id)
    except HTTPException as he:
        print(f"[/plan/voice-text] HTTPException: {he.detail}")
        raise
    except Exception as e:
        print(f"[/plan/voice-text] error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"从文本生成行程失败: {str(e)}"
        )


@router.get("/{trip_id}", response_model=Dict[str, Any])
async def get_trip_detail(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """获取行程详情"""
    try:
        trip_data = await trip_service.get_trip_details(trip_id)
        
        # 验证行程归属
        if trip_data["trip_header"]["user_id"] != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此行程"
            )
        
        return trip_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取行程详情失败: {str(e)}"
        )


@router.get("/", response_model=Dict[str, Any])
async def get_trip_list(
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """获取用户的行程列表"""
    try:
        trips = await trip_service.get_trip_list(current_user["user_id"])
        return {"trips": trips}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取行程列表失败: {str(e)}"
        )


@router.put("/{trip_id}", response_model=MessageResponse)
async def update_trip(
    trip_id: str,
    updates: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """修改行程"""
    try:
        # 验证行程归属
        trip_data = await trip_service.get_trip_details(trip_id)
        if trip_data["trip_header"]["user_id"] != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改此行程"
            )
        
        success = await trip_service.update_trip(trip_id, updates)
        if success:
            return MessageResponse(message="行程更新成功", trip_id=trip_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="更新行程失败"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新行程失败: {str(e)}"
        )



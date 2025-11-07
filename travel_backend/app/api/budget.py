"""费用预算与管理路由"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from app.models.api_models import ExpenseInputText, ExpenseInputVoice, ExpenseResponse, MessageResponse
from app.services.expense_service import expense_service
from app.api.auth import get_current_user
from app.data.trip_repository import get_trip_repository
from supabase import Client
from app.data.database import get_db
from typing import Dict, Any
import base64
import os
import tempfile

router = APIRouter(prefix="/api/v1/budget", tags=["费用管理"])


@router.get("/{trip_id}", response_model=Dict[str, Any])
async def get_trip_finance(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """获取预算与开销"""
    try:
        # 验证行程归属
        trip_repo = get_trip_repository(db)
        trip = trip_repo.get_trip_by_id(trip_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="行程不存在"
            )
        if trip.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此行程的费用信息"
            )
        
        finance_data = await expense_service.get_trip_finance(trip_id)
        return finance_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取费用信息失败: {str(e)}"
        )


@router.post("/expense/text", response_model=ExpenseResponse)
async def record_expense_text(
    expense_input: ExpenseInputText,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """文本录入开销"""
    try:
        # 验证行程归属
        trip_repo = get_trip_repository(db)
        trip = trip_repo.get_trip_by_id(expense_input.trip_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="行程不存在"
            )
        if trip.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权操作此行程"
            )
        
        expense_data = await expense_service.record_expense_text(expense_input)
        return ExpenseResponse(**expense_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"记录开销失败: {str(e)}"
        )


@router.post("/expense/voice", response_model=ExpenseResponse)
async def record_expense_voice(
    trip_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    """
    语音录入开销
    接收 WebM 格式音频文件，自动转换为 WAV (PCM) 格式后调用科大讯飞API
    """
    try:
        # 验证行程归属
        trip_repo = get_trip_repository(db)
        trip = trip_repo.get_trip_by_id(trip_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="行程不存在"
            )
        if trip.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权操作此行程"
            )
        
        # 获取文件扩展名
        file_ext = os.path.splitext(file.filename or "")[1].lower() or ".webm"
        
        # 保存上传的音频文件到临时文件（保持原始格式）
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # 使用语音服务转换和转写
            from app.services.voice_service import voice_service
            text = await voice_service.transcribe_audio_file(tmp_path)
            
            # 构造文本输入对象
            expense_input = ExpenseInputText(
                trip_id=trip_id,
                text_input=text
            )
            
            expense_data = await expense_service.record_expense_text(expense_input)
            return ExpenseResponse(**expense_data)
        finally:
            # 删除临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"记录开销失败: {str(e)}"
        )



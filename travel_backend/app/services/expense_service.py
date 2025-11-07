"""费用管理服务"""
from app.services.ai_service import ai_service
from app.services.voice_service import voice_service
from app.data.expense_repository import get_expense_repository, ExpenseRepository
from app.models.api_models import ExpenseInputText, ExpenseInputVoice
from typing import Dict, Any, List
import tempfile
import base64
import os


class ExpenseService:
    """费用管理服务"""
    
    def __init__(self):
        self.ai_service = ai_service
        self.voice_service = voice_service
    
    async def record_expense_text(self, expense_input: ExpenseInputText) -> Dict[str, Any]:
        """
        文本录入开销
        1. LLM解析文本中的开销信息
        2. 存储到Expense表
        """
        expense_repo = get_expense_repository()
        
        # LLM解析开销信息
        expense_data = await self.ai_service.parse_expense_text(expense_input.text_input)
        
        # 创建开销记录
        expense = expense_repo.add_expense(
            trip_id=expense_input.trip_id,
            category=expense_data.get("category", "其他"),
            amount=expense_data.get("amount", 0.0),
            currency=expense_data.get("currency", "CNY"),
            description=expense_data.get("description", expense_input.text_input)
        )
        
        return expense.dict()
    
    async def record_expense_voice(self, expense_input: ExpenseInputVoice) -> Dict[str, Any]:
        """
        语音录入开销
        1. 语音转文本（科大讯飞）
        2. LLM解析开销信息
        3. 存储到Expense表
        """
        expense_repo = get_expense_repository()
        
        # 1. 语音转文本（需要先保存base64音频为临时文件）
        if expense_input.audio_base64:
            # 解码base64音频
            audio_data = base64.b64decode(expense_input.audio_base64)
            
            # 保存到临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_file.write(audio_data)
                tmp_path = tmp_file.name
            
            try:
                text = await self.voice_service.transcribe_audio_file(tmp_path)
            finally:
                # 删除临时文件
                os.unlink(tmp_path)
        else:
            raise ValueError("音频数据为空")
        
        # 2. LLM解析开销信息
        expense_data = await self.ai_service.parse_expense_text(text)
        
        # 3. 创建开销记录
        expense = expense_repo.add_expense(
            trip_id=expense_input.trip_id,
            category=expense_data.get("category", "其他"),
            amount=expense_data.get("amount", 0.0),
            currency=expense_data.get("currency", "CNY"),
            description=expense_data.get("description", text)
        )
        
        return expense.dict()
    
    async def get_trip_finance(self, trip_id: str) -> Dict[str, Any]:
        """获取行程的预算和实际开销报告"""
        expense_repo = get_expense_repository()
        
        budget = expense_repo.get_budget_by_trip_id(trip_id)
        expenses = expense_repo.get_expenses_by_trip_id(trip_id)
        
        # 计算实际总开销
        total_expense = sum(exp.amount for exp in expenses)
        
        # 按类别汇总开销
        expense_by_category = {}
        for exp in expenses:
            if exp.category not in expense_by_category:
                expense_by_category[exp.category] = 0.0
            expense_by_category[exp.category] += exp.amount
        
        # 预算对比分析
        variance = {}
        if budget:
            estimated_total = float(budget.estimated_total)
            variance["total"] = {
                "estimated": estimated_total,
                "actual": total_expense,
                "difference": estimated_total - total_expense,  # 正数表示剩余预算，负数表示超支
                "percentage": ((estimated_total - total_expense) / estimated_total * 100) if estimated_total > 0 else 0
            }
            
            # 按类别对比
            budget_categories = budget.categories
            # 处理JSONB格式：可能是list of dict或dict
            if isinstance(budget_categories, dict):
                # 如果是dict格式，转换为list
                budget_categories = list(budget_categories.values()) if budget_categories else []
            if not isinstance(budget_categories, list):
                budget_categories = []
            
            if len(budget_categories) > 0:
                for cat in budget_categories:
                    if isinstance(cat, dict):
                        cat_name = cat.get("name", "")
                        estimated = float(cat.get("estimated_cny", 0.0))
                    elif isinstance(cat, str):
                        # 如果categories是字符串格式，跳过
                        continue
                    else:
                        continue
                    
                    actual = expense_by_category.get(cat_name, 0.0)
                    variance[cat_name] = {
                        "estimated": estimated,
                        "actual": actual,
                        "difference": estimated - actual,  # 正数表示剩余预算，负数表示超支
                        "percentage": ((estimated - actual) / estimated * 100) if estimated > 0 else 0
                    }
        
        return {
            "budget": budget.dict() if budget else None,
            "expenses": [exp.dict() for exp in expenses],
            "summary": {
                "total_expense": total_expense,
                "expense_by_category": expense_by_category,
                "variance": variance
            }
        }


# 全局费用服务实例
expense_service = ExpenseService()


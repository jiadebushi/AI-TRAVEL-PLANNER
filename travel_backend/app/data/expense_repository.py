"""费用数据访问层"""
from supabase import Client
from app.models.db_models import Budget, Expense
from app.data.database import get_db
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime


class ExpenseRepository:
    """费用数据仓库"""
    
    def __init__(self, db: Client):
        self.db = db
    
    def create_budget(self, trip_id: str, user_budget: float, estimated_total: float, categories: Dict[str, Any]) -> Budget:
        """创建预算"""
        budget_id = str(uuid.uuid4())
        data = {
            "budget_id": budget_id,
            "trip_id": trip_id,
            "user_budget": user_budget,
            "estimated_total": estimated_total,
            "categories": categories,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        result = self.db.table("budgets").insert(data).execute()
        if result.data:
            return Budget(**result.data[0])
        raise Exception("创建预算失败")
    
    def get_budget_by_trip_id(self, trip_id: str) -> Optional[Budget]:
        """获取行程预算"""
        result = self.db.table("budgets").select("*").eq("trip_id", trip_id).execute()
        if result.data and len(result.data) > 0:
            return Budget(**result.data[0])
        return None
    
    def add_expense(self, trip_id: str, category: str, amount: float,
                   currency: str, description: str) -> Expense:
        """添加开销记录"""
        expense_id = str(uuid.uuid4())
        data = {
            "expense_id": expense_id,
            "trip_id": trip_id,
            "category": category,
            "amount": amount,
            "currency": currency,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat()
        }
        result = self.db.table("expenses").insert(data).execute()
        if result.data:
            return Expense(**result.data[0])
        raise Exception("添加开销失败")
    
    def get_expenses_by_trip_id(self, trip_id: str) -> List[Expense]:
        """获取行程的所有开销"""
        result = self.db.table("expenses").select("*").eq("trip_id", trip_id).order("timestamp", desc=True).execute()
        if result.data:
            return [Expense(**item) for item in result.data]
        return []
    
    def update_budget(self, trip_id: str, estimated_total: float, categories: Dict[str, Any]) -> bool:
        """更新预算"""
        data = {
            "estimated_total": estimated_total,
            "categories": categories,
            "updated_at": datetime.now().isoformat()
        }
        result = self.db.table("budgets").update(data).eq("trip_id", trip_id).execute()
        return result.data is not None and len(result.data) > 0


def get_expense_repository(db: Client = None) -> ExpenseRepository:
    """获取费用仓库实例"""
    if db is None:
        db = get_db()
    return ExpenseRepository(db)



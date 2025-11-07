// 最近消费记录弹窗组件
// 显示指定行程的所有消费记录

import { useState, useEffect } from 'react'
import { budgetApi } from '../api/budget'
import { Expense } from '../types'
import './ExpenseListModal.css'

interface ExpenseListModalProps {
  tripId: string
  isOpen: boolean
  onClose: () => void
}

function ExpenseListModal({ tripId, isOpen, onClose }: ExpenseListModalProps) {
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen && tripId) {
      loadExpenses()
    }
  }, [isOpen, tripId])

  const loadExpenses = async () => {
    try {
      setLoading(true)
      const data = await budgetApi.getBudgetDetail(tripId)
      setExpenses(data.expenses)
    } catch (err) {
      console.error('加载消费记录失败:', err)
    } finally {
      setLoading(false)
    }
  }

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content expense-list-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>最近消费记录</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="expense-list-container">
          {loading ? (
            <div className="expenses-loading">加载中...</div>
          ) : expenses.length === 0 ? (
            <div className="no-expenses">暂无消费记录</div>
          ) : (
            <div className="expenses-list">
              {expenses.map((expense) => (
                <div key={expense.expense_id} className="expense-item">
                  <div className="expense-item-header">
                    <span className="expense-category">{expense.category}</span>
                    <span className="expense-amount">¥{expense.amount.toLocaleString()}</span>
                  </div>
                  <div className="expense-description">{expense.description}</div>
                  <div className="expense-time">{formatDateTime(expense.timestamp)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ExpenseListModal


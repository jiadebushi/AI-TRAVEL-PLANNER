// 行程主页（行程列表页）
// 对应接口: GET /api/v1/plan/, POST /api/v1/plan/text, POST /api/v1/plan/voice

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { tripsApi } from '../api/trips'
import { Trip } from '../types'
// import CreateTripModal from '../components/CreateTripModal' // 旧版本（后端转接）
// import CreateTripModalXunfei from '../components/CreateTripModalXunfei' // 讯飞标准版（已注释）
import CreateTripModalXunfeiLLM from '../components/CreateTripModalXunfeiLLM' // 讯飞大模型版
import './TripListPage.css'

function TripListPage() {
  const [trips, setTrips] = useState<Trip[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    loadTrips()
  }, [])

  const loadTrips = async () => {
    try {
      setLoading(true)
      setError('')
      const response = await tripsApi.getTripList()
      setTrips(response.trips)
    } catch (err: any) {
      setError(err.response?.data?.detail || '加载行程列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateSuccess = (_tripId: string) => {
    setIsModalOpen(false)
    // 注意：跳转逻辑已在 CreateTripModal 中处理
    // 这里可以保留用于其他用途，比如刷新列表（如果用户取消跳转）
  }

  const getStatusLabel = (status: Trip['status']) => {
    const statusMap = {
      draft: '草稿',
      generated: '已生成',
      active: '进行中',
      completed: '已完成',
    }
    return statusMap[status] || status
  }

  const getStatusClass = (status: Trip['status']) => {
    return `status-badge status-${status}`
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  const formatDateRange = (start: string, end: string) => {
    const startDate = new Date(start)
    const endDate = new Date(end)
    const startStr = startDate.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' })
    const endStr = endDate.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' })
    return `${startStr} - ${endStr}`
  }

  return (
    <div className="trip-list-page">
      <nav className="top-navbar">
        <div className="navbar-content">
          <h1 className="navbar-title">🧭 AI旅行规划师</h1>
          <button
            className="navbar-button"
            onClick={() => navigate('/profile')}
          >
            个人主页
          </button>
        </div>
      </nav>

      <div className="trip-list-container">
        <div className="trip-list-header">
          <h2>我的行程</h2>
          <button
            className="create-trip-button"
            onClick={() => setIsModalOpen(true)}
          >
            + 规划新行程
          </button>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {loading ? (
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>加载中...</p>
          </div>
        ) : trips.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">✈️</div>
            <h3>还没有行程</h3>
            <p>点击上方按钮开始规划您的第一次旅行吧！</p>
          </div>
        ) : (
          <div className="trip-grid">
            {trips.map((trip) => (
              <div
                key={trip.trip_id}
                className="trip-card"
                onClick={() => navigate(`/trips/${trip.trip_id}`)}
              >
                <div className="trip-card-header">
                  <h3 className="trip-name">{trip.trip_name}</h3>
                  <span className={getStatusClass(trip.status)}>
                    {getStatusLabel(trip.status)}
                  </span>
                </div>
                <div className="trip-card-body">
                  <div className="trip-info-item">
                    <span className="info-label">📍 目的地</span>
                    <span className="info-value">{trip.destination}</span>
                  </div>
                  <div className="trip-info-item">
                    <span className="info-label">📅 日期</span>
                    <span className="info-value">
                      {formatDateRange(trip.start_date, trip.end_date)}
                    </span>
                  </div>
                  <div className="trip-info-item">
                    <span className="info-label">🕐 创建时间</span>
                    <span className="info-value">
                      {formatDate(trip.created_at)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <CreateTripModalXunfeiLLM
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleCreateSuccess}
      />
    </div>
  )
}

export default TripListPage


// 行程详情页
// 对应接口: GET /api/v1/plan/{trip_id}, GET /api/v1/budget/{trip_id}, PUT /api/v1/plan/{trip_id}

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { tripsApi } from '../api/trips'
import { budgetApi } from '../api/budget'
import { usersApi } from '../api/users'
import { TripDetailResponse, BudgetDetailResponse, Trip, User } from '../types'
// import ExpenseModal from '../components/ExpenseModal' // 旧版本（文件上传）
import ExpenseModalXunfeiLLM from '../components/ExpenseModalXunfeiLLM' // 讯飞大模型版
import ExpenseListModal from '../components/ExpenseListModal'
import ImagePreviewModal from '../components/ImagePreviewModal'
import './TripDetailPage.css'

function TripDetailPage() {
  const { tripId } = useParams<{ tripId: string }>()
  const navigate = useNavigate()
  const [tripData, setTripData] = useState<TripDetailResponse | null>(null)
  const [budgetData, setBudgetData] = useState<BudgetDetailResponse | null>(null)
  const [, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [isExpenseModalOpen, setIsExpenseModalOpen] = useState(false)
  const [isExpenseListModalOpen, setIsExpenseListModalOpen] = useState(false)
  const [isEditingName, setIsEditingName] = useState(false)
  const [editedName, setEditedName] = useState('')
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null)

  useEffect(() => {
    if (tripId) {
      loadTripDetail()
      loadBudgetDetail()
      loadUserProfile()
    }
  }, [tripId])

  // 如果行程还在生成中，定期检查状态
  useEffect(() => {
    if (!tripData || tripData.trip_header.status !== 'draft') return
    if (tripData.trip_details && tripData.trip_details.length > 0) return // 如果已经有详情了，停止检查

    const checkInterval = setInterval(() => {
      loadTripDetail(true) // 静默刷新，不显示loading
    }, 5000) // 每5秒检查一次

    return () => clearInterval(checkInterval)
  }, [tripData, tripId])

  const loadTripDetail = async (silent = false) => {
    if (!tripId) return
    try {
      if (!silent) {
        setLoading(true)
      }
      setError('')
      const data = await tripsApi.getTripDetail(tripId)
      setTripData(data)
      setEditedName(data.trip_header.trip_name)
    } catch (err: any) {
      // 如果是404错误，可能是行程不存在
      if (err.response?.status === 404) {
        setError('行程不存在或已被删除')
      } else {
        setError(err.response?.data?.detail || '加载行程详情失败')
      }
    } finally {
      if (!silent) {
        setLoading(false)
      }
    }
  }

  const loadBudgetDetail = async () => {
    if (!tripId) return
    try {
      const data = await budgetApi.getBudgetDetail(tripId)
      setBudgetData(data)
    } catch (err: any) {
      // 预算数据加载失败不影响页面显示
      console.error('加载预算详情失败:', err)
    }
  }

  const loadUserProfile = async () => {
    try {
      const userData = await usersApi.getProfile()
      setUser(userData)
    } catch (err: any) {
      // 用户信息加载失败不影响页面显示
      console.error('加载用户信息失败:', err)
    }
  }

  const handleSaveName = async () => {
    if (!tripId || !editedName.trim()) return
    try {
      await tripsApi.updateTrip(tripId, { trip_name: editedName.trim() })
      if (tripData) {
        setTripData({
          ...tripData,
          trip_header: {
            ...tripData.trip_header,
            trip_name: editedName.trim(),
          },
        })
      }
      setIsEditingName(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || '保存失败，请重试')
    }
  }

  const handleExpenseSuccess = () => {
    setIsExpenseModalOpen(false)
    loadBudgetDetail() // 刷新预算数据
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

  const getActivityTypeLabel = (type: string) => {
    const typeMap: Record<string, string> = {
      Meal_Breakfast: '早餐',
      Meal_Lunch: '午餐',
      Meal_Dinner: '晚餐',
      Attraction: '景点',
    }
    return typeMap[type] || type
  }

  // const formatDate = (dateString: string) => {
  //   const date = new Date(dateString)
  //   return date.toLocaleDateString('zh-CN', {
  //     year: 'numeric',
  //     month: 'long',
  //     day: 'numeric',
  //   })
  // }

  const formatDateRange = (start: string, end: string) => {
    const startDate = new Date(start)
    const endDate = new Date(end)
    const startStr = startDate.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' })
    const endStr = endDate.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' })
    return `${startStr} - ${endStr}`
  }

  // 获取用户当前位置
  const getCurrentLocation = (): Promise<{ lat: number; lng: number }> => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('您的浏览器不支持地理定位'))
        return
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          })
        },
        (error) => {
          reject(new Error('获取位置失败：' + error.message))
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0,
        }
      )
    })
  }

  // 跳转到高德地图导航
  const navigateToAmap = async (
    destinationLat: number,
    destinationLng: number,
    destinationName: string
  ) => {
    try {
      // 获取用户当前位置
      const currentLocation = await getCurrentLocation()
      
      // 构建高德地图导航URL
      // 格式：https://uri.amap.com/navigation?from=lon,lat,name&to=lon,lat,name&mode=car&policy=1&src=mypage&callnative=0
      const from = `${currentLocation.lng},${currentLocation.lat},当前位置`
      const to = `${destinationLng},${destinationLat},${encodeURIComponent(destinationName)}`
      const mode = 'car' // 默认驾车，可以根据需要修改
      const policy = '1' // 避免拥堵
      const src = 'ai-travel-planner' // 来源信息
      const callnative = '0' // 不调起APP，使用网页版

      const amapUrl = `https://uri.amap.com/navigation?from=${from}&to=${to}&mode=${mode}&policy=${policy}&src=${src}&callnative=${callnative}`
      
      // 在新窗口打开高德地图导航
      window.open(amapUrl, '_blank')
    } catch (error: any) {
      alert(error.message || '无法获取您的位置，请检查浏览器定位权限设置')
    }
  }

  if (loading) {
    return (
      <div className="trip-detail-page">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>加载中...</p>
        </div>
      </div>
    )
  }

  if (error && !tripData) {
    return (
      <div className="trip-detail-page">
        <div className="error-container">
          <p>{error}</p>
          <button className="retry-button" onClick={() => loadTripDetail()}>
            重试
          </button>
          <button className="back-button" onClick={() => navigate('/trips')}>
            返回列表
          </button>
        </div>
      </div>
    )
  }

  if (!tripData) return null

  const { trip_header, trip_details, budget } = tripData

  // 如果行程还在生成中，显示提示
  const isGenerating = trip_header.status === 'draft' && (!trip_details || trip_details.length === 0)

  return (
    <div className="trip-detail-page">
      <nav className="top-navbar">
        <div className="navbar-content">
          <button className="back-button-nav" onClick={() => navigate('/trips')}>
            返回列表
          </button>
          <h1 className="navbar-title">🧭 AI旅行规划师</h1>
          <div style={{ width: '100px' }}></div>
        </div>
      </nav>

      <div className="trip-detail-container">
        {/* 行程头部信息 */}
        <div className="trip-header-card">
          <div className="trip-header-info">
            {isEditingName ? (
              <div className="name-edit-group">
                <input
                  type="text"
                  value={editedName}
                  onChange={(e) => setEditedName(e.target.value)}
                  className="name-input"
                  autoFocus
                />
                <button className="save-name-button" onClick={handleSaveName}>
                  保存
                </button>
                <button
                  className="cancel-name-button"
                  onClick={() => {
                    setEditedName(trip_header.trip_name)
                    setIsEditingName(false)
                  }}
                >
                  取消
                </button>
              </div>
            ) : (
              <div className="name-display-group">
                <h1 className="trip-title">{trip_header.trip_name}</h1>
                <button
                  className="edit-name-button"
                  onClick={() => setIsEditingName(true)}
                  title="编辑名称"
                >
                  ✏️
                </button>
              </div>
            )}
            <div className="trip-meta">
              <span className="meta-item">📍 {trip_header.destination}</span>
              <span className="meta-item">
                📅 {formatDateRange(trip_header.start_date, trip_header.end_date)}
              </span>
              <span className={getStatusClass(trip_header.status)}>
                {getStatusLabel(trip_header.status)}
              </span>
            </div>
          </div>
          <button
            className="add-expense-button"
            onClick={() => setIsExpenseModalOpen(true)}
          >
            + 添加开销
          </button>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {isGenerating && (
          <div className="generating-notice">
            <div className="generating-content">
              <div className="generating-spinner"></div>
              <h3>行程正在生成中...</h3>
              <p>AI正在为您规划行程，这可能需要30-60秒，请稍候</p>
              <p className="generating-tip">您可以稍后刷新页面查看生成结果</p>
            </div>
          </div>
        )}

        {/* 每日行程 */}
        {!isGenerating && trip_details && trip_details.length > 0 && (
          <div className="days-section">
            <h2 className="section-title">每日行程</h2>
            <div className="days-list">
              {trip_details.map((detail) => (
              <div key={detail.detail_id} className="day-card">
                <div className="day-header">
                  <h3 className="day-title">第 {detail.day_number} 天</h3>
                  <span className="day-theme">{detail.theme}</span>
                </div>

                <div className="day-content">
                  <div className="day-activities-section">
                    {detail.hotel_recommendation && (
                      <div className="hotel-recommendation">
                        <div className="hotel-icon">🏨</div>
                        <div className="hotel-info">
                          <div className="hotel-name">{detail.hotel_recommendation.name}</div>
                          <div className="hotel-reasoning">{detail.hotel_recommendation.reasoning}</div>
                        </div>
                      </div>
                    )}

                    <div className="activities-list">
                      {detail.activities.map((activity, index) => (
                        <div key={index} className="activity-item">
                          <div className="activity-time">{activity.estimated_time_slot}</div>
                          <div className="activity-content">
                            <div className="activity-header">
                              <div className="activity-header-left">
                                <span className="activity-type-badge">
                                  {getActivityTypeLabel(activity.activity_type)}
                                </span>
                                <span className="activity-name">{activity.poi_name}</span>
                              </div>
                              {activity.latitude !== null && activity.longitude !== null && (
                                <button
                                  className="navigate-button"
                                  onClick={() =>
                                    navigateToAmap(
                                      activity.latitude!,
                                      activity.longitude!,
                                      activity.poi_name || '目的地'
                                    )
                                  }
                                  title="到这去"
                                >
                                  ✈️ 到这去
                                </button>
                              )}
                            </div>
                            {activity.notes && (
                              <div className="activity-notes">{activity.notes}</div>
                            )}
                            {activity.transport_to_next && (
                              <div className="transport-info">
                                <span className="transport-icon">🚇</span>
                                <span className="transport-text">
                                  {activity.transport_to_next.recommendation}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {detail.map_url && (
                    <div className="day-map-section">
                      <img
                        src={detail.map_url}
                        alt={`第${detail.day_number}天行程地图`}
                        className="day-map-image"
                        onClick={() => setPreviewImageUrl(detail.map_url!)}
                      />
                    </div>
                  )}
                </div>
              </div>
              ))}
            </div>
          </div>
        )}

        {/* 预算和支出 */}
        {!isGenerating && budget && (
          <div className="budget-section">
          <div className="section-header">
            <h2 className="section-title">预算与支出</h2>
            <div className="section-actions">
              <button
                className="view-expenses-button"
                onClick={() => setIsExpenseListModalOpen(true)}
              >
                📋 最近消费记录
              </button>
              <button
                className="add-expense-button"
                onClick={() => setIsExpenseModalOpen(true)}
              >
                + 添加开销
              </button>
            </div>
          </div>
          <div className="budget-card">
            <div className="budget-summary">
              <div className="budget-total">
                <span className="budget-label">用户预算</span>
                <span className="budget-amount user-budget-amount">¥{budget.user_budget.toLocaleString()}</span>
              </div>
              <div className="budget-estimated">
                <span className="budget-label">AI预估预算</span>
                <span className="budget-amount estimated-budget-amount">¥{budget.estimated_total.toLocaleString()}</span>
              </div>
              {budgetData && (
                <div className="expense-total">
                  <span className="expense-label">实际支出</span>
                  <span className="expense-amount">
                    ¥{budgetData.summary.total_expense.toLocaleString()}
                  </span>
                </div>
              )}
            </div>

            <div className="budget-categories">
              {budget.categories.map((category) => {
                const actualExpense =
                  budgetData?.summary.expense_by_category[category.name] || 0
                const variance =
                  budgetData?.summary.variance[category.name] || null

                return (
                  <div key={category.name} className="category-item">
                    <div className="category-header">
                      <span className="category-name">{category.name}</span>
                      <span className="category-amount">
                        预算: ¥{category.estimated_cny.toLocaleString()}
                      </span>
                    </div>
                    {budgetData && (
                      <div className="category-details">
                        <span className="actual-expense">
                          实际: ¥{actualExpense.toLocaleString()}
                        </span>
                        {variance && (
                          <span
                            className={`variance ${
                              variance.difference >= 0 ? 'positive' : 'negative'
                            }`}
                          >
                            剩余: {variance.difference >= 0 ? '+' : ''}
                            {variance.difference.toLocaleString()} (
                            {variance.percentage >= 0 ? '+' : ''}
                            {variance.percentage.toFixed(1)}%)
                          </span>
                        )}
                      </div>
                    )}
                    {budgetData && (
                      <div className="category-progress">
                        <div
                          className="progress-bar"
                          style={{
                            width: `${
                              Math.min(
                                (actualExpense / category.estimated_cny) * 100,
                                100
                              ) || 0
                            }%`,
                          }}
                        ></div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
        )}

      </div>

      <ExpenseModalXunfeiLLM
        tripId={tripId!}
        isOpen={isExpenseModalOpen}
        onClose={() => setIsExpenseModalOpen(false)}
        onSuccess={handleExpenseSuccess}
      />

      <ExpenseListModal
        tripId={tripId!}
        isOpen={isExpenseListModalOpen}
        onClose={() => setIsExpenseListModalOpen(false)}
      />

      <ImagePreviewModal
        imageUrl={previewImageUrl || ''}
        isOpen={previewImageUrl !== null}
        onClose={() => setPreviewImageUrl(null)}
      />
    </div>
  )
}

export default TripDetailPage


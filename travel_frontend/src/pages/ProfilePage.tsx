// 个人主页
// 对应接口: GET /api/v1/users/me, PUT /api/v1/users/me

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { usersApi } from '../api/users'
import { User } from '../types'
import './ProfilePage.css'

function ProfilePage() {
  const [user, setUser] = useState<User | null>(null)
  const [preferences, setPreferences] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    loadProfile()
  }, [])

  const loadProfile = async () => {
    try {
      setLoading(true)
      setError('')
      const userData = await usersApi.getProfile()
      setUser(userData)
      setPreferences(userData.preferences || '')
    } catch (err: any) {
      setError(err.response?.data?.detail || '加载用户信息失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setError('')
      setSuccess('')
      const updatedUser = await usersApi.updatePreferences(preferences)
      setUser(updatedUser)
      setSuccess('偏好设置已保存')
      // 3秒后清除成功消息
      setTimeout(() => setSuccess(''), 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || '保存失败，请重试')
    } finally {
      setSaving(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    navigate('/login')
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="profile-page">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>加载中...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="profile-page">
        <div className="error-container">
          <p>{error || '无法加载用户信息'}</p>
          <button className="retry-button" onClick={loadProfile}>
            重试
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="profile-page">
      <nav className="top-navbar">
        <div className="navbar-content">
          <h1 className="navbar-title">🧭 AI旅行规划师</h1>
          <button
            className="navbar-button"
            onClick={() => navigate('/trips')}
          >
            返回首页
          </button>
        </div>
      </nav>

      <div className="profile-container">
        <div className="profile-card">
          <div className="profile-header">
            <div className="profile-avatar">
              {user.email.charAt(0).toUpperCase()}
            </div>
            <h2>个人资料</h2>
          </div>

          <div className="profile-body">
            {error && (
              <div className="error-message">
                {error}
              </div>
            )}

            {success && (
              <div className="success-message">
                {success}
              </div>
            )}

            <div className="profile-field">
              <label htmlFor="email">邮箱</label>
              <input
                id="email"
                type="email"
                value={user.email}
                disabled
                className="readonly-input"
              />
              <span className="field-hint">邮箱不可修改</span>
            </div>

            <div className="profile-field">
              <label htmlFor="preferences">旅行偏好</label>
              <textarea
                id="preferences"
                value={preferences}
                onChange={(e) => setPreferences(e.target.value)}
                placeholder="例如：喜欢美食和动漫，带孩子旅游"
                rows={4}
                className="preferences-textarea"
              />
              <span className="field-hint">描述您的旅行偏好，帮助我们为您推荐更合适的行程</span>
            </div>

            <div className="profile-info">
              <div className="info-item">
                <span className="info-label">用户ID</span>
                <span className="info-value">{user.user_id}</span>
              </div>
              <div className="info-item">
                <span className="info-label">注册时间</span>
                <span className="info-value">{formatDate(user.create_time)}</span>
              </div>
              {user.update_time !== user.create_time && (
                <div className="info-item">
                  <span className="info-label">最后更新</span>
                  <span className="info-value">{formatDate(user.update_time)}</span>
                </div>
              )}
            </div>

            <div className="profile-actions">
              <button
                className="save-button"
                onClick={handleSave}
                disabled={saving || preferences === (user.preferences || '')}
              >
                {saving ? '保存中...' : '保存修改'}
              </button>
              <button
                className="logout-button"
                onClick={handleLogout}
              >
                退出登录
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ProfilePage


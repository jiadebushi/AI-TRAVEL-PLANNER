// 登录/注册页
// 对应接口: POST /api/v1/auth/login, POST /api/v1/auth/register

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../api/auth'
import './LoginPage.css'

function LoginPage() {
  const [isLogin, setIsLogin] = useState(true) // true: 登录模式, false: 注册模式
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [preferences, setPreferences] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (isLogin) {
        // 登录
        const response = await authApi.login(email, password)
        localStorage.setItem('access_token', response.access_token)
        navigate('/trips')
      } else {
        // 注册
        await authApi.register(email, password, preferences || undefined)
        // 注册成功后自动登录
        const loginResponse = await authApi.login(email, password)
        localStorage.setItem('access_token', loginResponse.access_token)
        navigate('/trips')
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 
        (isLogin ? '登录失败，请检查邮箱和密码' : '注册失败，请检查输入信息')
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const switchMode = () => {
    setIsLogin(!isLogin)
    setError('')
    setEmail('')
    setPassword('')
    setPreferences('')
  }

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <h1>🧭 AI旅行规划师</h1>
          <p className="login-subtitle">
            {isLogin ? '欢迎回来' : '创建您的账号'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="email">邮箱</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="请输入邮箱"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">密码</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              required
              disabled={loading}
              minLength={6}
            />
          </div>

          {!isLogin && (
            <div className="form-group">
              <label htmlFor="preferences">旅行偏好（可选）</label>
              <input
                id="preferences"
                type="text"
                value={preferences}
                onChange={(e) => setPreferences(e.target.value)}
                placeholder="例如：喜欢美食和动漫"
                disabled={loading}
              />
            </div>
          )}

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <button 
            type="submit" 
            className="submit-button"
            disabled={loading}
          >
            {loading ? '处理中...' : (isLogin ? '登录' : '注册')}
          </button>
        </form>

        <div className="switch-mode">
          <span>
            {isLogin ? '还没有账号？' : '已有账号？'}
          </span>
          <button 
            type="button" 
            onClick={switchMode}
            className="switch-button"
            disabled={loading}
          >
            {isLogin ? '立即注册' : '立即登录'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default LoginPage


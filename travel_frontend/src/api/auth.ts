// 认证相关API
import axios from 'axios'
import { LoginResponse, User } from '../types'

// 使用环境变量或默认值
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

// 创建独立的 axios 实例用于认证，不使用 token 拦截器
const authApiInstance = axios.create({
  baseURL: API_BASE_URL,
})

export const authApi = {
  // 用户注册
  register: async (email: string, password: string, preferences?: string) => {
    const response = await authApiInstance.post<User>('/auth/register', {
      email,
      password,
      preferences,
    })
    return response.data
  },

  // 用户登录
  login: async (email: string, password: string) => {
    const formData = new URLSearchParams()
    formData.append('username', email)
    formData.append('password', password)
    
    const response = await authApiInstance.post<LoginResponse>(
      '/auth/login',
      formData,
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      }
    )
    return response.data
  },
}


// 用户相关API
import api from '../utils/api'
import { User } from '../types'

export const usersApi = {
  // 获取用户档案
  getProfile: async () => {
    const response = await api.get<User>('/users/me')
    return response.data
  },

  // 更新用户偏好
  updatePreferences: async (preferences: string) => {
    const response = await api.put<User>('/users/me', { preferences })
    return response.data
  },
}


// 行程相关API
import api from '../utils/api'
import { TripListResponse, TripDetailResponse } from '../types'

export const tripsApi = {
  // 获取行程列表
  getTripList: async () => {
    const response = await api.get<TripListResponse>('/plan/')
    return response.data
  },

  // 获取行程详情
  getTripDetail: async (tripId: string) => {
    const response = await api.get<TripDetailResponse>(`/plan/${tripId}`)
    return response.data
  },

  // 文本创建行程
  createTripByText: async (data: {
    destination: string
    start_date: string
    end_date: string
    budget_cny: number
    people: string
    preferences?: string
  }) => {
    const response = await api.post<{ message: string; trip_id: string }>(
      '/plan/text',
      data
    )
    return response.data
  },

  // 语音创建行程（文件上传）
  createTripByVoice: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await api.post<{ message: string; trip_id: string }>(
      '/plan/voice',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )
    return response.data
  },

  // 语音文本创建行程（实时语音识别后的文本）
  createTripByVoiceText: async (text: string) => {
    const response = await api.post<{ message: string; trip_id: string }>(
      '/plan/voice-text',
      { text }
    )
    return response.data
  },

  // 修改行程
  updateTrip: async (tripId: string, data: {
    trip_name?: string
    status?: string
  }) => {
    const response = await api.put<{ message: string; trip_id: string }>(
      `/plan/${tripId}`,
      data
    )
    return response.data
  },
}


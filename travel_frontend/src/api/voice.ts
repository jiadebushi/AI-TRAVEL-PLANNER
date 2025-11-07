// 语音相关API
import api from '../utils/api'

export const voiceApi = {
  // 获取讯飞 WebSocket URL（标准版 - 已注释，改用大模型版）
  // getXunfeiWsUrl: async () => {
  //   const response = await api.get<{
  //     ws_url: string
  //     expires_in: number
  //   }>('/voice/xunfei/ws-url')
  //   return response.data
  // },

  // 获取讯飞大模型 WebSocket URL
  getXunfeiLLMWsUrl: async () => {
    const response = await api.get<{
      ws_url: string
      session_id: string
      expires_in: number
    }>('/voice/xunfei-llm/ws-url')
    return response.data
  },
}


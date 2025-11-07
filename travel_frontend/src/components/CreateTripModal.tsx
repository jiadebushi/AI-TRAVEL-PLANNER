// 创建新行程弹窗组件
// 对应接口: POST /api/v1/plan/text, POST /api/v1/plan/voice
// 此组件可在行程列表页中使用

import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { tripsApi } from '../api/trips'
import './CreateTripModal.css'

interface CreateTripModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (tripId: string) => void
}

function CreateTripModal({ isOpen, onClose, onSuccess }: CreateTripModalProps) {
  const navigate = useNavigate()
  const [mode, setMode] = useState<'text' | 'voice'>('text')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  // 文本输入表单
  const [destination, setDestination] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [budget, setBudget] = useState('')
  const [people, setPeople] = useState('')
  const [preferences, setPreferences] = useState('')

  // 语音输入（实时识别）
  const [isRecording, setIsRecording] = useState(false)
  const [recognizedText, setRecognizedText] = useState('')
  const [recordingTime, setRecordingTime] = useState(0)
  const wsRef = useRef<WebSocket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const timerRef = useRef<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  if (!isOpen) return null

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    // 去除空白字符并验证必填字段
    const trimmedDestination = destination.trim()
    const trimmedStartDate = startDate.trim()
    const trimmedEndDate = endDate.trim()
    const trimmedBudget = budget.trim()
    const trimmedPeople = people.trim()
    const trimmedPreferences = preferences.trim()

    // 验证必填字段（偏好除外）
    if (!trimmedDestination || !trimmedStartDate || !trimmedEndDate || !trimmedBudget || !trimmedPeople) {
      setError('请填写所有必填字段（目的地、开始日期、结束日期、预算、同行人数）')
      return
    }

    // 验证日期格式
    if (isNaN(Date.parse(trimmedStartDate))) {
      setError('请输入有效的开始日期')
      return
    }
    if (isNaN(Date.parse(trimmedEndDate))) {
      setError('请输入有效的结束日期')
      return
    }
    if (new Date(trimmedStartDate) >= new Date(trimmedEndDate)) {
      setError('结束日期必须晚于开始日期')
      return
    }

    // 验证预算
    const budgetNum = parseFloat(trimmedBudget)
    if (isNaN(budgetNum) || budgetNum <= 0) {
      setError('请输入有效的预算金额（必须大于0）')
      return
    }

    try {
      setLoading(true)
      setError('')
      const response = await tripsApi.createTripByText({
        destination: trimmedDestination,
        start_date: trimmedStartDate,
        end_date: trimmedEndDate,
        budget_cny: budgetNum,
        people: trimmedPeople,
        preferences: trimmedPreferences || undefined,
      })
      resetForm()
      onSuccess(response.trip_id)
      // 跳转到行程详情页
      navigate(`/trips/${response.trip_id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || '创建行程失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  // 将 Float32 数组转换为 16bit PCM
  const floatTo16BitPCM = (float32Array: Float32Array): Uint8Array => {
    const len = float32Array.length
    const buffer = new ArrayBuffer(len * 2)
    const view = new DataView(buffer)
    let offset = 0
    for (let i = 0; i < len; i++, offset += 2) {
      let s = Math.max(-1, Math.min(1, float32Array[i]))
      // 转为 Int16
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    }
    return new Uint8Array(buffer)
  }

  const startRecording = async () => {
    try {
      setError('')
      setRecognizedText('')
      
      // 获取 WebSocket URL（从当前页面协议和主机构建）
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
      // 如果是相对路径，使用当前页面的主机；否则使用配置的完整 URL
      const apiHost = apiBaseUrl.startsWith('http') 
        ? apiBaseUrl.replace(/^https?:\/\//, '').replace(/\/api\/v1.*$/, '')
        : window.location.host
      const token = localStorage.getItem('access_token')
      const wsUrl = `${wsProtocol}//${apiHost}/api/v1/voice/realtime?token=${token || ''}`
      
      // 1. 建立 WebSocket 连接
      const ws = new WebSocket(wsUrl)
      ws.binaryType = 'arraybuffer'
      wsRef.current = ws

      ws.onmessage = (event) => {
        // 接收识别文本
        const text = event.data
        if (typeof text === 'string') {
          // 过滤掉所有错误和状态消息，只显示识别文本
          const statusPatterns = [
            '[SEND_ERROR]',
            '[ERROR]',
            '[WS_CLOSED]',
            '[WS_OPEN]',
            '[WS_CONNECTING]',
            '[WS_ERROR]',
            '[CONNECTION_ERROR]',
            '[CLOSED]',
            '[OPEN]',
            '[CONNECTING]',
            '[STATUS]',
          ]
          const isStatusMessage = statusPatterns.some((pattern) => text.includes(pattern))
          
          if (!isStatusMessage && text.trim()) {
            setRecognizedText(text)
          } else if (isStatusMessage) {
            // 如果是状态消息，记录到控制台但不显示在输入框
            console.log('WebSocket status message:', text)
          }
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setError('语音识别连接失败，请重试')
        // 立即停止音频处理
        if (processorRef.current) {
          processorRef.current.disconnect()
          processorRef.current = null
        }
        stopRecording()
      }

      ws.onclose = (event) => {
        console.log('WebSocket closed', event.code, event.reason)
        // 连接关闭时，立即停止音频处理
        if (processorRef.current) {
          processorRef.current.disconnect()
          processorRef.current = null
        }
        
        // 如果连接异常关闭（非正常关闭），显示错误提示
        // 1000 = 正常关闭，1001 = 端点离开，1005 = 无状态码
        if (event.code !== 1000 && event.code !== 1001 && event.code !== 1005) {
          setError('语音识别连接异常关闭，请重试')
        }
        
        // 如果还在录音状态，更新状态
        if (isRecording) {
          setIsRecording(false)
          if (timerRef.current) {
            clearInterval(timerRef.current)
            timerRef.current = null
          }
        }
      }

      ws.onopen = async () => {
        try {
          // 2. 获取麦克风权限
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
          mediaStreamRef.current = stream

          // 3. 创建 AudioContext（16kHz 采样率）
          const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext
          const audioContext = new AudioContextClass({ sampleRate: 16000 })
          audioContextRef.current = audioContext

          const source = audioContext.createMediaStreamSource(stream)

          // 4. 使用 ScriptProcessorNode 获取 PCM 数据
          const bufferSize = 4096
          const processor = audioContext.createScriptProcessor(bufferSize, 1, 1)
          processorRef.current = processor

          processor.onaudioprocess = (e) => {
            // 使用 wsRef.current 而不是局部变量，确保获取最新的连接状态
            const currentWs = wsRef.current
            if (currentWs && currentWs.readyState === WebSocket.OPEN) {
              try {
                const input = e.inputBuffer.getChannelData(0) // Float32 [-1,1]
                // 转 Int16 PCM
                const pcm16 = floatTo16BitPCM(input)
                currentWs.send(pcm16.buffer) // 发送二进制音频块
              } catch (sendError) {
                // 如果发送失败，停止处理
                console.error('Failed to send audio data:', sendError)
                if (processorRef.current) {
                  processorRef.current.disconnect()
                  processorRef.current = null
                }
              }
            } else {
              // 连接已关闭，停止处理
              if (processorRef.current) {
                processorRef.current.disconnect()
                processorRef.current = null
              }
            }
          }

          source.connect(processor)
          processor.connect(audioContext.destination)

          setIsRecording(true)
          setRecordingTime(0)

          // 计时器
          timerRef.current = setInterval(() => {
            setRecordingTime((prev) => prev + 1)
          }, 1000)
        } catch (err: any) {
          setError('无法访问麦克风，请检查权限设置')
          if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
            ws.close()
          }
        }
      }
    } catch (err: any) {
      setError('启动语音识别失败：' + (err.message || '未知错误'))
    }
  }

  const stopRecording = async () => {
    try {
      // 先断开音频处理，避免继续发送数据
      if (processorRef.current) {
        processorRef.current.disconnect()
        processorRef.current = null
      }

      // 发送停止信号（如果连接仍然打开）
      if (wsRef.current) {
        if (wsRef.current.readyState === WebSocket.OPEN) {
          try {
            wsRef.current.send('stop')
          } catch (err) {
            console.error('Failed to send stop signal:', err)
          }
        }
        wsRef.current.close()
        wsRef.current = null
      }

      // 关闭 AudioContext
      if (audioContextRef.current) {
        try {
          await audioContextRef.current.close()
        } catch (err) {
          console.error('Failed to close AudioContext:', err)
        }
        audioContextRef.current = null
      }

      // 停止媒体流
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop())
        mediaStreamRef.current = null
      }

      // 清除计时器
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }

      setIsRecording(false)
    } catch (err) {
      console.error('Stop recording error:', err)
      setIsRecording(false)
    }
  }

  const handleVoiceSubmit = async () => {
    // 去除空白字符并验证
    const trimmedText = recognizedText.trim()
    
    if (!trimmedText) {
      setError('请先进行语音识别或手动输入行程信息')
      return
    }

    try {
      setLoading(true)
      setError('')
      // 使用文本输入创建行程（后端 LLM 会从文本中解析所有信息）
      // 将识别文本作为 preferences 字段传递，后端会解析整个文本
      const response = await tripsApi.createTripByText({
        destination: trimmedText, // 将完整文本放在 destination，后端会解析
        start_date: '',
        end_date: '',
        budget_cny: 0,
        people: '',
        preferences: trimmedText,
      })
      resetForm()
      onSuccess(response.trip_id)
      // 跳转到行程详情页
      navigate(`/trips/${response.trip_id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || '创建行程失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setDestination('')
    setStartDate('')
    setEndDate('')
    setBudget('')
    setPeople('')
    setPreferences('')
    setRecognizedText('')
    setRecordingTime(0)
    setError('')
    setMode('text')
    setIsRecording(false)
    // 清理 WebSocket 和音频资源
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    if (processorRef.current) {
      processorRef.current.disconnect()
      processorRef.current = null
    }
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop())
      mediaStreamRef.current = null
    }
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleClose = () => {
    if (isRecording) {
      stopRecording()
    }
    resetForm()
    onClose()
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>规划新行程</h2>
          <button className="modal-close" onClick={handleClose}>×</button>
        </div>

        <div className="modal-tabs">
          <button
            className={`tab-button ${mode === 'text' ? 'active' : ''}`}
            onClick={() => setMode('text')}
          >
            📝 文本输入
          </button>
          <button
            className={`tab-button ${mode === 'voice' ? 'active' : ''}`}
            onClick={() => setMode('voice')}
          >
            🎤 语音输入
          </button>
        </div>

        {error && (
          <div className="modal-error">
            {error}
          </div>
        )}

        {mode === 'text' ? (
          <form onSubmit={handleTextSubmit} className="text-form" noValidate>
            <div className="form-group">
              <label htmlFor="destination">目的地 *</label>
              <input
                id="destination"
                type="text"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                placeholder="例如：东京"
                disabled={loading}
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="startDate">开始日期 *</label>
                <input
                  id="startDate"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  disabled={loading}
                />
              </div>

              <div className="form-group">
                <label htmlFor="endDate">结束日期 *</label>
                <input
                  id="endDate"
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  min={startDate}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="budget">预算（人民币）*</label>
                <input
                  id="budget"
                  type="number"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  placeholder="例如：15000"
                  min="0"
                  step="0.01"
                  disabled={loading}
                />
              </div>

              <div className="form-group">
                <label htmlFor="people">同行人数 *</label>
                <input
                  id="people"
                  type="text"
                  value={people}
                  onChange={(e) => setPeople(e.target.value)}
                  placeholder="例如：2大1小"
                  disabled={loading}
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="preferences">旅行偏好（可选）</label>
              <input
                id="preferences"
                type="text"
                value={preferences}
                onChange={(e) => setPreferences(e.target.value)}
                placeholder="例如：喜欢美食和动漫，带孩子旅游"
                disabled={loading}
              />
            </div>

            <div className="modal-actions">
              <button
                type="button"
                className="cancel-button"
                onClick={handleClose}
                disabled={loading}
              >
                取消
              </button>
              <button
                type="submit"
                className="submit-button"
                disabled={loading}
              >
                {loading ? '生成中...' : '生成行程'}
              </button>
            </div>
          </form>
        ) : (
          <div className="voice-form">
            <div className="voice-instructions">
              <p>请说出您的旅行计划，例如：</p>
              <p className="example-text">
                "我想去东京旅行，12月1日到12月7日，预算15000元，2大1小，喜欢美食和动漫，带孩子旅游"
              </p>
            </div>

            {/* 实时识别文本输入框 */}
            <div className="form-group">
              <label htmlFor="recognizedText">识别文本</label>
              <textarea
                id="recognizedText"
                value={recognizedText}
                onChange={(e) => setRecognizedText(e.target.value)}
                placeholder="语音识别结果会实时显示在这里，您也可以手动编辑..."
                className="recognized-text-input"
                rows={6}
                disabled={loading}
              />
              <p className="input-hint">
                💡 提示：点击"开始识别"后说话，识别结果会实时显示在上方文本框中，您可以随时编辑
              </p>
            </div>

            <div className="voice-controls">
              {!isRecording && (
                <button
                  type="button"
                  className="record-button"
                  onClick={startRecording}
                  disabled={loading}
                >
                  🎤 开始识别
                </button>
              )}

              {isRecording && (
                <div className="recording-status">
                  <div className="recording-indicator"></div>
                  <span className="recording-time">{formatTime(recordingTime)}</span>
                  <button
                    type="button"
                    className="stop-button"
                    onClick={stopRecording}
                  >
                    停止识别
                  </button>
                </div>
              )}
            </div>

            <div className="modal-actions">
              <button
                type="button"
                className="cancel-button"
                onClick={handleClose}
                disabled={loading || isRecording}
              >
                取消
              </button>
              <button
                type="button"
                className="submit-button"
                onClick={handleVoiceSubmit}
                disabled={loading || isRecording || !recognizedText.trim()}
              >
                {loading ? '生成中...' : '生成行程'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default CreateTripModal


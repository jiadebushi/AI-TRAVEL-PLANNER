// 创建新行程弹窗组件（使用讯飞实时语音转写）
// 对应接口: POST /api/v1/plan/text, POST /api/v1/plan/voice
// 此组件可在行程列表页中使用

import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { tripsApi } from '../api/trips'
import { voiceApi } from '../api/voice'
import './CreateTripModal.css'

interface CreateTripModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (tripId: string) => void
}

function CreateTripModalXunfei({ isOpen, onClose, onSuccess }: CreateTripModalProps) {
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

  // 语音输入（讯飞实时识别）
  const [isRecording, setIsRecording] = useState(false)
  const [recognizedText, setRecognizedText] = useState('')
  const [recordingTime, setRecordingTime] = useState(0)
  const wsRef = useRef<WebSocket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const timerRef = useRef<number | null>(null)
  const recognizedTextRef = useRef<string>('') // 存储所有已确认的识别文本（只增不减）
  const intermediateTextRef = useRef<string>('') // 存储当前中间结果（用于实时显示，会不断更新）
  const processedSegmentsRef = useRef<Set<number>>(new Set()) // 记录已处理的最终结果seg_id，避免重复

  if (!isOpen) return null


  // 将 Float32 数组转换为 16bit PCM
  const floatTo16BitPCM = (float32Array: Float32Array): Uint8Array => {
    const len = float32Array.length
    const buffer = new ArrayBuffer(len * 2)
    const view = new DataView(buffer)
    let offset = 0
    for (let i = 0; i < len; i++, offset += 2) {
      let s = Math.max(-1, Math.min(1, float32Array[i]))
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    }
    return new Uint8Array(buffer)
  }

  // 解析讯飞转写结果
  const parseXunfeiResult = (data: string): string => {
    try {
      const result = JSON.parse(data)
      if (result.cn && result.cn.st && result.cn.st.rt) {
        // 提取所有词
        const words: string[] = []
        result.cn.st.rt.forEach((rt: any) => {
          if (rt.ws) {
            rt.ws.forEach((ws: any) => {
              if (ws.cw) {
                ws.cw.forEach((cw: any) => {
                  if (cw.w) {
                    words.push(cw.w)
                  }
                })
              }
            })
          }
        })
        return words.join('')
      }
      return ''
    } catch (err) {
      console.error('Failed to parse Xunfei result:', err)
      return ''
    }
  }

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
      navigate(`/trips/${response.trip_id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || '创建行程失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  const startRecording = async () => {
    try {
      setError('')
      setRecognizedText('')
      recognizedTextRef.current = '' // 重置最终文本
      intermediateTextRef.current = '' // 重置中间结果
      processedSegmentsRef.current.clear() // 清空已处理段落记录

      // 1. 从后端获取已鉴权的 WebSocket URL
      setError('正在获取连接...')
      const { ws_url } = await voiceApi.getXunfeiLLMWsUrl()
      setError('')

      // 验证 URL 是否是讯飞服务器（确保不是后端转接）
      if (!ws_url.includes('rtasr.xfyun.cn')) {
        setError('获取的 WebSocket URL 不是讯飞服务器地址，请检查后端配置')
        return
      }

      console.log('Connecting to Xunfei WebSocket:', ws_url.replace(/signa=[^&]+/, 'signa=***')) // 隐藏签名

      // 2. 建立WebSocket连接（直接连接到讯飞服务器，不经过后端）
      const ws = new WebSocket(ws_url)
      wsRef.current = ws

      ws.onmessage = (event) => {
        try {
          const result = JSON.parse(event.data)
          
          if (result.action === 'started') {
            // 握手成功
            console.log('Xunfei WebSocket connected:', result.sid)
          } else if (result.action === 'result') {
            // 转写结果
            if (result.code === '0' && result.data) {
              try {
                const dataObj = JSON.parse(result.data)
                const text = parseXunfeiResult(result.data)
                
                if (text) {
                  const resultType = dataObj.cn?.st?.type || '1'
                  const segId = dataObj.seg_id !== undefined ? dataObj.seg_id : -1
                  
                  if (resultType === '0') {
                    // 最终结果（type=0）：追加到最终文本，不删除
                    // 检查是否已经处理过这个seg_id，避免重复
                    if (!processedSegmentsRef.current.has(segId)) {
                      // 确保是追加操作：先保存旧值，然后追加新值
                      const previousText = recognizedTextRef.current
                      recognizedTextRef.current = previousText + text
                      // 添加空格，使文本更易读
                      if (!recognizedTextRef.current.endsWith(' ') && !recognizedTextRef.current.endsWith('\n')) {
                        recognizedTextRef.current += ' '
                      }
                      processedSegmentsRef.current.add(segId)
                      console.log('Final result added, segId:', segId, 'previous length:', previousText.length, 'new length:', recognizedTextRef.current.length)
                    }
                    // 清空中间结果（因为最终结果已经确认）
                    intermediateTextRef.current = ''
                    // 显示最终文本（确保是追加后的完整文本）
                    setRecognizedText(recognizedTextRef.current)
                  } else {
                    // 中间结果（type=1）：只用于实时显示，不保存到最终文本
                    // 中间结果会不断更新同一个句子，直接替换当前中间结果
                    intermediateTextRef.current = text
                    // 显示：最终文本 + 当前中间结果
                    // 重要：使用 recognizedTextRef.current 确保最终文本不会被替换
                    const finalText = recognizedTextRef.current
                    const intermediateText = intermediateTextRef.current
                    setRecognizedText(finalText + intermediateText)
                  }
                }
              } catch (parseErr) {
                console.error('Failed to parse result data:', parseErr)
              }
            }
          } else if (result.action === 'error') {
            // 错误
            console.error('Xunfei error:', result)
            setError(`语音识别错误: ${result.desc || result.code}`)
            stopRecording()
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setError('语音识别连接失败，请重试')
        stopRecording()
      }

      ws.onclose = (event) => {
        console.log('WebSocket closed', event.code, event.reason)
        if (processorRef.current) {
          processorRef.current.disconnect()
          processorRef.current = null
        }
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
          // 4. 获取麦克风权限
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
          mediaStreamRef.current = stream

          // 5. 创建 AudioContext（16kHz 采样率）
          const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext
          const audioContext = new AudioContextClass({ sampleRate: 16000 })
          audioContextRef.current = audioContext

          const source = audioContext.createMediaStreamSource(stream)

          // 6. 使用 ScriptProcessorNode 获取 PCM 数据
          const bufferSize = 4096
          const processor = audioContext.createScriptProcessor(bufferSize, 1, 1)
          processorRef.current = processor

          let lastSendTime = Date.now()

          processor.onaudioprocess = (e) => {
            const currentWs = wsRef.current
            if (!currentWs || currentWs.readyState !== WebSocket.OPEN) {
              if (processorRef.current) {
                processorRef.current.disconnect()
                processorRef.current = null
              }
              return
            }

            try {
              const input = e.inputBuffer.getChannelData(0)
              const pcm16 = floatTo16BitPCM(input)
              
              // 控制发送频率：每40ms发送一次（约1280字节）
              const now = Date.now()
              if (now - lastSendTime >= 40) {
                currentWs.send(pcm16.buffer)
                lastSendTime = now
              }
            } catch (sendError) {
              console.error('Failed to send audio data:', sendError)
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
      // 先断开音频处理
      if (processorRef.current) {
        processorRef.current.disconnect()
        processorRef.current = null
      }

      // 发送结束标识
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        try {
          wsRef.current.send(JSON.stringify({ end: true }))
        } catch (err) {
          console.error('Failed to send end signal:', err)
        }
        // 等待一下，让服务端处理完最后的数据（可能会有最终结果返回）
        setTimeout(() => {
          // 如果还有中间结果，保存到最终文本
          if (intermediateTextRef.current) {
            recognizedTextRef.current += intermediateTextRef.current
            intermediateTextRef.current = ''
            setRecognizedText(recognizedTextRef.current)
          }
          // 关闭连接
          if (wsRef.current) {
            wsRef.current.close()
          }
        }, 1000) // 增加等待时间，确保收到最后的最终结果
      } else {
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
    const trimmedText = recognizedText.trim()
    
    if (!trimmedText) {
      setError('请先进行语音识别或手动输入行程信息')
      return
    }

    try {
      setLoading(true)
      setError('')
      // 使用文本输入创建行程（后端 LLM 会从文本中解析所有信息）
      const response = await tripsApi.createTripByText({
        destination: trimmedText,
        start_date: '',
        end_date: '',
        budget_cny: 0,
        people: '',
        preferences: trimmedText,
      })
      resetForm()
      onSuccess(response.trip_id)
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

  // const getActivityTypeLabel = (type: string) => {
  //   const typeMap: Record<string, string> = {
  //     Meal_Breakfast: '早餐',
  //     Meal_Lunch: '午餐',
  //     Meal_Dinner: '晚餐',
  //     Attraction: '景点',
  //     Hotel: '酒店',
  //     Transport: '交通',
  //   }
  //   return typeMap[type] || type
  // }

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>规划新行程（讯飞版）</h2>
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
            🎤 语音输入（讯飞）
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
                onChange={(e) => {
                  // 用户手动编辑时，同步更新 recognizedTextRef
                  const newValue = e.target.value
                  recognizedTextRef.current = newValue
                  intermediateTextRef.current = ''
                  setRecognizedText(newValue)
                }}
                placeholder="语音识别结果会实时显示在这里，您也可以手动编辑..."
                className="recognized-text-input"
                rows={6}
                disabled={loading || isRecording}
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

export default CreateTripModalXunfei


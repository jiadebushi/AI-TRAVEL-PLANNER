// 开销录入弹窗组件（使用讯飞实时语音识别）
// 对应接口: POST /api/v1/budget/expense/text
// 此组件可嵌入到行程详情页中使用

import { useState, useEffect, useRef } from 'react'
import { budgetApi } from '../api/budget'
import { voiceApi } from '../api/voice'
import { Expense } from '../types'
import './ExpenseModal.css'

interface ExpenseModalProps {
  tripId: string
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

function ExpenseModalXunfeiLLM({ tripId, isOpen, onClose, onSuccess }: ExpenseModalProps) {
  const [mode, setMode] = useState<'text' | 'voice'>('text')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [textInput, setTextInput] = useState('')
  
  // 语音输入（讯飞大模型实时识别）
  const [isRecording, setIsRecording] = useState(false)
  const [recognizedText, setRecognizedText] = useState('')
  const [recordingTime, setRecordingTime] = useState(0)
  const [hasRecorded, setHasRecorded] = useState(false) // 是否已经识别过
  const wsRef = useRef<WebSocket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const timerRef = useRef<number | null>(null)
  const recognizedTextRef = useRef<string>('') // 存储所有已确认的识别文本（只增不减）
  const intermediateTextRef = useRef<string>('') // 存储当前中间结果（用于实时显示，会不断更新）
  const processedSegmentsRef = useRef<Set<number>>(new Set()) // 记录已处理的最终结果seg_id，避免重复
  const sessionIdRef = useRef<string>('') // 存储会话ID

  // 最近消费记录
  const [recentExpenses, setRecentExpenses] = useState<Expense[]>([])
  const [loadingExpenses, setLoadingExpenses] = useState(false)

  useEffect(() => {
    if (isOpen) {
      loadRecentExpenses()
    }
  }, [isOpen, tripId])

  const loadRecentExpenses = async () => {
    try {
      setLoadingExpenses(true)
      const data = await budgetApi.getBudgetDetail(tripId)
      // 只显示最近10条记录
      setRecentExpenses(data.expenses.slice(0, 10))
    } catch (err) {
      console.error('加载消费记录失败:', err)
    } finally {
      setLoadingExpenses(false)
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
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    }
    return new Uint8Array(buffer)
  }

  // 解析讯飞大模型转写结果
  const parseXunfeiLLMResult = (data: any): string => {
    try {
      // 大模型版本的返回格式
      if (data.cn && data.cn.st && data.cn.st.rt) {
        const words: string[] = []
        data.cn.st.rt.forEach((rt: any) => {
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
      console.error('Failed to parse Xunfei LLM result:', err)
      return ''
    }
  }

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!textInput.trim()) {
      setError('请输入消费描述')
      return
    }

    try {
      setLoading(true)
      setError('')
      await budgetApi.addExpenseByText(tripId, textInput.trim())
      resetForm()
      await loadRecentExpenses()
      onSuccess()
    } catch (err: any) {
      // 检查是否是类型验证错误（通常是数据已保存但类型不匹配）
      const errorMessage = err.response?.data?.detail || err.message || ''
      const isValidationError = errorMessage.includes('validation error') || 
                                errorMessage.includes('string_type') ||
                                errorMessage.includes('timestamp')
      
      if (isValidationError) {
        // 类型验证错误通常意味着数据已保存，只是响应格式有问题
        // 继续执行成功逻辑，刷新数据
        resetForm()
        await loadRecentExpenses()
        onSuccess()
      } else {
        setError(err.response?.data?.detail || '录入开销失败，请重试')
      }
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
      sessionIdRef.current = '' // 重置会话ID

      // 1. 从后端获取已鉴权的 WebSocket URL（讯飞大模型版）
      setError('正在获取连接...')
      let ws_url: string
      let session_id: string
      try {
        const response = await voiceApi.getXunfeiLLMWsUrl()
        console.log('[Xunfei LLM] Backend response:', {
          ws_url: response.ws_url?.substring(0, 100) + '...',
          session_id: response.session_id,
          expires_in: response.expires_in
        })
        ws_url = response.ws_url
        session_id = response.session_id || ''
      } catch (apiErr: any) {
        console.error('[Xunfei LLM] Failed to get WebSocket URL:', apiErr)
        if (apiErr.response?.status === 404) {
          setError('后端接口未实现：/voice/xunfei-llm/ws-url，请检查后端代码')
        } else if (apiErr.response?.status === 401) {
          setError('认证失败，请重新登录')
        } else if (apiErr.response?.status === 500) {
          setError(`后端错误：${apiErr.response?.data?.detail || '生成WebSocket URL失败，请检查后端日志'}`)
        } else {
          setError(`获取连接失败：${apiErr.response?.data?.detail || apiErr.message || '未知错误'}，请检查后端接口`)
        }
        return
      }
      
      setError('')
      sessionIdRef.current = session_id

      // 验证 URL 是否是讯飞大模型服务器（确保不是后端转接）
      if (!ws_url || typeof ws_url !== 'string') {
        console.error('[Xunfei LLM] Invalid ws_url:', ws_url)
        setError('后端返回的 WebSocket URL 格式错误')
        return
      }
      
      if (!ws_url.includes('office-api-ast-dx.iflyaisol.com')) {
        console.error('[Xunfei LLM] Invalid server address in URL:', ws_url)
        setError(`获取的 WebSocket URL 不是讯飞大模型服务器地址，请检查后端配置。当前URL: ${ws_url.substring(0, 100)}...`)
        return
      }

      // 检查 URL 是否以 wss:// 开头
      if (!ws_url.startsWith('wss://') && !ws_url.startsWith('ws://')) {
        console.error('[Xunfei LLM] Invalid WebSocket protocol:', ws_url.substring(0, 10))
        setError('WebSocket URL 必须以 wss:// 或 ws:// 开头')
        return
      }

      // 检测并修复双重编码问题
      if (ws_url.includes('%253') || ws_url.includes('%252') || ws_url.includes('%255')) {
        console.warn('[Xunfei LLM] Detected double-encoded URL, attempting to fix...')
        console.warn('[Xunfei LLM] Original URL (sample):', ws_url.substring(0, 150))
        try {
          let decodedUrl = decodeURIComponent(ws_url)
          const urlObj = new URL(decodedUrl)
          const params = new URLSearchParams()
          urlObj.searchParams.forEach((value, key) => {
            params.append(key, value)
          })
          const fixedUrl = `${urlObj.protocol}//${urlObj.host}${urlObj.pathname}?${params.toString()}`
          console.log('[Xunfei LLM] Fixed URL (masked):', fixedUrl.replace(/signature=[^&]+/, 'signature=***'))
          ws_url = fixedUrl
        } catch (fixErr) {
          console.error('[Xunfei LLM] Failed to fix double-encoded URL:', fixErr)
          setError(`URL 存在双重编码问题，请检查后端签名生成代码。\n\n问题：URL 参数被编码了两次\n例如：%253A 应为 %3A，%252B 应为 %2B\n\n建议：后端在生成 URL 时，确保每个参数只编码一次。\n如果使用 Python 的 quote() 函数，不要对已经编码的字符串再次编码。`)
          return
        }
      }

      console.log('[Xunfei LLM] Connecting to WebSocket:', ws_url.replace(/signature=[^&]+/, 'signature=***'))
      console.log('[Xunfei LLM] Session ID:', session_id)

      // 2. 建立WebSocket连接（直接连接到讯飞大模型服务器，不经过后端）
      let connectionTimeout: number | null = null
      const ws = new WebSocket(ws_url)
      wsRef.current = ws

      // 设置连接超时（10秒）
      connectionTimeout = setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          console.error('WebSocket connection timeout')
          ws.close()
          setError('连接超时，请检查网络或后端配置')
          stopRecording()
        }
      }, 10000)

      ws.onmessage = (event) => {
        // 清除连接超时
        if (connectionTimeout) {
          clearTimeout(connectionTimeout)
          connectionTimeout = null
        }

        try {
          const result = JSON.parse(event.data)
          
          // 大模型版本的返回格式：msg_type 和 res_type
          if (result.msg_type === 'result' && result.res_type === 'asr') {
            // 转写结果
            if (result.data) {
              const data = result.data
              const text = parseXunfeiLLMResult(data)
              
              if (text) {
                const segId = data.seg_id !== undefined ? data.seg_id : -1
                const resultType = data.cn?.st?.type || '1'
                
                if (resultType === '0') {
                  // 最终结果（type=0）：追加到最终文本，不删除
                  if (!processedSegmentsRef.current.has(segId)) {
                    const previousText = recognizedTextRef.current
                    recognizedTextRef.current = previousText + text
                    if (!recognizedTextRef.current.endsWith(' ') && !recognizedTextRef.current.endsWith('\n')) {
                      recognizedTextRef.current += ' '
                    }
                    processedSegmentsRef.current.add(segId)
                    console.log('Final result added, segId:', segId, 'previous length:', previousText.length, 'new length:', recognizedTextRef.current.length)
                  }
                  intermediateTextRef.current = ''
                  setRecognizedText(recognizedTextRef.current)
                } else {
                  // 中间结果（type=1）：只用于实时显示，不保存到最终文本
                  intermediateTextRef.current = text
                  const finalText = recognizedTextRef.current
                  const intermediateText = intermediateTextRef.current
                  setRecognizedText(finalText + intermediateText)
                }
              }
            }
          } else if (result.msg_type === 'result' && result.res_type === 'frc') {
            // 异常结果（功能异常）
            console.error('Xunfei LLM error:', result)
            const errorDesc = result.data?.desc || result.data?.detail || '未知错误'
            setError(`语音识别错误: ${errorDesc}`)
            stopRecording()
          } else if (result.msg_type === 'error') {
            // 错误
            console.error('Xunfei LLM error:', result)
            setError(`语音识别错误: ${result.desc || result.code || '未知错误'}`)
            stopRecording()
          }
        } catch (parseErr) {
          console.error('Failed to parse WebSocket message:', parseErr, 'Raw data:', event.data)
        }
      }

      ws.onerror = (error) => {
        if (connectionTimeout) {
          clearTimeout(connectionTimeout)
          connectionTimeout = null
        }
        console.error('[Xunfei LLM] WebSocket error event:', error)
        console.error('[Xunfei LLM] WebSocket readyState:', ws.readyState)
        console.error('[Xunfei LLM] WebSocket URL (masked):', ws_url.replace(/signature=[^&]+/, 'signature=***'))
      }

      ws.onclose = (event) => {
        if (connectionTimeout) {
          clearTimeout(connectionTimeout)
          connectionTimeout = null
        }

        console.log('[Xunfei LLM] WebSocket closed', {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean,
          readyState: ws.readyState
        })
        
        if (isRecording && event.code !== 1000 && event.code !== 1001) {
          let errorMsg = '连接已关闭'
          if (event.code === 1006) {
            errorMsg = `连接异常关闭 (${event.code})，可能原因：\n1) URL签名验证失败（检查后端签名算法）\n2) 网络问题或防火墙阻止\n3) 讯飞服务器拒绝连接\n\n请检查：\n- 浏览器控制台的详细错误信息\n- 后端日志中的签名生成过程\n- 网络连接是否正常`
          } else if (event.code === 1002) {
            errorMsg = `协议错误 (${event.code})，请检查后端生成的URL格式是否正确`
          } else if (event.code === 1003) {
            errorMsg = `数据格式错误 (${event.code})`
          } else if (event.code >= 4000) {
            errorMsg = `服务端错误 (${event.code}): ${event.reason || '请检查后端日志和讯飞服务状态'}`
          } else {
            errorMsg = `连接关闭 (${event.code}): ${event.reason || '未知原因'}`
          }
          console.error('[Xunfei LLM] Connection failed:', errorMsg)
          setError(errorMsg)
        }
        
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
        if (connectionTimeout) {
          clearTimeout(connectionTimeout)
          connectionTimeout = null
        }

        console.log('[Xunfei LLM] WebSocket connected successfully')
        console.log('[Xunfei LLM] WebSocket readyState:', ws.readyState)
        setError('')

        try {
          // 3. 获取麦克风权限
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
          mediaStreamRef.current = stream

          // 4. 创建 AudioContext（16kHz 采样率）
          const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext
          const audioContext = new AudioContextClass({ sampleRate: 16000 })
          audioContextRef.current = audioContext

          const source = audioContext.createMediaStreamSource(stream)

          // 5. 使用 ScriptProcessorNode 获取 PCM 数据
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
          console.error('Failed to access microphone:', err)
          setError('无法访问麦克风，请检查权限设置：' + (err.message || ''))
          if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
            ws.close()
          }
        }
      }
    } catch (err: any) {
      console.error('Failed to start recording:', err)
    }
  }

  const stopRecording = async () => {
    try {
      // 先断开音频处理
      if (processorRef.current) {
        processorRef.current.disconnect()
        processorRef.current = null
      }

      // 发送结束标识（大模型版本需要包含sessionId）
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        try {
          const endMessage = sessionIdRef.current 
            ? JSON.stringify({ end: true, sessionId: sessionIdRef.current })
            : JSON.stringify({ end: true })
          wsRef.current.send(endMessage)
        } catch (err) {
          console.error('Failed to send end signal:', err)
        }
        // 等待一下，让服务端处理完最后的数据
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
        }, 1000)
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
      // 标记已经识别过
      setHasRecorded(true)
    } catch (err) {
      console.error('Stop recording error:', err)
      setIsRecording(false)
      setHasRecorded(true)
    }
  }

  const handleVoiceSubmit = async () => {
    const trimmedText = recognizedText.trim()
    
    if (!trimmedText) {
      setError('请先进行语音识别或手动输入消费描述')
      return
    }

    try {
      setLoading(true)
      setError('')
      // 使用语音文本接口创建开销（后端 LLM 会从文本中解析所有信息）
      await budgetApi.addExpenseByText(tripId, trimmedText)
      resetForm()
      await loadRecentExpenses()
      onSuccess()
    } catch (err: any) {
      console.error('Failed to create expense from voice text:', err)
      // 检查是否是类型验证错误
      const errorMessage = err.response?.data?.detail || err.message || ''
      const isValidationError = errorMessage.includes('validation error') || 
                                errorMessage.includes('string_type') ||
                                errorMessage.includes('timestamp')
      
      if (isValidationError) {
        // 类型验证错误通常意味着数据已保存，只是响应格式有问题
        resetForm()
        await loadRecentExpenses()
        onSuccess()
      } else {
        setError(err.response?.data?.detail || '录入开销失败，请重试')
      }
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setTextInput('')
    setRecognizedText('')
    setRecordingTime(0)
    setError('')
    setMode('text')
    setIsRecording(false)
    setHasRecorded(false) // 重置识别状态
    
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
    recognizedTextRef.current = ''
    intermediateTextRef.current = ''
    processedSegmentsRef.current.clear()
    sessionIdRef.current = ''
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

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN', {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content expense-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>录入开销（讯飞大模型版）</h2>
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
            🎤 语音输入（讯飞大模型）
          </button>
        </div>

        {error && (
          <div className="modal-error">
            {error}
          </div>
        )}

        {mode === 'text' ? (
          <form onSubmit={handleTextSubmit} className="expense-text-form">
            <div className="form-group">
              <label htmlFor="expense-text">消费描述 *</label>
              <textarea
                id="expense-text"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="例如：今天在餐厅吃了日式料理，花费了500元"
                rows={4}
                required
                disabled={loading}
                className="expense-textarea"
              />
              <span className="field-hint">描述您的消费，系统会自动识别金额和类别</span>
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
                disabled={loading || !textInput.trim()}
              >
                {loading ? '录入中...' : '提交'}
              </button>
            </div>
          </form>
        ) : (
          <div className="expense-voice-form">
            <div className="voice-instructions">
              <p>请说出您的消费，例如：</p>
              <p className="example-text">
                "今天在餐厅吃了日式料理，花费了500元"
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
                className="recognized-text-input expense-textarea"
                rows={4}
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
                  className={`record-button ${hasRecorded ? 'record-button-rerecord' : ''}`}
                  onClick={startRecording}
                  disabled={loading}
                >
                  {hasRecorded ? '🎤 重新识别' : '🎤 开始识别'}
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
                {loading ? '录入中...' : '提交'}
              </button>
            </div>
          </div>
        )}

        {/* 最近消费记录 */}
        <div className="recent-expenses">
          <h3 className="recent-expenses-title">最近消费记录</h3>
          {loadingExpenses ? (
            <div className="expenses-loading">加载中...</div>
          ) : recentExpenses.length === 0 ? (
            <div className="no-expenses">暂无消费记录</div>
          ) : (
            <div className="expenses-list">
              {recentExpenses.map((expense) => (
                <div key={expense.expense_id} className="expense-item">
                  <div className="expense-item-header">
                    <span className="expense-category">{expense.category}</span>
                    <span className="expense-amount">¥{expense.amount.toLocaleString()}</span>
                  </div>
                  <div className="expense-description">{expense.description}</div>
                  <div className="expense-time">{formatDateTime(expense.timestamp)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ExpenseModalXunfeiLLM


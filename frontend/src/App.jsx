import { useState, useEffect, useRef } from 'react'
import { 
  Send, 
  Bot, 
  User, 
  HelpCircle, 
  Activity, 
  Sparkles, 
  RefreshCw, 
  ChevronDown, 
  ChevronUp, 
  Server, 
  Scale, 
  Clock,
  MessageSquarePlus,
  History,
  Trash2,
} from 'lucide-react'
import './App.css'
import MarkdownContent from './components/MarkdownContent'
import {
  generateUUID,
  loadActiveSessionId,
  saveActiveSessionId,
  getSession,
  upsertSession,
  deleteSession,
  listSessions,
  sessionTitleFromMessages,
  createEmptySession,
} from './utils/chatStorage'

function App() {
  const [messages, setMessages] = useState([])
  const [inputText, setInputText] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [serverUrl, setServerUrl] = useState('http://localhost:10100')
  const [contextId, setContextId] = useState(() => generateUUID())
  const [sessions, setSessions] = useState([])
  const [lastLatency, setLastLatency] = useState(null)
  const [currentThinkingStep, setCurrentThinkingStep] = useState(0)
  const [expandedTraceId, setExpandedTraceId] = useState(null)

  const messagesEndRef = useRef(null)
  const hydratedRef = useRef(false)

  // Khôi phục phiên chat từ localStorage
  useEffect(() => {
    const activeId = loadActiveSessionId()
    if (activeId) {
      const saved = getSession(activeId)
      if (saved) {
        setContextId(saved.contextId)
        setMessages(saved.messages || [])
      }
    }
    setSessions(listSessions())
    hydratedRef.current = true
  }, [])

  // Lưu lịch sử chat khi có thay đổi
  useEffect(() => {
    if (!hydratedRef.current) return
    const title = sessionTitleFromMessages(messages)
    upsertSession({ contextId, messages, title })
    saveActiveSessionId(contextId)
    setSessions(listSessions())
  }, [messages, contextId])

  // Tự động cuộn xuống cuối đoạn hội thoại
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isThinking])

  // Tiến trình suy nghĩ giả lập để mô tả quy trình A2A chạy thực tế dưới nền
  const thinkingSteps = [
    "Đang kết nối tới Registry (Port 10000) & xác định địa chỉ Customer Agent...",
    "Customer Agent đang ủy quyền cho Law Agent (Luật sư trưởng - Port 10101)...",
    "Law Agent đang phân tích khía cạnh pháp lý chung & xác định điều hướng chuyên gia...",
    "Đang gọi đồng thời các chuyên gia chuyên sâu (Thuế - Port 10102 & Tuân thủ - Port 10103) chạy song song...",
    "Các chuyên gia đã hoàn thành. Luật sư trưởng đang tổng hợp báo cáo pháp lý cuối cùng gửi khách hàng..."
  ]

  useEffect(() => {
    let interval;
    if (isThinking) {
      setCurrentThinkingStep(0)
      interval = setInterval(() => {
        setCurrentThinkingStep(prev => (prev < 4 ? prev + 1 : prev))
      }, 7000) // Cập nhật bước sau mỗi 7 giây
    } else {
      setCurrentThinkingStep(0)
    }
    return () => clearInterval(interval)
  }, [isThinking])

  // Câu hỏi mẫu tiếng Việt
  const samplePrompts = [
    {
      title: "Vi phạm Tổng hợp (A2A)",
      text: "Một startup vi phạm hợp đồng đám mây, trốn thuế doanh thu nước ngoài và chia sẻ dữ liệu người dùng không xin phép đối tác. Hậu quả pháp lý là gì?"
    },
    {
      title: "Vi phạm Hợp đồng & Thuế (EN)",
      text: "If a company breaks a contract and avoids taxes, what are the legal and regulatory consequences?"
    },
    {
      title: "Bảo mật & Tuân thủ Dữ liệu",
      text: "Một doanh nghiệp công nghệ muốn bảo vệ dữ liệu người dùng ở EU (GDPR) và Mỹ (CCPA) cần tuân thủ những quy định pháp lý gì?"
    }
  ]

  const handleSendMessage = async (textToSend) => {
    if (!textToSend.trim() || isThinking) return

    const userMessage = {
      id: generateUUID(),
      role: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    setMessages(prev => [...prev, userMessage])
    setInputText('')
    setIsThinking(true)
    setLastLatency(null)

    const startTime = performance.now()

    // Cấu trúc gói tin A2A JSON-RPC tiêu chuẩn
    const requestPayload = {
      id: generateUUID(),
      jsonrpc: "2.0",
      method: "message/send",
      params: {
        configuration: null,
        message: {
          contextId: contextId,
          extensions: null,
          kind: "message",
          messageId: generateUUID(),
          metadata: {
            trace_id: generateUUID(),
            delegation_depth: 0,
          },
          parts: [
            {
              kind: "text",
              metadata: null,
              text: textToSend
            }
          ],
          referenceTaskIds: null,
          role: "user",
          taskId: null
        },
        metadata: null
      }
    }

    try {
      const response = await fetch(`${serverUrl}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestPayload),
      })

      if (!response.ok) {
        throw new Error(`Máy chủ phản hồi mã trạng thái HTTP ${response.status}`)
      }

      const responseData = await response.json()
      const endTime = performance.now()
      const duration = ((endTime - startTime) / 1000).toFixed(2)
      setLastLatency(duration)

      const result = responseData.result
      if (!result) {
        throw new Error("Lỗi cấu trúc phản hồi: Không tìm thấy khóa 'result'.")
      }

      // Lưu trữ contextId để duy trì lịch sử hội thoại (memory)
      if (result.contextId) {
        setContextId(result.contextId)
      } else if (result.context_id) {
        setContextId(result.context_id)
      }

      // Trích xuất văn bản từ parts hoặc artifacts
      let text = ""
      if (result.parts && Array.isArray(result.parts)) {
        for (const part of result.parts) {
          const innerPart = part.root || part
          if (innerPart.text) text += innerPart.text
        }
      } else if (result.artifacts && Array.isArray(result.artifacts)) {
        for (const artifact of result.artifacts) {
          if (artifact.parts && Array.isArray(artifact.parts)) {
            for (const part of artifact.parts) {
              const innerPart = part.root || part
              if (innerPart.text) text += innerPart.text
            }
          }
        }
      }

      if (!text && result.status?.message?.parts) {
        for (const part of result.status.message.parts) {
          const innerPart = part.root || part
          if (innerPart.text) text += innerPart.text
        }
      }

      if (!text) {
        text = "Nhận phản hồi thành công nhưng không chứa dữ liệu văn bản. Vui lòng kiểm tra chi tiết luồng xử lý."
      }

      // Trích xuất các bước trung gian từ result.history (Trace phân tán)
      const trace = []
      const history = result.history || []
      
      history.forEach((msg) => {
        const metadata = msg.metadata || {}
        const depth = metadata.delegation_depth || 0
        
        if (depth > 0) {
          let msgText = ""
          const parts = msg.parts || []
          parts.forEach(p => {
            const inner = p.root || p
            if (inner.text) msgText += inner.text
          })

          if (msgText && msg.role === 'agent') {
            let name = "Luật sư Trưởng (Law Agent)"
            let type = "law"
            
            if (depth === 2) {
              const textLower = msgText.toLowerCase()
              if (textLower.includes("tax") || textLower.includes("thuế") || textLower.includes("irs") || textLower.includes("cpa")) {
                name = "Chuyên gia Thuế (Tax Agent)"
                type = "tax"
              } else {
                name = "Chuyên gia Tuân thủ (Compliance Agent)"
                type = "compliance"
              }
            }
            
            // Tránh thêm trùng lặp các tin nhắn trùng lặp
            const exists = trace.some(t => t.text.substring(0, 100) === msgText.substring(0, 100))
            if (!exists) {
              trace.push({ name, type, text: msgText })
            }
          }
        }
      })

      const botMessage = {
        id: generateUUID(),
        role: 'agent',
        text: text,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        trace: trace,
        latency: duration
      }

      setMessages(prev => [...prev, botMessage])

    } catch (err) {
      console.error(err)
      const botErrorMessage = {
        id: generateUUID(),
        role: 'agent',
        text: `**Lỗi:** Không thể kết nối tới Customer Agent tại \`${serverUrl}\`.\n\n*Chi tiết:* ${err.message}\n\n*Vui lòng đảm bảo rằng bạn đã khởi động toàn bộ dịch vụ (chạy lệnh \`uv run python start_all.py\`) trước khi thực hiện gửi câu hỏi.*`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isError: true
      }
      setMessages(prev => [...prev, botErrorMessage])
    } finally {
      setIsThinking(false)
    }
  }

  const handleNewChat = () => {
    if (isThinking) return
    const session = createEmptySession()
    setContextId(session.contextId)
    setMessages([])
    setLastLatency(null)
    setExpandedTraceId(null)
    saveActiveSessionId(session.contextId)
    setSessions(listSessions())
  }

  const handleSelectSession = (session) => {
    if (isThinking || session.contextId === contextId) return
    setContextId(session.contextId)
    setMessages(session.messages || [])
    setLastLatency(null)
    setExpandedTraceId(null)
    saveActiveSessionId(session.contextId)
  }

  const handleDeleteSession = (e, sessionId) => {
    e.stopPropagation()
    deleteSession(sessionId)
    const remaining = listSessions()
    setSessions(remaining)
    if (sessionId === contextId) {
      if (remaining.length > 0) {
        handleSelectSession(remaining[0])
      } else {
        handleNewChat()
      }
    }
  }

  return (
    <div className="app-container">
      {/* Sidebar: Trạng thái & Gợi ý */}
      <aside className="sidebar">
        <div className="brand-section">
          <div className="brand-logo">A2A</div>
          <div>
            <h1 className="brand-name">Mạng Pháp Lý</h1>
            <p className="brand-subtitle">Giao Thức A2A</p>
          </div>
        </div>

        {/* Trạng thái các dịch vụ agent trong hệ thống */}
        <div>
          <h2 className="section-title">
            <Server size={14} /> Trạng Thái Hệ Thống
          </h2>
          <div className="status-board">
            <div className="agent-status-item">
              <div className="agent-info">
                <span className="agent-name-text">Registry</span>
                <span className="agent-port">10000</span>
              </div>
              <span className="status-badge">
                <span className="status-dot active"></span> đang chạy
              </span>
            </div>
            <div className="agent-status-item">
              <div className="agent-info">
                <span className="agent-name-text">Customer Agent</span>
                <span className="agent-port">10100</span>
              </div>
              <span className="status-badge">
                <span className="status-dot active"></span> đang chạy
              </span>
            </div>
            <div className="agent-status-item">
              <div className="agent-info">
                <span className="agent-name-text">Law Agent</span>
                <span className="agent-port">10101</span>
              </div>
              <span className="status-badge">
                <span className="status-dot active"></span> đang chạy
              </span>
            </div>
            <div className="agent-status-item">
              <div className="agent-info">
                <span className="agent-name-text">Tax Agent</span>
                <span className="agent-port">10102</span>
              </div>
              <span className="status-badge">
                <span className="status-dot active"></span> đang chạy
              </span>
            </div>
            <div className="agent-status-item">
              <div className="agent-info">
                <span className="agent-name-text">Compliance Agent</span>
                <span className="agent-port">10103</span>
              </div>
              <span className="status-badge">
                <span className="status-dot active"></span> đang chạy
              </span>
            </div>
          </div>
        </div>

        {/* Lịch sử hội thoại */}
        <div>
          <div className="history-header">
            <h2 className="section-title" style={{ marginBottom: 0 }}>
              <History size={14} /> Lịch Sử Chat
            </h2>
            <button className="new-chat-btn" onClick={handleNewChat} disabled={isThinking}>
              <MessageSquarePlus size={14} />
              Mới
            </button>
          </div>
          <div className="history-list">
            {sessions.length === 0 ? (
              <p className="history-empty">Chưa có cuộc hội thoại. Bắt đầu hỏi để lưu lịch sử.</p>
            ) : (
              sessions.map((session) => (
                <div
                  key={session.contextId}
                  role="button"
                  tabIndex={0}
                  className={`history-item ${session.contextId === contextId ? 'active' : ''}`}
                  onClick={() => handleSelectSession(session)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      handleSelectSession(session)
                    }
                  }}
                >
                  <div className="history-item-main">
                    <span className="history-item-title">{session.title}</span>
                    <span className="history-item-meta">
                      {session.messages?.length || 0} tin •{' '}
                      {new Date(session.updatedAt).toLocaleDateString('vi-VN')}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="history-delete-btn"
                    onClick={(e) => handleDeleteSession(e, session.contextId)}
                    title="Xóa cuộc hội thoại"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Danh sách câu hỏi mẫu */}
        <div>
          <h2 className="section-title">
            <HelpCircle size={14} /> Câu Hỏi Pháp Lý Mẫu
          </h2>
          <div className="suggestions-list">
            {samplePrompts.map((p, idx) => (
              <button 
                key={idx} 
                className="suggestion-btn"
                onClick={() => setInputText(p.text)}
              >
                <strong>{p.title}</strong>
                <div style={{ fontSize: '11px', marginTop: '4px', opacity: 0.8 }}>
                  {p.text.substring(0, 75)}...
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Cấu hình kết nối */}
        <div className="config-section">
          <h2 className="section-title">
            <Activity size={14} /> Cấu Hình Kết Nối
          </h2>
          <label style={{ fontSize: '11px', color: 'hsl(var(--text-muted))', fontWeight: '500' }}>
            Địa chỉ Customer Agent
          </label>
          <input 
            type="text" 
            className="config-input" 
            value={serverUrl} 
            onChange={(e) => setServerUrl(e.target.value)} 
          />
          <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '10px', color: 'hsl(var(--text-muted))', fontFamily: 'monospace' }}>
              Phiên: {contextId.substring(0, 8)}...
            </span>
            <button 
              className="suggestion-btn" 
              style={{ padding: '6px 12px', fontSize: '11px', fontWeight: '600' }}
              onClick={handleNewChat}
              disabled={isThinking}
            >
              Cuộc Chat Mới
            </button>
          </div>
        </div>
      </aside>

      {/* Vùng Chat chính */}
      <main className="chat-area">
        {/* Header vùng Chat */}
        <header className="chat-header">
          <div className="header-title-container">
            <h1 className="header-title">Hệ Thống Trợ Lý Pháp Lý</h1>
            <div className="header-status">
              <span className="status-dot active"></span> 
              <span>Đã kết nối với Mạng lưới Agent (A2A Protocol)</span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {lastLatency && (
              <div className="latency-indicator" style={{ background: 'rgba(0,0,0,0.03)', padding: '6px 12px', borderRadius: '10px', border: '1px solid hsl(var(--border))', fontWeight: '600', color: 'hsl(var(--text-primary))' }}>
                <Clock size={12} style={{ marginRight: '4px', verticalAlign: 'middle', display: 'inline-block' }} /> 
                {lastLatency} giây
              </div>
            )}
            <div style={{ display: 'flex', gap: '4px', fontSize: '10px', background: 'rgba(16, 185, 129, 0.1)', color: '#047857', border: '1px solid rgba(16, 185, 129, 0.25)', padding: '4px 8px', borderRadius: '6px', fontWeight: 'bold' }}>
              <Sparkles size={10} /> Live Search
            </div>
          </div>
        </header>

        {/* Danh sách tin nhắn */}
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <Scale className="empty-icon" />
              <h2 className="empty-title">Tư Vấn Pháp Lý Trực Tuyến</h2>
              <p className="empty-desc">
                Chào mừng bạn đến với hệ thống Multi-Agent tư vấn pháp lý phân tán.
                Giao thức <strong>A2A (Agent-to-Agent)</strong> kết nối các chuyên gia
                (Thuế, Bảo mật, Tuân thủ) để phân tích toàn diện câu hỏi của bạn.
              </p>
              <p className="empty-desc" style={{ fontSize: '12px', color: 'hsl(var(--text-muted))' }}>
                Chọn một câu hỏi mẫu ở thanh bên trái hoặc nhập vấn đề pháp lý của bạn ở phía dưới để bắt đầu tư vấn.
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`message-bubble ${msg.role}`}>
                <span className="message-sender">
                  {msg.role === 'user' ? <User size={12} /> : <Bot size={12} />}
                  {msg.role === 'user' ? 'Khách Hàng' : 'Hệ Thống Trợ Lý Pháp Lý'}
                </span>
                <div className={`message-content ${msg.isError ? 'is-error' : ''}`}>
                  {msg.role === 'agent' ? (
                    <MarkdownContent content={msg.text} />
                  ) : (
                    msg.text
                  )}

                  {/* Chi tiết phản hồi từ các chuyên gia trung gian (Trace A2A) */}
                  {msg.trace && msg.trace.length > 0 && (
                    <div className="trace-dashboard">
                      <button 
                        className="trace-toggle"
                        onClick={() => setExpandedTraceId(expandedTraceId === msg.id ? null : msg.id)}
                      >
                        {expandedTraceId === msg.id ? (
                          <>Thu gọn chi tiết chuyên gia <ChevronUp size={12} /></>
                        ) : (
                          <>Xem phản hồi từ các chuyên gia chuyên môn ({msg.trace.length}) <ChevronDown size={12} /></>
                        )}
                      </button>

                      {expandedTraceId === msg.id && (
                        <div className="trace-steps">
                          <div className="trace-title">
                            <Activity size={12} /> Tiến Trình Xử Lý Phân Tán (A2A Trace)
                          </div>
                          {msg.trace.map((step, sIdx) => (
                            <div key={sIdx} className="trace-step active">
                              <div className="trace-step-node"></div>
                              <div className="trace-step-header">
                                <span className="trace-step-name">{step.name}</span>
                                <span className={`trace-step-badge ${step.type}`}>
                                  {step.type === 'law' ? 'luật' : step.type === 'tax' ? 'thuế' : 'tuân thủ'}
                                </span>
                              </div>
                              <div className="trace-step-body">
                                <MarkdownContent content={step.text} />
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
                <span className="message-time">
                  {msg.timestamp} {msg.latency && `(Thời gian xử lý: ${msg.latency}s)`}
                </span>
              </div>
            ))
          )}

          {/* Vòng lặp suy nghĩ / điều phối Agent */}
          {isThinking && (
            <div className="thinking-bubble">
              <span className="message-sender" style={{ color: '#7c3aed' }}>
                <RefreshCw size={12} className="spin-animation" style={{ animation: 'spin 2s linear infinite' }} />
                Hệ thống đang điều phối...
              </span>
              <div className="thinking-content">
                <div className="dot-flashing"></div>
                <div style={{ marginLeft: '12px' }}>
                  <strong>Đang xử lý phân tán dưới nền...</strong>
                  <div className="thinking-steps">
                    {thinkingSteps.map((stepText, idx) => (
                      <div key={idx} className={`thinking-step ${idx === currentThinkingStep ? 'active' : ''}`}>
                        <div className={`thinking-step-dot ${idx === currentThinkingStep ? 'active' : ''}`}></div>
                        <span className="thinking-step-text">{stepText}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Thanh nhập dữ liệu câu hỏi */}
        <footer className="input-container">
          <div className="input-row">
            <textarea
              className="chat-input"
              placeholder="Nhập câu hỏi pháp lý của bạn ở đây..."
              value={inputText}
              rows={1}
              onChange={(e) => {
                setInputText(e.target.value)
                e.target.style.height = 'auto'
                e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSendMessage(inputText)
                }
              }}
              disabled={isThinking}
            />
            <button
              className="send-btn"
              onClick={() => handleSendMessage(inputText)}
              disabled={isThinking || !inputText.trim()}
            >
              <Send size={18} />
            </button>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0 8px' }}>
            <span style={{ fontSize: '10px', color: 'hsl(var(--text-muted))' }}>
              A2A v1.0 • Memory: {messages.length} tin nhắn • Phiên {contextId.substring(0, 8)}
            </span>
            <span style={{ fontSize: '10px', color: 'hsl(var(--text-muted))' }}>
              Kết quả mang tính chất tham khảo học thuật và giáo dục
            </span>
          </div>
        </footer>
      </main>
      
      {/* CSS Keyframe bổ sung cho biểu tượng xoay */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

export default App

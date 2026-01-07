import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { chatStream, chat } from '../api'

type Turn = {
  role: 'user' | 'assistant'
  text: string
  sources?: { source: string; snippet: string }[]
  agentic?: boolean
  reasoning_log?: Array<{ phase: string; details: string; duration: string }>
}

function ReasoningLog({ steps }: { steps: Array<{ phase: string; details: string; duration: string }> }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="source" style={{ marginTop: 12 }}>
      <button
        className="btn"
        style={{ background: '#0969da', color: '#ffffff', fontSize: '12px', padding: '6px 12px' }}
        onClick={() => setOpen(!open)}
      >
        {open ? 'Hide reasoning' : 'Show reasoning'}
      </button>
      {open && (
        <div style={{ 
          marginTop: 12, 
          padding: 12, 
          background: '#f6f8fa', 
          borderRadius: 8,
          border: '1px solid #d0d7de'
        }}>
          {steps.map((step, i) => (
            <div key={i} style={{ 
              marginBottom: 12,
              paddingBottom: 12,
              borderBottom: i < steps.length - 1 ? '1px solid #d0d7de' : 'none'
            }}>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginBottom: 4
              }}>
                <strong style={{ color: '#0969da', fontSize: '13px' }}>{step.phase}</strong>
                <span style={{ 
                  color: '#57606a', 
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  background: '#ffffff',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  border: '1px solid #d0d7de'
                }}>
                  {step.duration}
                </span>
              </div>
              <div style={{ 
                color: '#1f2328',
                lineHeight: '1.6',
                fontSize: '13px',
                paddingLeft: 8
              }}>
                {step.details}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function SourcesList({ sources }: { sources: { source: string; snippet: string }[] }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="source" style={{ marginTop: 12 }}>
      <button
        className="btn"
        style={{ background: '#6e7781', color: '#ffffff', fontSize: '12px', padding: '6px 12px' }}
        onClick={() => setOpen(!open)}
      >
        {open ? 'Hide sources' : `Show sources (${sources.length})`}
      </button>
      {open && (
        <div style={{ 
          marginTop: 12, 
          padding: 12, 
          background: '#f6f8fa', 
          borderRadius: 8,
          border: '1px solid #d0d7de'
        }}>
          {sources.map((s, j) => (
            <div key={j} style={{ marginBottom: 8, color: '#1f2328', fontSize: '14px' }}>
              <strong style={{ color: '#0969da' }}>• {s.source}</strong>
              <div style={{ marginTop: 4, color: '#57606a', paddingLeft: 12 }}>
                {s.snippet}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function ChatStream() {
  const [q, setQ] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [loading, setLoading] = useState(false)

  const samplePrompts = [
    "What are the pricing plans for the Enterprise Cloud Platform?",
    "What are the key features of the collaboration suite?",
    "What support and training options are provided?",
    "What is the company vacation policy?",
    "How do I submit an expense report?",
    "What are the requirements for remote work?",
    "What is the process for requesting time off?",
    "What are the company's core values?"
  ]

  async function send() {
    const prompt = q.trim()
    if (!prompt) return
    setTurns(prev => [...prev, { role: 'user', text: prompt }])
    setQ('')
    setLoading(true)

    try {
      // Fetch complete response from /chat (which includes answer, sources, and reasoning)
      const result = await chat(prompt, 5)
      setTurns(prev => [...prev, {
        role: 'assistant',
        text: result.answer,
        sources: result.sources,
        agentic: result.agentic,
        reasoning_log: result.reasoning_log
      }])
    } catch (error) {
      console.error('Chat error:', error)
      setTurns(prev => [...prev, {
        role: 'assistant',
        text: 'Error: Failed to get response',
        sources: [],
        agentic: false
      }])
    } finally {
      setLoading(false)
    }
  }

  const handlePromptClick = (prompt: string) => {
    setQ(prompt)
  }

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '100%', flex: 1, maxWidth: '1200px', margin: '0 auto', minHeight: 0 }}>
      <div style={{ 
        padding: '12px 16px', 
        borderBottom: '1px solid #d0d7de',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        borderRadius: '12px 12px 0 0',
        flexShrink: 0
      }}>
        <h3 style={{ margin: 0, color: '#ffffff', fontSize: '16px', fontWeight: 600 }}>💬 Chat with your documents</h3>
        <p style={{ margin: '2px 0 0 0', color: '#e6e6ff', fontSize: '12px' }}>Ask questions about your uploaded documents</p>
      </div>
      
      <div className="chat-scroll-container" style={{ padding: '20px' }}>
        {/* Sample prompts - always visible */}
        <div style={{ marginBottom: turns.length > 0 ? '20px' : '0', paddingBottom: turns.length > 0 ? '20px' : '0', borderBottom: turns.length > 0 ? '2px solid #e6e6e6' : 'none' }}>
          {turns.length === 0 && (
            <div style={{ textAlign: 'center', marginBottom: '16px' }}>
              <div style={{ fontSize: '32px', marginBottom: 8 }}>🚀</div>
              <h4 style={{ margin: '0 0 4px 0', color: '#1f2328', fontSize: '18px' }}>Get started with these questions</h4>
              <p style={{ margin: '0 0 12px 0', color: '#57606a', fontSize: '14px' }}>Click on any question below or type your own</p>
            </div>
          )}
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', 
            gap: 8,
            maxWidth: '900px',
            margin: '0 auto'
          }}>
            {samplePrompts.map((prompt, i) => (
              <button
                key={i}
                onClick={() => handlePromptClick(prompt)}
                style={{
                  padding: turns.length > 0 ? '12px' : '16px',
                  background: '#ffffff',
                  border: '2px solid #d0d7de',
                  borderRadius: 12,
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: turns.length > 0 ? '13px' : '14px',
                  color: '#1f2328',
                  transition: 'all 0.2s',
                  fontFamily: 'inherit'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#667eea'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.15)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#d0d7de'
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = 'none'
                }}
              >
                💡 {prompt}
              </button>
            ))}
          </div>
        </div>

        {/* Conversation messages */}
        {turns.length === 0 ? null : (
          <div>
        
        {turns.map((t, i) => (
          <div key={i} style={{
            background: t.role === 'user' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#ffffff',
            border: t.role === 'user' ? 'none' : '1px solid #d0d7de',
            borderRadius: 12,
            padding: 14,
            marginBottom: 12,
            textAlign: 'left',
            boxShadow: t.role === 'assistant' ? '0 2px 8px rgba(0,0,0,0.05)' : 'none'
          }}>
            <strong style={{ 
              color: t.role === 'user' ? '#ffffff' : '#667eea',
              fontSize: '12px',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              {t.role === 'user' ? '👤 You' : '🤖 Assistant'}
            </strong>
            {t.role === 'user' ? (
              <div style={{ 
                marginTop: 8, 
                whiteSpace: 'pre-wrap', 
                color: '#ffffff',
                lineHeight: '1.6',
                fontSize: '14px'
              }}>
                {t.text}
              </div>
            ) : (
              <div style={{ 
                marginTop: 8, 
                color: '#1f2328',
                lineHeight: '1.6',
                fontSize: '14px'
              }}>
                <ReactMarkdown
                  components={{
                    p: ({node, ...props}) => <p style={{margin: '0.5em 0'}} {...props} />,
                    ul: ({node, ...props}) => <ul style={{margin: '0.5em 0', paddingLeft: '1.5em'}} {...props} />,
                    ol: ({node, ...props}) => <ol style={{margin: '0.5em 0', paddingLeft: '1.5em'}} {...props} />,
                    li: ({node, ...props}) => <li style={{margin: '0.25em 0'}} {...props} />,
                    strong: ({node, ...props}) => <strong style={{fontWeight: 700, color: '#667eea'}} {...props} />,
                    em: ({node, ...props}) => <em style={{fontStyle: 'italic'}} {...props} />,
                    code: ({node, ...props}) => <code style={{background: '#f6f8fa', padding: '2px 6px', borderRadius: '3px', fontSize: '0.9em'}} {...props} />,
                  }}
                >
                  {t.text}
                </ReactMarkdown>
              </div>
            )}

            {t.agentic !== undefined && t.role === 'assistant' && (
              <div style={{ 
                marginTop: 12,
                display: 'inline-block',
                padding: '6px 12px',
                background: t.agentic ? '#d1fae5' : '#e5e7eb',
                color: t.agentic ? '#065f46' : '#374151',
                borderRadius: 20,
                fontSize: '12px',
                fontWeight: 600
              }}>
                {t.agentic ? '✅ Grounded answer' : '⚠️ Ungrounded'}
              </div>
            )}

            {t.reasoning_log && t.reasoning_log.length > 0 && (
              <ReasoningLog steps={t.reasoning_log} />
            )}

            {t.sources && t.sources.length > 0 && (
              <SourcesList sources={t.sources} />
            )}
          </div>
        ))}
          </div>
        )}
      </div>

      <div style={{ 
        borderTop: '2px solid #d0d7de', 
        padding: '12px 16px',
        background: '#f6f8fa',
        flexShrink: 0
      }}>
        <div style={{ display: 'flex', gap: 10, maxWidth: '100%' }}>
          <input
            className="input"
            style={{ 
              flex: 1,
              padding: '10px 14px',
              fontSize: '14px',
              borderRadius: 20,
              border: '2px solid #d0d7de',
              outline: 'none',
              transition: 'border-color 0.2s'
            }}
            value={q}
            placeholder="Ask anything about your documents..."
            onChange={e => setQ(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !loading && send()}
            onFocus={(e) => e.currentTarget.style.borderColor = '#667eea'}
            onBlur={(e) => e.currentTarget.style.borderColor = '#d0d7de'}
          />
          <button 
            className="btn" 
            disabled={!q.trim() || loading} 
            onClick={send}
            style={{
              padding: '10px 24px',
              borderRadius: 20,
              background: loading ? '#9ca3af' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: '#ffffff',
              border: 'none',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: 600,
              transition: 'all 0.2s',
              minWidth: '90px'
            }}
          >
            {loading ? '⏳ Thinking...' : '🚀 Ask'}
          </button>
        </div>
      </div>
    </div>
  )
}

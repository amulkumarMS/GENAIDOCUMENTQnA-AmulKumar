import React, { useState } from 'react'
import { chat } from '../api'

type Turn = {
  role: 'user' | 'assistant'
  text: string
  sources?: { source: string; snippet: string }[]
  agentic?: boolean
  reasoning_log?: string[]
}

function ReasoningLog({ steps }: { steps: string[] }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="source">
      <button
        className="btn"
        style={{ background: '#172039', color: '#9db0d0', fontSize: '12px', padding: '6px 10px' }}
        onClick={() => setOpen(!open)}
      >
        {open ? 'Hide reasoning' : 'Show reasoning'}
      </button>
      {open && (
        <ol style={{ marginTop: 8 }}>
          {steps.map((s, i) => (<li key={i}>{s}</li>))}
        </ol>
      )}
    </div>
  )
}

export default function Chat() {
  const [q, setQ] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [loading, setLoading] = useState(false)

  async function send() {
    const prompt = q.trim()
    if (!prompt) return
    setTurns(prev => [...prev, { role: 'user', text: prompt }])
    setQ('')
    setLoading(true)
    try {
      const res = await chat(prompt, 5)
      setTurns(prev => [
        ...prev,
        {
          role: 'assistant',
          text: res.answer,
          sources: res.sources,
          agentic: res.agentic,
          reasoning_log: res.reasoning_log
        }
      ])
    } catch (e: any) {
      setTurns(prev => [...prev, { role: 'assistant', text: `Error: ${e.message}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <h3>Chat with your documents</h3>
      <div className="row">
        <input
          className="input"
          value={q}
          placeholder="Ask anything…"
          onChange={e => setQ(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !loading && send()}
        />
        <button className="btn" disabled={!q.trim() || loading} onClick={send}>
          {loading ? 'Thinking…' : 'Ask'}
        </button>
      </div>

      <div style={{ marginTop: 16, maxHeight: '60vh', overflowY: 'auto' }}>
        {turns.map((t, i) => (
          <div key={i} style={{
            background: t.role === 'user' ? '#0e1526' : '#0b1424',
            border: '1px solid #263255', borderRadius: 12, padding: 12, marginBottom: 12,
            textAlign: t.role === 'user' ? 'right' : 'left'
          }}>
            <strong style={{ color: '#9db0d0' }}>{t.role === 'user' ? 'You' : 'Assistant'}</strong>
            <div style={{ marginTop: 6, whiteSpace: 'pre-wrap' }}>{t.text}</div>

            {t.agentic !== undefined && t.role === 'assistant' && (
              <div className="badge">
                {t.agentic ? 'Grounded answer ✅' : 'Ungrounded ⚠️'}
              </div>
            )}

            {t.reasoning_log && t.reasoning_log.length > 0 && (
              <ReasoningLog steps={t.reasoning_log} />
            )}

            {t.sources && t.sources.length > 0 && (
              <div className="source">
                <strong>Sources:</strong>
                {t.sources.map((s, j) => (
                  <div key={j}>• {s.source}: {s.snippet}</div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

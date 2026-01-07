import React, { useEffect, useState } from 'react'
import Upload from './components/Upload'
import Process from './components/Process'
import ChatStream from './components/ChatStream'
import { health, listFiles } from './api'

export default function App() {
  const [files, setFiles] = useState<string[]>([])
  const [ok, setOk] = useState(false)

  const loadFiles = async () => {
    try {
      const res = await listFiles()
      setFiles(res.files.map((f: any) => f.name))
    } catch (e) {
      console.error('Failed to load files:', e)
    }
  }

  useEffect(() => {
    health().then(() => setOk(true)).catch(() => setOk(false))
    loadFiles()
    // Refresh file list every 2 seconds to stay in sync
    const interval = setInterval(loadFiles, 2000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="container">
      <header style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
        <div style={{ fontSize: 48 }}>🤖</div>
        <div>
          <h1 style={{ margin: 0 }}>DocuMind AI</h1>
          <p style={{ margin: 0, fontSize: 14, color: 'var(--muted)' }}>AI-powered document intelligence</p>
        </div>
      </header>
      <div style={{ display: 'grid', gridTemplateColumns: '350px 1fr', gap: '20px', flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {/* Left sidebar - Upload and Process stacked */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
          <Upload onUploaded={loadFiles} uploadedCount={files.length} />
          <Process files={files} />
        </div>
        {/* Right side - Chat taking full height */}
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <ChatStream />
        </div>
      </div>
    </div>
  )
}

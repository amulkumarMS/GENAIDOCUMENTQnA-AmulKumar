import React, { useState } from 'react'
import { processBlob } from '../api'

export default function Process({ files }: { files: string[] }) {
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)

  const processAll = async () => {
    setLoading(true)
    setStatus(`Processing ${files.length} file(s)...`)
    let totalChunks = 0
    
    for (const file of files) {
      try {
        const res = await processBlob(file)
        totalChunks += res.chunks || 0
        setStatus(`Processing... ${file} (${res.chunks} chunks)`)
      } catch (e: any) {
        setStatus(`Error processing ${file}: ${e.message}`)
        setLoading(false)
        return
      }
    }
    
    setStatus(`✓ Indexed ${totalChunks} chunks from ${files.length} file(s)`)
    setLoading(false)
  }

  return (
    <div className="card" style={{ padding: '16px' }}>
      <h3 style={{ fontSize: '16px', marginBottom: '8px' }}>Index documents</h3>
      <p className="badge" style={{ fontSize: '11px', padding: '4px 10px' }}>Azure AI Search • {files.length} file(s) ready</p>
      {files.length > 0 && (
        <div style={{ marginBottom: 8, fontSize: 12, color: 'var(--muted)' }}>
          Files: {files.join(', ')}
        </div>
      )}
      <div className="row" style={{ gap: '8px' }}>
        <button
          className="btn"
          style={{ padding: '8px 16px', fontSize: '13px' }}
          disabled={files.length === 0 || loading}
          onClick={processAll}
        >
          Start indexing
        </button>
        <span style={{ fontSize: '12px' }}>{status}</span>
      </div>
      <p style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '8px', marginBottom: 0 }}>
        Tip: Creates embeddings and indexes documents
      </p>
    </div>
  )
}

import React, { useState } from 'react'
import { uploadFile } from '../api'

export default function Upload({ onUploaded, uploadedCount }: { onUploaded: () => void, uploadedCount: number }) {
  const [files, setFiles] = useState<FileList | null>(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')

  return (
    <div className="card" style={{ padding: '16px' }}>
      <h3 style={{ fontSize: '16px', marginBottom: '8px' }}>Upload documents</h3>
      <p className="badge" style={{ fontSize: '11px', padding: '4px 10px' }}>PDF, DOCX, TXT, MD • {uploadedCount} uploaded</p>
      <div style={{ marginBottom: '12px' }}>
        <input 
          className="input" 
          style={{ padding: '8px 12px', fontSize: '13px', maxWidth: '350px' }}
          type="file" 
          multiple 
          accept=".pdf,.docx,.txt,.md" 
          onChange={(e) => setFiles(e.target.files)} 
        />
      </div>
      <div className="row" style={{ gap: '8px' }}>
        <button
          className="btn"
          style={{ padding: '8px 16px', fontSize: '13px' }}
          disabled={!files || files.length === 0 || loading}
          onClick={async () => {
            setLoading(true); setStatus(`Uploading ${files!.length} file(s)…`)
            try {
              const res = await uploadFile(files!)
              const fileNames = res.files.map((f: any) => f.name).join(', ')
              setStatus(`Uploaded: ${fileNames}`)
              onUploaded()
            } catch (e: any) {
              setStatus(`Error: ${e.message}`)
            } finally {
              setLoading(false)
            }
          }}
        >
          Upload
        </button>
        <span style={{ fontSize: '12px' }}>{status}</span>
      </div>
    </div>
  )
}

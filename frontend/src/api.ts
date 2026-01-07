import axios from 'axios'
const BASE = 'http://localhost:8000'

export async function uploadFile(files: FileList) {
  const form = new FormData()
  for (let i = 0; i < files.length; i++) {
    form.append('files', files[i])
  }
  const res = await axios.post(`${BASE}/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return res.data
}

export async function processBlob(blob: string) {
  const res = await axios.post(`${BASE}/process`, null, { params: { blob } })
  return res.data
}

export async function chat(query: string, top_k = 5) {
  const res = await axios.post(`${BASE}/chat`, { query, top_k })
  return res.data
}

export async function chatStream(query: string, top_k = 5) {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k })
  })
  return res
}

export async function health() {
  const res = await axios.get(`${BASE}/health`)
  return res.data
}

export async function listFiles() {
  const res = await axios.get(`${BASE}/files`)
  return res.data
}

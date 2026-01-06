# DocuMind AI - Technical Documentation

## Detailed Workflow and Architecture

This document provides an in-depth explanation of the backend and frontend workflows, architectural decisions, and implementation details.

---

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Backend Workflow](#backend-workflow)
3. [Frontend Workflow](#frontend-workflow)
4. [Data Flow](#data-flow)
5. [Component Details](#component-details)
6. [Azure Services Integration](#azure-services-integration)
7. [Error Handling and Logging](#error-handling-and-logging)
8. [Performance Optimizations](#performance-optimizations)

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                             │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    React Frontend                          │  │
│  │  (TypeScript + Vite - Port 5174)                          │  │
│  │                                                            │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │  │
│  │  │ Upload   │  │ Process  │  │   ChatStream         │   │  │
│  │  │ Component│  │Component │  │   Component          │   │  │
│  │  └──────────┘  └──────────┘  └──────────────────────┘   │  │
│  │                                                            │  │
│  │                    API Client (api.ts)                    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP/REST
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│                  (Python 3.14 - Port 8000)                       │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Endpoints                             │    │
│  │  • POST /upload      • POST /chat                        │    │
│  │  • GET  /files       • POST /chat/stream                │    │
│  │  • POST /process     • GET  /health                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  RAG Pipeline (rag_pipeline.py)          │    │
│  │  1. Document Loading (PyPDF, simple text loading)       │    │
│  │  2. Text Splitting (RecursiveCharacterTextSplitter)     │    │
│  │  3. Embedding Generation (Azure OpenAI)                 │    │
│  │  4. Hybrid Search (Azure AI Search)                     │    │
│  │  5. Response Generation (GPT-4o)                        │    │
│  │  6. Grounding Evaluation (Azure AI Evaluation 0-5)      │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────┬──────────────┬──────────────┬───────────────────┘
                │              │              │
                ▼              ▼              ▼
    ┌─────────────────┐ ┌────────────┐ ┌─────────────────┐
    │  Azure Blob     │ │ Azure AI   │ │ Azure AI        │
    │  Storage        │ │ Search     │ │ Foundry         │
    │                 │ │            │ │                 │
    │ • documents/    │ │ • Vector   │ │ • gpt-4o        │
    │   container     │ │   Index    │ │ • embeddings    │
    └─────────────────┘ │ • Hybrid   │ └─────────────────┘
                        │   Search   │
                        └────────────┘
```

---

## Modular Architecture

### Backend Components

The backend is organized into three main modules:

**1. `main.py` - FastAPI Endpoints and Orchestration**
- Defines all REST API endpoints
- Handles CORS configuration
- Initializes dependencies (blob manager, document processor, RAG pipeline)
- Routes requests to appropriate modules

**2. `rag_pipeline.py` - RAG Pipeline Class**
- Encapsulates the entire RAG workflow
- Manages Azure OpenAI clients (chat, embeddings)
- Handles vector store operations
- Implements grounding evaluation
- Methods:
  - `chat()` - Complete RAG flow with grounding
  - `stream_chat()` - Streaming responses
  - `_search()` - Hybrid search with fallback
  - `_calculate_grounding_score()` - Azure AI Evaluation or heuristics
  - `_build_context()` - Format retrieved chunks
  - `_dedupe_sources()` - Merge chunks by source

**3. `document_utils.py` - Document Processing Utilities**
- `AzureBlobDocumentManager` - Blob storage operations
  - Upload, download, list, delete files
- `DocumentProcessor` - Document loading and chunking
  - Multi-format support (PDF, TXT, MD, DOCX)
  - RecursiveCharacterTextSplitter integration
  - Metadata management

**Benefits of Modular Architecture:**
- **Separation of Concerns**: Each module has a single responsibility
- **Testability**: Easy to unit test individual components
- **Reusability**: RAGPipeline can be used in different contexts
- **Maintainability**: Changes to one component don't affect others
- **Scalability**: Easy to add new document types or evaluation methods

---

### 1. Application Initialization


**File:** `backend/main.py`

```python
# Application starts via start.ps1
# Uvicorn loads FastAPI app with auto-reload
# Environment variables loaded from .env
```

**Startup Sequence:**
1. Load environment variables (`.env` file)
2. Initialize Azure Blob Storage and Document Processor:
   - `AzureBlobDocumentManager` for blob operations
   - `DocumentProcessor` for chunking documents
3. Initialize RAG Pipeline (`RAGPipeline` class):
   - `AzureChatOpenAI` for GPT-4o chat completions
   - `AzureOpenAIEmbeddings` for text-embedding-3-large
   - `AzureSearch` vector store for hybrid search
   - `GroundednessEvaluator` for grounding scores (0-5 scale)
4. Load external prompt template from `prompt_instructions.txt`
5. Start FastAPI server on `127.0.0.1:8000`

**Key Configuration:**
```python
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_CHAT_DEPLOYMENT = "gpt-4o"
AZURE_OPENAI_EMBED_DEPLOYMENT = "text-embedding-3-large"
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX = "capstone-search-index"
AZURE_BLOB_CONN_STRING = os.getenv("AZURE_BLOB_CONN_STRING")
AZURE_BLOB_CONTAINER = "documents"
```

---

### 2. Document Upload Workflow

**Endpoint:** `POST /upload`

**Flow:**
```
User selects files → Frontend calls uploadFile() → POST /upload
                                                         ↓
                                      Validate file types (.pdf, .docx, .txt, .md)
                                                         ↓
                                      For each file:
                                        - Get blob client from Azure Blob Storage
                                        - Upload file bytes to container "documents"
                                        - Store with original filename
                                                         ↓
                                      Return list of uploaded files with URLs
```

**Code Flow:**
```python
@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    # 1. Get blob container client
    blob_service = BlobServiceClient.from_connection_string(AZURE_BLOB_CONN_STRING)
    container_client = blob_service.get_container_client(AZURE_BLOB_CONTAINER)
    
    # 2. Upload each file to Blob Storage
    uploaded = []
    for file in files:
        blob_client = container_client.get_blob_client(file.filename)
        content = await file.read()
        blob_client.upload_blob(content, overwrite=True)
        uploaded.append({
            "name": file.filename,
            "url": blob_client.url
        })
    
    # 3. Return uploaded file metadata
    return {"files": uploaded}
```

**Error Handling:**
- Invalid file types rejected
- Blob upload failures caught and returned as HTTP 500
- Duplicate filenames overwritten with `overwrite=True`

---

### 3. Document Processing Workflow

**Endpoint:** `POST /process`

**Flow:**
```
User clicks "Process All" → Frontend iterates files → POST /process (per file)
                                                              ↓
                                        Download file from Azure Blob Storage
                                                              ↓
                                        Save temporarily to local disk
                                                              ↓
                                        Load document based on file extension:
                                          • .pdf → PyPDFLoader
                                          • .txt/.md → Simple text loading (direct file read)
                                          • .docx → UnstructuredFileLoader
                                                              ↓
                                        Split text into chunks:
                                          • RecursiveCharacterTextSplitter
                                          • chunk_size=2000, overlap=200
                                          • No mode="elements" for markdown
                                                              ↓
                                        Generate embeddings for each chunk:
                                          • Azure OpenAI text-embedding-3-large
                                                              ↓
                                        Index chunks to Azure AI Search:
                                          • Hybrid search enabled
                                          • Vector + keyword indexing
                                                              ↓
                                        Return chunk count and preview
```

**Code Flow:**
```python
@app.post("/process")
async def process_blob(req: ProcessRequest):
    # 1. Download file from Blob Storage
    blob_client = container_client.get_blob_client(req.blob_name)
    download_stream = blob_client.download_blob()
    local_path = f"temp_{req.blob_name}"
    with open(local_path, "wb") as f:
        f.write(download_stream.readall())
    
    # 2. Load document based on file type
    if req.blob_name.endswith(".pdf"):
        loader = PyPDFLoader(local_path)
        docs = loader.load()
    elif req.blob_name.endswith((".txt", ".md")):
        # Simple text loading - no external dependencies needed
        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()
        docs = [Document(page_content=content, metadata={"source": req.blob_name})]
    elif req.blob_name.endswith(".docx"):
        loader = UnstructuredFileLoader(local_path)
        docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,        # Larger chunks preserve context
        chunk_overlap=200       # Overlap prevents splitting related content
    )
    chunks = text_splitter.split_documents(docs)
    
    # 4. Add metadata to chunks (including page number)
    for i, chunk in enumerate(chunks):
        chunk.metadata["source"] = req.blob_name
        if "page" not in chunk.metadata:
            chunk.metadata["page"] = i  # Required by Azure AI Search index
    
    # 5. Index to Azure AI Search with embeddings
    vectorstore = get_vectorstore()  # AzureSearch instance
    vectorstore.add_documents(chunks)  # Auto-generates embeddings
    
    # 6. Cleanup and return
    os.remove(local_path)
    return {
        "chunks": len(chunks),
        "chunks_indexed": len(chunks),
        "preview": chunks[0].page_content[:200] if chunks else ""
    }
```

**Key Design Decisions:**

1. **Why 2000-char chunks?**
   - Smaller chunks (1200) were splitting related content
   - Example: Vacation policy header separated from actual days
2. **Why simple text loading for .txt and .md?**
   - UnstructuredFileLoader requires additional dependencies (unstructured package)
   - Simple text reading is faster and more reliable
   - Markdown and text files are already clean and structured
   - RecursiveCharacterTextSplitter handles chunking effectively

3. **Why RecursiveCharacterTextSplitter?**gether

3. **Why RecursiveCharacterTextSplitter?**
   - Splits on paragraph boundaries first, then sentences
   - Preserves semantic meaning better than fixed-length splitting
   - Overlap ensures context isn't lost at boundaries

**Logging:**
```python
print(f"✅ Loaded {len(docs)} documents")
print(f"✅ Split into {len(chunks)} chunks")
print(f"Preview of first chunk:\n{chunks[0].page_content[:200]}")
```

---

### 4. Chat Query Workflow

**Endpoint:** `POST /chat`

**Flow:**
```
User types question → POST /chat with query and top_k
                              ↓
                    Hybrid search in Azure AI Search (via RAGPipeline)
                      • Vector similarity (semantic)
                      • Keyword matching (lexical)
                      • Returns top 5 chunks
                              ↓
                    Build context from retrieved chunks
                              ↓
                    Load prompt template from file
                      • prompt_instructions.txt
                      • Inject context and question
                              ↓
                    Call Azure OpenAI GPT-4o
                      • Generate answer using context
                      • No temperature parameter (default=1)
                              ↓
                    Grounding evaluation (Azure AI Evaluation)
                      • GroundednessEvaluator analyzes answer vs context
                      • Returns score 0-5 (5 = fully grounded)
                      • Falls back to heuristics if Azure eval fails
                              ↓
                    Build reasoning log
                      • Phase 1: Retrieval (5 docs found, duration)
                      • Phase 2: Generation (model, context size, duration)
                      • Phase 3: Grounding (score X.X/5.0, status)
                      • Phase 4: Total (end-to-end time)
                              ↓
                    Return response with:
                      • answer: Generated text
                      • sources: Retrieved chunks
                      • grounding_score: 0-5 scale
                      • reasoning_log: Process steps with timings
                      • agentic: true if score >= 3.0
```

**Code Flow (Modular Architecture):**
```python
@app.post("/chat")
def chat(req: ChatRequest):
    # Delegate to RAG pipeline class
    return rag_pipeline.chat(req.query, req.top_k)

# In RAGPipeline class (rag_pipeline.py):
def chat(self, query: str, top_k: int):
    # 1. Retrieve relevant documents (hybrid search)
    start = time.time()
    docs = self._search(query, top_k)
    search_time = time.time() - start
    
    # 2. Build context from retrieved documents
    context = self._build_context(docs)
    
    # 3. Format prompt with context and question
    prompt_text = self.prompt_template.format(
        context=context,
        question=query
    )
    
    # 4. Generate answer using GPT-4o
    llm_start = time.time()
    answer = self.llm.invoke(prompt_text).content
    llm_time = time.time() - llm_start
    
    # 5. Deduplicate sources by filename
    sources = self._dedupe_sources(docs)
    
    # 6. Calculate grounding score (0-5 scale)
    grounding_score = self._calculate_grounding_score(answer, context)
    is_grounded = grounding_score >= 3.0
    
    # 7. Build reasoning log with timings
    total_time = time.time() - start
    reasoning_log = [
        {
            "phase": "Retrieval",
            "details": f"Retrieved {len(docs)} documents using hybrid search",
            "duration": f"{search_time:.2f}s"
        },
        {
            "phase": "Generation",
            "details": f"Model: {self.chat_deployment} | Context size: {len(context)} chars",
            "duration": f"{llm_time:.2f}s"
        },
        {
            "phase": "Grounding",
            "details": f"Score: {grounding_score:.1f}/5.0 | {'Fully grounded' if is_grounded else 'Partially grounded'}",
            "duration": "N/A"
        },
        {
            "phase": "Total",
            "details": "End-to-end response time",
            "duration": f"{total_time:.2f}s"
        }
    ]
    
    # 8. Return complete response
    return {
        "answer": answer,
        "sources": sources,
        "agentic": is_grounded,
        "grounding_score": grounding_score,
        "reasoning_log": reasoning_log
    }
```

**Hybrid Search Explanation:**

Azure AI Search hybrid search combines:
1. **Vector Search** (Semantic):
  - Converts query to embedding using text-embedding-3-large
   - Finds documents with similar vector representations
   - Great for semantic similarity ("vacation days" matches "time off")

2. **Keyword Search** (Lexical):
   - Traditional BM25 algorithm
   - Exact term matching and proximity
  - Great for specific terms ("15 days", "gpt-4o")

3. **Fusion**:
   - Reciprocal Rank Fusion (RRF) combines scores
   - Results ranked by combined relevance
   - Best of both worlds

**Grounding Evaluation:**

The system uses **Azure AI Evaluation** with the `GroundednessEvaluator` to score how well answers are grounded in the retrieved context:

**Primary Method (Azure AI Evaluation):**
- Uses an LLM to semantically analyze the answer against the context
- Returns a score from 0-5 where:
  - **5**: Fully grounded - all information comes from context
  - **4**: Mostly grounded - minor inferences but based on context
  - **3**: Partially grounded - some context-based, some missing
  - **2**: Minimally grounded - little connection to context
  - **1**: Not grounded - answer doesn't align with context
  - **0**: Completely ungrounded
- Score >= 3.0 is considered "grounded"

**Fallback Heuristics (if Azure eval fails):**
```python
# Remove ungrounded phrases and measure meaningful content
if meaningful_content > 200 chars and no ungrounded phrases:
    return 5.0  # Fully grounded
elif meaningful_content > 200 chars:
    return 3.5  # Substantial but mentions missing info
elif meaningful_content > 100 chars and no ungrounded phrases:
    return 4.0  # Good content, fully grounded
elif meaningful_content > 100 chars:
    return 2.5  # Some content but partially ungrounded
else:
    return 1.0-2.0  # Minimal content
```

If found → `agentic: false` (ungrounded)  
If not found → `agentic: true` (grounded)

**Prompt Template Structure:**
```
You are a helpful AI assistant. Your task is to answer using ONLY the context.

Context from documents:
{context}

Question: {question}

CRITICAL INSTRUCTIONS:
1. Read entire context carefully
2. Answer ONLY based on context
3. Quote specific details
4. Do NOT cite sources (shown separately)
5. Include all details (numbers, dates, percentages)
6. If not in context, say "I don't have this information"
7. Do NOT use general knowledge
8. Be precise with all relevant details

Answer:
```

---

### 5. Streaming Chat Workflow

**Endpoint:** `POST /chat/stream`

**Flow:**
```
User requests streaming → POST /chat/stream
                               ↓
                    Same retrieval and prompt building
                               ↓
                    Stream response from GPT-4o
                      • Async generator yields chunks
                      • Frontend displays in real-time
                               ↓
                    After streaming complete:
                      • Send sources as JSON
                      • Send reasoning log
```

**Code Flow:**
```python
@app.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    # Same retrieval logic as /chat
    docs = vectorstore.similarity_search(req.query, k=req.top_k)
    context = build_context(docs)
    prompt = PROMPT_TEMPLATE.format(context=context, question=req.query)
    
    # Stream response
    async def generate():
        llm = get_llm()
        full_answer = ""
        
        # Stream answer chunks
        async for chunk in llm.astream(prompt):
            content = chunk.content
            full_answer += content
            yield f"data: {json.dumps({'type': 'content', 'data': content})}\n\n"
        
        # Send sources after answer complete
        yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"
        
        # Send reasoning log
        yield f"data: {json.dumps({'type': 'reasoning', 'data': reasoning_log})}\n\n"
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## Frontend Workflow

### 1. Application Structure

**File:** `frontend/src/App.tsx`

**Component Hierarchy:**
```
App (main container)
├── Header (🤖 DocuMind AI)
├── Left Sidebar (350px fixed width)
│   ├── Upload Component
│   └── Process Component
└── Right Content (flex: 1)
    └── ChatStream Component
```

**State Management:**
```typescript
const [files, setFiles] = useState<string[]>([])  // List of uploaded filenames
const [ok, setOk] = useState(false)               // Backend health status

// Load files on mount
useEffect(() => {
  health().then(() => setOk(true))
  loadFiles()  // Fetch list from /files endpoint
}, [])
```

**Layout:**
```typescript
<div style={{ 
  display: 'grid', 
  gridTemplateColumns: '350px 1fr',  // Fixed left, flexible right
  gap: '20px', 
  alignItems: 'start' 
}}>
  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
    <Upload onUploaded={loadFiles} uploadedCount={files.length} />
    <Process files={files} />
  </div>
  <ChatStream />
</div>
```

---

### 2. Upload Component Workflow

**File:** `frontend/src/components/Upload.tsx`

**Flow:**
```
User clicks "Choose Files" → File picker opens
                                   ↓
User selects files → onChange sets files state
                                   ↓
User clicks "Upload" → uploadFile(files) API call
                                   ↓
                    POST /upload with multipart/form-data
                                   ↓
                    Backend uploads to Blob Storage
                                   ↓
                    Success response with file metadata
                                   ↓
                    Update status message
                                   ↓
                    Call onUploaded() callback → Parent refreshes file list
```

**Code Flow:**
```typescript
export default function Upload({ onUploaded, uploadedCount }) {
  const [files, setFiles] = useState<FileList | null>(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')

  const handleUpload = async () => {
    setLoading(true)
    setStatus(`Uploading ${files!.length} file(s)…`)
    
    try {
      const res = await uploadFile(files!)  // API call
      const fileNames = res.files.map(f => f.name).join(', ')
      setStatus(`Uploaded: ${fileNames}`)
      onUploaded()  // Refresh parent file list
    } catch (e: any) {
      setStatus(`Error: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <h3>Upload documents</h3>
      <p className="badge">PDF, DOCX, TXT, MD • {uploadedCount} uploaded</p>
      
      <div style={{ marginBottom: '12px' }}>
        <input 
          type="file" 
          multiple 
          accept=".pdf,.docx,.txt,.md" 
          onChange={(e) => setFiles(e.target.files)} 
        />
      </div>
      
      <button 
        className="btn" 
        disabled={!files || loading}
        onClick={handleUpload}
      >
        Upload
      </button>
      
      <span>{status}</span>
    </div>
  )
}
```

**API Call:**
```typescript
// api.ts
export async function uploadFile(files: FileList) {
  const formData = new FormData()
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i])
  }
  
  const res = await fetch('http://127.0.0.1:8000/upload', {
    method: 'POST',
    body: formData  // No Content-Type header - browser sets multipart boundary
  })
  
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`)
  return res.json()
}
```

---

### 3. Process Component Workflow

**File:** `frontend/src/components/Process.tsx`

**Flow:**
```
Files uploaded → Process component receives files prop
                                   ↓
User clicks "Process All" → Iterate through files
                                   ↓
For each file:
  POST /process with { blob_name: filename }
                                   ↓
  Backend downloads, chunks, indexes
                                   ↓
  Response: { chunks: 5, chunks_indexed: 5, preview: "..." }
                                   ↓
  Update progress status
                                   ↓
All files processed → Show completion message
```

**Code Flow:**
```typescript
export default function Process({ files }) {
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')

  const handleProcess = async () => {
    setLoading(true)
    setStatus('Processing files...')
    
    for (const filename of files) {
      try {
        const res = await processBlob(filename)
        setStatus(`Processed ${filename}: ${res.chunks} chunks indexed`)
        await new Promise(resolve => setTimeout(resolve, 500))  // Brief pause
      } catch (e: any) {
        setStatus(`Error processing ${filename}: ${e.message}`)
        break
      }
    }
    
    setLoading(false)
    setStatus('All files processed!')
  }

  return (
    <div className="card">
      <h3>Process and index</h3>
      <p className="badge">Azure AI Search • {files.length} file(s) ready</p>
      
      <div>
        <strong>Files:</strong>
        <ul>
          {files.map(f => <li key={f}>{f}</li>)}
        </ul>
      </div>
      
      <button 
        className="btn" 
        disabled={files.length === 0 || loading}
        onClick={handleProcess}
      >
        Process All
      </button>
      
      <span>{status}</span>
      <p className="tip">Creates embeddings and indexes documents</p>
    </div>
  )
}
```

---

### 4. ChatStream Component Workflow

**File:** `frontend/src/components/ChatStream.tsx`

**Initialization:**
```typescript
const [q, setQ] = useState('')  // Current question input
const [turns, setTurns] = useState<Turn[]>([])  // Conversation history
const [loading, setLoading] = useState(false)

const samplePrompts = [
  "What are the core values mentioned in the company policies?",
  "What is the vacation policy for employees?",
  "Tell me about the product specifications",
  "What technical documentation is available?",
  "Summarize the key points from all documents"
]
```

**Query Flow:**
```
User clicks sample prompt OR types question → send() function called
                                                       ↓
                              Add user message to turns state
                                                       ↓
                              POST /chat with { query, top_k: 5 }
                                                       ↓
                              Backend performs RAG pipeline
                                                       ↓
                              Response received:
                                • answer: "According to the document..."
                                • sources: [{ source: "file.md", content: "..." }]
                                • reasoning_log: [{ phase, details, timestamp }]
                                • agentic: true/false
                                                       ↓
                              Add assistant message to turns state
                                                       ↓
                              UI auto-scrolls to bottom
                                                       ↓
                              Sample prompts remain visible at top
```

**Code Flow:**
```typescript
const send = async () => {
  if (!q.trim()) return
  
  // Add user message
  const userTurn: Turn = { role: 'user', content: q }
  setTurns(prev => [...prev, userTurn])
  setQ('')  // Clear input
  setLoading(true)
  
  try {
    // Call backend
    const res = await chat(q, 5)  // top_k=5
    
    // Add assistant message
    const assistantTurn: Turn = {
      role: 'assistant',
      content: res.answer,
      sources: res.sources,
      reasoning_log: res.reasoning_log,
      agentic: res.agentic
    }
    setTurns(prev => [...prev, assistantTurn])
  } catch (e: any) {
    // Add error message
    setTurns(prev => [...prev, {
      role: 'assistant',
      content: `Error: ${e.message}`,
      sources: [],
      reasoning_log: [],
      agentic: false
    }])
  } finally {
    setLoading(false)
  }
}

const handlePromptClick = (prompt: string) => {
  setQ(prompt)
  // Automatically send after brief delay
  setTimeout(() => send(), 100)
}
```

**UI Rendering:**
```typescript
return (
  <div style={{ /* Chat container */ }}>
    {/* Header */}
    <div style={{ /* Purple gradient header */ }}>
      <h3>💬 Chat with your documents</h3>
    </div>
    
    {/* Scrollable content */}
    <div style={{ flex: 1, overflowY: 'auto' }}>
      {/* Sample prompts - always visible */}
      <div>
        {turns.length === 0 && (
          <div>🚀 Get started with these questions</div>
        )}
        <div className="sample-prompts-grid">
          {samplePrompts.map(prompt => (
            <button onClick={() => handlePromptClick(prompt)}>
              💡 {prompt}
            </button>
          ))}
        </div>
      </div>
      
      {/* Conversation messages */}
      {turns.map((turn, i) => (
        <div key={i} className={turn.role}>
          <strong>{turn.role === 'user' ? '👤 You' : '🤖 Assistant'}</strong>
          <div>{turn.content}</div>
          
          {/* Reasoning log (collapsible) */}
          {turn.reasoning_log && (
            <ReasoningLog steps={turn.reasoning_log} />
          )}
          
          {/* Sources (collapsible) */}
          {turn.sources && (
            <SourcesList sources={turn.sources} />
          )}
        </div>
      ))}
    </div>
    
    {/* Fixed input at bottom */}
    <div style={{ borderTop: '2px solid', padding: '12px' }}>
      <input 
        value={q}
        placeholder="Ask anything about your documents..."
        onChange={e => setQ(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && send()}
      />
      <button disabled={loading} onClick={send}>
        {loading ? '⏳ Thinking...' : '🚀 Ask'}
      </button>
    </div>
  </div>
)
```

**Collapsible Components:**

**ReasoningLog:**
```typescript
function ReasoningLog({ steps }: { steps: ReasoningStep[] }) {
  const [show, setShow] = useState(false)
  
  return (
    <div>
      <button onClick={() => setShow(!show)}>
        {show ? '▼ Hide' : '▶ Show'} Reasoning
      </button>
      
      {show && (
        <div className="reasoning-steps">
          {steps.map((step, i) => (
            <div key={i}>
              <strong>{step.phase}</strong>
              <p>{step.details}</p>
              <small>{step.timestamp}</small>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

**SourcesList:**
```typescript
function SourcesList({ sources }: { sources: Source[] }) {
  const [show, setShow] = useState(false)
  
  return (
    <div>
      <button onClick={() => setShow(!show)}>
        {show ? '▼ Hide' : '▶ Show'} Sources ({sources.length})
      </button>
      
      {show && (
        <div className="sources-list">
          {sources.map((src, i) => (
            <div key={i}>
              <strong>📄 {src.source}</strong>
              <p>{src.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

---

## Data Flow

### End-to-End Example: Asking "What is the vacation policy?"

```
1. USER ACTION
   └─ Clicks sample prompt "What is the vacation policy for employees?"

2. FRONTEND (ChatStream.tsx)
   ├─ handlePromptClick() sets q state
   ├─ send() function called
   ├─ Adds user turn to conversation
   └─ POST http://127.0.0.1:8000/chat
      Body: { "query": "What is the vacation policy for employees?", "top_k": 5 }

3. BACKEND (main.py - /chat endpoint)
   ├─ Receives request
   ├─ RETRIEVAL PHASE
   │  ├─ get_vectorstore() returns AzureSearch instance
   │  ├─ Converts query to embedding [0.123, -0.456, ...]
   │  ├─ Hybrid search in Azure AI Search:
   │  │  ├─ Vector search finds semantically similar chunks
   │  │  ├─ Keyword search finds exact term matches
   │  │  └─ RRF fusion combines results
   │  └─ Returns top 5 chunks:
   │     [
   │       { source: "company_policies.md", content: "## Vacation Policy\n..." },
   │       { source: "company_policies.md", content: "Employees receive 15..." },
   │       ...
   │     ]
   │
   ├─ CONTEXT BUILDING
   │  └─ Joins chunks: "Document: company_policies.md\n## Vacation Policy\n..."
   │
   ├─ PROMPT BUILDING
   │  ├─ Loads template from prompt_instructions.txt
   │  └─ Formats: context=<chunks>, question=<query>
   │
  ├─ GENERATION PHASE
  │  ├─ AzureChatOpenAI.invoke(prompt)
  │  ├─ Calls https://aifoundry-eus-capstone.openai.azure.com
  │  ├─ Deployment: gpt-4o
  │  └─ Returns: "Employees receive 15 days for 0-5 years, 20 days for 5-10 years..."
   │
   ├─ GROUNDING VALIDATION
   │  ├─ Checks answer for "don't have", "not provided"
   │  └─ Result: grounded=true (answer uses context)
   │
   ├─ REASONING LOG
   │  └─ [
   │       { phase: "Retrieval", details: "Retrieved 5 documents..." },
   │       { phase: "Generation", details: "Generated answer with 1234 chars..." },
   │       { phase: "Grounding", details: "Answer is grounded in documents" }
   │     ]
   │
   └─ RESPONSE
      {
        "answer": "Employees receive 15 days...",
        "sources": [{ source: "company_policies.md", content: "..." }],
        "reasoning_log": [...],
        "agentic": true
      }

4. FRONTEND (ChatStream.tsx)
   ├─ Receives response
   ├─ Creates assistant turn with all data
   ├─ setTurns([...prev, assistantTurn])
   ├─ React re-renders:
   │  ├─ User message: Purple gradient bubble "What is the vacation policy?"
   │  ├─ Assistant message: White bubble with answer
   │  ├─ ReasoningLog: Collapsed by default, click to expand
   │  └─ SourcesList: Shows "▶ Show Sources (5)"
   └─ Auto-scrolls to bottom

5. USER INTERACTION
   ├─ Reads answer
   ├─ Clicks "Show Sources" → Expands to show all 5 chunks
   ├─ Clicks "Show Reasoning" → See RAG pipeline steps
   └─ Sample prompts still visible at top for next question
```

---

## Component Details

### Backend Components

#### 1. Document Loaders

**PyPDFLoader** (for PDFs):
```python
from langchain_community.document_loaders import PyPDFLoader

loader = PyPDFLoader("document.pdf")
docs = loader.load()  # Returns list of Document objects, one per page
```

**UnstructuredFileLoader** (for DOCX/TXT/MD):
```python
from langchain_community.document_loaders import UnstructuredFileLoader

# NO mode="elements" - keeps sections together
loader = UnstructuredFileLoader("document.md")
docs = loader.load()  # Returns list of Documents
```

#### 2. Text Splitter

**RecursiveCharacterTextSplitter:**
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,           # Target chunk size
    chunk_overlap=200,         # Overlap to preserve context
    separators=["\n\n", "\n", " ", ""]  # Split on paragraphs first
)

chunks = splitter.split_documents(docs)
```

**How it works:**
1. Try to split on `\n\n` (paragraphs)
2. If chunks too large, split on `\n` (lines)
3. If still too large, split on spaces
4. Last resort: split on characters
5. Maintains 200-char overlap between chunks

#### 3. Embeddings

**AzureOpenAIEmbeddings:**
```python
from langchain_openai import AzureOpenAIEmbeddings

embeddings = AzureOpenAIEmbeddings(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_KEY,
    azure_deployment="text-embedding-3-large",
    api_version="2024-08-01-preview"
)

# Generates 3072-dimensional vectors
vector = embeddings.embed_query("What is the vacation policy?")
# Returns: [0.123, -0.456, 0.789, ...]
```

#### 4. Vector Store

**AzureSearch:**
```python
from langchain_community.vectorstores.azuresearch import AzureSearch

vectorstore = AzureSearch(
    azure_search_endpoint=AZURE_SEARCH_ENDPOINT,
    azure_search_key=AZURE_SEARCH_KEY,
    index_name=AZURE_SEARCH_INDEX,
    embedding_function=embeddings.embed_query
)

# Add documents (auto-generates embeddings)
vectorstore.add_documents(chunks)

# Hybrid search
docs = vectorstore.similarity_search(
    query="vacation policy",
    k=5,
    search_type="hybrid"
)
```

#### 5. LLM

**AzureChatOpenAI:**
```python
from langchain_openai import AzureChatOpenAI

llm = AzureChatOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_KEY,
  azure_deployment="gpt-4o",
  api_version="2024-08-01-preview"
  # Use default temperature recommended for gpt-4o
)

response = llm.invoke("Your prompt here")
answer = response.content
```

---

### Frontend Components

#### API Client (api.ts)

```typescript
const BASE_URL = 'http://127.0.0.1:8000'

export async function health() {
  const res = await fetch(`${BASE_URL}/health`)
  return res.json()
}

export async function uploadFile(files: FileList) {
  const formData = new FormData()
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i])
  }
  const res = await fetch(`${BASE_URL}/upload`, {
    method: 'POST',
    body: formData
  })
  if (!res.ok) throw new Error('Upload failed')
  return res.json()
}

export async function listFiles() {
  const res = await fetch(`${BASE_URL}/files`)
  return res.json()
}

export async function processBlob(blobName: string) {
  const res = await fetch(`${BASE_URL}/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ blob_name: blobName })
  })
  if (!res.ok) throw new Error('Process failed')
  return res.json()
}

export async function chat(query: string, topK: number = 5) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK })
  })
  if (!res.ok) throw new Error('Chat failed')
  return res.json()
}
```

---

## Azure Services Integration

### 1. Azure Blob Storage

**Purpose:** Persistent document storage

**Configuration:**
```python
AZURE_BLOB_CONN_STRING = "DefaultEndpointsProtocol=https;AccountName=sadeveuscapstone;..."
AZURE_BLOB_CONTAINER = "documents"
```

**Operations:**
- Upload: `blob_client.upload_blob(content, overwrite=True)`
- Download: `blob_client.download_blob().readall()`
- List: `container_client.list_blobs()`

**Container Structure:**
```
documents/
├── company_policies.md
├── product_specifications.txt
└── technical_documentation.md
```

---

### 2. Azure AI Search

**Purpose:** Hybrid vector + keyword search

**Configuration:**
```python
AZURE_SEARCH_ENDPOINT = "https://aisearch-service-capstone.search.windows.net"
AZURE_SEARCH_KEY = "<key>"
AZURE_SEARCH_INDEX = "capstone-search-index"
```

**Tier:** Standard (required for vector search)

**Index Schema:**
```json
{
  "name": "capstone-search-index",
  "fields": [
    { "name": "id", "type": "Edm.String", "key": true },
    { "name": "content", "type": "Edm.String", "searchable": true },
    { "name": "content_vector", "type": "Collection(Edm.Single)", "dimensions": 1536 },
    { "name": "metadata", "type": "Edm.String" }
  ],
  "vectorSearch": {
    "algorithms": [
      { "name": "default", "kind": "hnsw" }  // Hierarchical Navigable Small World
    ]
  }
}
```

**Search Process:**
1. **Vector Search:**
  - Query embedded to 3072-dim vector
   - HNSW algorithm finds nearest neighbors
   - Returns top N by cosine similarity

2. **Keyword Search:**
   - BM25 ranking on text content
   - Considers term frequency, document frequency
   - Returns top N by relevance score

3. **Hybrid Fusion:**
   - Reciprocal Rank Fusion combines scores
   - Formula: `score = sum(1 / (k + rank_i))`
   - Final ranking by combined score

---

### 3. Azure AI Foundry (OpenAI)

**Purpose:** GPT-4o chat completions and embeddings

**Configuration:**
```python
AZURE_OPENAI_ENDPOINT = "https://aifoundry-eus-capstone.openai.azure.com"
AZURE_OPENAI_KEY = "<key>"
AZURE_OPENAI_CHAT_DEPLOYMENT = "gpt-4o"
AZURE_OPENAI_EMBED_DEPLOYMENT = "text-embedding-3-large"
API_VERSION = "2024-08-01-preview"
```

**Deployments:**

1. **gpt-4o:**
  - Model: GPT-4o
  - Context window: 128K tokens
  - Temperature: Default (1.0)
  - Used for: Generating answers from context

2. **text-embedding-3-large:**
  - Dimensions: 3072
  - Max input: 8191 tokens
  - Used for: Document and query embeddings

**API Calls:**

Chat completion:
```python
POST https://aifoundry-eus-capstone.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview

Headers:
  api-key: <key>
  Content-Type: application/json

Body:
{
  "messages": [
    { "role": "system", "content": "<prompt>" },
    { "role": "user", "content": "<question>" }
  ]
}
```

Embeddings:
```python
POST https://aifoundry-eus-capstone.openai.azure.com/openai/deployments/text-embedding-3-large/embeddings?api-version=2024-08-01-preview

Body:
{
  "input": "text to embed"
}

Response:
{
  "data": [
    { "embedding": [0.123, -0.456, ...] }  // 3072 floats
  ]
}
```

---

## Error Handling and Logging

### Backend Error Handling

**Upload Errors:**
```python
@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    try:
        # Upload logic
    except Exception as e:
        print(f"❌ Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Process Errors:**
```python
@app.post("/process")
async def process_blob(req: ProcessRequest):
    try:
        # Processing logic
    except Exception as e:
        print(f"❌ Processing failed for {req.blob_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp file
        if os.path.exists(local_path):
            os.remove(local_path)
```

**Chat Errors:**
```python
@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        # Hybrid search with fallback
        try:
            docs = vectorstore.similarity_search(req.query, k=req.top_k, search_type="hybrid")
        except:
            print("⚠️ Hybrid search failed, falling back to default")
            docs = vectorstore.similarity_search(req.query, k=req.top_k)
        
        # Rest of chat logic
    except Exception as e:
        print(f"❌ Chat failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Backend Logging

**Debug Logging:**
```python
print(f"✅ Loaded {len(docs)} documents from {req.blob_name}")
print(f"✅ Split into {len(chunks)} chunks")
print(f"Preview of first chunk:\n{chunks[0].page_content[:200]}")
print(f"🔍 Retrieved {len(docs)} documents for query: {req.query}")
print(f"📝 Context preview: {context[:200]}...")
```

**Reasoning Log (returned to user):**
```python
reasoning_log = [
    {
        "phase": "Retrieval",
        "details": f"Retrieved {len(docs)} relevant documents using hybrid search",
        "timestamp": datetime.now().isoformat()
    },
    {
        "phase": "Generation",
        "details": f"Generated answer using GPT-4o with {len(context)} chars of context",
        "timestamp": datetime.now().isoformat()
    },
    {
        "phase": "Grounding",
        "details": f"Answer is {'grounded in documents' if grounded else 'missing information'}",
        "timestamp": datetime.now().isoformat()
    }
]
```

### Frontend Error Handling

**API Call Errors:**
```typescript
try {
  const res = await uploadFile(files)
  setStatus(`Uploaded: ${res.files.map(f => f.name).join(', ')}`)
} catch (e: any) {
  setStatus(`Error: ${e.message}`)
  console.error('Upload failed:', e)
}
```

**Chat Errors:**
```typescript
try {
  const res = await chat(q, 5)
  setTurns(prev => [...prev, { role: 'assistant', content: res.answer, ... }])
} catch (e: any) {
  setTurns(prev => [...prev, {
    role: 'assistant',
    content: `Error: ${e.message}`,
    sources: [],
    reasoning_log: [],
    agentic: false
  }])
}
```

---

## Performance Optimizations

### 1. Chunking Strategy

**Problem:** Small chunks lose context, large chunks reduce retrieval precision

**Solution:**
- Chunk size: 2000 characters (preserves complete sections)
- Overlap: 200 characters (prevents context loss at boundaries)
- Recursive splitting (paragraph → sentence → word → char)

**Result:** 
- Vacation policy section stays together
- Related content not split across chunks
- Better retrieval accuracy

---

### 2. Hybrid Search

**Problem:** Vector search misses exact matches, keyword search misses semantic similarity

**Solution:**
- Combine vector similarity and BM25 keyword search
- Reciprocal Rank Fusion merges results
- Best of both approaches

**Example:**
- Query: "time off policy"
- Vector search finds: "vacation days", "annual leave" (semantic)
- Keyword search finds: "policy" (exact match)
- Fusion ranks documents with both signals

---

### 3. Grounding Validation

**Problem:** LLM might hallucinate or say "I don't know" when answer exists

**Solution:**
- Check answer for phrases indicating missing info
- Classify responses as grounded/ungrounded
- Display status to user

**Implementation:**
```python
ungrounded_phrases = [
    "don't have this information",
    "not provided in the documents",
    "information is not available"
]

grounded = not any(phrase in answer.lower() for phrase in ungrounded_phrases)
```

---

### 4. UI Responsiveness

**Problem:** Large responses slow down UI, sources clutter interface

**Solution:**
- Collapsible sections for sources and reasoning
- Default collapsed state
- Only render when expanded
- Sample prompts always visible but compact after first message

**Implementation:**
```typescript
const [showSources, setShowSources] = useState(false)

<button onClick={() => setShowSources(!show)}>
  {show ? '▼ Hide' : '▶ Show'} Sources
</button>

{show && <div>{/* Render sources */}</div>}
```

---

### 5. External Prompt Configuration

**Problem:** Changing prompt requires code changes and redeployment

**Solution:**
- Store prompt in external file `prompt_instructions.txt`
- Load at startup with fallback
- Update prompt without touching code

**Implementation:**
```python
def load_prompt_template():
    try:
        with open("prompt_instructions.txt", "r") as f:
            return f.read()
    except:
        return DEFAULT_PROMPT  # Fallback

PROMPT_TEMPLATE = load_prompt_template()
```

---

## Conclusion

DocuMind AI is a production-ready, enterprise-grade RAG system that demonstrates:

- **Full-stack integration:** React + FastAPI + Azure services
- **Advanced RAG:** Hybrid search, grounding validation, reasoning logs
- **Modern UX:** ChatGPT-style interface, sample prompts, collapsible sections
- **Robust architecture:** Error handling, logging, external configuration
- **Scalability:** Azure AI Search Standard tier, Blob Storage, AI Foundry

The system successfully accomplishes all project requirements and provides a solid foundation for further enhancements like authentication, multi-language support, or advanced analytics.

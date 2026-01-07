import os
import time
import traceback
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Document utilities
from document_utils import create_blob_manager, create_document_processor
from rag_pipeline import RAGPipeline

load_dotenv()

app = FastAPI(title="Agentic RAG Backend")

# CORS - Allow both common frontend ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("CORS_ORIGIN", "http://localhost:5173"),
        "http://localhost:5174",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ENV
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
EMBED_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT")

BLOB_ACCOUNT_URL = os.getenv("AZURE_BLOB_ACCOUNT_URL")  # e.g., https://myaccount.blob.core.windows.net
BLOB_CONN = os.getenv("AZURE_BLOB_CONN_STRING")  # Fallback to connection string
BLOB_CONTAINER = os.getenv("AZURE_BLOB_CONTAINER", "docs")

SEARCH_SERVICE = os.getenv("AZURE_SEARCH_SERVICE")
SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")
SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")

# Load prompt template from file
PROMPT_FILE = os.path.join(os.path.dirname(__file__), "prompt_instructions.txt")
def load_prompt_template():
    """Load the system prompt from disk, falling back to a default template on error."""
    try:
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Could not load prompt file, using default. Error: {e}")
        return """You are a helpful AI assistant. Answer based ONLY on the provided context.

Context from documents:
{context}

Question: {question}

Answer:"""

PROMPT_TEMPLATE = load_prompt_template()

# Initialize blob manager and document processor
blob_manager = None
doc_processor = None

# Don't try to use Azure if connection string has dummy-key
skip_azure = BLOB_CONN and "dummy-key" in BLOB_CONN

if (BLOB_CONN or BLOB_ACCOUNT_URL) and not skip_azure:
    try:
        blob_manager = create_blob_manager(BLOB_CONTAINER, connection_string=BLOB_CONN, account_url=BLOB_ACCOUNT_URL)
        doc_processor = create_document_processor(chunk_size=2000, chunk_overlap=200)
        
        # Ensure container exists (for Azure Blob Storage)
        try:
            blob_manager.container_client.create_container()
            print("[OK] Blob storage configured")
        except Exception:
            pass  # Container already exists or using local storage
    except Exception as e:
        print(f"[WARN] Blob storage initialization failed: {str(e)}")
        print("The application will still start, but file upload functionality will not work.")
        blob_manager = None
        doc_processor = None
else:
    if skip_azure:
        print("Warning: Azure Blob Storage has dummy key. Using local file storage.")
    else:
        print("Warning: Azure Blob Storage not configured. Using local file storage.")

# Always ensure we have a blob_manager for local fallback
if blob_manager is None:
    blob_manager = create_blob_manager(BLOB_CONTAINER, connection_string=None, account_url=None)
    doc_processor = create_document_processor(chunk_size=2000, chunk_overlap=200)

rag_pipeline = None
if AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY:
    try:
        rag_pipeline = RAGPipeline(
            azure_openai_endpoint=AZURE_OPENAI_ENDPOINT,
            azure_openai_api_key=AZURE_OPENAI_API_KEY,
            chat_deployment=CHAT_DEPLOYMENT,
            embed_deployment=EMBED_DEPLOYMENT,
            search_endpoint=SEARCH_SERVICE,
            search_key=SEARCH_API_KEY,
            search_index=SEARCH_INDEX,
            prompt_template=PROMPT_TEMPLATE,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        )
        print("[OK] RAG system ready")
    except Exception as e:
        print(f"[WARN] Warning: RAG pipeline initialization failed: {str(e)}")
        print("The application will still start, but chat functionality will not work.")
        rag_pipeline = None
else:
    print("Warning: Azure OpenAI not configured. Chat functionality will not work until you configure .env file.")

class ChatRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

@app.get("/health")
def health():
    """Lightweight health probe for container orchestrators."""
    return {"status": "ok"}

@app.get("/files")
def list_files():
    """List all uploaded files in Blob Storage"""
    try:
        files = blob_manager.list_files()
        return {"files": files, "count": len(files)}
    except Exception as e:
        return {"error": str(e), "files": [], "count": 0}

@app.post("/upload")
async def upload_file(request: Request, files: List[UploadFile] = File(...)):
    """Upload one or more files to Blob Storage and return their metadata."""
    try:
        if not blob_manager:
            return {
                "error": "Blob storage not configured",
                "files": [],
                "message": "Upload functionality is not available"
            }, 503
        
        uploaded_files = []
        
        for file in files:
            try:
                data = await file.read()
                
                # Upload using blob manager
                file_info = blob_manager.upload_file(file.filename, data)
                uploaded_files.append({
                    "name": file_info["name"],
                    "location": "blob",
                    "path": file_info["name"]
                })
            except Exception as file_error:
                print(f"[UPLOAD ERROR] Failed to upload {file.filename}: {str(file_error)}")
                uploaded_files.append({
                    "name": file.filename,
                    "error": str(file_error),
                    "success": False
                })
        
        return {"files": uploaded_files, "message": f"Uploaded {len(uploaded_files)} file(s)"}
    except Exception as e:
        print(f"[UPLOAD ERROR] Unexpected error: {str(e)}")
        return {
            "error": str(e),
            "files": [],
            "message": "Upload failed"
        }, 500

@app.post("/process")
def process_blob(request: Request, blob: str = Query(...)):
    """Download a blob, chunk it, and index the chunks into Azure AI Search."""
    try:
        print(f"\n[PROCESS] Starting processing for: {blob}")
        
        # Process file using document processor
        print(f"[PROCESS] Loading and chunking {blob}...")
        chunks, chunk_count = doc_processor.process_file(blob_manager, blob)
        print(f"[PROCESS] Created {chunk_count} chunks")
        
        if chunk_count == 0:
            print(f"[PROCESS WARNING] No chunks created for {blob}")
            return {
                "blob": blob,
                "chunks": 0,
                "chunks_indexed": 0,
                "message": "No chunks created - file may be empty or unsupported format"
            }

        # Try to index into Azure AI Search
        try:
            print(f"[PROCESS] Indexing {chunk_count} chunks into Azure AI Search...")
            vectorstore = rag_pipeline.get_vectorstore()
            if vectorstore is None:
                print(f"[PROCESS WARNING] Vectorstore not available - chunks created but not indexed")
                return {
                    "blob": blob,
                    "chunks": chunk_count,
                    "chunks_indexed": 0,
                    "message": "Chunks created but indexing failed - Azure AI Search not available"
                }
            
            vectorstore.add_documents(chunks)
            print(f"[PROCESS] ✓ Successfully indexed {chunk_count} chunks for {blob}\n")
            return {
                "blob": blob,
                "chunks": chunk_count,
                "chunks_indexed": chunk_count,
                "message": "Indexed into Azure AI Search"
            }
        except Exception as index_error:
            print(f"[PROCESS WARNING] Failed to index chunks but they were created: {str(index_error)}")
            # Still return the chunks created even if indexing failed
            return {
                "blob": blob,
                "chunks": chunk_count,
                "chunks_indexed": 0,
                "message": f"Chunks created but indexing failed: {str(index_error)}"
            }
    
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"[PROCESS ERROR] Failed to process {blob}")
        print(f"Error: {str(e)}")
        print(f"Traceback:\n{error_trace}")
        return {"error": str(e), "blob": blob, "chunks": 0}

@app.post("/chat")
def chat(req: ChatRequest):
    """Answer a question using RAG over the indexed documents."""
    try:
        if not rag_pipeline:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "RAG pipeline not configured",
                    "answer": "Chat functionality is not available. Please configure Azure OpenAI credentials in .env file.",
                    "documents": [],
                    "query": req.query
                }
            )
        
        return rag_pipeline.chat(req.query, req.top_k)
    except Exception as e:
        print(f"[CHAT ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "answer": f"Error processing chat request: {str(e)}",
                "documents": [],
                "query": req.query
            }
        )

# Streaming endpoint (LLM-only streaming of final synthesis text)
@app.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    """Stream the synthesized answer tokens as they are generated."""
    try:
        if not rag_pipeline:
            async def error_streamer():
                yield "Error: RAG pipeline not configured. Please configure Azure OpenAI credentials in .env file."
            return StreamingResponse(error_streamer(), media_type="text/plain", status_code=503)
        
        async def streamer():
            try:
                async for chunk in rag_pipeline.stream_chat(req.query, req.top_k):
                    yield chunk
            except Exception as e:
                print(f"[STREAM ERROR] {str(e)}")
                yield f"\n\n[Error: {str(e)}]"
        
        return StreamingResponse(streamer(), media_type="text/plain")
    except Exception as e:
        print(f"[STREAM ERROR] {str(e)}")
        async def error_streamer():
            yield f"Error: {str(e)}"
        return StreamingResponse(error_streamer(), media_type="text/plain", status_code=500)

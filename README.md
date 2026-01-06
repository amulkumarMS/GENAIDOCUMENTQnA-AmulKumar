# DocuMind AI

**Intelligent Document Q&A System using Azure AI Foundry, AI Search, LangChain and RAG**

Build an enterprise-grade RAG system for conversational document queries.

DocuMind AI is a production-ready RAG assistant that answers questions over your files with citations. It pairs Azure AI Foundry (GPT-4o for chat, text-embedding-3-large for embeddings) with Azure AI Search and a React/Vite UI backed by FastAPI.

**Highlights**
- Multi-format ingestion: PDF, DOCX, TXT, MD (HTML via unstructured loader)
- Hybrid retrieval: vectors + keyword with semantic ranking
- Grounded responses: answers always include source snippets
- Modern UI: React/Vite chat with sample prompts and citations
- Azure-native: OpenAI, Search, Blob Storage; easy to deploy and observe

**RAG flow**
User question → Azure AI Search (hybrid) → top-k chunks → GPT-4o with context → answer + citations

**Building blocks**
- Azure AI Foundry: GPT-4o chat deployment; text-embedding-3-large for vectors
- Azure AI Search: hybrid vector + lexical with semantic ranker
- LangChain: loading, splitting, retrieval orchestration
- FastAPI: RAG API and orchestration
- React + Vite: chat frontend consuming the API

See `TECHNICAL_DOCUMENTATION.md` for deeper architecture details.

## ✅ Features Accomplished

### Core Capabilities
- ✅ **Functional web application with real-time Q&A**
- ✅ **Document ingestion pipeline supporting multiple formats** (.pdf, .docx, .txt, .md)
- ✅ **RAG system with source citations**
- ✅ **Sample queries and detailed outputs**

### Technology Stack

**Backend:**
- FastAPI with Python 3.14
- Azure AI Foundry (gpt-4o, text-embedding-3-large)
- Azure AI Search (Standard tier with hybrid search)
- Azure Blob Storage (document management)
- LangChain (langchain_openai, langchain_community, langchain_text_splitters)
- Azure AI Evaluation (GroundednessEvaluator for 0-5 grounding scores)

**Frontend:**
- React 18.3.1 with TypeScript
- Vite 5.4.21 (build tool with HMR)
- Modern responsive UI with purple gradient theme

### Key Features

🤖 **AI-Powered Intelligence**
- GPT-4o chat model from Azure AI Foundry
- Hybrid search combining vector similarity and keyword matching
- Azure AI Evaluation for grounding scores (0-5 scale)
- Detailed reasoning logs showing retrieval → generation → grounding phases with scores
- Modular RAG pipeline architecture for easy customization

📄 **Document Processing**
- Multi-file upload support (PDF, DOCX, TXT, Markdown)
- Azure Blob Storage integration for persistent document storage
- Smart chunking with RecursiveCharacterTextSplitter (2000 chars, 200 overlap)
- Automatic embedding generation and indexing

💬 **Conversational Interface**
- ChatGPT-style interface with fixed input at bottom
- 5 sample prompts always visible for easy exploration
- Collapsible sources and reasoning sections
- Real-time responses with loading indicators

🎨 **Modern UI/UX**
- Professional purple gradient theme (#667eea → #764ba2)
- Responsive design for desktop and mobile
- Hover effects and smooth transitions
- Left sidebar layout: Upload/Process cards stacked
- Right side: Full-height chat interface

## 🚀 Getting Started

### Prerequisites
- Python 3.14+
- Node.js 18+
- Azure subscription with:
  - Azure AI Foundry deployment
  - Azure AI Search (Standard tier)
  - Azure Blob Storage account

### Backend Setup

1. Navigate to backend directory:
```powershell
cd backend
```

2. Install Python dependencies:
```powershell
pip install -r requirements.txt
```

3. Configure `.env` file with your Azure credentials:
```env
AZURE_OPENAI_ENDPOINT=https://your-foundry-endpoint.openai.azure.com
AZURE_OPENAI_KEY=your-api-key
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-large
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_KEY=your-search-key
AZURE_SEARCH_INDEX=your-index-name
AZURE_BLOB_CONN_STRING=your-blob-connection-string
AZURE_BLOB_CONTAINER=documents
```

4. Start the backend server:
```powershell
.\start.ps1
```

Backend will run on `http://127.0.0.1:8000`

### Frontend Setup

1. Navigate to frontend directory:
```powershell
cd frontend
```

2. Install Node.js dependencies:
```powershell
npm install
```

3. Start the development server:
```powershell
npm run dev
```

Frontend will run on `http://localhost:5174`

## 📖 Usage

1. **Upload Documents**: Use the Upload card on the left to select and upload files (.pdf, .docx, .txt, .md)
2. **Process Documents**: Click "Process All" in the Process card to chunk and index documents
3. **Ask Questions**: 
   - Click on sample prompts in the chat area, or
   - Type your own question in the input box at the bottom
4. **View Results**: 
   - Read the AI-generated answer
   - Click "Show Reasoning" to see the RAG process steps
   - Click "Show Sources" to see retrieved document chunks

## 🏗️ Architecture

### RAG Pipeline
1. **Document Upload** → Azure Blob Storage
2. **Processing** → PyPDFLoader (PDFs) / Simple text loading (.txt, .md) → RecursiveCharacterTextSplitter
3. **Indexing** → Azure OpenAI Embeddings (text-embedding-3-large) → Azure AI Search
4. **Query** → Hybrid Search (vector + keyword) → Top 5 chunks retrieved
5. **Generation** → GPT-4o generates answer using retrieved context
6. **Grounding Evaluation** → Azure AI Evaluation scores answer (0-5 scale)
7. **Response** → Answer + Sources + Grounding Score + Reasoning log returned to UI

### Project Structure
```
Documind-AI-QnA-RAG/
├── backend/
│   ├── main.py                    # FastAPI endpoints and orchestration
│   ├── rag_pipeline.py            # RAG pipeline with grounding evaluation
│   ├── document_utils.py          # Document loaders and chunking helpers
│   ├── index_setup.py             # Creates Azure AI Search index
│   ├── prompt_instructions.txt    # System prompt template
│   ├── requirements.txt           # Backend dependencies
│   ├── start.ps1                  # Helper to run uvicorn
│   └── .env.example               # Env template (copy to .env)
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── App.tsx                # Main layout
│   │   ├── api.ts                 # API client
│   │   ├── main.tsx               # Vite/React entry
│   │   ├── styles.css             # Theme and layout
│   │   └── components/
│   │       ├── Upload.tsx         # Upload widget
│   │       ├── Process.tsx        # Indexing trigger
│   │       └── ChatStream.tsx     # Chat UI with citations
│   ├── sample_docs/               # Example files for testing
│   ├── deployment_scripts/
│   │   ├── azure_setup.ps1        # Provision Azure resources (PowerShell)
│   │   └── azure_setup.sh         # Provision Azure resources (Bash)
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   └── node_modules/ (gitignored)
├── azure_setup.ps1                # Root helper to provision Azure (pwsh)
├── azure_setup.sh                 # Root helper to provision Azure (bash)
├── QUICKSTART.md                  # One-page setup guide
├── TECHNICAL_DOCUMENTATION.md     # Deep dive architecture
├── FIXES_APPLIED.md               # Applied fixes log
├── .gitignore
└── README.md
```

## 🔧 Configuration

### Prompt Customization
Edit `backend/prompt_instructions.txt` to customize the AI's behavior without changing code.

### Search Parameters
Adjust in `backend/main.py`:
- `chunk_size`: Default 2000 characters
- `chunk_overlap`: Default 200 characters
- `top_k`: Default 5 retrieved documents

### UI Theming
Modify CSS variables in `frontend/src/styles.css`:
```css
:root {
  --bg: #f9fafb;
  --card: #ffffff;
  --accent: #667eea;
  --text: #1f2328;
  --muted: #57606a;
  --border: #d0d7de;
}
```

## 📝 API Endpoints

- `GET /health` - Health check
- `POST /upload` - Upload files to Blob Storage
- `GET /files` - List uploaded files
- `POST /process` - Process and index a document
- `POST /chat` - Query documents with RAG
- `POST /chat/stream` - Streaming chat responses

## 🎯 Sample Queries

The application includes these pre-configured sample prompts:
1. "What are the core values mentioned in the company policies?"
2. "What is the vacation policy for employees?"
3. "Tell me about the product specifications"
4. "What technical documentation is available?"
5. "Summarize the key points from all documents"

## 🔒 Security Notes

- Never commit `.env` file to version control
- Use Azure Key Vault for production secrets
- Implement proper authentication/authorization for production deployment
- Review Azure AI content filtering settings

## 📊 Performance

- **Hybrid Search**: Combines vector similarity (semantic) and keyword matching (lexical)
- **Chunking Strategy**: 2000 chars with 200 overlap prevents splitting related content
- **Standard Tier**: Azure AI Search supports vector search with better performance
- **Grounding Validation**: Ensures responses are factual and context-based

## 🚀 Deployment Considerations

For production deployment:
1. Use a proper WSGI server (e.g., Gunicorn) instead of Uvicorn dev mode
2. Build frontend: `npm run build` and serve static files
3. Configure environment variables in hosting platform
4. Set up Application Insights for monitoring
5. Implement rate limiting and caching
6. Use Azure CDN for static assets

## 📄 License

This project is for educational/demonstration purposes.

## 🤝 Contributing

This is a capstone project. For questions or feedback, please contact the development team.

---

**DocuMind AI** - AI-powered document intelligence 🤖

Current implementation: a FastAPI-based RAG pipeline that retrieves top-k chunks from Azure AI Search, formats a prompt, and calls Azure OpenAI (GPT-4o). It does not use `initialize_agent`; responses are produced directly via the LLM with retrieved context.

## API Endpoints

- `GET /health` - Health check
- `POST /upload` - Upload document to Blob Storage
- `POST /process?blob=<name>` - Process and index document
- `POST /chat` - Chat with documents (returns full response)
- `POST /chat/stream` - Streaming chat (returns text stream)

## Development

### Backend Structure

```
backend/
├── main.py              # FastAPI application with agentic RAG
├── index_setup.py       # Azure AI Search index creation
├── requirements.txt     # Python dependencies
└── .env                 # Environment variables
```

### Frontend Structure

```
frontend/
├── src/
│   ├── App.tsx          # Main application component
│   ├── api.ts           # API client
│   ├── components/      # React components
│   │   ├── Chat.tsx     # Non-streaming chat
│   │   ├── ChatStream.tsx # Streaming chat
│   │   ├── Upload.tsx   # Document upload
│   │   └── Process.tsx  # Document processing
│   └── styles.css       # Styles
├── package.json         # Node dependencies
└── vite.config.ts       # Vite configuration
```

## Troubleshooting

### Python Environment Issues
- Make sure you're using Python 3.11 or 3.12 (not 3.14)
- Activate the virtual environment before running commands
- Run `pip install --upgrade pip` if you see warnings

### Import Errors
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt` again
- Check that VS Code is using the correct Python interpreter (`.venv\Scripts\python.exe`)

### Frontend Errors
- Run `npm install` in the frontend directory
- Clear cache with `npm cache clean --force` and reinstall
- Check Node.js version with `node --version` (should be 18+)

### Azure Connection Issues
- Verify all environment variables in `.env` are correct
- Check Azure service endpoints are accessible
- Ensure API keys have proper permissions
- Run `python index_setup.py` to create the search index

## License

MIT

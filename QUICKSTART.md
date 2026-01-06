# Quick Start

Stand up DocuMind AI end-to-end, then publish to GitHub.

## Prerequisites
- Python 3.14+ and Node.js 18+
- Azure resources: AI Foundry (chat + embedding deployments), AI Search, Blob Storage
- PowerShell on Windows (commands below use `pwsh` syntax)

## 1) Clone and install
```powershell
git clone <your-repo-url> capstoneproj
cd capstoneproj

# Backend deps
cd backend
python -m venv ..\.venv
..\.venv\Scripts\pip install -r requirements.txt
cd ..

# Frontend deps
cd frontend
npm install
cd ..
```

## 2) Provision Azure resources (one-click)
Choose PowerShell or Bash:

PowerShell:
```powershell
pwsh ./azure_setup.ps1 -SubscriptionId "<sub-id>" -Location "eastus" -ResourceGroup "documind-rg" -NamePrefix "documind"
```

Bash:
```bash
bash azure_setup.sh -s <sub-id> -l eastus -g documind-rg -p documind
```

Outputs show the values to paste into `backend/.env` (endpoint, keys, deployments, search endpoint/key, blob connection string + container). If model deployment names differ, use your own when setting `AZURE_OPENAI_CHAT_DEPLOYMENT` and `AZURE_OPENAI_EMBED_DEPLOYMENT`.

## 2) Configure backend
```powershell
cd backend
copy .env.example .env
```
Edit `.env` with your Azure values:
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, `AZURE_OPENAI_CHAT_DEPLOYMENT`, `AZURE_OPENAI_EMBED_DEPLOYMENT`
- `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_KEY`, `AZURE_SEARCH_INDEX`
- `AZURE_BLOB_CONN_STRING`, `AZURE_BLOB_CONTAINER`
- Optional: `APPLICATIONINSIGHTS_CONNECTION_STRING`

Create the search index:
```powershell
..\.venv\Scripts\python.exe index_setup.py
```

Run the backend:
```powershell
..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
Backend: http://127.0.0.1:8000

## 3) Run frontend
Open a new terminal:
```powershell
cd frontend
npm run dev
```
Frontend: http://localhost:5173 (Vite will pick 5174 if 5173 is busy).

## 4) Smoke test
- Health check: `curl http://127.0.0.1:8000/health`
- UI: open the frontend URL, upload docs, click “Process All”, then ask a question.

## 5) Publish to GitHub
- Ensure secrets stay local: `.env` is already in `.gitignore`.
- Commit your changes, then push:
```powershell
git add .
git commit -m "Add DocuMind AI quick start"
git remote add origin <your-github-url>  # if not set
git push -u origin main
```

## Notes
- For theming, edit `frontend/src/styles.css` variables.
- To adjust retrieval, tune chunking/top_k in `backend/main.py`.
- More detail is in `README.md` and `TECHNICAL_DOCUMENTATION.md`.

"""Document utilities for Azure Blob Storage operations and document processing."""

import os
from azure.storage.blob import BlobServiceClient, ContainerClient
from azure.identity import DefaultAzureCredential
from langchain_community.document_loaders import PyPDFLoader, UnstructuredFileLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Tuple, Optional
from langchain_core.documents import Document


class AzureBlobDocumentManager:
    """Manage uploads, downloads, and listings against a single blob container."""
    
    def __init__(self, container_name: str, account_url: Optional[str] = None, connection_string: Optional[str] = None):
        """
        Initialize the blob document manager.
        
        Args:
            container_name: Name of the container to use
            account_url: Azure Storage Account URL (e.g., https://mystorageaccount.blob.core.windows.net)
            connection_string: Azure Blob Storage connection string
        """
        self.container_name = container_name
        
        # Prefer connection string (more reliable for local development)
        if connection_string:
            try:
                self.blob_service = BlobServiceClient.from_connection_string(connection_string)
            except Exception as e:
                raise ValueError(f"Failed to initialize blob service with connection string: {e}")
        elif account_url:
            try:
                # Use account_url with DefaultAzureCredential if connection string not provided
                credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
                self.blob_service = BlobServiceClient(account_url=account_url, credential=credential)
            except Exception as e:
                raise ValueError(f"Failed to initialize blob service with account URL and credentials: {e}")
        else:
            raise ValueError("Either connection_string or account_url must be provided")
            
        self.container_client = self.blob_service.get_container_client(container_name)
    
    def upload_file(self, file_name: str, file_content: bytes, overwrite: bool = True) -> dict:
        """
        Upload a file to Azure Blob Storage.
        
        Args:
            file_name: Name of the file
            file_content: File content as bytes
            overwrite: Whether to overwrite existing file
            
        Returns:
            Dictionary with file metadata
        """
        blob_client = self.container_client.get_blob_client(file_name)
        blob_client.upload_blob(file_content, overwrite=overwrite)
        
        return {
            "name": file_name,
            "url": blob_client.url,
            "size": len(file_content)
        }
    
    def list_files(self) -> List[dict]:
        """
        List all files in the blob container.
        
        Returns:
            List of file metadata dictionaries
        """
        blobs = self.container_client.list_blobs()
        return [
            {
                "name": blob.name,
                "size": blob.size,
                "last_modified": blob.last_modified.isoformat() if blob.last_modified else None
            }
            for blob in blobs
        ]
    
    def download_file(self, file_name: str) -> bytes:
        """
        Download a file from Azure Blob Storage.
        
        Args:
            file_name: Name of the file to download
            
        Returns:
            File content as bytes
        """
        blob_client = self.container_client.get_blob_client(file_name)
        download_stream = blob_client.download_blob()
        return download_stream.readall()
    
    def delete_file(self, file_name: str) -> bool:
        """
        Delete a file from Azure Blob Storage.
        
        Args:
            file_name: Name of the file to delete
            
        Returns:
            True if successful
        """
        blob_client = self.container_client.get_blob_client(file_name)
        blob_client.delete_blob()
        return True


class DocumentProcessor:
    """Processes documents for RAG indexing."""
    
    def __init__(self, chunk_size: int = 2000, chunk_overlap: int = 200):
        """
        Initialize the document processor.
        
        Args:
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    def load_document(self, file_path: str, file_name: str) -> List[Document]:
        """
        Load a document based on file extension.
        
        Args:
            file_path: Path to the file
            file_name: Original file name (for extension detection)
            
        Returns:
            List of Document objects
        """
        if file_name.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
            return loader.load()
        elif file_name.endswith((".txt", ".md")):
            # Simple text loading for .txt and .md files
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return [Document(page_content=content, metadata={"source": file_name})]
        elif file_name.endswith(".docx"):
            # Use UnstructuredFileLoader only for .docx
            loader = UnstructuredFileLoader(file_path)
            return loader.load()
        else:
            raise ValueError(f"Unsupported file type: {file_name}")
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks.
        
        Args:
            documents: List of documents to chunk
            
        Returns:
            List of chunked documents
        """
        return self.text_splitter.split_documents(documents)
    
    def process_file(
        self, 
        blob_manager, 
        file_name: str, 
        temp_dir: str = "temp"
    ) -> Tuple[List[Document], int]:
        """
        Download, load, and chunk a document from blob storage (Azure or local).
        
        Args:
            blob_manager: Blob manager instance (Azure or local)
            file_name: Name of the file to process
            temp_dir: Temporary directory for downloads
            
        Returns:
            Tuple of (chunked documents, number of chunks)
        """
        # Create temp directory if it doesn't exist
        os.makedirs(temp_dir, exist_ok=True)
        
        # Download file from blob storage
        file_content = blob_manager.download_file(file_name)
        
        # Save temporarily to local disk
        local_path = os.path.join(temp_dir, f"temp_{file_name}")
        with open(local_path, "wb") as f:
            f.write(file_content)
        
        try:
            # Load document
            documents = self.load_document(local_path, file_name)
            print(f"[DEBUG] Loaded {len(documents)} raw documents from {file_name}")
            
            # Add source metadata and ensure page number exists
            for i, doc in enumerate(documents):
                doc.metadata["source"] = file_name
                # Ensure page metadata exists (required by Azure AI Search index)
                if "page" not in doc.metadata:
                    doc.metadata["page"] = i
            
            # Chunk documents
            chunks = self.chunk_documents(documents)
            print(f"[DEBUG] Created {len(chunks)} chunks from {file_name}")
            
            return chunks, len(chunks)
        
        finally:
            # Cleanup temporary file
            if os.path.exists(local_path):
                os.remove(local_path)


class LocalFileDocumentManager:
    """Manage uploads and listings using local file system (fallback when Azure not available)."""
    
    def __init__(self, container_name: str):
        """
        Initialize the local file document manager.
        
        Args:
            container_name: Directory name to use for storing files
        """
        self.container_name = container_name
        self.storage_path = os.path.join("uploads", container_name)
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Create a dummy container_client attribute for compatibility
        class DummyContainerClient:
            def create_container(self):
                pass
        
        self.container_client = DummyContainerClient()
        
    def upload_file(self, file_name: str, file_content: bytes, overwrite: bool = True) -> dict:
        """
        Upload a file to local storage.
        
        Args:
            file_name: Name of the file
            file_content: File content as bytes
            overwrite: Whether to overwrite existing file
            
        Returns:
            Dictionary with file metadata
        """
        file_path = os.path.join(self.storage_path, file_name)
        
        if os.path.exists(file_path) and not overwrite:
            raise FileExistsError(f"File {file_name} already exists")
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        return {
            "name": file_name,
            "path": file_path,
            "size": len(file_content)
        }
    
    def list_files(self) -> list[dict]:
        """
        List all files in the local storage.
        
        Returns:
            List of file metadata dictionaries
        """
        files = []
        if os.path.exists(self.storage_path):
            for file_name in os.listdir(self.storage_path):
                file_path = os.path.join(self.storage_path, file_name)
                if os.path.isfile(file_path):
                    files.append({
                        "name": file_name,
                        "size": os.path.getsize(file_path),
                        "last_modified": os.path.getmtime(file_path)
                    })
        return files
    
    def download_file(self, file_name: str) -> bytes:
        """
        Download a file from local storage.
        
        Args:
            file_name: Name of the file to download
            
        Returns:
            File content as bytes
        """
        file_path = os.path.join(self.storage_path, file_name)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_name} not found")
        
        with open(file_path, "rb") as f:
            return f.read()
    
    def delete_file(self, file_name: str) -> bool:
        """
        Delete a file from local storage.
        
        Args:
            file_name: Name of the file to delete
            
        Returns:
            True if successful
        """
        file_path = os.path.join(self.storage_path, file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False


def create_blob_manager(container_name: str, account_url: Optional[str] = None, connection_string: Optional[str] = None):
    """
    Factory function to create a blob manager (Azure or local fallback).
    
    Args:
        container_name: Container name
        account_url: Azure Storage Account URL (preferred - uses Azure AD)
        connection_string: Connection string (uses key-based auth)
        
    Returns:
        AzureBlobDocumentManager or LocalFileDocumentManager instance
    """
    # Try to use connection string first (most reliable)
    if connection_string:
        try:
            manager = AzureBlobDocumentManager(container_name, connection_string=connection_string)
            print(f"[OK] Using Azure Blob Storage with connection string")
            return manager
        except Exception as e:
            print(f"[WARN] Failed to initialize Azure Blob Storage with connection string")
            print(f"   Falling back to local file storage")
    elif account_url:
        try:
            manager = AzureBlobDocumentManager(container_name, account_url=account_url)
            print(f"[OK] Using Azure Blob Storage with Azure AD (auth will be handled at runtime)")
            return manager
        except Exception as e:
            print(f"[WARN] Failed to initialize Azure Blob Storage: {e}")
            print(f"   Falling back to local file storage")
    
    # Fallback to local file storage
    print(f"[OK] Using local file storage in ./uploads/{container_name}")
    return LocalFileDocumentManager(container_name)


def create_document_processor(chunk_size: int = 2000, chunk_overlap: int = 200) -> DocumentProcessor:
    """
    Factory function to create a document processor.
    
    Args:
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
        
    Returns:
        DocumentProcessor instance
    """
    return DocumentProcessor(chunk_size, chunk_overlap)

"""Create the Azure AI Search index used for vector-based retrieval."""

import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchFieldDataType,
    SearchableField,
    VectorSearch,
    HnswParameters,
    VectorSearchAlgorithmConfiguration,
    VectorField
)

load_dotenv()

def create_index() -> None:
    """Build the Azure AI Search index with HNSW vector search enabled."""
    service = os.getenv("AZURE_SEARCH_SERVICE")
    index_name = os.getenv("AZURE_SEARCH_INDEX")
    api_key = os.getenv("AZURE_SEARCH_API_KEY")

    client = SearchIndexClient(
        f"https://{service}.search.windows.net",
        AzureKeyCredential(api_key),
    )

    # Dimensions must match your embedding deployment output (e.g., 1536 for ada-002 or text-embedding-3-large: 3072)
    EMBED_DIM = 1536

    vector_search = VectorSearch(
        algorithms=[
            VectorSearchAlgorithmConfiguration(
                name="hnsw-config",
                kind="hnsw",
                parameters=HnswParameters(m=4, ef_construction=400, ef_search=40),
            )
        ]
    )

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
        SimpleField(name="source", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="page", type=SearchFieldDataType.Int32, filterable=True, facetable=True),
        VectorField(
            name="content_vector",
            vector_search_dimensions=EMBED_DIM,
            vector_search_configuration="hnsw-config",
        ),
    ]

    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)

    try:
        client.create_index(index)
        print(f"Created index: {index_name}")
    except Exception as e:
        print(f"Index exists or failed: {e}")


if __name__ == "__main__":
    create_index()

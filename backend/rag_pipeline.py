import os
import time
from typing import List, Optional, AsyncGenerator

from langchain_community.vectorstores import AzureSearch as AzureSearchVS
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_core.prompts import PromptTemplate

try:
    from azure.ai.evaluation import GroundednessEvaluator
    GROUNDING_EVALUATOR_AVAILABLE = True
except ImportError:
    GROUNDING_EVALUATOR_AVAILABLE = False
    print("Warning: azure-ai-evaluation not installed. Grounding scores will use basic heuristics.")


class RAGPipeline:
    def __init__(
        self,
        *,
        azure_openai_endpoint: str,
        azure_openai_api_key: str,
        chat_deployment: str,
        embed_deployment: str,
        search_endpoint: str,
        search_key: str,
        search_index: str,
        prompt_template: str,
        api_version: str = "2024-08-01-preview",
    ) -> None:
        """Initialize RAG pipeline clients and prompt template."""
        self.azure_openai_endpoint = azure_openai_endpoint
        self.azure_openai_api_key = azure_openai_api_key
        self.chat_deployment = chat_deployment
        self.embed_deployment = embed_deployment
        self.search_endpoint = search_endpoint
        self.search_key = search_key
        self.search_index = search_index
        self.api_version = api_version

        self.prompt_template = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"],
        )

        # Try to initialize embeddings, but make it optional
        self.embeddings = None
        try:
            embeddings_obj = AzureOpenAIEmbeddings(
                azure_endpoint=self.azure_openai_endpoint,
                api_key=self.azure_openai_api_key,
                azure_deployment=self.embed_deployment,
                api_version=self.api_version,
            )
            # Note: We don't test it here to avoid timeout during initialization
            # It will be tested when actually used in get_vectorstore()
            self.embeddings = embeddings_obj
            print(f"[OK] Embeddings client created: {self.embed_deployment}")
        except Exception as e:
            print(f"[WARN] Could not initialize embeddings ({self.embed_deployment}): {str(e)}")
            print("Chat will work without document search/RAG features")
            self.embeddings = None
        
        self.llm = AzureChatOpenAI(
            azure_endpoint=self.azure_openai_endpoint,
            api_key=self.azure_openai_api_key,
            azure_deployment=self.chat_deployment,
            api_version=self.api_version,
        )

        self._vectorstore = None
        
        # Initialize grounding evaluator if available
        self._grounding_evaluator = None
        if GROUNDING_EVALUATOR_AVAILABLE:
            try:
                self._grounding_evaluator = GroundednessEvaluator(
                    model_config={
                        "azure_endpoint": self.azure_openai_endpoint,
                        "api_key": self.azure_openai_api_key,
                        "azure_deployment": self.chat_deployment,
                        "api_version": self.api_version,
                    }
                )
                print("[OK] Grounding evaluator initialized")
            except Exception as e:
                print(f"Warning: Could not initialize grounding evaluator: {e}")

    def get_vectorstore(self):
        """Return (or create) the Azure AI Search vector store using the embedding client."""
        if self.embeddings is None:
            print("[WARN] Embeddings not available - returning None (RAG search disabled)")
            return None
        if self._vectorstore is None:
            try:
                self._vectorstore = AzureSearchVS(
                    azure_search_endpoint=self.search_endpoint,
                    azure_search_key=self.search_key,
                    index_name=self.search_index,
                    embedding_function=self.embeddings.embed_query,
                )
                print(f"[OK] Vectorstore initialized: {self.search_index}")
            except Exception as e:
                print(f"[WARN] Could not initialize vectorstore: {str(e)}")
                print("RAG search will be disabled")
                return None
        return self._vectorstore

    def _search(self, query: str, top_k: int):
        """Run hybrid search with vector+keyword, falling back to vector-only if needed."""
        vs = self.get_vectorstore()
        if vs is None:
            return []  # Return empty list if vectorstore not available
        try:
            return vs.similarity_search(query, k=top_k, search_type="hybrid")
        except Exception:
            return vs.similarity_search(query, k=top_k)

    @staticmethod
    def _build_context(docs) -> str:
        """Concatenate retrieved docs into a single context string with source labels."""
        return "\n\n".join(
            [f"Document: {doc.metadata.get('source', 'Unknown')}\n{doc.page_content}" for doc in docs]
        )

    @staticmethod
    def _dedupe_sources(docs) -> List[dict]:
        """Merge chunks by source name to keep a single entry per document."""
        sources_dict = {}
        for d in docs:
            source_name = d.metadata.get("source", "")
            if source_name not in sources_dict:
                sources_dict[source_name] = d.page_content
            else:
                sources_dict[source_name] += f"\n\n---\n\n{d.page_content}"
        return [{"source": name, "content": content} for name, content in sources_dict.items()]
    
    def _calculate_grounding_score(self, answer: str, context: str) -> float:
        """
        Calculate grounding score (0-5 scale) using Azure AI Evaluation or fallback heuristics.
        
        Args:
            answer: The generated answer
            context: The retrieved context used to generate the answer
            
        Returns:
            Score from 0-5 where 5 is fully grounded
        """
        if self._grounding_evaluator:
            try:
                # Use Azure AI Evaluation grounding evaluator
                result = self._grounding_evaluator(
                    answer=answer,
                    context=context
                )
                # The evaluator returns a score, typically 1-5
                return result.get("groundedness", 0)
            except Exception as e:
                print(f"Warning: Grounding evaluation failed, using fallback: {e}")
        
        # Fallback heuristic scoring (0-5 scale)
        ungrounded_phrases = (
            "i don't have",
            "not in the",
            "no information",
            "cannot find",
            "not available",
            "not mentioned",
            "not provided",
            "don't have this information",
        )
        
        answer_lower = answer.lower()
        has_ungrounded_phrase = any(p in answer_lower for p in ungrounded_phrases)
        
        # Remove ungrounded phrases and check meaningful content
        answer_without_ungrounded = answer_lower
        for phrase in ungrounded_phrases:
            answer_without_ungrounded = answer_without_ungrounded.replace(phrase, "")
        
        meaningful_content_length = len(answer_without_ungrounded.strip())
        
        if meaningful_content_length > 200 and not has_ungrounded_phrase:
            return 5.0  # Fully grounded with substantial content
        elif meaningful_content_length > 200 and has_ungrounded_phrase:
            return 3.5  # Substantial content but mentions missing info
        elif meaningful_content_length > 100 and not has_ungrounded_phrase:
            return 4.0  # Good content, fully grounded
        elif meaningful_content_length > 100:
            return 2.5  # Some content but partially ungrounded
        elif meaningful_content_length > 50:
            return 2.0  # Minimal content
        else:
            return 1.0  # Very little or no grounded content

    def chat(self, query: str, top_k: int):
        """Retrieve, build context, generate an answer, and return answer + sources + reasoning."""
        start = time.time()
        docs = self._search(query, top_k)
        search_time = time.time() - start

        context = self._build_context(docs)
        prompt_text = self.prompt_template.format(context=context, question=query)

        llm_start = time.time()
        answer = self.llm.invoke(prompt_text).content
        llm_time = time.time() - llm_start

        sources = self._dedupe_sources(docs)
        
        # Calculate grounding score using Azure AI Evaluation or fallback heuristics
        grounding_score = self._calculate_grounding_score(answer, context)
        
        # Determine if grounded (score >= 3 out of 5)
        is_grounded = grounding_score >= 3.0

        total_time = time.time() - start
        reasoning_log = [
            {
                "phase": "Retrieval",
                "details": f"Retrieved {len(docs)} documents using hybrid search",
                "duration": f"{search_time:.2f}s",
            },
            {
                "phase": "Generation",
                "details": f"Model: {self.chat_deployment} | Context size: {len(context)} chars",
                "duration": f"{llm_time:.2f}s",
            },
            {
                "phase": "Grounding",
                "details": f"Score: {grounding_score:.1f}/5.0 | {'Fully grounded' if is_grounded else 'Partially grounded'}",
                "duration": "N/A",
            },
            {
                "phase": "Total", 
                "details": "End-to-end response time", 
                "duration": f"{total_time:.2f}s"
            },
        ]

        return {
            "answer": answer,
            "sources": sources,
            "agentic": is_grounded,
            "grounding_score": grounding_score,
            "reasoning_log": reasoning_log,
        }

    async def stream_chat(self, query: str, top_k: int) -> AsyncGenerator[bytes, None]:
        """Stream the LLM answer text while using the same retrieval + prompt context."""
        docs = self._search(query, top_k)
        context = self._build_context(docs)
        prompt_text = self.prompt_template.format(context=context, question=query)

        streaming_llm = AzureChatOpenAI(
            azure_endpoint=self.azure_openai_endpoint,
            api_key=self.azure_openai_api_key,
            azure_deployment=self.chat_deployment,
            streaming=True,
            api_version=self.api_version,
        )

        try:
            async for chunk in streaming_llm.astream(prompt_text):
                if chunk.content:
                    yield chunk.content.encode("utf-8")
        except Exception as e:
            yield f"\n\nError: {str(e)}".encode("utf-8")

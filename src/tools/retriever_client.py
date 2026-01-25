"""
NeMo Retriever Client for Embeddings and Reranking

Optional tools for RAG-enhanced strategy generation:
- Text embedding via NeMo Retriever Embedding NIM
- Reranking via NeMo Retriever Reranking NIM

These services help ground Nemotron outputs in relevant context.
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import requests
from requests.exceptions import RequestException

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils.config import Config

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result from embedding request"""
    embeddings: List[List[float]]
    model: str
    usage: Dict[str, int]


@dataclass
class RerankResult:
    """Result from reranking request"""
    rankings: List[Dict[str, Any]]  # [{"index": 0, "score": 0.95, "text": "..."}]
    model: str


class RetrieverClient:
    """
    Client for NeMo Retriever NIM microservices.
    
    Provides:
    - Text embeddings for semantic similarity
    - Reranking for citation relevance ordering
    
    Example usage:
        client = RetrieverClient()
        
        # Get embeddings
        embeddings = client.embed_texts(["text1", "text2"])
        
        # Rerank candidates
        rankings = client.rerank("query", ["doc1", "doc2", "doc3"])
    """
    
    def __init__(
        self,
        embedding_url: str = None,
        reranking_url: str = None,
        api_key: str = None,
    ):
        self.embedding_url = embedding_url or Config.EMBEDDING_NIM_URL
        self.reranking_url = reranking_url or Config.RERANKING_NIM_URL
        self.api_key = api_key or Config.NEMOTRON_API_KEY
    
    def is_embedding_available(self) -> bool:
        """Check if embedding service is available"""
        try:
            response = requests.get(f"{self.embedding_url}/health", timeout=5)
            return response.status_code == 200
        except RequestException:
            return False
    
    def is_reranking_available(self) -> bool:
        """Check if reranking service is available"""
        try:
            response = requests.get(f"{self.reranking_url}/health", timeout=5)
            return response.status_code == 200
        except RequestException:
            return False
    
    def embed_texts(
        self,
        texts: List[str],
        model: str = "nv-embedqa-e5-v5",
    ) -> Optional[EmbeddingResult]:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed
            model: Embedding model name
        
        Returns:
            EmbeddingResult or None if service unavailable
        """
        if not texts:
            return EmbeddingResult(embeddings=[], model=model, usage={})
        
        try:
            url = f"{self.embedding_url}/embeddings"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {
                "model": model,
                "input": texts,
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            embeddings = [item["embedding"] for item in data.get("data", [])]
            
            return EmbeddingResult(
                embeddings=embeddings,
                model=data.get("model", model),
                usage=data.get("usage", {}),
            )
            
        except RequestException as e:
            logger.warning(f"Embedding request failed: {e}")
            return None
    
    def rerank(
        self,
        query: str,
        candidates: List[str],
        model: str = "nv-rerank-qa-mistral-4b:1",
        top_n: int = None,
    ) -> Optional[RerankResult]:
        """
        Rerank candidate documents by relevance to query.
        
        Args:
            query: Query string
            candidates: List of candidate documents
            model: Reranking model name
            top_n: Return only top N results
        
        Returns:
            RerankResult or None if service unavailable
        """
        if not candidates:
            return RerankResult(rankings=[], model=model)
        
        try:
            url = f"{self.reranking_url}/rerank"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {
                "model": model,
                "query": query,
                "documents": candidates,
            }
            if top_n:
                payload["top_n"] = top_n
            
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            # Format rankings with original text
            rankings = []
            for item in data.get("results", []):
                idx = item.get("index", 0)
                rankings.append({
                    "index": idx,
                    "score": item.get("relevance_score", 0.0),
                    "text": candidates[idx] if idx < len(candidates) else "",
                })
            
            return RerankResult(
                rankings=rankings,
                model=data.get("model", model),
            )
            
        except RequestException as e:
            logger.warning(f"Reranking request failed: {e}")
            return None
    
    def semantic_search(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using embeddings.
        
        If reranking is available, uses it for better accuracy.
        Falls back to cosine similarity with embeddings.
        
        Args:
            query: Search query
            documents: Documents to search
            top_k: Number of results to return
        
        Returns:
            List of {index, score, text} dicts
        """
        if not documents:
            return []
        
        # Try reranking first (more accurate)
        if self.is_reranking_available():
            result = self.rerank(query, documents, top_n=top_k)
            if result:
                return result.rankings[:top_k]
        
        # Fall back to embedding similarity
        if self.is_embedding_available():
            return self._embedding_search(query, documents, top_k)
        
        # No retrieval services available
        logger.warning("No retrieval services available, returning empty results")
        return []
    
    def _embedding_search(
        self,
        query: str,
        documents: List[str],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Internal embedding-based search"""
        import numpy as np
        
        # Get all embeddings
        all_texts = [query] + documents
        result = self.embed_texts(all_texts)
        
        if not result or len(result.embeddings) < 2:
            return []
        
        query_emb = np.array(result.embeddings[0])
        doc_embs = np.array(result.embeddings[1:])
        
        # Compute cosine similarities
        query_norm = query_emb / np.linalg.norm(query_emb)
        doc_norms = doc_embs / np.linalg.norm(doc_embs, axis=1, keepdims=True)
        similarities = np.dot(doc_norms, query_norm)
        
        # Get top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append({
                "index": int(idx),
                "score": float(similarities[idx]),
                "text": documents[idx],
            })
        
        return results


# Convenience functions
def embed_texts(texts: List[str]) -> List[List[float]]:
    """Simple function to embed texts"""
    client = RetrieverClient()
    result = client.embed_texts(texts)
    return result.embeddings if result else []


def rerank(query: str, candidates: List[str]) -> List[Dict[str, Any]]:
    """Simple function to rerank candidates"""
    client = RetrieverClient()
    result = client.rerank(query, candidates)
    return result.rankings if result else []

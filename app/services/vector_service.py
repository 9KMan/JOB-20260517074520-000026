from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.core.config import get_settings

settings = get_settings()
embeddings = OpenAIEmbeddings(api_key=settings.openai_api_key, model="text-embedding-3-small")


class TextSplitter:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )

    def split_documents(self, documents: List[str]) -> List[str]:
        chunks = []
        for doc in documents:
            chunks.extend(self.splitter.split_text(doc))
        return chunks


class VectorStore:
    def __init__(self):
        self.embedding_model = embeddings

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return await self.embedding_model.aembed_documents(texts)

    async def search_similar(
        self,
        query: str,
        embeddings_matrix: List[List[float]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        query_embedding = await self.embedding_model.aembed_query(query)

        similarities = []
        for i, embedding in enumerate(embeddings_matrix):
            similarity = self._cosine_similarity(query_embedding, embedding)
            similarities.append((i, similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)
        top_results = similarities[:top_k]

        return [{"index": idx, "score": score} for idx, score in top_results]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        return dot_product / (norm1 * norm2) if norm1 and norm2 else 0


class RAGService:
    def __init__(self):
        self.vector_store = VectorStore()
        self.text_splitter = TextSplitter()

    def prepare_documents(self, documents: List[str], chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
        self.text_splitter.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return self.text_splitter.split_documents(documents)

    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        return await self.vector_store.embed_texts(texts)

    async def retrieve_relevant(
        self,
        query: str,
        embeddings_matrix: List[List[float]],
        chunks: List[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        results = await self.vector_store.search_similar(query, embeddings_matrix, top_k)

        enriched_results = []
        for result in results:
            enriched_results.append({
                "chunk_text": chunks[result["index"]],
                "score": result["score"],
                "index": result["index"],
            })

        return enriched_results


rag_service = RAGService()
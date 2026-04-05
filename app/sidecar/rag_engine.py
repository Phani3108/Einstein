"""
RAG Engine — Retrieval-Augmented Generation for Einstein.
Chunks notes, builds vector index, retrieves relevant context,
and generates answers with source citations.
"""

import os
import json
import time
import logging
import asyncio
from typing import Optional, AsyncGenerator
from dataclasses import dataclass, field, asdict
from pydantic import BaseModel, Field

LOG = logging.getLogger("einstein-sidecar")

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class Chunk:
    """A chunk of a note for embedding."""
    chunk_id: str
    note_id: str
    note_title: str
    content: str
    start_pos: int
    end_pos: int


@dataclass
class ChunkResult:
    """A retrieved chunk with similarity score."""
    chunk: Chunk
    score: float


class RAGIndexRequest(BaseModel):
    notes: list[dict] = Field(..., description="List of {id, title, content}")


class RAGIndexResponse(BaseModel):
    status: str = "ok"
    indexed: int = 0
    chunks: int = 0
    provider: str = ""


class RAGAskRequest(BaseModel):
    question: str = Field(..., description="Natural language question")
    conversation_history: list[dict] = Field(default_factory=list)
    top_k: int = Field(default=10, ge=1, le=50)


class RAGSource(BaseModel):
    note_id: str
    title: str
    snippet: str
    score: float


class RAGStatusResponse(BaseModel):
    indexed: int = 0
    chunks: int = 0
    ready: bool = False
    provider: str = ""
    model: str = ""
    last_indexed: Optional[str] = None


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def chunk_note(
    content: str,
    note_id: str,
    note_title: str,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[Chunk]:
    """Split note content into overlapping chunks for embedding."""
    if not content or not content.strip():
        return []

    # Split by paragraphs first for more natural chunks
    paragraphs = content.split("\n\n")
    chunks = []
    current_chunk = ""
    current_start = 0
    char_pos = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            char_pos += 2  # \n\n
            continue

        # If adding this paragraph exceeds chunk_size, flush current chunk
        if current_chunk and len(current_chunk) + len(para) + 2 > chunk_size:
            chunks.append(
                Chunk(
                    chunk_id=f"{note_id}:{len(chunks)}",
                    note_id=note_id,
                    note_title=note_title,
                    content=current_chunk.strip(),
                    start_pos=current_start,
                    end_pos=char_pos,
                )
            )
            # Keep overlap from end of previous chunk
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + "\n\n" + para
            else:
                current_chunk = para
            current_start = max(0, char_pos - overlap)
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
                current_start = char_pos

        char_pos += len(para) + 2

    # Flush remaining
    if current_chunk.strip():
        chunks.append(
            Chunk(
                chunk_id=f"{note_id}:{len(chunks)}",
                note_id=note_id,
                note_title=note_title,
                content=current_chunk.strip(),
                start_pos=current_start,
                end_pos=char_pos,
            )
        )

    return chunks


# ---------------------------------------------------------------------------
# Vector Index (FAISS or fallback numpy cosine)
# ---------------------------------------------------------------------------


class VectorIndex:
    """In-memory vector index. Uses FAISS if available, falls back to numpy."""

    def __init__(self):
        self.chunks: list[Chunk] = []
        self.vectors: list[list[float]] = []
        self.dimension: int = 0
        self.last_indexed: Optional[str] = None
        self._faiss_index = None
        self._use_faiss = False

        try:
            import faiss
            self._use_faiss = True
            LOG.info("FAISS available — using optimized vector search")
        except ImportError:
            LOG.info("FAISS not available — using numpy cosine similarity fallback")

    def build(self, chunks: list[Chunk], vectors: list[list[float]]):
        """Build the index from chunks and their embedding vectors."""
        if not chunks or not vectors:
            return

        self.chunks = chunks
        self.vectors = vectors
        self.dimension = len(vectors[0])
        self.last_indexed = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if self._use_faiss:
            self._build_faiss(vectors)

        LOG.info(f"Index built: {len(chunks)} chunks, dimension={self.dimension}")

    def _build_faiss(self, vectors: list[list[float]]):
        """Build FAISS index."""
        import faiss
        import numpy as np

        data = np.array(vectors, dtype=np.float32)
        # Normalize for cosine similarity
        faiss.normalize_L2(data)
        self._faiss_index = faiss.IndexFlatIP(self.dimension)
        self._faiss_index.add(data)

    def search(self, query_vector: list[float], top_k: int = 10) -> list[ChunkResult]:
        """Search for most similar chunks to the query vector."""
        if not self.chunks:
            return []

        if self._use_faiss and self._faiss_index is not None:
            return self._search_faiss(query_vector, top_k)
        else:
            return self._search_numpy(query_vector, top_k)

    def _search_faiss(self, query_vector: list[float], top_k: int) -> list[ChunkResult]:
        """Search using FAISS."""
        import faiss
        import numpy as np

        query = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(query)
        k = min(top_k, len(self.chunks))
        scores, indices = self._faiss_index.search(query, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.chunks):
                results.append(ChunkResult(chunk=self.chunks[idx], score=float(score)))
        return results

    def _search_numpy(self, query_vector: list[float], top_k: int) -> list[ChunkResult]:
        """Fallback: cosine similarity using numpy or pure Python."""
        try:
            import numpy as np

            query = np.array(query_vector, dtype=np.float32)
            query = query / max(np.linalg.norm(query), 1e-10)

            data = np.array(self.vectors, dtype=np.float32)
            norms = np.linalg.norm(data, axis=1, keepdims=True)
            norms = np.maximum(norms, 1e-10)
            data = data / norms

            scores = data @ query
            top_indices = np.argsort(scores)[::-1][:top_k]

            return [
                ChunkResult(chunk=self.chunks[i], score=float(scores[i]))
                for i in top_indices
            ]
        except ImportError:
            # Pure Python fallback
            return self._search_pure_python(query_vector, top_k)

    def _search_pure_python(self, query_vector: list[float], top_k: int) -> list[ChunkResult]:
        """Pure Python cosine similarity — no numpy required."""
        def cosine_sim(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(x * x for x in b) ** 0.5
            return dot / max(norm_a * norm_b, 1e-10)

        scored = [
            ChunkResult(chunk=self.chunks[i], score=cosine_sim(query_vector, self.vectors[i]))
            for i in range(len(self.chunks))
        ]
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    @property
    def indexed_count(self) -> int:
        """Number of unique notes indexed."""
        return len(set(c.note_id for c in self.chunks))

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)


# ---------------------------------------------------------------------------
# RAG Engine
# ---------------------------------------------------------------------------


class RAGEngine:
    """Main RAG orchestrator — indexes notes, retrieves context, generates answers."""

    def __init__(self):
        self.index = VectorIndex()
        self._indexing = False

    async def index_notes(self, notes: list[dict]) -> RAGIndexResponse:
        """Chunk and embed all notes into the vector index."""
        from embedding_adapter import get_embeddings, get_provider_info

        if self._indexing:
            return RAGIndexResponse(status="already_indexing", indexed=0, chunks=0)

        self._indexing = True
        try:
            # Chunk all notes
            all_chunks: list[Chunk] = []
            for note in notes:
                note_id = note.get("id", "")
                title = note.get("title", "Untitled")
                content = note.get("content", "")
                if not content.strip():
                    continue
                chunks = chunk_note(content, note_id, title)
                all_chunks.extend(chunks)

            if not all_chunks:
                return RAGIndexResponse(status="ok", indexed=0, chunks=0)

            # Generate embeddings for all chunks
            texts = [c.content for c in all_chunks]
            LOG.info(f"Embedding {len(texts)} chunks...")

            # Batch embeddings to avoid memory issues
            batch_size = 50
            all_vectors: list[list[float]] = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                vectors = await get_embeddings(batch)
                all_vectors.extend(vectors)

            # Build the index
            self.index.build(all_chunks, all_vectors)

            provider_info = get_provider_info()
            return RAGIndexResponse(
                status="ok",
                indexed=self.index.indexed_count,
                chunks=self.index.chunk_count,
                provider=provider_info["provider"],
            )
        finally:
            self._indexing = False

    async def ask(
        self,
        question: str,
        conversation_history: list[dict] | None = None,
        top_k: int = 10,
    ) -> AsyncGenerator[dict, None]:
        """
        Answer a question using RAG.
        Yields SSE-style dicts: {type: "chunk"/"sources"/"done", ...}
        """
        from embedding_adapter import get_embedding

        if not self.index.chunks:
            yield {"type": "chunk", "content": "No notes have been indexed yet. Please index your notes first using the 'Index Notes' button."}
            yield {"type": "done"}
            return

        # 1. Embed the question
        query_vector = await get_embedding(question)

        # 2. Retrieve top-K chunks
        results = self.index.search(query_vector, top_k=top_k)

        if not results:
            yield {"type": "chunk", "content": "I couldn't find any relevant notes to answer your question. Try rephrasing or adding more notes."}
            yield {"type": "done"}
            return

        # 3. Build RAG context
        context_parts = []
        sources: list[RAGSource] = []
        seen_notes = set()

        for r in results:
            context_parts.append(
                f"[Source: {r.chunk.note_title}]\n{r.chunk.content}"
            )
            if r.chunk.note_id not in seen_notes:
                seen_notes.add(r.chunk.note_id)
                sources.append(
                    RAGSource(
                        note_id=r.chunk.note_id,
                        title=r.chunk.note_title,
                        snippet=r.chunk.content[:150] + "..." if len(r.chunk.content) > 150 else r.chunk.content,
                        score=round(r.score, 3),
                    )
                )

        context = "\n\n---\n\n".join(context_parts)

        # 4. Build the RAG prompt
        system_prompt = """You are Einstein, an AI assistant that answers questions based on the user's personal notes.

RULES:
- Answer ONLY based on the provided note excerpts below. Do not make up information.
- If the notes don't contain enough information to fully answer, say so honestly.
- Cite your sources by mentioning the note title in brackets, e.g., [Meeting Notes] or [Project Ideas].
- Be concise but thorough. Use markdown formatting for clarity.
- If multiple notes are relevant, synthesize the information across them.
- Maintain a helpful, knowledgeable tone."""

        user_prompt = f"""Here are relevant excerpts from the user's notes:

{context}

---

Question: {question}

Answer based on the notes above, citing sources:"""

        # Include conversation history if provided
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            for msg in conversation_history[-6:]:  # Keep last 3 exchanges
                messages.append(msg)
        messages.append({"role": "user", "content": user_prompt})

        # 5. Stream LLM response
        try:
            import litellm

            litellm.drop_params = True

            model = os.environ.get("EINSTEIN_LLM_MODEL", "gpt-4o-mini")
            provider = os.environ.get("EINSTEIN_LLM_PROVIDER", "openai")

            if provider == "ollama":
                model = f"ollama/{model}"
            elif provider == "anthropic":
                model = f"anthropic/{model}"

            response = await litellm.acompletion(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
                stream=True,
                api_key=os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or None,
                api_base=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434") if provider == "ollama" else None,
            )

            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield {"type": "chunk", "content": delta.content}

        except ImportError:
            # Fallback: non-streaming
            from server import call_llm
            full_response = await call_llm(system_prompt, user_prompt)
            yield {"type": "chunk", "content": full_response}
        except Exception as e:
            LOG.error(f"RAG generation error: {e}")
            yield {"type": "chunk", "content": f"Error generating answer: {str(e)}"}

        # 6. Yield sources
        yield {
            "type": "sources",
            "sources": [s.model_dump() for s in sources],
        }
        yield {"type": "done"}

    def get_status(self) -> RAGStatusResponse:
        """Return current index status."""
        from embedding_adapter import get_provider_info

        provider_info = get_provider_info()
        return RAGStatusResponse(
            indexed=self.index.indexed_count,
            chunks=self.index.chunk_count,
            ready=self.index.chunk_count > 0,
            provider=provider_info["provider"],
            model=provider_info["model"],
            last_indexed=self.index.last_indexed,
        )


# Global RAG engine instance
rag_engine = RAGEngine()

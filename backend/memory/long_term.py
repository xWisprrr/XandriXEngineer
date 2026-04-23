import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

COLLECTIONS = ["code_snippets", "solutions", "errors", "general"]


@dataclass
class MemoryResult:
    content: str
    metadata: Dict[str, Any]
    score: float
    id: str


class _InMemoryFallback:
    """Simple in-memory fallback when ChromaDB is unavailable."""

    def __init__(self) -> None:
        self._store: Dict[str, List[Dict[str, Any]]] = {}

    def add(self, collection: str, doc_id: str, content: str, metadata: Dict[str, Any]) -> None:
        self._store.setdefault(collection, [])
        self._store[collection].append({"id": doc_id, "content": content, "metadata": metadata})

    def search(self, collection: str, query: str, n_results: int) -> List[MemoryResult]:
        items = self._store.get(collection, [])
        # Simple substring match as fallback
        results = [
            MemoryResult(content=item["content"], metadata=item["metadata"], score=0.5, id=item["id"])
            for item in items
            if query.lower() in item["content"].lower()
        ]
        return results[:n_results]

    def delete(self, collection: str, doc_id: str) -> None:
        items = self._store.get(collection, [])
        self._store[collection] = [i for i in items if i["id"] != doc_id]


class LongTermMemory:
    def __init__(self, persist_dir: str = "./data/chroma") -> None:
        self.persist_dir = persist_dir
        self._client = None
        self._collections: Dict[str, Any] = {}
        self._fallback = _InMemoryFallback()
        self._use_fallback = False
        self._initialized = False

    def _initialize(self) -> None:
        if self._initialized:
            return
        try:
            import chromadb
            import os
            os.makedirs(self.persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_dir)
            for col in COLLECTIONS:
                self._collections[col] = self._client.get_or_create_collection(name=col)
            logger.info("ChromaDB initialized successfully")
        except ImportError:
            logger.warning("chromadb not installed, using in-memory fallback")
            self._use_fallback = True
        except Exception as exc:
            logger.warning(f"ChromaDB initialization failed: {exc}, using in-memory fallback")
            self._use_fallback = True
        self._initialized = True

    def store(self, content: str, metadata: Optional[Dict[str, Any]] = None, collection: str = "general") -> str:
        self._initialize()
        doc_id = str(uuid.uuid4())
        meta = metadata or {}
        if self._use_fallback:
            self._fallback.add(collection, doc_id, content, meta)
            return doc_id
        try:
            col = self._collections.get(collection)
            if col is None:
                col = self._client.get_or_create_collection(name=collection)
                self._collections[collection] = col
            col.add(documents=[content], metadatas=[meta], ids=[doc_id])
            return doc_id
        except Exception as exc:
            logger.error(f"LongTermMemory store error: {exc}")
            self._fallback.add(collection, doc_id, content, meta)
            return doc_id

    def search(self, query: str, collection: str = "general", n_results: int = 5) -> List[MemoryResult]:
        self._initialize()
        if self._use_fallback:
            return self._fallback.search(collection, query, n_results)
        try:
            col = self._collections.get(collection)
            if col is None:
                return []
            results = col.query(query_texts=[query], n_results=min(n_results, col.count() or 1))
            memories: List[MemoryResult] = []
            if results and results.get("documents"):
                docs = results["documents"][0]
                metas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0]
                ids = results.get("ids", [[]])[0]
                for doc, meta, dist, rid in zip(docs, metas, distances, ids):
                    memories.append(
                        MemoryResult(
                            content=doc,
                            metadata=meta or {},
                            score=1.0 - (dist or 0),
                            id=rid,
                        )
                    )
            return memories
        except Exception as exc:
            logger.error(f"LongTermMemory search error: {exc}")
            return self._fallback.search(collection, query, n_results)

    def delete(self, doc_id: str, collection: str = "general") -> None:
        self._initialize()
        if self._use_fallback:
            self._fallback.delete(collection, doc_id)
            return
        try:
            col = self._collections.get(collection)
            if col:
                col.delete(ids=[doc_id])
        except Exception as exc:
            logger.error(f"LongTermMemory delete error: {exc}")


long_term_memory = LongTermMemory()

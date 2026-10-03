import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import chromadb
from app.config import settings

class VectorService:
    _instance = None

    def __init__(self, persist_dir: str = settings.CHROMA_PERSIST_DIR):
        print(f"🔄 Initializing persistent ChromaDB at '{persist_dir}'...")
        os.makedirs(persist_dir, exist_ok=True)
        registry_dir = Path(settings.DOCUMENTS_REGISTRY_PATH).parent
        os.makedirs(registry_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(name="pdf_docs")
        self.registry_path = Path(settings.DOCUMENTS_REGISTRY_PATH)
        print("✅ ChromaDB persistent client initialized successfully.")

    @classmethod
    def get_instance(cls) -> "VectorService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_registry(self) -> Dict[str, Dict[str, Any]]:
        if not self.registry_path.exists():
            return {}
        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_registry(self, registry: Dict[str, Dict[str, Any]]) -> None:
        try:
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Warning: Failed to save document registry: {e}")

    def add_document_chunks(
        self,
        document_id: str,
        filename: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        number_of_pages: int,
    ) -> None:
        """Stores chunk embeddings, text, and metadata in ChromaDB, isolated by document_id."""
        if not chunks:
            raise ValueError("No chunks to store.")

        ids = [c["id"] for c in chunks]
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        # Add to ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        # Update persistent registry
        registry = self._load_registry()
        registry[document_id] = {
            "document_id": document_id,
            "filename": filename,
            "number_of_pages": number_of_pages,
            "number_of_chunks": len(chunks),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_registry(registry)

    def document_exists(self, document_id: str) -> bool:
        registry = self._load_registry()
        if document_id in registry:
            return True
        # Fallback check against Chroma collection
        results = self.collection.get(where={"document_id": document_id}, limit=1)
        return bool(results and results.get("ids"))

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        registry = self._load_registry()
        if document_id in registry:
            return registry[document_id]
        
        # Fallback query from ChromaDB
        results = self.collection.get(where={"document_id": document_id}, include=["metadatas"])
        if results and results.get("metadatas"):
            meta = results["metadatas"][0]
            return {
                "document_id": document_id,
                "filename": meta.get("document_name", "document.pdf"),
                "number_of_pages": 1,
                "number_of_chunks": len(results["metadatas"]),
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            }
        return None

    def list_documents(self) -> List[Dict[str, Any]]:
        registry = self._load_registry()
        return list(registry.values())

    def delete_document(self, document_id: str) -> bool:
        """
        Deletes all chunks and metadata associated with document_id from ChromaDB
        and removes the document from the persistent registry.
        """
        registry = self._load_registry()
        existed = document_id in registry

        # 1. Delete all vectors from ChromaDB matching document_id
        try:
            self.collection.delete(where={"document_id": document_id})
            existed = True
        except Exception as e:
            print(f"Warning during ChromaDB deletion for {document_id}: {e}")

        # 2. Remove from JSON registry
        if document_id in registry:
            del registry[document_id]
            self._save_registry(registry)
            existed = True

        return existed

    def get_leading_chunks(self, document_id: str, max_chunks: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve early chunks (e.g. chunk index 0, 1, 2) which contain title,
        abstract, table of contents, and introductory project details.
        """
        try:
            results = self.collection.get(
                where={"document_id": document_id},
                include=["documents", "metadatas"],
            )
            sources = []
            if results and results.get("documents"):
                docs = results["documents"]
                metas = results.get("metadatas", [])
                for idx, doc_text in enumerate(docs):
                    meta = metas[idx] if idx < len(metas) else {}
                    sources.append({
                        "page": meta.get("page", 1),
                        "text": doc_text,
                        "chunk_index": meta.get("chunk_index", idx),
                    })
            # Sort by chunk_index ascending and return the first max_chunks
            sources.sort(key=lambda s: s.get("chunk_index", 0))
            return sources[:max_chunks]
        except Exception as e:
            print(f"Warning retrieving leading chunks for {document_id}: {e}")
            return []

    def query_document(
        self,
        document_id: str,
        query_embedding: List[float],
        top_k: int = settings.TOP_K_CHUNKS,
    ) -> List[Dict[str, Any]]:
        """
        Query ChromaDB strictly scoped to document_id.
        Guarantees that chunks from different documents are never mixed.
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"document_id": document_id},
        )

        sources = []
        if results and results.get("documents") and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else []
            for idx, doc_text in enumerate(docs):
                meta = metas[idx] if idx < len(metas) else {}
                sources.append({
                    "page": meta.get("page", 1),
                    "text": doc_text,
                    "chunk_index": meta.get("chunk_index"),
                })
        return sources

def get_vector_service() -> VectorService:
    return VectorService.get_instance()


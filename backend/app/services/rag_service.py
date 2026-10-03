import uuid
import re
from typing import List, Optional, Any
from app.config import settings
from app.models import DocumentUploadResponse, DocumentInfo, ChatResponse, SourceChunk
from app.services.pdf_service import PDFService
from app.services.embedding_service import get_embedding_service, EmbeddingService
from app.services.vector_service import get_vector_service, VectorService
from app.services.llm_service import get_llm_service, LLMService

class DocumentNotFoundError(Exception):
    pass

class RAGService:
    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        vector_service: Optional[VectorService] = None,
        llm_service: Optional[LLMService] = None,
    ):
        self.embedding_service = embedding_service or get_embedding_service()
        self.vector_service = vector_service or get_vector_service()
        self.llm_service = llm_service or get_llm_service()

    def process_and_index_document(self, file_bytes: bytes, filename: str) -> DocumentUploadResponse:
        """
        Processes PDF into chunks, generates embeddings, and saves to ChromaDB.
        """
        document_id = f"doc_{uuid.uuid4().hex[:12]}"

        # 1. Parse and chunk with PyMuPDF
        chunks, total_pages = PDFService.process_pdf(
            file_bytes=file_bytes,
            filename=filename,
            document_id=document_id,
            chunk_size=settings.CHUNK_SIZE,
            overlap=settings.CHUNK_OVERLAP,
        )

        # 2. Generate embeddings with SentenceTransformer
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_service.embed_texts(texts)

        # 3. Store in persistent ChromaDB with document scoping
        self.vector_service.add_document_chunks(
            document_id=document_id,
            filename=filename,
            chunks=chunks,
            embeddings=embeddings,
            number_of_pages=total_pages,
        )

        return DocumentUploadResponse(
            document_id=document_id,
            filename=filename,
            number_of_pages=total_pages,
            number_of_chunks=len(chunks),
            message=f"Successfully indexed {len(chunks)} chunks across {total_pages} page(s).",
        )

    @staticmethod
    def _is_toc_chunk(text: str) -> bool:
        """
        Detects pure Table of Contents chunks containing dotted leaders (e.g. '. . . . .').
        """
        dots_count = len(re.findall(r"\.\s*\.\s*\.\s*\.", text))
        if dots_count >= 2:
            return True
        if text.strip().startswith("Contents\n") and dots_count >= 1:
            return True
        return False

    @staticmethod
    def _resolve_contextual_question(question: str, history: Optional[List[Any]]) -> str:
        """
        Resolves conversational follow-ups (e.g. 'explain it', 'what does it do', 'tell me more')
        by combining the current query with the previous user context.
        """
        clean_q = question.strip()
        if not history:
            return clean_q

        ql = clean_q.lower()
        referential_markers = [
            "it", "this", "that", "them", "these", "the model", "the approach",
            "the methodology", "its", "their", "explain it", "tell me more",
            "elaborate", "how does it", "what about it", "explain that"
        ]
        tokens = ql.split()
        is_referential = any(m in ql for m in referential_markers) or len(tokens) <= 3

        if is_referential:
            for h in reversed(history):
                role = getattr(h, "role", None) or (h.get("role") if isinstance(h, dict) else "")
                text = getattr(h, "text", None) or (h.get("text") if isinstance(h, dict) else "")
                if role == "user" and text and str(text).strip():
                    return f"{str(text).strip()} {clean_q}"
        return clean_q

    @staticmethod
    def _is_methodology_or_architecture_question(question: str) -> bool:
        ql = question.lower()
        keywords = [
            "methodology", "method", "methods", "architecture", "approach",
            "pipeline", "framework", "plain hgt", "kg-hgt", "graph transformer",
            "attention", "message passing", "relation gates", "severity head",
            "how does the model", "how it works", "how does it work",
            "components", "explain the", "describe the model", "proposed model",
            "auxiliary", "graph learning", "model architecture", "baseline",
            "patient conditioning", "patient-conditioned"
        ]
        return any(k in ql for k in keywords)

    @staticmethod
    def _is_overview_question(question: str) -> bool:
        ql = question.lower()
        overview_terms = [
            "topic", "about", "summary", "summarize", "objective", "objectives",
            "btp", "project", "overview", "title", "main theme", "purpose", "scope",
            "what does this document", "what is this document"
        ]
        return any(term in ql for term in overview_terms)

    def answer_question(
        self,
        document_id: str,
        question: str,
        history: Optional[List[Any]] = None,
    ) -> ChatResponse:
        """
        Answers a user question strictly using context retrieved from the specified document.
        - Resolves conversational follow-ups using conversation history.
        - Dynamically expands retrieval depth (top-k=10-12) for methodology/architecture questions.
        - Excludes pure Table of Contents chunks so explanatory paragraphs are prioritized.
        - Synthesizes conceptual explanations via Gemini.
        """
        # Validate document exists
        if not self.vector_service.document_exists(document_id):
            raise DocumentNotFoundError(f"Document with ID '{document_id}' not found.")

        clean_question = question.strip()
        search_query = self._resolve_contextual_question(clean_question, history)

        retrieved: List[dict] = []
        seen_keys = set()

        def chunk_key(c: dict) -> tuple:
            return (c.get("page", 1), c.get("chunk_index"), c.get("text", "")[:60])

        is_methodology = self._is_methodology_or_architecture_question(search_query)
        is_overview = self._is_overview_question(search_query)

        if is_methodology:
            # Multi-faceted deep retrieval for methodology, architecture, and framework questions (top_k=10-12)
            facet_queries = [
                search_query,
                f"{search_query} proposed approach model architecture methodology",
                "Section 5 Objectives and Methodology proposed approach architecture model components",
                "Section 5.10 Knowledge-Guided Patient-Conditioned HGT Plain HGT relation gates attention message passing severity head auxiliary edge reconstruction 5.11 architecture",
                "patient node features biological prior graph pooling auxiliary edge reconstruction"
            ]

            raw_candidates = []
            for fq in facet_queries:
                qv = self.embedding_service.embed_query(fq)
                res = self.vector_service.query_document(
                    document_id=document_id,
                    query_embedding=qv,
                    top_k=8,
                )
                raw_candidates.extend(res)

            # Filter out pure TOC chunks
            non_toc = []
            for c in raw_candidates:
                k = chunk_key(c)
                if k not in seen_keys and not self._is_toc_chunk(c.get("text", "")):
                    seen_keys.add(k)
                    non_toc.append(c)

            # Gap-filling: if adjacent chunks in methodology cluster are present, fill small 1-2 chunk gaps
            try:
                all_chunks = self.vector_service.collection.get(
                    where={"document_id": document_id},
                    include=["documents", "metadatas"],
                )
                chunks_by_idx = {}
                if all_chunks and all_chunks.get("documents"):
                    for doc_txt, meta in zip(all_chunks["documents"], all_chunks.get("metadatas", [])):
                        idx = meta.get("chunk_index")
                        if idx is not None:
                            chunks_by_idx[idx] = {
                                "page": meta.get("page", 1),
                                "text": doc_txt,
                                "chunk_index": idx,
                            }

                matched_indices = sorted([c.get("chunk_index") for c in non_toc if c.get("chunk_index") is not None])
                expanded_indices = set(matched_indices)
                for i in range(len(matched_indices) - 1):
                    idx_a = matched_indices[i]
                    idx_b = matched_indices[i+1]
                    if 1 <= idx_b - idx_a <= 3:
                        for mid in range(idx_a + 1, idx_b):
                            if mid in chunks_by_idx and not self._is_toc_chunk(chunks_by_idx[mid]["text"]):
                                expanded_indices.add(mid)

                cluster_chunks = [chunks_by_idx[i] for i in sorted(expanded_indices) if i in chunks_by_idx]
                retrieved = cluster_chunks[:12] if cluster_chunks else non_toc[:12]
            except Exception as e:
                print(f"Warning during cluster gap-filling: {e}")
                retrieved = non_toc[:12]

        elif is_overview:
            # Overview question: prioritize leading chunks + semantic search
            leading_chunks = self.vector_service.get_leading_chunks(document_id, max_chunks=3)
            for c in leading_chunks:
                k = chunk_key(c)
                if k not in seen_keys:
                    seen_keys.add(k)
                    retrieved.append(c)

            qv = self.embedding_service.embed_query(search_query)
            semantic_chunks = self.vector_service.query_document(
                document_id=document_id,
                query_embedding=qv,
                top_k=settings.TOP_K_CHUNKS,
            )
            for c in semantic_chunks:
                k = chunk_key(c)
                if k not in seen_keys:
                    seen_keys.add(k)
                    retrieved.append(c)
        else:
            # Normal factual question: top_k=settings.TOP_K_CHUNKS (default 5)
            qv = self.embedding_service.embed_query(search_query)
            semantic_chunks = self.vector_service.query_document(
                document_id=document_id,
                query_embedding=qv,
                top_k=settings.TOP_K_CHUNKS + 3,
            )
            # Deprioritize TOC chunks if valid content chunks exist
            non_toc = [c for c in semantic_chunks if not self._is_toc_chunk(c.get("text", ""))]
            chosen = non_toc if len(non_toc) >= settings.TOP_K_CHUNKS else semantic_chunks
            for c in chosen[:settings.TOP_K_CHUNKS]:
                k = chunk_key(c)
                if k not in seen_keys:
                    seen_keys.add(k)
                    retrieved.append(c)

        if not retrieved:
            return ChatResponse(
                answer="I couldn't find the answer in the uploaded document.",
                sources=[],
            )

        # Sort chronologically by page & chunk_index for natural narrative reading
        retrieved.sort(key=lambda s: (s.get("page", 1), s.get("chunk_index", 0)))

        # Format context string
        context_blocks = []
        sources: List[SourceChunk] = []
        for item in retrieved:
            context_blocks.append(f"[Page {item['page']} | Chunk #{item.get('chunk_index', 0)}]:\n{item['text']}")
            sources.append(
                SourceChunk(
                    page=item["page"],
                    text=item["text"],
                    chunk_index=item.get("chunk_index"),
                )
            )

        context_str = "\n\n---\n\n".join(context_blocks)

        # Generate answer via Gemini with history and grounded prompt
        import inspect
        try:
            sig = inspect.signature(self.llm_service.generate_grounded_answer)
            has_history = "history" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        except Exception:
            has_history = True

        if has_history:
            answer = self.llm_service.generate_grounded_answer(
                question=clean_question,
                context=context_str,
                history=history,
            )
        else:
            answer = self.llm_service.generate_grounded_answer(
                question=clean_question,
                context=context_str,
            )

        return ChatResponse(
            answer=answer,
            sources=sources,
        )


    def delete_document(self, document_id: str) -> bool:
        if not self.vector_service.document_exists(document_id):
            raise DocumentNotFoundError(f"Document with ID '{document_id}' not found.")
        return self.vector_service.delete_document(document_id)

    def list_documents(self) -> List[DocumentInfo]:
        raw_docs = self.vector_service.list_documents()
        return [
            DocumentInfo(
                document_id=d["document_id"],

                filename=d["filename"],
                number_of_pages=d.get("number_of_pages", 1),
                number_of_chunks=d.get("number_of_chunks", 0),
                uploaded_at=d.get("uploaded_at", ""),
            )
            for d in raw_docs
        ]

_rag_service = None

def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service

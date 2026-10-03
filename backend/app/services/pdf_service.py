import fitz
from typing import List, Dict, Any, Tuple

class PDFService:
    @staticmethod
    def process_pdf(
        file_bytes: bytes,
        filename: str,
        document_id: str,
        chunk_size: int = 500,
        overlap: int = 100,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Extract text page-by-page from PDF bytes and create chunk dictionaries with metadata.
        
        Preserves original RAG logic:
        - 500-character chunk size
        - 100-character overlap
        - Associates 1-indexed page number with each chunk for accurate citations
        """
        if not file_bytes:
            raise ValueError("Empty file uploaded. Please upload a valid PDF.")

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            raise ValueError(f"Could not parse file as a PDF: {str(e)}")

        try:
            total_pages = len(doc)
            if total_pages == 0:
                raise ValueError("PDF document contains no pages.")

            chunks: List[Dict[str, Any]] = []
            chunk_global_idx = 0

            for page_idx in range(total_pages):
                page = doc[page_idx]
                page_num = page_idx + 1
                text = page.get_text()

                if not text or not text.strip():
                    continue

                clean_text = text.strip()
                start = 0
                while start < len(clean_text):
                    end = start + chunk_size
                    chunk_text = clean_text[start:end].strip()
                    if chunk_text:
                        chunks.append({
                            "id": f"{document_id}_p{page_num}_c{chunk_global_idx}",
                            "text": chunk_text,
                            "metadata": {
                                "document_id": document_id,
                                "document_name": filename,
                                "page": page_num,
                                "chunk_index": chunk_global_idx,
                            },
                        })
                        chunk_global_idx += 1
                    start += chunk_size - overlap

            if not chunks:
                raise ValueError("The uploaded PDF contains no extractable text.")

            return chunks, total_pages
        finally:
            doc.close()

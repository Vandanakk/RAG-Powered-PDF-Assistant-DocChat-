import io
import fitz
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.rag_service import get_rag_service
from app.services.vector_service import get_vector_service
from app.services.embedding_service import get_embedding_service
from app.services.llm_service import LLMService

def create_sample_pdf(pages_text: list) -> bytes:
    """Helper to generate a real PDF in memory with PyMuPDF."""
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

def test_upload_invalid_extension(client):
    files = {"file": ("test.txt", b"plain text content", "text/plain")}
    res = client.post("/api/documents/upload", files=files)
    assert res.status_code == 400
    assert "Invalid file format" in res.json()["detail"]

def test_upload_corrupt_pdf(client):
    files = {"file": ("test.pdf", b"not a real pdf content", "application/pdf")}
    res = client.post("/api/documents/upload", files=files)
    assert res.status_code == 400

def test_upload_empty_file(client):
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    res = client.post("/api/documents/upload", files=files)
    assert res.status_code == 400

def test_upload_valid_pdf_and_list(client):
    pdf_bytes = create_sample_pdf([
        "DocChat is a RAG-powered document assistant created for question answering.",
        "It supports chunking with 500 characters and 100 character overlap."
    ])
    files = {"file": ("sample_test.pdf", pdf_bytes, "application/pdf")}
    res = client.post("/api/documents/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert "document_id" in data
    assert data["filename"] == "sample_test.pdf"
    assert data["number_of_pages"] == 2
    assert data["number_of_chunks"] >= 2

    # Verify document appears in list
    docs_res = client.get("/api/documents")
    assert docs_res.status_code == 200
    docs = docs_res.json()
    assert any(d["document_id"] == data["document_id"] for d in docs)

def test_document_isolation(client):
    # Upload doc 1
    doc1_bytes = create_sample_pdf(["Apollo mission landed humans on the Moon in July 1969."])
    res1 = client.post("/api/documents/upload", files={"file": ("apollo.pdf", doc1_bytes, "application/pdf")})
    assert res1.status_code == 200
    doc1_id = res1.json()["document_id"]

    # Upload doc 2
    doc2_bytes = create_sample_pdf(["Voyager 1 is an interstellar space probe launched by NASA in 1977."])
    res2 = client.post("/api/documents/upload", files={"file": ("voyager.pdf", doc2_bytes, "application/pdf")})
    assert res2.status_code == 200
    doc2_id = res2.json()["document_id"]

    vector_service = get_vector_service()
    embed_service = get_embedding_service()

    # Query doc1 with space probe query: must ONLY return doc1 chunks, never doc2
    q_vec = embed_service.embed_query("interstellar space probe")
    doc1_chunks = vector_service.query_document(doc1_id, q_vec, top_k=5)
    for c in doc1_chunks:
        assert "Voyager" not in c["text"]
        assert "Moon" in c["text"]

    # Query doc2 with Moon query: must ONLY return doc2 chunks, never doc1
    q_vec2 = embed_service.embed_query("humans on the Moon")
    doc2_chunks = vector_service.query_document(doc2_id, q_vec2, top_k=5)
    for c in doc2_chunks:
        assert "Apollo" not in c["text"]
        assert "Voyager" in c["text"]

def test_chat_nonexistent_document(client):
    res = client.post("/api/chat", json={
        "document_id": "nonexistent_doc_id",
        "question": "What is DocChat?"
    })
    assert res.status_code == 404

def test_chat_empty_question(client):
    res = client.post("/api/chat", json={
        "document_id": "any_doc_id",
        "question": "   "
    })
    assert res.status_code == 400

def test_chat_with_mocked_llm(client, monkeypatch):
    pdf_bytes = create_sample_pdf(["Photosynthesis converts carbon dioxide and sunlight into sugars."])
    res = client.post("/api/documents/upload", files={"file": ("bio.pdf", pdf_bytes, "application/pdf")})
    assert res.status_code == 200
    doc_id = res.json()["document_id"]

    # Mock the LLM generation so we can test the complete chat pipeline without external network API calls
    rag_service = get_rag_service()
    mock_llm = MagicMock()
    mock_llm.generate_grounded_answer.return_value = "Photosynthesis creates sugars from sunlight and CO2."
    monkeypatch.setattr(rag_service, "llm_service", mock_llm)

    chat_res = client.post("/api/chat", json={
        "document_id": doc_id,
        "question": "How do plants make sugars?"
    })
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert data["answer"] == "Photosynthesis creates sugars from sunlight and CO2."
    assert len(data["sources"]) > 0
    assert data["sources"][0]["page"] == 1
    assert "Photosynthesis" in data["sources"][0]["text"]

def test_cors_preflight_upload_endpoints(client):
    """Verify CORS preflight succeeds for localhost and 127.0.0.1 on ports 5173 and 5174."""
    for origin in ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"]:

        # Preflight for multipart/form-data upload
        res = client.options(
            "/api/documents/upload",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert res.status_code == 200, f"Preflight failed for {origin}: {res.text}"
        assert res.headers.get("access-control-allow-origin") == origin
        assert "POST" in res.headers.get("access-control-allow-methods", "")

        # Preflight for JSON chat endpoint
        res_chat = client.options(
            "/api/chat",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert res_chat.status_code == 200, f"Preflight chat failed for {origin}: {res_chat.text}"
        assert res_chat.headers.get("access-control-allow-origin") == origin

        # Preflight for DELETE document endpoint
        res_delete = client.options(
            "/api/documents/doc_123",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "DELETE",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert res_delete.status_code == 200, f"Preflight delete failed for {origin}: {res_delete.text}"
        assert res_delete.headers.get("access-control-allow-origin") == origin
        assert "DELETE" in res_delete.headers.get("access-control-allow-methods", "")

def test_cors_preflight_rejected_for_untrusted_origin(client):
    """Verify that origins outside the allowed list are rejected with 400 Bad Request."""
    res = client.options(
        "/api/documents/upload",
        headers={
            "Origin": "http://malicious-website.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert res.status_code == 400
    assert "Disallowed CORS origin" in res.text

def test_cors_origin_parser():
    from app.config import parse_cors_origins
    # Test JSON list string
    assert "http://localhost:5173" in parse_cors_origins('["http://localhost:5173", "http://127.0.0.1:5173"]')
    # Test trailing slashes stripped
    parsed = parse_cors_origins("http://localhost:5173/,http://127.0.0.1:5173/")
    assert "http://localhost:5173" in parsed
    assert "http://localhost:5173/" not in parsed
    # Test quoted strings
    assert "http://localhost:5173" in parse_cors_origins('"http://localhost:5173,http://127.0.0.1:5173"')
    # Test production Vercel URL
    prod_parsed = parse_cors_origins("https://docchat.vercel.app,http://localhost:5173")
    assert "https://docchat.vercel.app" in prod_parsed
    # Test wildcard '*' is filtered out to protect credentialed CORS
    assert "*" not in parse_cors_origins("*,https://docchat.vercel.app")

def test_delete_document_success(client):
    pdf_bytes = create_sample_pdf(["Temporary document to be deleted."])
    res = client.post("/api/documents/upload", files={"file": ("to_delete.pdf", pdf_bytes, "application/pdf")})
    assert res.status_code == 200
    doc_id = res.json()["document_id"]

    # Ensure document exists
    docs = client.get("/api/documents").json()
    assert any(d["document_id"] == doc_id for d in docs)

    # Delete the document
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["success"] is True
    assert del_data["document_id"] == doc_id

    # Verify document is no longer listed
    docs_after = client.get("/api/documents").json()
    assert not any(d["document_id"] == doc_id for d in docs_after)

    # Verify second delete returns 404
    del_again = client.delete(f"/api/documents/{doc_id}")
    assert del_again.status_code == 404

    # Verify chat on deleted document returns 404
    chat_res = client.post("/api/chat", json={"document_id": doc_id, "question": "test"})
    assert chat_res.status_code == 404

def test_delete_document_isolation(client):
    # Upload doc A and doc B
    doc_a_bytes = create_sample_pdf(["Alpha document content about astrophysics and galaxies."])
    res_a = client.post("/api/documents/upload", files={"file": ("doc_a.pdf", doc_a_bytes, "application/pdf")})
    doc_a_id = res_a.json()["document_id"]

    doc_b_bytes = create_sample_pdf(["Beta document content about biology and cell membranes."])
    res_b = client.post("/api/documents/upload", files={"file": ("doc_b.pdf", doc_b_bytes, "application/pdf")})
    doc_b_id = res_b.json()["document_id"]

    # Delete Doc A only
    del_a = client.delete(f"/api/documents/{doc_a_id}")
    assert del_a.status_code == 200

    # Doc A must be gone, Doc B must remain intact
    docs = client.get("/api/documents").json()
    assert not any(d["document_id"] == doc_a_id for d in docs)
    assert any(d["document_id"] == doc_b_id for d in docs)

    # Doc B chunks must still be queryable
    vector_service = get_vector_service()
    embed_service = get_embedding_service()
    q_vec = embed_service.embed_query("cell membranes")
    b_chunks = vector_service.query_document(doc_b_id, q_vec, top_k=5)
    assert len(b_chunks) > 0
    assert "biology" in b_chunks[0]["text"]

def test_selected_document_retrieval(client, monkeypatch):
    doc1_bytes = create_sample_pdf(["Quantum mechanics describes behavior of particles at nanoscale."])
    res1 = client.post("/api/documents/upload", files={"file": ("physics.pdf", doc1_bytes, "application/pdf")})
    doc1_id = res1.json()["document_id"]

    doc2_bytes = create_sample_pdf(["Economics studies the production and distribution of goods."])
    res2 = client.post("/api/documents/upload", files={"file": ("econ.pdf", doc2_bytes, "application/pdf")})
    doc2_id = res2.json()["document_id"]

    rag_service = get_rag_service()
    mock_llm = MagicMock()
    mock_llm.generate_grounded_answer.side_effect = lambda question, context: f"Answer using: {context}"
    monkeypatch.setattr(rag_service, "llm_service", mock_llm)

    # Ask with selected doc1_id
    chat_res1 = client.post("/api/chat", json={
        "document_id": doc1_id,
        "question": "What is quantum mechanics?"
    })
    assert chat_res1.status_code == 200
    data1 = chat_res1.json()
    assert len(data1["sources"]) > 0
    for s in data1["sources"]:
        assert "Economics" not in s["text"]
    assert "nanoscale" in data1["sources"][0]["text"]

    # Ask with selected doc2_id
    chat_res2 = client.post("/api/chat", json={
        "document_id": doc2_id,
        "question": "What does economics study?"
    })
    assert chat_res2.status_code == 200
    data2 = chat_res2.json()
    assert len(data2["sources"]) > 0
    for s in data2["sources"]:
        assert "Quantum" not in s["text"]
    assert "goods" in data2["sources"][0]["text"]

def test_broad_overview_question_retrieval(client, monkeypatch):
    # Multi-page PDF representing a BTP report
    btp_pages = [
        "Major Project Report on Knowledge-Guided Patient-Condition Severity Prediction. Submitted for Bachelor of Technology degree. Supervised by Dr. Smith.",
        "Table of Contents: Chapter 1 Introduction, Chapter 2 Literature Review, Chapter 3 Methodology, Chapter 4 Results.",
        "Detailed experimental setup involving MRI imaging data and patient progression tracking algorithms."
    ]
    pdf_bytes = create_sample_pdf(btp_pages)
    res = client.post("/api/documents/upload", files={"file": ("BTP_Project.pdf", pdf_bytes, "application/pdf")})
    assert res.status_code == 200
    doc_id = res.json()["document_id"]

    rag_service = get_rag_service()
    captured_context = []
    mock_llm = MagicMock()
    def fake_generate(question, context):
        captured_context.append(context)
        return "The topic of this BTP is Knowledge-Guided Patient-Condition Severity Prediction."
    mock_llm.generate_grounded_answer.side_effect = fake_generate
    monkeypatch.setattr(rag_service, "llm_service", mock_llm)

    # Test "what is the topic of this btp?"
    chat_res = client.post("/api/chat", json={
        "document_id": doc_id,
        "question": "what is the topic of this btp?"
    })
    assert chat_res.status_code == 200
    assert len(captured_context) > 0
    # Must contain the leading chunk with BTP title from page 1
    assert "Knowledge-Guided Patient-Condition Severity Prediction" in captured_context[-1]

    # Verify sources include chunk 0 / page 1
    sources = chat_res.json()["sources"]
    pages = [s["page"] for s in sources]
    assert 1 in pages
    assert any("Knowledge-Guided" in s["text"] for s in sources)

    # Test another broad overview question: "What is this document about?"
    chat_res2 = client.post("/api/chat", json={
        "document_id": doc_id,
        "question": "What is this document about?"
    })
    assert chat_res2.status_code == 200
    assert any("Knowledge-Guided" in s["text"] for s in chat_res2.json()["sources"])

def test_cloud_settings_port_and_storage(monkeypatch):
    from app.config import Settings
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setenv("DATA_DIR", "/var/data")
    s = Settings()
    assert s.PORT == 10000
    assert "/var/data" in s.CHROMA_PERSIST_DIR
    assert "/var/data" in s.DOCUMENTS_REGISTRY_PATH




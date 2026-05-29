import fitz
import chromadb
from google import genai
from sentence_transformers import SentenceTransformer

import os
from dotenv import load_dotenv
load_dotenv()
print("KEY LOADED:", os.environ.get("GEMINI_API_KEY"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SAMPLE_PDF = "sample.pdf"
client = genai.Client(api_key=GEMINI_API_KEY)
model = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="./chroma_data")
try:
    chroma_client.delete_collection(name="pdf_docs")
    print("Old database deleted")
except Exception:
    pass  # If it doesn't exist yet, don't worry
collection = chroma_client.get_or_create_collection(name="pdf_docs")

# Extract and chunk text from pdf
def process_pdf(pdf_path, chunk_size=500, overlap=100):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    
    chunks = []
    start = 0
    while(start < len(full_text)):
        end = start + chunk_size
        chunk = full_text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

# Chunks into chromadb

def index_chunks(chunks):
    embeddings = model.encode(chunks).tolist()
    ids = [f"pdf_chunk_{i}" for i in range(len(chunks))]

    collection.add(embeddings=embeddings, documents=chunks, ids=ids)
    
# Retrieve and generate answer

def ask_question(question):
    query_vector = model.encode(question).tolist()
    db_results = collection.query(query_embeddings=[query_vector], n_results=2)
    retrieved_chunks = db_results["documents"][0]
    print(f"\n🔍 DEBUG: ChromaDB retrieved these chunks:\n {retrieved_chunks}\n")
    context = "\n---\n".join(retrieved_chunks)

    prompt = f"""
    You are a helpful assistant. Answer the user's question using ONLY the provided context snippet. 
    If the answer cannot be found in the context, say "I cannot find the answer in the document."

    Context Document Snippets:
    {context}

    User Question: {question}
    Answer:
    """
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)

    print(response.text.strip())


if __name__ == "__main__":
    try:
        chunks = process_pdf(SAMPLE_PDF)
        index_chunks(chunks)
        user_query = "How is my Plant-Disease-Detection project?"
        ask_question(user_query)

    except FileNotFoundError:
        print(
            f"\n❌ Setup needed: Please drop a PDF file named '{SAMPLE_PDF}' into your project folder so the script can parse it!"
        )
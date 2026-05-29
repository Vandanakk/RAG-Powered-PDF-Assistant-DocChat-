from sentence_transformers import SentenceTransformer
import numpy as np
import chromadb

model = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="./chroma_data")
collection = chroma_client.get_or_create_collection(name="pdf_chunks")

document_text = """
The Golden Pavilion, officially named Rokuon-ji, is a Zen Buddhist temple in Kyoto, Japan. It is one of the most popular buildings in the country, attracting a large number of visitors annually. The top two floors of the pavilion are completely covered in brilliant gold leaf.

The Indian Space Research Organisation (ISRO) successfully launched its Chandrayaan-3 mission on July 14, 2023. The mission successfully demonstrated a soft landing of a rover on the lunar south pole region, making India the first nation to achieve this historic feat.

Photosynthesis is a biologically vital process used by plants and other organisms to convert light energy into chemical energy. This energy is stored in carbohydrate molecules, such as sugars, which are synthesized from carbon dioxide and water.

The standard layout of a computer keyboard is known as QWERTY. It was designed by Christopher Latham Sholes in 1873 for early typewriters to prevent the physical mechanical keys from jamming when frequently typed letters were struck in quick succession.
"""

paragraphs = [p.strip() for p in document_text.strip().split("\n\n")]
embeddings = model.encode(paragraphs).tolist()
ids = [f"chunk_{i}" for i in range(len(paragraphs))]

collection.add(embeddings = embeddings,
               documents=paragraphs,
               ids=ids)

print("We indexed {len(paragraphs)} chunks into ChromaDB")

query_text = "Tell me about space missions to the moon"
query_vector = model.encode(query_text).tolist()

results = collection.query(query_embeddings=[query_vector], n_results=1)

print("Query: ", query_text)
print("Retrieved chunk: ", results['documents'][0][0])
print("Chunk ID: ", results['ids'][0][0])

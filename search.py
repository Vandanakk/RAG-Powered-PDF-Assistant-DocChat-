from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

sentences = ["The weather is absolutely beautiful today.",
    "A quick brown fox jumps over the lazy dog.",
    "I love building machine learning pipelines with Python.",
    "Deep learning models require a lot of computational data.",
    "The kitchen is clean and the food is ready.",
    "He enjoys cooking delicious meals for his family.",
    "Exploring ancient philosophy and historical texts is fascinating.",
    "The stock market experienced a massive drop today.",
    "An Apple a day keeps the doctor away.",
    "The new software update fixed several critical bugs.",]

sentence_embeddings = model.encode(sentences)

query = "feline on a rug"
query_embedding = model.encode(query)

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

scores = []
for emb in sentence_embeddings:
    score = cosine_similarity(query_embedding, emb)
    scores.append(score)

best_match_idx = np.argmax(scores)

print("best match: ", sentences[best_match_idx])
print("similarity score: ", scores[best_match_idx])
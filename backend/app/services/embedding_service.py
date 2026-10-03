from typing import List
from sentence_transformers import SentenceTransformer
from app.config import settings

class EmbeddingService:
    _instance = None

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL_NAME):
        print(f"🔄 Loading SentenceTransformer model '{model_name}' once...")
        self.model = SentenceTransformer(model_name)
        print("✅ SentenceTransformer model loaded successfully.")

    @classmethod
    def get_instance(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(texts)
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        embedding = self.model.encode(query)
        return embedding.tolist()

# Global singleton instance accessor
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService.get_instance()

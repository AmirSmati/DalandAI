import json
from pathlib import Path

from sentence_transformers import SentenceTransformer

from config.settings import HF_TOKEN

class MemoryEmbeddingModel:
    """Creates, stores, and loads embeddings for long-term memories."""

    MODEL_NAME = "all-MiniLM-L6-v2"
    EMBEDDINGS_FILE = Path("workspace/organizer/memory_embeddings.json")

    def __init__(self):
        self.model = SentenceTransformer(self.MODEL_NAME, token=HF_TOKEN)

    def encode(self, text):
        """Convert text or texts into normalized embedding vectors."""
        return self.model.encode(
            text,
            normalize_embeddings=True,
        )

    def similarity(self, embedding_a, embedding_b) -> float:
        """Calculate cosine similarity between two normalized embeddings."""
        return float(embedding_a @ embedding_b)

    def save_embedding(
        self,
        category: str,
        key: str,
        embedding,
    ) -> None:
        """Save an embedding for a memory entry."""

        self.EMBEDDINGS_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = {}

        if self.EMBEDDINGS_FILE.exists():
            try:
                data = json.loads(
                    self.EMBEDDINGS_FILE.read_text(
                        encoding="utf-8"
                    )
                )
            except (json.JSONDecodeError, OSError):
                data = {}

        if category not in data:
            data[category] = {}

        data[category][key] = embedding.tolist()

        self.EMBEDDINGS_FILE.write_text(
            json.dumps(data),
            encoding="utf-8",
        )

    def load_embedding(
        self,
        category: str,
        key: str,
    ):
        """Load a stored embedding for a memory entry."""

        if not self.EMBEDDINGS_FILE.exists():
            return None

        try:
            data = json.loads(
                self.EMBEDDINGS_FILE.read_text(
                    encoding="utf-8"
                )
            )
        except (json.JSONDecodeError, OSError):
            return None

        embedding = (
            data
            .get(category, {})
            .get(key)
        )

        return embedding

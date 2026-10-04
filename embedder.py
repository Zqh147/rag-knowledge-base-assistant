from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL

model = SentenceTransformer(
    EMBEDDING_MODEL
)


def embed_text(text):
    return model.encode(text).tolist()
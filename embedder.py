from functools import lru_cache
from config import EMBEDDING_MODEL, MODEL_DEVICE, CPU_THREADS


@lru_cache(maxsize=1)
def get_model():
    if MODEL_DEVICE == "cpu":
        import torch
        torch.set_num_threads(CPU_THREADS)
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBEDDING_MODEL, device=MODEL_DEVICE)
    model.max_seq_length = 512
    return model


def embed_text(text):
    model = get_model()
    texts = [text] if isinstance(text, str) else text
    if any(len(model.tokenizer.encode(t)) > model.max_seq_length for t in texts):
        raise ValueError("text exceeds embedding token limit; shorten into complete sections")
    return model.encode(text, show_progress_bar=False).tolist()

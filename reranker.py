from functools import lru_cache
import math
from config import RERANK_K, RERANKER_MODEL, MODEL_DEVICE, CPU_THREADS


@lru_cache(maxsize=1)
def get_model():
    if MODEL_DEVICE == "cpu":
        import torch
        torch.set_num_threads(CPU_THREADS)
    from sentence_transformers import CrossEncoder
    return CrossEncoder(RERANKER_MODEL, device=MODEL_DEVICE, max_length=512)


def rerank(question, candidates, top_n=RERANK_K):
    if top_n < 1:
        raise ValueError("top_n must be positive")
    if not candidates:
        return []
    from torch.nn import Identity
    # Explicit logits: a stable score scale, never an answer-confidence probability.
    scores = get_model().predict([[question, c["document"]] for c in candidates],
                                 activation_fn=Identity(), batch_size=4, show_progress_bar=False)
    if len(scores) != len(candidates) or any(not math.isfinite(float(s)) for s in scores):
        raise RuntimeError("reranker returned invalid scores")
    results = [{**c, "reranker_score": float(s)} for c, s in zip(candidates, scores)]
    return sorted(results, key=lambda c: c["reranker_score"], reverse=True)[:top_n]

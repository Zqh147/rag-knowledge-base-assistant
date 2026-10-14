import jieba
from rank_bm25 import BM25Okapi
from config import TOP_K
from vector_store import get_documents

STOP_WORDS = {"的", "了", "是", "什么", "一个", "这个", "可以", "？", "?", "。", "，", ","}


def tokenize(text):
    return [w.strip() for w in jieba.lcut(text.lower()) if w.strip() and w.strip() not in STOP_WORDS]


def retrieve_bm25(question, top_k=TOP_K, filters=None):
    if top_k < 1:
        raise ValueError("top_k must be positive")
    # Filter the persisted corpus BEFORE BM25 scoring and Top-K selection.
    stored = get_documents(filters)
    documents, metadatas = stored["documents"], stored["metadatas"]
    if not documents:
        return []
    bm25 = BM25Okapi([tokenize(d) for d in documents])
    scores = bm25.get_scores(tokenize(question))
    results = list(zip(documents, map(float, scores), metadatas))
    return sorted(results, key=lambda x: x[1], reverse=True)[:top_k]

from functools import lru_cache
from config import DB_PATH, COLLECTION_NAME, EMBEDDING_MODEL
from product_scope import chroma_where


@lru_cache(maxsize=1)
def get_collection():
    import chromadb
    client = chromadb.PersistentClient(path=DB_PATH)
    return client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


def add_documents(ids, documents, chunks_vector, metadatas):
    get_collection().upsert(ids=ids, documents=documents, embeddings=chunks_vector, metadatas=metadatas)


def get_document_count():
    return get_collection().count()


def get_documents(filters=None):
    kwargs = {"include": ["documents", "metadatas"]}
    where = chroma_where(filters)
    if where:
        kwargs["where"] = where
    return get_collection().get(**kwargs)


def query_documents(query_embedding, top_k, filters=None):
    if top_k < 1:
        raise ValueError("top_k must be positive")
    count = len(get_documents(filters)["ids"])
    if not count:
        return {"documents": [[]], "distances": [[]], "metadatas": [[]]}
    kwargs = {"query_embeddings": [query_embedding], "n_results": min(top_k, count),
              "include": ["documents", "distances", "metadatas"]}
    where = chroma_where(filters)
    if where:
        kwargs["where"] = where
    return get_collection().query(**kwargs)


def verify_router_index(chunks, digest):
    """Fail on stale/partial/different indexes, never fall back to demo data."""
    collection = get_collection()
    meta = collection.metadata or {}
    if meta.get("corpus_digest") != digest or meta.get("embedding_model") != EMBEDDING_MODEL:
        raise RuntimeError("router index is missing/stale; run python build_index.py")
    expected = {c["id"]: c for c in chunks}
    stored = collection.get(include=["documents", "metadatas"])
    if set(stored["ids"]) != set(expected):
        raise RuntimeError("router index is partial/stale; run python build_index.py")
    for uid, document, metadata in zip(stored["ids"], stored["documents"], stored["metadatas"]):
        if expected[uid]["document"] != document or expected[uid]["metadata"] != metadata:
            raise RuntimeError("router index differs from corpus; rebuild it")
    return len(expected)

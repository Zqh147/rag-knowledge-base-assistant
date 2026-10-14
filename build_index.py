"""Router indexing reuses the existing embedding and Chroma implementation."""
from config import PROFILE, BASE_DIR, EMBEDDING_MODEL
from embedder import embed_text
from vector_store import add_documents, get_collection, get_document_count


def build_router_index():
    from router_corpus import make_chunks, corpus_digest
    chunks = make_chunks()
    embeddings = embed_text([c["document"] for c in chunks])
    collection = get_collection()
    old_ids = set(collection.get(include=[])["ids"])
    ids = [c["id"] for c in chunks]
    collection.modify(metadata={"corpus_digest": "building",
                                "embedding_model": EMBEDDING_MODEL})
    add_documents(ids, [c["document"] for c in chunks], embeddings, [c["metadata"] for c in chunks])
    stale = list(old_ids - set(ids))
    if stale:
        collection.delete(ids=stale)
    collection.modify(metadata={"corpus_digest": corpus_digest(chunks),
                                "embedding_model": EMBEDDING_MODEL})
    return get_document_count()


def build_demo_index():
    from loader import load_document
    from chunker import split_text
    ids, documents, metadatas = [], [], []
    for path in sorted((BASE_DIR / "data").iterdir()):
        if path.suffix.lower() not in {".txt", ".pdf"}:
            continue
        for page in load_document(str(path)):
            for index, chunk in enumerate(split_text(page["text"])):
                ids.append(f"{path.name}_page_{page['page']}_chunk_{index}")
                documents.append(chunk)
                metadata = {"source": path.name, "chunk_id": index}
                if page["page"] is not None:
                    metadata["page"] = page["page"]
                metadatas.append(metadata)
    if not documents:
        raise RuntimeError("demo corpus is empty")
    add_documents(ids, documents, embed_text(documents), metadatas)
    return get_document_count()


if __name__ == "__main__":
    count = build_router_index() if PROFILE == "router" else build_demo_index()
    print(f"{PROFILE} index ready: {count} chunks")

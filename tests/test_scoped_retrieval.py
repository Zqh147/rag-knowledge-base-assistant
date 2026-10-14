import pytest
import chromadb
import vector_store
from retriever import retrieve
from bm25_retriever import retrieve_bm25
from hybrid_retriever import retrieve_hybrid, reciprocal_rank_fusion
import hybrid_retriever

SCOPE = {"product_model": "Archer AX10", "hardware_version": "V1", "region": "US"}


@pytest.fixture
def store(tmp_path, monkeypatch):
    client = chromadb.PersistentClient(path=str(tmp_path))
    collection = client.create_collection("scope_tests", metadata={"hnsw:space": "cosine"})
    metas = [
        {**SCOPE, "source": "knowledge.json", "chunk_id": 0, "evidence_id": "correct"},
        {**SCOPE, "product_model": "Archer AX20", "source": "knowledge.json", "chunk_id": 0, "evidence_id": "wrong-model"},
        {**SCOPE, "hardware_version": "V2", "source": "knowledge.json", "chunk_id": 0, "evidence_id": "wrong-version"},
        {**SCOPE, "region": "EU", "source": "knowledge.json", "chunk_id": 0, "evidence_id": "wrong-region"},
    ]
    collection.upsert(ids=["correct", "wrong-model", "wrong-version", "wrong-region"],
                      documents=["修改无线密码 保存", "密码 密码 密码 修改", "密码 密码 修改", "密码 密码 修改"],
                      embeddings=[[0.7, 0.3], [1.0, 0.0], [1.0, 0.0], [1.0, 0.0]], metadatas=metas)
    monkeypatch.setattr(vector_store, "get_collection", lambda: collection)
    return collection


def test_real_chroma_filter_precedes_vector_topk(store, monkeypatch):
    import retriever
    monkeypatch.setattr(retriever, "embed_text", lambda q: [1.0, 0.0])
    # All distractors have stronger cosine scores but must not occupy the one candidate slot.
    result = retrieve("密码", top_k=1, filters=SCOPE)
    assert len(result) == 1 and result[0][2]["evidence_id"] == "correct"
    assert vector_store.query_documents([1.0, 0.0], 3, {"product_model": "unknown"})["documents"] == [[]]


def test_real_bm25_is_built_only_from_scoped_chroma_records(store):
    result = retrieve_bm25("密码", top_k=1, filters=SCOPE)
    assert len(result) == 1 and result[0][2]["evidence_id"] == "correct"
    assert retrieve_bm25("密码", filters={"region": "unknown"}) == []


def test_hybrid_passes_the_same_scope_to_both_lanes(monkeypatch):
    called = []
    def lane(q, top_k, filters):
        called.append(filters)
        return [("证据", 1.0, {"source": "s", "chunk_id": 0, "evidence_id": "one"})]
    monkeypatch.setattr(hybrid_retriever, "retrieve", lane)
    monkeypatch.setattr(hybrid_retriever, "retrieve_bm25", lane)
    fused = retrieve_hybrid("密码", filters=SCOPE)
    assert called == [SCOPE, SCOPE]
    assert fused[0]["rrf_score"] == pytest.approx(2 / 61)


def test_rrf_identity_does_not_merge_different_manual_sections():
    vector = [("A", 0.9, {"source": "knowledge.json", "chunk_id": 0, "evidence_id": "section-a"})]
    bm25 = [("B", 8.0, {"source": "knowledge.json", "chunk_id": 0, "evidence_id": "section-b"})]
    assert len(reciprocal_rank_fusion(vector, bm25)) == 2


def test_stale_or_partial_index_is_rejected(store):
    from config import EMBEDDING_MODEL
    store.modify(metadata={"corpus_digest": "current", "embedding_model": EMBEDDING_MODEL})
    with pytest.raises(RuntimeError, match="partial/stale"):
        vector_store.verify_router_index([], "current")
    with pytest.raises(RuntimeError, match="missing/stale"):
        vector_store.verify_router_index([], "changed")

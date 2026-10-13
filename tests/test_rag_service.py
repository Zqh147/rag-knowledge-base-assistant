from fastapi.testclient import TestClient
from rag_service import create_app


def test_existing_functions_are_called_and_metadata_is_preserved():
    called = []
    candidates = [{"document": "RAG证据", "metadata": {"source": "manual.pdf", "page": 3, "chunk_id": 7}, "rrf_score": 0.03}]
    def hybrid(question, candidate_k, final_k):
        called.append(("hybrid", question, candidate_k, final_k))
        return candidates
    def rerank(question, items, top_n):
        assert items is candidates
        called.append(("rerank", question, top_n))
        return [{**items[0], "reranker_score": 1.2}]
    with TestClient(create_app(hybrid, rerank)) as client:
        assert client.get("/health").json()["ready"]
        response = client.post("/retrieve", json={"question": "RAG", "top_k": 3})
    assert response.status_code == 200
    assert called == [("hybrid", "RAG", 10, 10), ("rerank", "RAG", 3)]
    assert response.json()["results"][0] == {"content": "RAG证据", "source": "manual.pdf", "page": 3, "chunk_id": 7, "rrf_score": 0.03, "reranker_score": 1.2}


def test_empty_and_invalid_requests():
    with TestClient(create_app(lambda *a, **k: [], lambda *a, **k: [])) as client:
        result = client.post("/retrieve", json={"question": "没有资料"}).json()
        assert result["results"] == [] and not result["has_results"]
        assert client.post("/retrieve", json={"question": "RAG", "top_k": 0}).status_code == 422
        assert client.post("/retrieve", json={"question": " "}).status_code == 422

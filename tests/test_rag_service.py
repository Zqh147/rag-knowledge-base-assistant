import pytest
from fastapi.testclient import TestClient
from rag_service import create_app
from router_corpus import make_chunks

SCOPE = {"product_model": "Archer AX10", "hardware_version": "V1", "region": "US"}
CANDIDATE = next(c for c in make_chunks() if c["metadata"]["evidence_id"] == "ax10-v1-us-wireless")


def app_with(retrieve=None, rerank=None, **kwargs):
    retrieve = retrieve or (lambda *a, **k: [{**CANDIDATE, "rrf_score": 0.03}])
    rerank = rerank or (lambda q, items, top_n: [{**i, "reranker_score": 3.0} for i in items])
    return create_app(retrieve, rerank, min_score=1.0, **kwargs)


def test_legacy_request_shape_and_additive_evidence_fields():
    called = []
    def hybrid(q, candidate_k, final_k, filters):
        called.append(("hybrid", q, candidate_k, final_k, filters))
        return [{**CANDIDATE, "rrf_score": 0.03}]
    def rerank(q, items, top_n):
        called.append(("rerank", q, top_n))
        return [{**items[0], "reranker_score": 3.2}]
    with TestClient(app_with(hybrid, rerank)) as client:
        assert client.get("/health").json()["ready"]
        response = client.post("/retrieve", json={"question": "AX10 V1 US 如何修改Wi-Fi密码？", "top_k": 3})
        assert client.get("/products").status_code == 200
    assert response.status_code == 200
    body = response.json()
    assert body["backend"] == "project1" and body["pipeline"] == "vector+bm25+rrf+cross_encoder"
    assert body["status"] == "ok" and body["has_results"]
    assert body["results"][0]["content"] == CANDIDATE["document"]
    assert body["results"][0]["page"] is None
    for key in ("source", "chunk_id", "rrf_score", "reranker_score", "section", "source_url", "citation_id"):
        assert key in body["results"][0]
    assert called == [("hybrid", "如何修改Wi-Fi密码", 10, 10, SCOPE), ("rerank", "如何修改Wi-Fi密码", 10)]


def test_explicit_scope_and_question_scope_agree():
    with TestClient(app_with()) as client:
        response = client.post("/retrieve", json={"question": "AX10 V1 美版如何修改无线密码？", **SCOPE})
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize("payload", [
    {"question": " "}, {"question": ""}, {"question": "a", "top_k": 0},
    {"question": "a", "top_k": 6}, {"question": "a", "top_k": True},
    {"question": "a", "top_k": 2.2}, {"question": "a", "region": " "},
])
def test_invalid_requests_are_422(payload):
    with TestClient(app_with()) as client:
        assert client.post("/retrieve", json=payload).status_code == 422


@pytest.mark.parametrize("payload,status", [
    ({"question": "怎么改密码"}, "needs_clarification"),
    ({"question": "AX10如何改密码"}, "needs_clarification"),
    ({"question": "AX99 V1 US如何改密码"}, "unsupported_product"),
    ({"question": "AX10 V2 US如何改密码"}, "unsupported_product"),
    ({"question": "AX10 V1 EU如何改密码"}, "unsupported_product"),
    ({"question": "AX20 V1 US如何改密码", **SCOPE}, "parameter_conflict"),
])
def test_scope_decisions_do_not_execute_retrieval(payload, status):
    def forbidden(*a, **k):
        raise AssertionError("retrieval must not run with unresolved scope")
    with TestClient(app_with(forbidden)) as client:
        response = client.post("/retrieve", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == status
    assert not response.json()["has_results"]


def test_service_failure_is_distinct_from_no_evidence():
    def broken(*a, **k):
        raise RuntimeError("index/model failed")
    with TestClient(app_with(broken)) as client:
        response = client.post("/retrieve", json={"question": "怎么修改密码", **SCOPE})
    assert response.status_code == 503 and response.json()["detail"]["code"] == "retrieval_unavailable"
    with TestClient(app_with(lambda *a, **k: [])) as client:
        body = client.post("/retrieve", json={"question": "怎么修改密码", **SCOPE}).json()
    assert body["status"] == "no_evidence" and not body["has_results"]


def test_threshold_rejects_irrelevant_candidates():
    with TestClient(app_with(rerank=lambda q, items, top_n: [{**CANDIDATE, "reranker_score": -9.0}])) as client:
        body = client.post("/retrieve", json={"question": "怎么查询快递", **SCOPE}).json()
    assert body["status"] == "no_evidence" and body["results"] == []


def test_unready_and_empty_index_fail():
    client = TestClient(app_with())
    assert client.get("/health").status_code == 503
    assert client.post("/retrieve", json={"question": "test"}).status_code == 503
    with pytest.raises(RuntimeError, match="index is empty"):
        with TestClient(app_with(ready_check=lambda: 0)):
            pass

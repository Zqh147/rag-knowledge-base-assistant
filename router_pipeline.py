"""Domain decisions are separate from the existing hybrid retrieval machinery."""
import json
import math
from config import POLICY_PATH, CANDIDATE_K, FINAL_K, RERANKER_MODEL
from product_scope import resolve_scope, matches
from router_corpus import load_sections, available_products, corpus_digest


def load_policy():
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if policy.get("score_scale") != "raw_logit" or policy.get("model") != RERANKER_MODEL:
        raise RuntimeError("retrieval policy uses a different model/score scale")
    if policy.get("corpus_digest") != corpus_digest():
        raise RuntimeError("retrieval policy is stale; recalibrate after corpus changes")
    score = float(policy["min_score"])
    if not math.isfinite(score):
        raise RuntimeError("invalid relevance threshold")
    return score


def retrieve_router(question, top_k=3, product_model=None, hardware_version=None, region=None,
                    retrieve_fn=None, rerank_fn=None, products=None, min_score=None):
    if not question.strip() or not isinstance(top_k, int) or isinstance(top_k, bool) or not 1 <= top_k <= 5:
        raise ValueError("question/top_k is invalid")
    products = available_products(load_sections()) if products is None else products
    scope = resolve_scope(question, products, product_model, hardware_version, region)
    base = {"status": scope.status, "message": scope.message, "resolved_scope": scope.filters,
            "missing_fields": scope.missing_fields, "results": [], "has_results": False}
    if scope.status != "ok":
        return base
    if retrieve_fn is None:
        from hybrid_retriever import retrieve_hybrid
        retrieve_fn = retrieve_hybrid
    if rerank_fn is None:
        from reranker import rerank
        rerank_fn = rerank
    min_score = load_policy() if min_score is None else min_score
    candidates = retrieve_fn(scope.query, candidate_k=CANDIDATE_K, final_k=FINAL_K, filters=scope.filters)
    if any(not matches(c["metadata"], scope.filters) for c in candidates):
        raise RuntimeError("retriever violated product scope")
    ranked = rerank_fn(scope.query, candidates, top_n=FINAL_K)
    if any(not matches(c["metadata"], scope.filters) for c in ranked):
        raise RuntimeError("reranker violated product scope")
    if any(not math.isfinite(c["reranker_score"]) for c in ranked):
        raise RuntimeError("reranker returned invalid scores")
    accepted = [c for c in ranked if c["reranker_score"] >= min_score][:top_k]
    if not accepted:
        base.update(status="no_evidence", message="本次检索未找到足够相关的路由器资料，无法依据这些资料回答该问题。当前服务仅提供已收录设备的资料问答与故障排查建议。")
        return base
    base.update(results=[{**c, "citation_id": f"[{i}]"} for i, c in enumerate(accepted, 1)], has_results=True)
    return base

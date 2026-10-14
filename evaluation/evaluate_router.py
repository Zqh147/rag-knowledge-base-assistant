"""Real retrieval evaluation; calibration questions never count as holdout tests."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import time
from config import BASE_DIR, POLICY_PATH, EMBEDDING_MODEL, RERANKER_MODEL
from router_corpus import make_chunks, corpus_digest
from vector_store import verify_router_index
from product_scope import resolve_scope
from router_corpus import available_products, load_sections
from retriever import retrieve
from bm25_retriever import retrieve_bm25
from hybrid_retriever import reciprocal_rank_fusion
from reranker import rerank


def evidence_ids(results):
    return [r["metadata"]["evidence_id"] if isinstance(r, dict) else r[2]["evidence_id"] for r in results]


def metrics(rows, method, k=3):
    positives = [r for r in rows if r["answerable"]]
    recall, reciprocal = [], []
    for r in positives:
        ids, gold = r["rankings"][method], set(r["gold_evidence_ids"])
        recall.append(len(set(ids[:k]) & gold) / len(gold))
        ranks = [i for i, uid in enumerate(ids, 1) if uid in gold]
        reciprocal.append(1 / min(ranks) if ranks else 0)
    return {f"Recall@{k}": sum(recall) / len(recall), "MRR": sum(reciprocal) / len(reciprocal), "positive_questions": len(positives)}


def choose_threshold(rows):
    scores = sorted(set(r["top_score"] for r in rows))
    thresholds = [scores[0] - 1, scores[-1] + 1] + [(a+b)/2 for a,b in zip(scores, scores[1:])]
    def errors(threshold):
        return sum((r["top_score"] >= threshold) != r["answerable"] for r in rows)
    # Higher threshold breaks ties conservatively.
    return min(thresholds, key=lambda t: (errors(t), -t))


def run(split):
    data = json.loads((BASE_DIR / "evaluation/router_questions.json").read_text(encoding="utf-8"))
    selected = [q for q in data if q["split"] == split]
    chunks = make_chunks()
    digest = corpus_digest(chunks)
    verify_router_index(chunks, digest)
    products = available_products(load_sections())
    rows = []
    for item in selected:
        scope = resolve_scope(item["question"], products, **{k:item[k] for k in ("product_model", "hardware_version", "region")})
        if scope.status != "ok":
            raise ValueError(f"evaluation question has unresolved scope: {item['id']}")
        started = time.perf_counter()
        vector = retrieve(scope.query, top_k=10, filters=scope.filters)
        bm25 = retrieve_bm25(scope.query, top_k=10, filters=scope.filters)
        hybrid = reciprocal_rank_fusion(vector, bm25)[:10]
        ranked = rerank(scope.query, hybrid, top_n=10)
        row = {**item, "rankings": {name:evidence_ids(result) for name,result in
               [("Vector",vector),("BM25",bm25),("Hybrid",hybrid),("Reranker",ranked)]},
               "top_score": ranked[0]["reranker_score"] if ranked else -100,
               "scored_evidence": [{"id": r["metadata"]["evidence_id"], "score": r["reranker_score"]} for r in ranked],
               "elapsed_seconds": round(time.perf_counter()-started,3)}
        if any(any(c["metadata"].get(k) != v for k,v in scope.filters.items()) for c in ranked):
            raise RuntimeError("product leakage in real evaluation")
        rows.append(row)
        print(item["id"], round(row["top_score"],3), row["rankings"]["Reranker"][:1], flush=True)
    if split == "calibration":
        threshold = choose_threshold(rows)
        policy = {"model": RERANKER_MODEL, "score_scale": "raw_logit", "min_score": threshold,
                  "corpus_digest": digest, "calibration_questions": len(rows),
                  "method": "minimize false accept + false reject on calibration only; higher threshold breaks ties",
                  "limitations": "Small hand-authored set. Score is relevance, not answer confidence. Threshold cannot ensure complete answer support."}
        POLICY_PATH.write_text(json.dumps(policy,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    else:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        if policy["corpus_digest"] != digest:
            raise RuntimeError("stale calibration policy")
        threshold = policy["min_score"]
    for row in rows:
        accepted = [r["id"] for r in row["scored_evidence"] if r["score"] >= threshold][:3]
        row.update(accepted_evidence=accepted, status="ok" if accepted else "no_evidence")
    report = {"split": split, "executed_at": datetime.now(timezone.utc).isoformat(),
              "python":platform.python_version(), "versions":{x:importlib.metadata.version(x) for x in
              ("torch","sentence-transformers","chromadb","jieba","rank-bm25","fastapi","pytest")},
              "models":{"embedding":EMBEDDING_MODEL,"reranker":RERANKER_MODEL},
              "corpus_digest":digest,"min_score":threshold, "score_scale":"raw_logit",
              "question_count":len(rows),"metrics":{m:metrics(rows,m) for m in ("Vector","BM25","Hybrid","Reranker")},
              "gated_recall_at_3": sum(len(set(r["accepted_evidence"]) & set(r["gold_evidence_ids"]))/len(r["gold_evidence_ids"])
                                      for r in rows if r["answerable"])/sum(r["answerable"] for r in rows),
              "false_accepts":sum(bool(r["accepted_evidence"]) and not r["answerable"] for r in rows),
              "false_rejects":sum(not r["accepted_evidence"] and r["answerable"] for r in rows),
              "rows":rows}
    output = BASE_DIR / "evaluation" / f"router_{split}_results.json"
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k != "rows"},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["calibration","holdout"], required=True)
    run(parser.parse_args().split)

"""Capture real answers and aggregate explicit human reviews; never invent scores."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform


def summarize(run):
    cases = run["cases"]
    rows = run["rows"]
    expected = {c["id"]: c for c in cases}
    if len(expected) != len(cases) or len(rows) != len(cases) or {r["id"] for r in rows} != set(expected):
        raise ValueError("every planned case must appear exactly once")
    coverage, citation_checks, refusal_checks = [], [], []
    supported, claim_count, answers_with_claims, unsupported_answers = 0, 0, 0, 0
    for row in rows:
        if row.get("error"):
            raise ValueError("run contains failed cases; retain errors and rerun before reporting complete metrics")
        case = expected[row["id"]]
        review = row["review"]
        if case["answerable"]:
            required = {p["id"] for p in case["required_points"]}
            covered = review.get("covered_point_ids")
            if not required or not isinstance(covered, list) or len(set(covered)) != len(covered) or not set(covered) <= required:
                raise ValueError("review every required point; unknown or duplicate point IDs are invalid")
            coverage.append(len(covered) / len(required))
        else:
            verdict = review.get("refusal_correct")
            if type(verdict) is not bool:
                raise ValueError("review every out-of-corpus refusal explicitly")
            refusal_checks.append(verdict)
        if row["generation_called"]:
            claims = review.get("claims")
            verdict = review.get("citation_correct")
            if not isinstance(claims, list) or type(verdict) is not bool:
                raise ValueError("generated answers need claim-level and citation reviews")
            citation_checks.append(verdict)
            unsupported = False
            for claim in claims:
                if not isinstance(claim.get("text"), str) or not claim["text"].strip() or type(claim.get("supported")) is not bool:
                    raise ValueError("each factual claim needs text and a boolean support verdict")
                claim_count += 1
                supported += claim["supported"]
                unsupported = unsupported or not claim["supported"]
            if claims:
                answers_with_claims += 1
                unsupported_answers += unsupported
    mean = lambda values: sum(values) / len(values) if values else None
    return {
        "evaluation_type": "human-reviewed regression cases; not an independent generalization benchmark",
        "case_count": len(cases), "answerable_cases": len(coverage), "out_of_corpus_cases": len(refusal_checks),
        "mean_required_point_coverage": mean(coverage),
        "evidence_support_rate": supported / claim_count if claim_count else None,
        "supported_claims": supported, "reviewed_factual_claims": claim_count,
        "answers_with_unsupported_claim_rate": unsupported_answers / answers_with_claims if answers_with_claims else None,
        "answers_with_unsupported_claims": unsupported_answers, "answers_with_factual_claims": answers_with_claims,
        "citation_review_pass_rate": mean(citation_checks), "generated_answers": len(citation_checks),
        "out_of_corpus_refusal_correct_rate": mean(refusal_checks),
        "limitations": "Human verdicts require evidence checks. Unsupported does not necessarily mean factually false. Zero claims gives no faithfulness score. Keep model errors and report denominators.",
    }


def capture(output, evidence_only=False):
    from config import BASE_DIR
    from generator import rag_answer, build_messages
    from router_corpus import make_chunks, corpus_digest
    from router_pipeline import retrieve_router, load_policy
    from vector_store import verify_router_index
    chunks = make_chunks()
    digest = corpus_digest(chunks)
    verify_router_index(chunks, digest)
    load_policy()
    cases = json.loads((BASE_DIR / "evaluation/generation_cases.json").read_text(encoding="utf-8"))
    prompt = build_messages("", [])[0]["content"]
    report = {"evaluation_type": "regression capture", "executed_at": datetime.now(timezone.utc).isoformat(),
              "python": platform.python_version(), "corpus_digest": digest,
              "generation_model": None if evidence_only else "deepseek-flash",
              "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "cases": cases, "rows": []}
    output = Path(output)
    if output.exists():
        raise ValueError("output already exists; choose a new filename to preserve earlier answers")
    output.parent.mkdir(parents=True, exist_ok=True)
    for case in cases:
        row = {"id": case["id"], "generation_called": False, "review": {
            "covered_point_ids": None, "claims": None, "citation_correct": None, "refusal_correct": None}}
        try:
            result = retrieve_router(case["question"], **case["scope"])
            row.update(retrieval_status=result["status"], evidence=result["results"])
            ids = {r["metadata"]["evidence_id"] for r in result["results"]}
            row["evidence_check_passed"] = (set(case["required_evidence_ids"]) <= ids if case["answerable"] else result["status"] == "no_evidence")
            if evidence_only:
                row["answer"] = None
            elif result["has_results"]:
                row["generation_called"] = True
                row["answer"] = rag_answer(case["question"], result["results"])
            else:
                row["answer"] = result["message"]
            print(case["id"], "evidence:", row["evidence_check_passed"], flush=True)
        except Exception as exc:
            row["error"] = type(exc).__name__
            print(case["id"], "ERROR", type(exc).__name__, flush=True)
        report["rows"].append(row)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Saved:", output.resolve())
    if any(r.get("error") for r in report["rows"]):
        raise SystemExit(1)
    if evidence_only:
        passed = sum(r["evidence_check_passed"] for r in report["rows"])
        print(f"{passed}/{len(cases)} regression evidence checks passed; generation not called")
        if passed != len(cases):
            raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser()
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--capture", action="store_true")
    actions.add_argument("--evidence-only", action="store_true")
    actions.add_argument("--summarize", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.summarize:
        run = json.loads(args.summarize.read_text(encoding="utf-8"))
        if run.get("generation_model") is None:
            raise ValueError("evidence-only runs cannot produce generation-quality metrics")
        print(json.dumps(summarize(run), ensure_ascii=False, indent=2))
    else:
        from config import BASE_DIR
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output = args.output or BASE_DIR / "evaluation/answer_runs" / f"{stamp}.json"
        capture(output, evidence_only=args.evidence_only)


if __name__ == "__main__":
    main()

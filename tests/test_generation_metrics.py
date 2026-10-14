"""Prevent unreviewed, failed or double-counted examples from becoming resume metrics."""
import copy
import pytest
from evaluation.evaluate_generation import summarize


def reviewed_run():
    return {
        "cases": [{"id": "a", "answerable": True, "required_points": [{"id": "a1"}, {"id": "a2"}]},
                  {"id": "b", "answerable": True, "required_points": [{"id": "b1"}]},
                  {"id": "c", "answerable": False, "required_points": []}],
        "rows": [{"id": "a", "generation_called": True, "review": {
                    "covered_point_ids": ["a1"], "citation_correct": False,
                    "claims": [{"text": "supported step", "supported": True}, {"text": "unsupported step", "supported": False}]}},
                 {"id": "b", "generation_called": True, "review": {
                    "covered_point_ids": ["b1"], "citation_correct": True,
                    "claims": [{"text": "supported fact", "supported": True}]}},
                 {"id": "c", "generation_called": False, "review": {"refusal_correct": True}}],
    }


def test_coverage_support_and_answer_level_rates_use_distinct_denominators():
    result = summarize(reviewed_run())
    assert result["mean_required_point_coverage"] == 0.75
    assert result["evidence_support_rate"] == pytest.approx(2 / 3)
    assert result["answers_with_unsupported_claim_rate"] == 0.5
    assert result["citation_review_pass_rate"] == 0.5
    assert result["out_of_corpus_refusal_correct_rate"] == 1.0


@pytest.mark.parametrize("field", ["covered_point_ids", "claims", "citation_correct"])
def test_unreviewed_fields_do_not_silently_count_as_passes(field):
    run = reviewed_run()
    run["rows"][0]["review"][field] = None
    with pytest.raises(ValueError):
        summarize(run)


def test_failed_missing_duplicate_and_double_counted_cases_are_rejected():
    original = reviewed_run()
    invalid = []
    failed = copy.deepcopy(original)
    failed["rows"][0]["error"] = "API unavailable"
    invalid.append(failed)
    missing = copy.deepcopy(original)
    missing["rows"].pop()
    invalid.append(missing)
    duplicate = copy.deepcopy(original)
    duplicate["rows"][1]["id"] = "a"
    invalid.append(duplicate)
    inflated = copy.deepcopy(original)
    inflated["rows"][0]["review"]["covered_point_ids"] = ["a1", "a1"]
    invalid.append(inflated)
    for run in invalid:
        with pytest.raises(ValueError):
            summarize(run)


def test_empty_claims_do_not_create_a_perfect_faithfulness_score():
    run = reviewed_run()
    for row in run["rows"][:2]:
        row["review"]["claims"] = []
        row["review"]["covered_point_ids"] = []
    result = summarize(run)
    assert result["mean_required_point_coverage"] == 0.0
    assert result["evidence_support_rate"] is None
    assert result["answers_with_unsupported_claim_rate"] is None

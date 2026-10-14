import json
from types import SimpleNamespace
import pytest
from product_scope import resolve_scope
from chunker import split_section, split_text
from router_corpus import load_sections, make_chunks
from generator import rag_answer, build_messages
from router_pipeline import retrieve_router

PRODUCTS = [("Archer AX10", "V1", "US"), ("Archer AX10", "V2", "US"), ("Archer AX20", "V1", "US")]


@pytest.mark.parametrize("question,fields,status", [
    ("AX10 V1 US怎么改Wi-Fi密码", {}, "ok"),
    ("archer ax10 v1.0 美版怎么改Wi-Fi密码", {}, "ok"),
    ("怎么改Wi-Fi密码", {"product_model": "AX10", "hardware_version": "1", "region": "us"}, "ok"),
    ("AX10怎么改密码", {}, "needs_clarification"),
    ("AX100 V1 US怎么改密码", {}, "unsupported_product"),
    ("AX10 V1.20 US怎么改密码", {}, "unsupported_product"),
    ("AX10 V1 US和AX20 V1 US怎么改密码", {}, "parameter_conflict"),
    ("AX10 V1 US怎么改密码", {"hardware_version": "V2"}, "parameter_conflict"),
    ("AX10 V1 US怎么改密码", {"region": "EU"}, "parameter_conflict"),
    ("华为AX10 V1 US怎么改密码", {}, "unsupported_product"),
])
def test_scope_resolution(question, fields, status):
    result = resolve_scope(question, PRODUCTS, **fields)
    assert result.status == status
    if status == "ok":
        assert result.filters == {"product_model": "Archer AX10", "hardware_version": "V1", "region": "US"}


def test_same_model_different_hardware_cannot_be_guessed():
    result = resolve_scope("AX10 US怎么改密码", PRODUCTS)
    assert result.status == "needs_clarification" and result.missing_fields == ["hardware_version"]
    assert resolve_scope("AX10 V2 US怎么改密码", PRODUCTS).filters["hardware_version"] == "V2"


def test_procedure_stays_complete_and_oversized_procedure_is_rejected():
    text = "适用：已联网。\n1. 登录。\n2. 改密码。\n3. 重新连接。\n注意：记录新密码。"
    chunks = split_section("无线设置", text)
    assert chunks == ["无线设置\n" + text]
    with pytest.raises(ValueError, match="complete procedures"):
        split_section("无线设置", text, max_chars=10)


@pytest.mark.parametrize("size,overlap", [(0, 0), (10, -1), (10, 10)])
def test_invalid_chunk_parameters(size, overlap):
    with pytest.raises(ValueError):
        split_text("text", size, overlap)


def test_corpus_metadata_and_duplicate_validation(tmp_path):
    records = load_sections()
    ids = [c["id"] for c in make_chunks(records)]
    assert len(ids) == len(set(ids))
    records.append(dict(records[0]))
    path = tmp_path / "knowledge.json"
    path.write_text(json.dumps(records))
    with pytest.raises(ValueError, match="duplicate"):
        load_sections(path)


def test_scope_leak_is_a_failure_not_an_answer():
    candidate = make_chunks()[0]
    foreign = {**candidate, "metadata": {**candidate["metadata"], "product_model": "Archer AX20"}}
    with pytest.raises(RuntimeError, match="violated product scope"):
        retrieve_router("AX10 V1 US指示灯为什么橙色", retrieve_fn=lambda *a, **k: [foreign],
                        rerank_fn=lambda *a, **k: [], min_score=0)


def test_generation_checks_citation_ids_and_preserves_source_steps():
    evidence = [next(c for c in make_chunks() if c["metadata"]["evidence_id"] == "ax10-v1-us-wireless")]
    captured = []
    def fake_client(answer):
        def create(**kwargs):
            captured.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=answer))])
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    answer = rag_answer("怎么改密码", evidence, client=fake_client("进入 Wireless Settings 修改密码。[1]"))
    assert evidence[0]["metadata"]["source_url"] in answer
    assert "3. 在 Network Name" in captured[0]["messages"][1]["content"]
    assert "不要输出相关性分数" in build_messages("test", evidence)[0]["content"]
    for bad in ("直接改密码。", "进入未知菜单。[99]"):
        assert "不展示操作建议" in rag_answer("test", evidence, client=fake_client(bad))
    assert "资料不足" in rag_answer("test", [], client=fake_client("must not be called"))
    assert len(captured) == 3

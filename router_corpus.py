"""Reviewed summaries of official sections, shared by both retrieval lanes."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from config import CORPUS_PATH
from chunker import split_section

REQUIRED = ("evidence_id", "product_model", "hardware_version", "region",
            "doc_type", "section", "source_url", "doc_version", "reviewed_at", "content")


def load_sections(path=CORPUS_PATH):
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError("router corpus must be a nonempty list")
    seen = set()
    for item in records:
        if not isinstance(item, dict) or any(not isinstance(item.get(k), str) or not item[k].strip() for k in REQUIRED):
            raise ValueError("router section is missing required metadata/content")
        if item["evidence_id"] in seen:
            raise ValueError("duplicate evidence_id")
        seen.add(item["evidence_id"])
        u = urlparse(item["source_url"])
        if u.scheme != "https" or u.hostname != "www.tp-link.com":
            raise ValueError("this corpus requires a TP-Link official HTTPS source")
        if item["product_model"] not in {"Archer AX10", "Archer AX20"} or item["hardware_version"] != "V1" or item["region"] != "US":
            raise ValueError("new product/version/region needs manual source review first")
        split_section(item["section"], item["content"])
    return records


def make_chunks(records=None):
    records = load_sections() if records is None else records
    chunks = []
    for item in records:
        for index, text in enumerate(split_section(item["section"], item["content"])):
            metadata = {k: item[k] for k in REQUIRED if k != "content"}
            metadata.update(source="knowledge.json", chunk_id=index)
            chunks.append({"id": f"{item['evidence_id']}_chunk_{index}",
                           "document": text, "metadata": metadata})
    return chunks


def corpus_digest(chunks=None):
    chunks = make_chunks() if chunks is None else chunks
    return hashlib.sha256(json.dumps(chunks, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def available_products(records):
    return sorted({(r["product_model"], r["hardware_version"], r["region"]) for r in records})

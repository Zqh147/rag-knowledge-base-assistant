"""Defaults isolate router knowledge; demo data requires an explicit profile."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
PROFILE = os.getenv("RAG_PROFILE", "router")
if PROFILE not in {"router", "demo"}:
    raise ValueError("RAG_PROFILE must be router or demo")
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
MODEL_DEVICE = os.getenv("RAG_MODEL_DEVICE", "cpu")
CPU_THREADS = int(os.getenv("RAG_CPU_THREADS", "4"))
DB_PATH = str(Path(os.getenv("RAG_DB_PATH", str(BASE_DIR / "chromadb"))).resolve())
COLLECTION_NAME = "router_manuals_v1" if PROFILE == "router" else "pdf_test"
CORPUS_PATH = BASE_DIR / "data" / "router" / "knowledge.json"
POLICY_PATH = BASE_DIR / "data" / "router" / "retrieval_policy.json"
CHUNK_SIZE, CHUNK_OVERLAP = 100, 25
TOP_K, THRESHOLD = 3, 0
CANDIDATE_K, FINAL_K, RERANK_K = 10, 10, 3

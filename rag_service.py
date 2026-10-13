"""Run from the existing RAG project root: python -m uvicorn rag_service:app --port 8001"""
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class RetrieveRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=3, ge=1, le=5)


class Evidence(BaseModel):
    content: str
    source: str
    page: int | None = None
    chunk_id: int
    rrf_score: float | None = None
    reranker_score: float | None = None


class RetrieveResponse(BaseModel):
    question: str
    backend: str = "project1"
    pipeline: str = "vector+bm25+rrf+cross_encoder"
    results: list[Evidence]
    has_results: bool


def create_app(retrieve_fn=None, rerank_fn=None, ready_check=None, candidate_k=10, final_k=10):
    lock = Lock()

    @asynccontextmanager
    async def lifespan(app):
        if retrieve_fn is None or rerank_fn is None:
            if Path.cwd().resolve() != Path(__file__).resolve().parent:
                raise RuntimeError("Start rag_service from your RAG project root directory")
            # Reuse the actual V2 functions. Import once to load models/indexes.
            from hybrid_retriever import retrieve_hybrid
            from reranker import rerank
            from vector_store import get_document_count
            from config import CANDIDATE_K, FINAL_K
            app.state.retrieve = retrieve_hybrid
            app.state.rerank = rerank
            app.state.candidate_k = CANDIDATE_K
            app.state.final_k = FINAL_K
            check = get_document_count
        else:
            app.state.retrieve, app.state.rerank = retrieve_fn, rerank_fn
            app.state.candidate_k, app.state.final_k = candidate_k, final_k
            check = ready_check
        if check is not None and check() <= 0:
            raise RuntimeError("RAG index is empty. Run python build_index.py first")
        app.state.ready = True
        try:
            yield
        finally:
            app.state.ready = False

    app = FastAPI(title="Project One Retrieval API", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok", "ready": getattr(app.state, "ready", False), "backend": "project1"}

    @app.post("/retrieve", response_model=RetrieveResponse)
    def retrieve(request: RetrieveRequest):
        if not request.question.strip():
            raise HTTPException(status_code=422, detail="question must not be blank")
        if not getattr(app.state, "ready", False):
            raise HTTPException(status_code=503, detail="retrieval service not ready")
        # Serialize CPU/model access for this single-process local service.
        with lock:
            candidates = app.state.retrieve(
                request.question, candidate_k=app.state.candidate_k,
                final_k=max(app.state.final_k, request.top_k),
            )
            ranked = app.state.rerank(request.question, candidates, top_n=request.top_k)
        results = [Evidence(content=item["document"], source=item["metadata"]["source"],
                            page=item["metadata"].get("page"), chunk_id=item["metadata"]["chunk_id"],
                            rrf_score=item.get("rrf_score"), reranker_score=item.get("reranker_score"))
                   for item in ranked]
        return RetrieveResponse(question=request.question, results=results, has_results=bool(results))

    return app


app = create_app()

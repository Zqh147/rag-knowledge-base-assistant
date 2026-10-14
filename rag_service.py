"""Project Two compatible evidence API. No generation-model call here."""
from contextlib import asynccontextmanager
import logging
from threading import Lock
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from router_corpus import load_sections, available_products, make_chunks, corpus_digest
from router_pipeline import retrieve_router, load_policy

log = logging.getLogger(__name__)


class RetrieveRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=3, ge=1, le=5, strict=True)
    product_model: str | None = Field(default=None, min_length=1, max_length=100)
    hardware_version: str | None = Field(default=None, min_length=1, max_length=30)
    region: str | None = Field(default=None, min_length=1, max_length=30)

    @field_validator("question", "product_model", "hardware_version", "region")
    @classmethod
    def nonblank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value.strip() if value is not None else None


class Evidence(BaseModel):
    content: str
    source: str
    page: int | None = None
    chunk_id: int
    rrf_score: float | None = None
    reranker_score: float | None = None
    citation_id: str
    evidence_id: str
    product_model: str
    hardware_version: str
    region: str
    doc_type: str
    section: str
    source_url: str
    doc_version: str
    reviewed_at: str


class RetrieveResponse(BaseModel):
    question: str
    backend: str = "project1"
    pipeline: str = "vector+bm25+rrf+cross_encoder"
    results: list[Evidence]
    has_results: bool
    status: str
    message: str = ""
    resolved_scope: dict[str, str] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    score_scale: str = "raw_logit"


def create_app(retrieve_fn=None, rerank_fn=None, ready_check=None, products=None, min_score=None):
    lock = Lock()

    @asynccontextmanager
    async def lifespan(app):
        app.state.ready = False
        if (retrieve_fn is None) != (rerank_fn is None):
            raise RuntimeError("inject both retrieval and reranking functions")
        if retrieve_fn is None:
            from config import PROFILE
            if PROFILE != "router":
                raise RuntimeError("domain API requires RAG_PROFILE=router; no demo fallback")
            from hybrid_retriever import retrieve_hybrid
            from reranker import rerank, get_model as reranker_model
            from embedder import get_model as embedding_model
            from vector_store import verify_router_index
            sections = load_sections()
            chunks = make_chunks(sections)
            verify_router_index(chunks, corpus_digest(chunks))
            app.state.products = available_products(sections)
            app.state.min_score = load_policy()
            embedding_model()
            reranker_model()
            app.state.retrieve, app.state.rerank = retrieve_hybrid, rerank
        else:
            app.state.products = available_products(load_sections()) if products is None else products
            app.state.min_score = load_policy() if min_score is None else min_score
            app.state.retrieve, app.state.rerank = retrieve_fn, rerank_fn
        if ready_check is not None and ready_check() <= 0:
            raise RuntimeError("RAG index is empty. Run python build_index.py first")
        app.state.ready = True
        try:
            yield
        finally:
            app.state.ready = False

    app = FastAPI(title="Router Knowledge Retrieval API", lifespan=lifespan)

    @app.get("/health")
    def health():
        ready = getattr(app.state, "ready", False)
        if not ready:
            raise HTTPException(status_code=503, detail={"code": "retrieval_unavailable", "message": "retrieval service not ready"})
        return {"status": "ok", "ready": True, "backend": "project1", "domain": "home_router"}

    @app.get("/products")
    def list_products():
        if not getattr(app.state, "ready", False):
            raise HTTPException(status_code=503, detail="retrieval service not ready")
        return [{"product_model": p[0], "hardware_version": p[1], "region": p[2]} for p in app.state.products]

    @app.post("/retrieve", response_model=RetrieveResponse)
    def retrieve(request: RetrieveRequest):
        if not getattr(app.state, "ready", False):
            raise HTTPException(status_code=503, detail={"code": "retrieval_unavailable", "message": "retrieval service not ready"})
        try:
            with lock:
                result = retrieve_router(**request.model_dump(), retrieve_fn=app.state.retrieve,
                                         rerank_fn=app.state.rerank, products=app.state.products,
                                         min_score=app.state.min_score)
            evidence = []
            for item in result["results"]:
                metadata = item["metadata"]
                evidence.append(Evidence(content=item["document"], citation_id=item["citation_id"],
                                         rrf_score=item.get("rrf_score"), reranker_score=item["reranker_score"],
                                         **metadata))
            return RetrieveResponse(question=request.question, **{**result, "results": evidence})
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            log.exception("Retrieval failed")
            raise HTTPException(status_code=503, detail={"code": "retrieval_unavailable",
                                  "message": "检索服务执行失败，请检查服务日志；此错误不表示知识库没有答案。"}) from exc

    return app


app = create_app()

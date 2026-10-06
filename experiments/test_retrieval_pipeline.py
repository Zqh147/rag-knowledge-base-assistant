from hybrid_retriever import retrieve_hybrid
from reranker import rerank
from generator import rag_answer


question = "Embedding在RAG系统中有什么作用？"

hybrid_results = retrieve_hybrid(question)

reranked_results = rerank(
    question,
    hybrid_results
)

print("\nReranker最终数量：", len(reranked_results))

print("Hybrid候选数量：", len(hybrid_results))

for index, result in enumerate(hybrid_results, start=1):

    metadata = result["metadata"]

    print(f"\n===== Hybrid Top{index} =====")

    print("RRF Score：", result["rrf_score"])

    print("Vector Rank：", result["vector_rank"])

    print("BM25 Rank：", result["bm25_rank"])

    print("来源：", metadata["source"])

    print("页码：", metadata.get("page"))

    print("Chunk ID：", metadata["chunk_id"])


for index, result in enumerate(reranked_results, start=1):

    metadata = result["metadata"]

    print(f"\n===== Reranker Top{index} =====")

    print("Reranker Score：", result["reranker_score"])

    print("RRF Score：", result["rrf_score"])

    print("Vector Rank：", result["vector_rank"])

    print("BM25 Rank：", result["bm25_rank"])

    print("来源：", metadata["source"])

    print("页码：", metadata.get("page"))

    print("Chunk ID：", metadata["chunk_id"])

    print("内容：", result["document"])

answer = rag_answer(
    question,
    reranked_results
)

print("\n========== AI Answer ==========")
print(answer)
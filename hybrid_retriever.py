from retriever import retrieve
from bm25_retriever import retrieve_bm25
from config import CANDIDATE_K, FINAL_K


def get_chunk_uid(metadata):

    source = metadata["source"]
    page = metadata.get("page")
    chunk_id = metadata["chunk_id"]

    if page is None:
        return f"{source}_chunk_{chunk_id}"

    return f"{source}_page_{page}_chunk_{chunk_id}"


def reciprocal_rank_fusion(
    vector_results,
    bm25_results,
    k=60
):

    fused_results = {}

    # 处理 Vector Search
    for rank, (document, similarity, metadata) in enumerate(
        vector_results,
        start=1
    ):

        chunk_uid = get_chunk_uid(metadata)

        rrf_score = 1 / (k + rank)

        fused_results[chunk_uid] = {
            "document": document,
            "metadata": metadata,
            "rrf_score": rrf_score,
            "vector_rank": rank,
            "bm25_rank": None
        }


    # 处理 BM25 Search
    for rank, (document, score, metadata) in enumerate(
        bm25_results,
        start=1
    ):

        chunk_uid = get_chunk_uid(metadata)

        rrf_score = 1 / (k + rank)

        if chunk_uid in fused_results:

            fused_results[chunk_uid]["rrf_score"] += rrf_score
            fused_results[chunk_uid]["bm25_rank"] = rank

        else:

            fused_results[chunk_uid] = {
                "document": document,
                "metadata": metadata,
                "rrf_score": rrf_score,
                "vector_rank": None,
                "bm25_rank": rank
            }


    results = list(fused_results.values())

    results.sort(
        key=lambda x: x["rrf_score"],
        reverse=True
    )

    return results

def retrieve_hybrid(
    question,
    candidate_k=CANDIDATE_K,
    final_k=FINAL_K
):

    vector_results = retrieve(
        question,
        top_k=candidate_k
    )

    bm25_results = retrieve_bm25(
        question,
        top_k=candidate_k
    )

    fused_results = reciprocal_rank_fusion(
        vector_results,
        bm25_results
    )

    return fused_results[:final_k]


if __name__ == "__main__":

    question = input("请输入问题：")

    hybrid_results = retrieve_hybrid(
        question,
        candidate_k=5,
        final_k=3
    )

    print("\n========== Hybrid Search ==========")

    for index, result in enumerate(hybrid_results):

        document = result["document"]
        metadata = result["metadata"]
        rrf_score = result["rrf_score"]


        print(f"\n===== Hybrid 检索结果 {index + 1} =====")

        print(f"内容：{document}")
        print(f"RRF Score：{rrf_score:.6f}")

        print(f"Vector Rank：{result['vector_rank']}")
        print(f"BM25 Rank：{result['bm25_rank']}")

        print(f"来源：{metadata['source']}")

        if metadata.get("page") is not None:
            print(f"页码：{metadata['page']}")

        print(f"Chunk ID：{metadata['chunk_id']}")
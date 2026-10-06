def get_chunk_uid(metadata):
    """
    根据 metadata 生成 Chunk 的唯一标识
    """

    source = metadata["source"]
    page = metadata.get("page")
    chunk_id = metadata["chunk_id"]

    if page is None:
        return f"{source}_chunk_{chunk_id}"

    return f"{source}_page_{page}_chunk_{chunk_id}"


def get_result_metadata(result):
    """
    从不同类型的检索结果中取出 metadata

    Vector / BM25:
        (document, score, metadata)

    Hybrid / Reranker:
        {
            "document": ...,
            "metadata": ...
        }
    """

    if isinstance(result, dict):
        return result["metadata"]

    return result[2]


def find_rank(results, ground_truth):
    """
    查找 Ground Truth 在检索结果中的排名

    如果没有找到，返回 None
    """

    ground_truth_uid = get_chunk_uid(ground_truth)

    for rank, result in enumerate(results, start=1):

        metadata = get_result_metadata(result)

        result_uid = get_chunk_uid(metadata)

        if result_uid == ground_truth_uid:
            return rank

    return None


def recall_at_k(results, ground_truth, k):
    """
    计算单个问题的 Recall@K

    命中 = 1
    未命中 = 0
    """

    rank = find_rank(results, ground_truth)

    if rank is not None and rank <= k:
        return 1

    return 0


def reciprocal_rank(results, ground_truth):
    """
    计算单个问题的 Reciprocal Rank
    """

    rank = find_rank(results, ground_truth)

    if rank is None:
        return 0.0

    return 1 / rank
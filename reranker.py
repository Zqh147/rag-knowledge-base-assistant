from sentence_transformers import CrossEncoder
from config import RERANK_K


# 加载 Reranker 模型
reranker_model = CrossEncoder(
    "BAAI/bge-reranker-v2-m3"
)


def rerank(question, candidates, top_n=RERANK_K):

    # 如果没有候选结果，直接返回空列表
    if not candidates:
        return []

    # 1. 构造 [Question, Chunk] 对
    pairs = []

    for candidate in candidates:
        document = candidate["document"]

        pairs.append([
            question,
            document
        ])

    # 2. Reranker 对每一个 Question-Chunk pair 打分
    scores = reranker_model.predict(pairs)

    # 3. 把 reranker score 和对应的 candidate 组合起来
    reranked_results = []

    for candidate, score in zip(candidates, scores):

        # 复制原来的 Hybrid 结果
        result = candidate.copy()

        # 新增 reranker score
        result["reranker_score"] = float(score)

        reranked_results.append(result)

    # 4. 按 reranker score 从高到低重新排序
    reranked_results.sort(
        key=lambda x: x["reranker_score"],
        reverse=True
    )

    # 5. 返回重新排序后的 Top-N
    return reranked_results[:top_n]
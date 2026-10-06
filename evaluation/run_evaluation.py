from retriever import retrieve
from bm25_retriever import retrieve_bm25
from hybrid_retriever import retrieve_hybrid
from reranker import rerank

from .evaluate import (
    find_rank,
    recall_at_k,
    reciprocal_rank
)

from .evaluation_data import evaluation_questions

EVAL_K = 10

# 每种检索方法的统计结果
metrics = {
    "Vector": {
        "recall@1": 0,
        "recall@3": 0,
        "recall@5": 0,
        "rr": 0.0
    },

    "BM25": {
        "recall@1": 0,
        "recall@3": 0,
        "recall@5": 0,
        "rr": 0.0
    },

    "Hybrid": {
        "recall@1": 0,
        "recall@3": 0,
        "recall@5": 0,
        "rr": 0.0
    },

    "Hybrid + Reranker": {
        "recall@1": 0,
        "recall@3": 0,
        "recall@5": 0,
        "rr": 0.0
    }
}


def update_metrics(method_name, results, ground_truth):

    metrics[method_name]["recall@1"] += recall_at_k(
        results,
        ground_truth,
        k=1
    )

    metrics[method_name]["recall@3"] += recall_at_k(
        results,
        ground_truth,
        k=3
    )

    metrics[method_name]["recall@5"] += recall_at_k(
        results,
        ground_truth,
        k=5
    )

    metrics[method_name]["rr"] += reciprocal_rank(
        results,
        ground_truth
    )


if __name__ == "__main__":

    total_questions = len(evaluation_questions)

    for index, item in enumerate(
        evaluation_questions,
        start=1
    ):

        question = item["question"]
        ground_truth = item["ground_truth"]

        print(f"\n========== Question {index} ==========")
        print(f"问题：{question}")

        print(
            "Ground Truth："
            f"{ground_truth['source']} | "
            f"page={ground_truth.get('page')} | "
            f"chunk={ground_truth['chunk_id']}"
        )

        # --------------------------------
        # 1. Vector Search
        # --------------------------------
        vector_results = retrieve(question,top_k=EVAL_K)

        # --------------------------------
        # 2. BM25
        # --------------------------------
        bm25_results = retrieve_bm25(question,top_k=EVAL_K)

        # --------------------------------
        # 3. Hybrid Search
        # --------------------------------
        hybrid_results = retrieve_hybrid(question,candidate_k=EVAL_K,final_k=EVAL_K)

        # --------------------------------
        # 4. Hybrid + Reranker
        # --------------------------------
        reranked_results = rerank(question,hybrid_results,top_n=EVAL_K)

        # --------------------------------
        # 更新评价指标
        # --------------------------------
        update_metrics(
            "Vector",
            vector_results,
            ground_truth
        )

        update_metrics(
            "BM25",
            bm25_results,
            ground_truth
        )

        update_metrics(
            "Hybrid",
            hybrid_results,
            ground_truth
        )

        update_metrics(
            "Hybrid + Reranker",
            reranked_results,
            ground_truth
        )

        # --------------------------------
        # 打印当前问题的 Ground Truth 排名
        # --------------------------------
        print(
            "Vector Rank：",
            find_rank(vector_results, ground_truth)
        )

        print(
            "BM25 Rank：",
            find_rank(bm25_results, ground_truth)
        )

        print(
            "Hybrid Rank：",
            find_rank(hybrid_results, ground_truth)
        )

        print(
            "Reranker Rank：",
            find_rank(reranked_results, ground_truth)
        )

    # ====================================
    # 计算所有问题的平均指标
    # ====================================

    print("\n\n========== Evaluation Result ==========")

    for method_name, result in metrics.items():

        recall_1 = result["recall@1"] / total_questions
        recall_3 = result["recall@3"] / total_questions
        recall_5 = result["recall@5"] / total_questions

        mrr = result["rr"] / total_questions

        print(f"\n{method_name}")

        print(f"Recall@1：{recall_1:.4f}")
        print(f"Recall@3：{recall_3:.4f}")
        print(f"Recall@5：{recall_5:.4f}")
        print(f"MRR：{mrr:.4f}")
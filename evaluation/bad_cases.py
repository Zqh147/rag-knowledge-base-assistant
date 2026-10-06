# 检索失败案例记录
#
# 排名含义：Ground Truth 在对应检索结果中的位置，1 为最优，None 表示未召回。
# 这些排名由 evaluation/run_evaluation.py 跑出来，会随切块参数
# （CHUNK_SIZE / CHUNK_OVERLAP）和检索参数（CANDIDATE_K / FINAL_K / RERANK_K）变化，
# 改完 config.py 后需要重跑评测同步这份记录。

bad_cases = [
    {
        "question": "Embedding在RAG系统中有什么作用？",

        "ground_truth": {
            "source": "test.pdf",
            "page": 2,
            "chunk_id": 3
        },

        "vector_rank": 5,
        "bm25_rank": 2,
        "hybrid_rank": 4,
        "reranker_rank": 1,

        "failure_stage": "Dense Retrieval Ranking + RRF Fusion",

        "analysis": (
            "向量检索把 Ground Truth 排在第5，说明语义召回本身命中了，"
            "但排序不如 BM25（第2），向量模型对这条 Question-Chunk 的区分度不够。"
            "RRF 融合后不升反降到第4：RRF 只用排名、不看相似度，"
            "这条 Chunk 的分数是 1/(60+5) + 1/(60+2) ≈ 0.0315，"
            "而两路都排第3的 Chunk 能拿到 2/(60+3) ≈ 0.0317，"
            "同时出现在两路靠前位置的 Chunk 会累加两份分数，把它挤到后面。"
            "Reranker 用 Cross-Encoder 联合编码 Question 和 Chunk，"
            "能判断出 RRF 看不到的深层相关性，重新排序后把它提升到第1。"
        )
    }
]

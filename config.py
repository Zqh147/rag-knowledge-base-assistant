EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

DB_PATH = "./chromadb"

COLLECTION_NAME = "pdf_test"

CHUNK_SIZE = 100

CHUNK_OVERLAP = 25

# 基础 Vector / BM25 单独检索时默认返回数量
TOP_K = 3

# Vector 相似度过滤阈值
THRESHOLD = 0

# Hybrid Search 中，Vector 和 BM25 各自召回的候选数量
CANDIDATE_K = 10

# RRF Fusion 后保留给 Reranker 的候选数量
FINAL_K = 10

# Reranker 最终保留并送给 LLM 的 Chunk 数量
RERANK_K = 3

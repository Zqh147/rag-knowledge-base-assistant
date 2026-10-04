from config import TOP_K, THRESHOLD
from embedder import embed_text
from vector_store import query_documents



#   定义检索函数
def retrieve(question, top_k=TOP_K, threshold=THRESHOLD):
    question_vector = embed_text(question)

    results = query_documents(question_vector, top_k)
    filtered_results = []
    for document, distance, metadata in zip(results["documents"][0], results["distances"][0], results["metadatas"][0]):
        similarity = 1 - distance
        if similarity >= threshold:
            filtered_results.append((document, similarity, metadata))
    return filtered_results

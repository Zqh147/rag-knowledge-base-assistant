import os
import jieba

from rank_bm25 import BM25Okapi

from loader import load_document
from chunker import split_text
from config import TOP_K


STOP_WORDS = {
    "的", "了", "是", "什么",
    "一个", "这个", "可以",
    "？", "?", "。", "，", ","
}

def tokenize(text):
    words = jieba.lcut(text.lower())

    words = [
        word.strip()
        for word in words
        if word.strip()
        and word.strip() not in STOP_WORDS
    ]

    return words


def load_chunks(data_dir="./data"):


    metadatas = []
    all_chunks = []

    for file_name in os.listdir(data_dir):

        if not file_name.endswith((".txt", ".pdf")):
            continue

        file_path = os.path.join(data_dir, file_name)

        pages = load_document(file_path)

        for page_data in pages:

            text = page_data["text"]
            page = page_data["page"]

            chunks = split_text(text)

            for index, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                chunk_id = index

                metadata = {
                "source": file_name,
                "page": page,
                "chunk_id": chunk_id,
                }


                metadatas.append(metadata)

    return all_chunks, metadatas


all_chunks, metadatas = load_chunks()


tokenized_documents = []

for document in all_chunks:
    tokenized_documents.append(
        tokenize(document)
    )


bm25 = BM25Okapi(tokenized_documents)


def retrieve_bm25(question, top_k=TOP_K):

    tokenized_question = tokenize(question)

    scores = bm25.get_scores(tokenized_question)

    results = []

    for index, score in enumerate(scores):

        results.append(
            (
                all_chunks[index],
                score,
                metadatas[index]
            )
        )

    results.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return results[:top_k]


if __name__ == "__main__":

    question = input("请输入问题：")

    results = retrieve_bm25(
        question,
        top_k=3
    )

    for index, (document, score, metadata) in enumerate(results):

        print(f"\n===== BM25 检索结果 {index + 1} =====")

        print(f"内容：{document}")
        print(f"BM25 Score：{score:.4f}")

        print(f"来源：{metadata['source']}")

        if metadata["page"] is not None:
            print(f"页码：{metadata['page']}")

        print(f"Chunk ID：{metadata['chunk_id']}")
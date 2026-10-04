import os

from loader import load_document
from chunker import split_text
from embedder import embed_text
from vector_store import add_documents, get_document_count


if __name__ == "__main__":

    data_dir = "data"

    ids = []
    all_chunks = []
    chunks_vector = []
    metadatas = []

    if not os.path.exists(data_dir):
        print(f"数据目录 '{data_dir}' 不存在，请检查路径。")
        exit()

    for file in os.listdir(data_dir):

        file_path = os.path.join(data_dir, file)


        document_data = load_document(file_path)

        for item in document_data:

            text = item["text"]
            page = item["page"]

            chunks = split_text(text)

            for index, chunk in enumerate(chunks):

                all_chunks.append(chunk)

                if page is None:
                    chunk_id = f"{file}_chunk_{index}"
                else:
                    chunk_id = f"{file}_page_{page}_chunk_{index}"

                ids.append(chunk_id)

                chunk_vector = embed_text(chunk)

                chunks_vector.append(chunk_vector)

                metadata = {
                    "source": file,
                    "chunk_id": index
                }

                if page is not None:
                    metadata["page"] = page

                metadatas.append(metadata)

    add_documents(
        ids,
        all_chunks,
        chunks_vector,
        metadatas
    )

    print("ID数量：", len(ids))
    print("Chunk数量：", len(all_chunks))
    print("Embedding数量：", len(chunks_vector))
    print("Metadata数量：", len(metadatas))
    print("数据库记录数量：", get_document_count())
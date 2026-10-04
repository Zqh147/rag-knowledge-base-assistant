import chromadb
from config import DB_PATH, COLLECTION_NAME

db_client = chromadb.PersistentClient(
    path = DB_PATH
)

collection = db_client.get_or_create_collection(
    name = COLLECTION_NAME,
    metadata = {"hnsw:space":"cosine"}
)

def add_documents(ids, documents, chunks_vector, metadatas):
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=chunks_vector,
        metadatas=metadatas
    )

def get_document_count():
    return collection.count()

def query_documents(query_embedding, top_k):
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include = ["documents", "distances", "metadatas"]
    )
    return results
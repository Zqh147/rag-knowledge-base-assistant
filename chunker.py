from config import CHUNK_SIZE, CHUNK_OVERLAP
#   划分chunk
def split_text(text, chunk_size = CHUNK_SIZE, chunk_overlap = CHUNK_OVERLAP):
    if chunk_size <= chunk_overlap:
        raise ValueError("chunk_size 必须大于 chunk_overlap")
    chunks = []
    start = 0
    while start < len(text):
         #   确定一段文本的结束位置
        end = start + chunk_size
        #   取出这一段文本
        chunk = text[start:end]
        #   chunks组装
        chunks.append(chunk)
        if end >= len(text):
            break
        start = end - chunk_overlap
    return chunks
from config import CHUNK_SIZE, CHUNK_OVERLAP
#   划分chunk
def split_text(text, chunk_size = CHUNK_SIZE, chunk_overlap = CHUNK_OVERLAP):
    if chunk_size <= 0 or chunk_overlap < 0 or chunk_size <= chunk_overlap:
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


def split_section(section, text, max_chars=1400):
    """Keep a complete reviewed procedure; reject silent step truncation."""
    if not section.strip() or not text.strip() or max_chars <= 0:
        raise ValueError("section, text and max_chars must be valid")
    chunk = f"{section.strip()}\n{text.strip()}"
    if len(chunk) > max_chars:
        raise ValueError("section too long; split it into complete procedures")
    return [chunk]

import os

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("DEEPSEEK_API_KEY")

#   检查是否获取到API Key，如果没有获取到，就提示用户
if not api_key:
    raise RuntimeError(
        "没有获取到 DEEPSEEK_API_KEY，请在 .env 文件中设置 DEEPSEEK_API_KEY"
    )


llm_client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

#   定义回答函数
def rag_answer(question, results):

    context = "\n参考资料："

    for index, (document, similarity, metadata) in enumerate(results):
        if "page" in metadata:
            context += (
                f"\n\n第{index + 1}条资料："
                f"\n来源：{metadata['source']}"
                f"\n页码：{metadata['page']}"
                f"\nChunk ID：{metadata['chunk_id']}"
                f"\n相似度：{similarity:.4f}"
                f"\n内容：\n{document}"
            )
        else:
            context += (
                f"\n\n第{index + 1}条资料："
                f"\n来源：{metadata['source']}"
                f"\nChunk ID：{metadata['chunk_id']}"
                f"\n相似度：{similarity:.4f}"
                f"\n内容：\n{document}"
            )

    system_prompt = """你是一个知识库问答助手。
请严格根据提供的参考资料回答用户的问题。
不要使用参考资料之外的知识。
如果参考资料中没有答案，请明确说明参考资料中没有相关信息。"""
    user_prompt = f"""
{context}

用户问题：
{question}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    response = llm_client.chat.completions.create(
        model="deepseek-flash",
        messages=messages,
        stream=False
    )

    return response.choices[0].message.content

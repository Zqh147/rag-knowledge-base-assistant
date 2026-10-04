from retriever import retrieve
from generator import rag_answer


if __name__ == "__main__":
    while True:
        question = input("请输入问题(输入'exit'退出)：")
        question = question.strip()
    #   判断问题是否为空
        if not question:
            print("问题不能为空，请输入有效的问题。")
            continue
        #   判断是否输入exit，如果输入exit，则退出程序
        if question.lower() == "exit":
            print("程序已退出。")
            break

        results = retrieve(question)

        if not results:
            print("未检索到相关内容")

        else:
            print("\n检索到相关内容")

            for index, (document, similarity, metadata) in enumerate(results):

                print(f"\n===== 检索结果 {index + 1} =====")
                print(document)
                print(f"相似度：{similarity:.4f}")
                print(f"来源：{metadata['source']}")

                if "page" in metadata:
                    print(f"页码：{metadata['page']}")

                print(f"Chunk ID：{metadata['chunk_id']}")

            answer = rag_answer(question, results)

            print("\nAI回答：")
            print(answer)
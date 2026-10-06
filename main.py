from hybrid_retriever import retrieve_hybrid
from reranker import rerank
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

        hybrid_results = retrieve_hybrid(question)

        reranked_results = rerank(
            question,
            hybrid_results
        )

        if not reranked_results:
            print("未检索到相关内容")

        else:
            print("\n检索到相关内容")

            for index, result in enumerate(reranked_results, start=1):

                document = result["document"]
                metadata = result["metadata"]

                print(f"\n===== 检索结果 {index} =====")
                print(document)

                print(f"Reranker Score：{result['reranker_score']:.4f}")
                print(f"来源：{metadata['source']}")

                if metadata.get("page") is not None:
                    print(f"页码：{metadata['page']}")

                print(f"Chunk ID：{metadata['chunk_id']}")

            answer = rag_answer(
                question,
                reranked_results
            )
            print("\nAI回答：")
            print(answer)
            print("\n参考来源")

            for result in reranked_results:

                metadata = result["metadata"]

                print(f"来源：{metadata['source']}")

                if metadata.get("page") is not None:
                    print(f"页码：{metadata['page']}")

                print(f"Chunk ID：{metadata['chunk_id']}")
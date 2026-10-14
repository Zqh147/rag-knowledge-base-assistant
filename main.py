from router_pipeline import retrieve_router, load_policy
from router_corpus import make_chunks, corpus_digest
from vector_store import verify_router_index
from generator import rag_answer


def main():
    chunks = make_chunks()
    verify_router_index(chunks, corpus_digest(chunks))
    load_policy()
    print("家用路由器知识库问答与故障排查助手")
    print("当前资料：Archer AX10 / AX20，V1，US。请输入设备标签信息；输入 exit 退出。")
    scope = {}
    for field, label in [("product_model", "设备型号"), ("hardware_version", "硬件版本"), ("region", "销售地区")]:
        value = input(label + "：").strip()
        if value.lower() == "exit":
            return
        scope[field] = value or None
    while True:
        question = input("请输入问题（exit 退出）：").strip()
        if question.lower() == "exit":
            return
        if not question:
            print("问题不能为空。")
            continue
        try:
            result = retrieve_router(question, **scope)
            if not result["has_results"]:
                print(result["message"])
                for field in result["missing_fields"]:
                    if field != "question":
                        scope[field] = input(field + "：").strip() or None
                continue
            print(rag_answer(question, result["results"]))
        except Exception as exc:
            print(f"执行失败：{exc}。请检查配置或日志；服务失败不表示资料没有答案。")


if __name__ == "__main__":
    main()

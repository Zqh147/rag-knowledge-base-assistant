"""Run against a live project-one service, optionally through the actual project-two adapter."""
import argparse
import importlib
import json
from pathlib import Path
import subprocess
import sys
import httpx
from config import BASE_DIR

CASES = [
    ("health", "GET", "/health", None, 200, None),
    ("legacy_request", "POST", "/retrieve", {"question":"AX10 V1 US如何修改无线密码","top_k":3}, 200, "ok"),
    ("explicit_scope", "POST", "/retrieve", {"question":"USB灯灭着是什么意思","product_model":"AX20","hardware_version":"V1","region":"US"},200,"ok"),
    ("missing_model", "POST", "/retrieve", {"question":"怎么改密码"},200,"needs_clarification"),
    ("missing_hardware", "POST", "/retrieve", {"question":"AX10 US怎么改密码"},200,"needs_clarification"),
    ("unknown_model", "POST", "/retrieve", {"question":"AX99 V1 US怎么改密码"},200,"unsupported_product"),
    ("uncollected_version", "POST", "/retrieve", {"question":"AX10 V2 US怎么改密码"},200,"unsupported_product"),
    ("uncollected_region", "POST", "/retrieve", {"question":"AX10 V1 EU怎么改密码"},200,"unsupported_product"),
    ("parameter_conflict", "POST", "/retrieve", {"question":"AX20 V1 US怎么改密码","product_model":"AX10"},200,"parameter_conflict"),
    ("out_of_corpus", "POST", "/retrieve", {"question":"AX10 V1 US如何查询淘宝订单退款"},200,"no_evidence"),
    ("invalid_top_k", "POST", "/retrieve", {"question":"AX10 V1 US怎么改密码","top_k":0},422,None),
]


def run(url, project2_source=None):
    rows = []
    with httpx.Client(base_url=url, timeout=90, trust_env=False) as client:
        for name,method,path,body,expected_code,expected_status in CASES:
            response = client.request(method,path,json=body) if body is not None else client.request(method,path)
            payload = response.json()
            passed = response.status_code == expected_code and (expected_status is None or payload.get("status") == expected_status)
            if payload.get("has_results"):
                passed = passed and all(r["hardware_version"] == "V1" and r["region"] == "US" for r in payload["results"])
                if name == "legacy_request":
                    passed = passed and all(r["product_model"] == "Archer AX10" for r in payload["results"])
                if name == "explicit_scope":
                    passed = passed and all(r["product_model"] == "Archer AX20" for r in payload["results"])
            rows.append({"case":name,"passed":passed,"http_status":response.status_code,"payload":payload})
            print(name, passed, flush=True)
    source_commit = None
    if project2_source:
        source = Path(project2_source).resolve()
        sys.path.insert(0,str(source))
        adapter = importlib.import_module("app.rag_tool").retrieve_from_project1
        for question,expected_status,name in [
            ("AX10 V1 US怎样改Wi-Fi密码","ok","actual_project2_adapter"),
            ("怎么改Wi-Fi密码","needs_clarification","actual_project2_adapter_clarification"),
        ]:
            payload = adapter(question,3,url,90)
            rows.append({"case":name,"passed":payload["backend"] == "project1" and payload["status"] == expected_status,"payload":payload})
            print(name, rows[-1]["passed"], flush=True)
        result = subprocess.run(["git","-C",str(source),"rev-parse","HEAD"],capture_output=True,text=True)
        source_commit = result.stdout.strip() if result.returncode == 0 else None
    report = {"test_type":"live HTTP + optional unchanged actual project-two Python adapter",
              "passed":sum(r["passed"] for r in rows),"total":len(rows),
              "project2_source_commit":source_commit,"rows":rows,
              "generation_model_called":False}
    (BASE_DIR / "evaluation/router_service_results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if not all(r["passed"] for r in rows):
        raise SystemExit(1)
    print(f"{report['passed']}/{report['total']} live checks passed")


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--url",default="http://127.0.0.1:8001")
    parser.add_argument("--project2-source")
    args=parser.parse_args()
    run(args.url,args.project2_source)

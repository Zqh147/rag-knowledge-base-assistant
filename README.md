# 家用路由器知识库问答与故障排查助手

从 Knowledge Base Assistant V2 增量改造，面向需要查询设备操作说明与排查家庭网络故障的用户。当前官方资料范围为 **TP-Link Archer AX10 / AX20，硬件 V1，US**。该范围是本次新增选择；不代表覆盖所有型号、地区或固件。

保留 Python、SentenceTransformer、Chroma、jieba、BM25、RRF、Cross-Encoder 和 DeepSeek。检索服务只返回证据，项目二负责自己的最终生成。

## 为什么这样设计

| 问题 | 实现 | 完成标准 |
|---|---|---|
| 短块截断步骤 | 每个已整理的章节作为完整操作单元，保留条件与注意事项；超长章节拒绝静默截断 | 文本包含完整步骤，并通过字符与 Embedding token 上限检查 |
| 两路文本不一致 | BM25 读取同一 Chroma collection 的原文与元数据 | 两路使用相同 evidence_id |
| 相似型号挤占候选 | 两路均先限定型号、硬件版本和地区，再取 Top-K | 错型号、错版本、错地区不能进入候选 |
| 不知道用户设备 | 解析问题或接收显式字段；缺信息、未知范围、冲突分别返回状态 | 不猜默认型号或版本 |
| 检索总能返回片段 | 用独立校准题选 raw-logit 相关性阈值 | 库外负例检查拒绝；分数不解释为概率 |
| 回答无法核对 | 保留章节、官方 URL、引用编号，生成后检查引用编号范围 | 语法可检查；事实支持仍需人工验收 |
| 索引或服务异常 | 校验语料指纹、索引内容；异常返回 HTTP 503 | 不把故障当作知识库没答案 |

## 快速运行（PowerShell）

在项目根目录，使用现有虚拟环境：

```powershell
python -m pip install -r requirements.txt -r requirements-service.txt
python -m pytest -q
python build_index.py
python -m uvicorn rag_service:app --host 127.0.0.1 --port 8001
```

首次运行需要下载原有的两种模型。检索、建库与评测不需要生成模型的 API Key。默认使用 CPU；GPU 可设置 `RAG_MODEL_DEVICE=cuda`，但须有相应 PyTorch 环境。

在另一个终端检索：

```powershell
$body = @{
    question = "怎么修改Wi-Fi名称和密码？"
    top_k = 3
    product_model = "Archer AX10"
    hardware_version = "V1"
    region = "US"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8001/retrieve" -Method Post -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

旧请求形状仍支持：

```json
{"question":"AX10 V1 US 怎么修改Wi-Fi密码？","top_k":3}
```

输入设备信息不足，例如仅“怎么修改Wi-Fi密码”，会返回 `needs_clarification`，而不是猜测型号。旧的旅行知识已被隔离，因此不再是此领域服务的资料。

`GET /products` 可查询当前支持的设备组合；`GET /health` 为就绪检查。

## 项目二兼容性

保留 `backend=project1`、`pipeline`、`results`、`has_results`，证据仍有 `content/source/page/chunk_id/rrf_score/reranker_score`。新增字段包含 `status/message/missing_fields/resolved_scope`，以及每条证据的型号、章节、URL、引用编号。

项目二原有适配器透传返回字典，能接收新增状态。旧工具 schema 只发送问题和 Top-K，所以问题必须携带已确认的型号、硬件版本与地区。是否能在多轮会话里始终保留这些设备信息，须在项目二的在线 Agent 验收中继续检查。

这是本地 Python 适配器通过 **HTTP** 调用项目一，不是 MCP 检索。

| 状态 | 含义 |
|---|---|
| `ok` | 有达到相关性阈值的证据，仍不保证能回答问题每个部分 |
| `needs_clarification` | 缺设备信息或具体问题 |
| `unsupported_product` | 未收录该组合 |
| `parameter_conflict` | 问题与参数冲突或包含多个设备组合 |
| `no_evidence` | 没有达到相关性要求的证据 |
| HTTP 422 | 请求参数错误 |
| HTTP 503 / `retrieval_unavailable` | 检索服务未就绪或执行故障 |

接口不会调用 DeepSeek，也不会静默回退到演示库。

## 本地问答与在线验收

保留你原有 `.env`，设置 `DEEPSEEK_API_KEY` 后：

```powershell
python main.py
```

先输入设备标签信息，再提问。回答包含引用与官方来源。缺引用或引用越界时不展示操作建议。此检查仅验证引用语法，不证明每段结论都被原文支持。

本次环境没有生成模型凭据，**未完成在线答案验收**。本机至少检查：修改 Wi-Fi 密码、AP 模式、重启与恢复出厂区别、固件升级、无线断连、库外问题。逐项核对引用原文、完整步骤、注意事项；断连现象不足时应先追问，不能给出确定根因。不要公开 API Key。

## 领域检索评测

```powershell
python -m evaluation.evaluate_router --split calibration
python -m evaluation.evaluate_router --split holdout
python -m evaluation.check_service
python -m evaluation.check_service --project2-source E:\github\agent-assistant-v1
```

先固定校准阈值，再运行保留测试集；不要根据保留集结果反复调整阈值后仍称其为独立测试。语料变化后必须重建、重新校准。校准策略的语料指纹不一致时，服务拒绝启动。

本次实测详见 `ROUTER_TEST_REPORT.md` 和 `evaluation/router_*_results.json`。它们是手工小样本验证，不是业务回答准确率，也不是原项目二全量 Agent 回归。

## 文件职责

| 文件 | 职责 |
|---|---|
| `data/router/knowledge.json`、`SOURCES.md` | 短篇官方资料整理和来源说明 |
| `router_corpus.py`、`chunker.py` | 元数据校验、稳定证据标识、完整章节分块 |
| `product_scope.py` | 型号/版本/地区解析、缺失与冲突检测 |
| `vector_store.py`、`retriever.py` | Chroma 持久化、范围内向量召回 |
| `bm25_retriever.py` | 同一范围内的 BM25；按请求构建，适合当前本地小库 |
| `hybrid_retriever.py`、`reranker.py` | RRF 融合与原模型重排 |
| `router_pipeline.py` | 设备范围、证据阈值与状态处理 |
| `rag_service.py` | 项目二兼容的证据接口 |
| `generator.py`、`main.py` | 项目一的本地问答与引用展示 |

默认 collection 为 `router_manuals_v1`。原 TXT/PDF 的读取、定长分块及理论题评测保留，只能显式切换 `RAG_PROFILE=demo` 后建演示索引、运行旧评测；它们不属于路由器验收，领域 API 不允许该 profile。没有新增 OCR、订单、工单、真实设备控制或部署能力。

当前 Embedding 输入上限设置为底层模型支持的 512 token，并在编码前检查长度；长流程须人工拆成完整子流程。相关性分数显式使用 raw logit，不能与旧版经过默认激活函数的分数直接比较。

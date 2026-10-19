# 家用路由器知识库问答与故障排查助手

面向家庭路由器用户的 RAG 知识库问答系统：回答设备操作问题、辅助排查家庭网络故障，并给出可核对的资料出处。

当前收录范围：**TP-Link Archer AX10 / Archer AX20，硬件 V1，美国（US）**。检索结果严格限定在已收录的型号、硬件版本与销售地区内，不借用其他版本的资料。

系统在原有 RAG 项目基础上升级为设备范围感知的两路混合检索，并提供：

- **Hybrid Retrieval**：Chroma 向量召回 + BM25 关键词召回，RRF 融合后由 Cross-Encoder 重排
- **设备范围约束**：型号、硬件版本、地区在召回前过滤，而非事后筛选
- **相关性阈值**：独立校准集选择 raw-logit 阈值，库外问题明确拒答
- **引用溯源**：回答附带章节、官方 URL、引用编号和 Chunk ID
- **状态化接口**：区分“资料不足”“信息缺失”“设备未收录”和“服务故障”

## 系统流程

```text
用户问题 + 设备字段（型号 / 硬件版本 / 地区）
                    │
                    ▼
        product_scope.resolve_scope
     ┌──────────────┼──────────────┐
     │              │              │
  信息缺失        参数冲突       未收录设备
     │              │              │
     ▼              ▼              ▼
needs_clarification / parameter_conflict / unsupported_product
                    │ ok
                    ▼
     ┌──────────────┴──────────────┐
     │                             │
     ▼                             ▼
Chroma 向量召回              同一范围内的 BM25
（带元数据过滤）              （同一批原文）
     │                             │
     └──────────────┬──────────────┘
                    ▼
              RRF 融合排序
                    ▼
        Cross-Encoder 重排（raw logit）
                    ▼
            相关性阈值过滤
                    ▼
       证据列表（/retrieve）或 RAG 回答（main.py）
```

## 数据范围

| 项目 | 当前值 |
|---|---|
| 型号 | Archer AX10、Archer AX20 |
| 硬件版本 | V1 |
| 销售地区 | US |
| 已整理章节 | 28 条结构化资料（每个型号 14 条） |
| 覆盖内容 | LED 指示、快速设置、PPPoE、AP 模式、无线设置、访客网络、固件升级、备份与恢复、登录异常、无法上网、无线断连、重启与恢复出厂区别、信道与带宽 |
| 资料来源 | TP-Link 官方手册与 FAQ 摘要，逐条记录 URL、章节、版本和复核日期 |

资料说明见 [`data/router/SOURCES.md`](data/router/SOURCES.md)。知识文件是官方章节的中文短篇整理，不是完整手册或逐字译本；网页可能随固件更新，实际界面不一致时应核对固件版本。

以下情况会被明确拒绝，而不是猜测或套用 V1 US 的操作：

- 缺少型号、硬件版本或地区 → `needs_clarification`
- 未收录的型号 / 版本 / 地区（如 AX10 V2、EU、CN）→ `unsupported_product`
- 问题与显式参数冲突，或一次询问多台设备 → `parameter_conflict`
- 其他品牌设备 → `unsupported_product`

## 快速开始

### 1. 环境要求

- Python 3.11+（已在 Python 3.12 + CPU 环境验证）
- 首次运行需联网下载 Embedding 与 Reranker 模型
- GPU 可选：设置 `RAG_MODEL_DEVICE=cuda`，需对应 PyTorch 环境

### 2. 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-service.txt
```

### 3. 配置环境变量

项目默认使用 `.env` 中的 `DEEPSEEK_API_KEY`（仅本地问答生成需要）：

```powershell
Copy-Item .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY=你的密钥
```

检索、建库和检索评测不需要生成模型 API Key。`.env` 已被 `.gitignore` 忽略，请勿提交密钥。

可选环境变量：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `RAG_PROFILE` | `router` | `router` 为领域检索；`demo` 才启用旧 TXT/PDF 演示库 |
| `RAG_MODEL_DEVICE` | `cpu` | 可设为 `cuda` |
| `RAG_CPU_THREADS` | `4` | CPU 推理线程数 |
| `RAG_DB_PATH` | `./chromadb` | Chroma 持久化目录 |

### 4. 构建索引

```powershell
python build_index.py
```

首次建库会下载 Embedding 模型 `paraphrase-multilingual-MiniLM-L12-v2`；首次检索或评测时再下载 Reranker `BAAI/bge-reranker-v2-m3`。语料或分块变化后必须重建索引；服务启动时会校验语料指纹，索引陈旧会直接拒绝启动。

### 5. 运行测试

```powershell
python -m pytest -q
```

### 6. 启动检索 API

```powershell
python -m uvicorn rag_service:app --host 127.0.0.1 --port 8001
```

### 7. 命令行问答

```powershell
python main.py
```

按提示输入型号、硬件版本、地区，然后逐题提问。回答包含引用编号和官方来源；引用缺失或编号越界时，不展示操作建议。

## API

### `POST /retrieve`

返回证据，不调用生成模型。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `question` | string | 是 | 用户问题，1–4000 字符 |
| `top_k` | int | 否 | 返回条数，默认 3，范围 1–5 |
| `product_model` | string | 否 | 如 `Archer AX10`；可从问题中解析 |
| `hardware_version` | string | 否 | 如 `V1`；可从问题中解析 |
| `region` | string | 否 | 如 `US`；可从问题中解析 |

请求示例：

```powershell
$body = @{
    question = "怎么修改Wi-Fi名称和密码？"
    top_k = 3
    product_model = "Archer AX10"
    hardware_version = "V1"
    region = "US"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8001/retrieve" `
    -Method Post `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

也兼容从问题中直接解析设备信息的旧请求形状：

```json
{"question": "AX10 V1 US 怎么修改Wi-Fi密码？", "top_k": 3}
```

响应示例（节选）：

```json
{
  "question": "怎么修改Wi-Fi名称和密码？",
  "backend": "project1",
  "pipeline": "vector+bm25+rrf+cross_encoder",
  "status": "ok",
  "has_results": true,
  "resolved_scope": {
    "product_model": "Archer AX10",
    "hardware_version": "V1",
    "region": "US"
  },
  "missing_fields": [],
  "score_scale": "raw_logit",
  "results": [
    {
      "content": "...",
      "citation_id": "[1]",
      "evidence_id": "ax10-v1-us-wireless",
      "product_model": "Archer AX10",
      "hardware_version": "V1",
      "region": "US",
      "section": "Chapter 12 / Specify Wireless Settings",
      "source": "knowledge.json",
      "source_url": "https://www.tp-link.com/us/user-guides/...",
      "chunk_id": 0,
      "page": null,
      "rrf_score": 0.032,
      "reranker_score": 2.41,
      "doc_type": "official_manual_summary",
      "doc_version": "US V1 online manual; software-specific UI may differ",
      "reviewed_at": "2026-10-14"
    }
  ]
}
```

### 状态说明

| `status` / HTTP | 含义 |
|---|---|
| `ok` | 有通过相关性阈值的证据；不保证覆盖问题的每一部分 |
| `needs_clarification` | 缺少设备信息或具体问题 |
| `unsupported_product` | 未收录该型号、硬件版本或地区组合 |
| `parameter_conflict` | 问题与参数冲突，或包含多个设备组合 |
| `no_evidence` | 没有达到相关性阈值的证据 |
| HTTP 422 | 请求参数不合法 |
| HTTP 503 / `retrieval_unavailable` | 检索服务未就绪或执行失败 |

`no_evidence` 只表示本次检索未找到足够相关的资料，不能推断整个知识库或官方手册没有该内容。服务异常返回 503，也不会静默回退到演示库。

### 其他接口

| 接口 | 说明 |
|---|---|
| `GET /health` | 就绪检查；未就绪返回 503 |
| `GET /products` | 返回当前收录的型号、硬件版本与地区组合 |

## 与 Agent 项目集成

接口保留 `backend=project1`、`pipeline`、`results`、`has_results` 等原有字段，证据仍包含 `content/source/page/chunk_id/rrf_score/reranker_score`。新增 `status/message/missing_fields/resolved_scope`，以及每条证据的型号、版本、地区、章节、官方 URL 与引用编号。

Agent 侧通过本地 Python 适配器以 **HTTP** 调用本服务，不是 MCP 检索。若工具 schema 只传问题和 Top-K，问题文本必须携带已确认的设备信息，否则会返回 `needs_clarification`。

## 评测

### 领域检索评测

```powershell
# 只用校准集选择相关性阈值，并写入 data/router/retrieval_policy.json
python -m evaluation.evaluate_router --split calibration

# 使用已固定的阈值评估保留集
python -m evaluation.evaluate_router --split holdout
```

保留集结果（16 道资料内题 + 6 道库外题）：

| 方法 | Recall@3 | MRR |
|---|---:|---:|
| Vector | 0.9375 | 0.8875 |
| BM25 | 0.9375 | 0.9141 |
| Hybrid (RRF) | 0.9375 | 0.9167 |
| Reranker | 1.0000 | 1.0000 |

经过阈值过滤后 Recall@3 为 1.0000，资料内误拒绝 0/16，库外误接受 0/6。

注意：这是手工编写的小样本回归集，不是业务回答准确率，也不代表独立泛化能力。阈值只使用 12 道校准题选择；修改语料后必须重建索引并重新校准。相关性分数是 raw logit，不是答案正确的概率。

### 服务与兼容性检查

先启动 API，再在另一个终端执行：

```powershell
python -m evaluation.check_service
```

如已有下游 Agent 项目源码，可同时验证其原适配器：

```powershell
python -m evaluation.check_service --project2-source 路径\到\agent 项目
```

该检查覆盖健康检查、旧请求形状、显式设备字段、缺失信息、未收录组合、参数冲突、库外拦截和 422 参数校验，并核对返回证据的设备范围。这是 HTTP 适配器检查，不是完整在线 Agent 回归。

### 生成质量评测

生成评测需要真实答案与人工审核，不会自动生成分数：

```powershell
# 保存六题真实检索证据并调用 DeepSeek 生成答案
python -m evaluation.evaluate_generation --capture

# 只检查证据，不调用生成模型
python -m evaluation.evaluate_generation --evidence-only

# 汇总已人工审核的报告
python -m evaluation.evaluate_generation --summarize "evaluation/answer_runs/你的审核报告.json"
```

审核口径与指标定义见 [`GENERATION_EVALUATION.md`](GENERATION_EVALUATION.md)。在完成人工审核前，不输出生成质量指标。

## 项目结构

| 路径 | 职责 |
|---|---|
| `config.py` | Profile、模型、路径与检索参数 |
| `data/router/knowledge.json` | 已审核的结构化章节资料 |
| `data/router/SOURCES.md` | 官方来源、适用范围与资料限制 |
| `data/router/retrieval_policy.json` | 相关性阈值、语料指纹与评分口径 |
| `router_corpus.py` | 语料校验、稳定证据 ID、分块与语料指纹 |
| `product_scope.py` | 型号 / 版本 / 地区解析、缺失与冲突检测 |
| `chunker.py` | 完整章节分块；保留旧定长分块供 demo 使用 |
| `embedder.py` | SentenceTransformer Embedding 封装 |
| `vector_store.py` | Chroma 持久化、范围内查询、索引一致性校验 |
| `retriever.py` | 向量召回 |
| `bm25_retriever.py` | jieba + BM25，仅在限定范围内构建 |
| `hybrid_retriever.py` | RRF 融合 |
| `reranker.py` | Cross-Encoder 重排，显式 raw logit |
| `router_pipeline.py` | 设备范围 → 召回 → 重排 → 阈值 → 状态处理 |
| `rag_service.py` | FastAPI 证据接口 |
| `generator.py` | DeepSeek 回答生成、引用检查与来源展示 |
| `main.py` | 命令行问答入口 |
| `build_index.py` | 路由器索引构建；`demo` profile 构建旧演示索引 |
| `evaluation/` | 检索、服务兼容性与生成质量评测 |
| `tests/` | 领域状态、范围过滤、接口契约与指标边界测试 |


## 相关文档

- [`data/router/SOURCES.md`](data/router/SOURCES.md)：官方来源与资料边界
- [`ROUTER_TEST_REPORT.md`](ROUTER_TEST_REPORT.md)：领域改造测试报告
- [`GENERATION_EVALUATION.md`](GENERATION_EVALUATION.md)：生成质量人工审核口径
- [`ONLINE_FIX_TEST_REPORT.md`](ONLINE_FIX_TEST_REPORT.md)：在线验收修复与回归结果

旧 TXT/PDF 演示链仍然保留，但只能显式设置 `RAG_PROFILE=demo` 后使用；领域 API 不接受 demo profile，旧演示资料不会进入路由器检索候选。

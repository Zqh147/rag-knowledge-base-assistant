# Knowledge Base Assistant（知识库问答助手）

一个从零手写的 RAG（检索增强生成）小项目：把本地文档切块、向量化后存入向量数据库，提问时先检索相关片段，再交给大模型基于检索结果生成回答，同时展示检索片段的来源信息。

检索部分已经从单一向量检索升级为 **Hybrid Search + Reranker** 的两段式管线：稠密向量检索和 BM25 稀疏检索并行召回，用 RRF 融合排序，再用 CrossEncoder 重排序，最后把 Top-N 片段交给大模型。

项目没有使用 LangChain 等框架，每个环节都是自己写的独立模块，适合用来理解 RAG 的完整链路。

## 功能特性

- 支持 **TXT / PDF** 文档加载（PDF 按页解析，回答时可定位到页码）
- 滑动窗口文本切块，块之间保留重叠，降低关键信息恰好被切分边界截断的影响
- 多语言向量模型做 Embedding，中英文文档都能检索
- ChromaDB 持久化向量库，余弦相似度检索
- **BM25 稀疏检索**：jieba 分词 + `rank-bm25`，补齐向量检索对关键词不敏感的问题
- **Hybrid Search**：向量与 BM25 各自召回候选，用 RRF（Reciprocal Rank Fusion）融合
- **Reranker 重排序**：`BAAI/bge-reranker-v2-m3` 对 Question-Chunk 逐对打分后重排
- **检索评估**：Vector / BM25 / Hybrid / Hybrid+Reranker 四路对比，输出 Recall@1/3/5 与 MRR
- 接入 DeepSeek 大模型基于参考资料生成回答，并展示检索结果的来源、页码、Chunk ID 与分数
- 命令行交互式问答，输入 `exit` 退出

## 技术栈

| 环节 | 选型 |
| --- | --- |
| 文档解析 | PyMuPDF (`pymupdf`) |
| 向量模型 | `sentence-transformers` / `paraphrase-multilingual-MiniLM-L12-v2` |
| 向量数据库 | ChromaDB（本地持久化） |
| 稀疏检索 | `jieba` + `rank-bm25` |
| 重排序模型 | `BAAI/bge-reranker-v2-m3`（`sentence-transformers` 的 CrossEncoder） |
| 大模型 | DeepSeek（通过 `openai` SDK 调用） |
| 环境管理 | `python-dotenv` |

## 目录结构

```
knowledge-base-assistant/
├── data/                  # 待入库的文档（放 .txt / .pdf）
├── chromadb/              # ChromaDB 持久化数据（自动生成，已被 git 忽略）
├── evaluation/            # 检索效果评估
|   ├──__init__.py
│   ├── evaluation_data.py # 评测问题 + Ground Truth（source / page / chunk_id）
│   ├── evaluate.py        # 指标计算：find_rank / recall_at_k / reciprocal_rank
│   ├── run_evaluation.py  # 入口：跑完整评测并打印四路结果对比
│   └── bad_cases.py       # 人工记录的失败案例分析
├── experiments/           # 临时验证脚本，不属于主流程
|   ├──__init__.py
│   └── test_retrieval_pipeline.py
├── config.py              # 全局配置：模型名、路径、切块参数、检索参数
├── loader.py              # 文档加载：txt / pdf -> [{text, page}]
├── chunker.py             # 文本切块：滑动窗口 + 重叠
├── embedder.py            # 向量化：文本 -> 向量
├── vector_store.py        # 向量库封装：写入 / 计数 / 查询
├── retriever.py           # 稠密检索：问题向量化 -> 查询 -> 阈值过滤
├── bm25_retriever.py      # 稀疏检索：jieba 分词 -> BM25 打分
├── hybrid_retriever.py    # 混合检索：RRF 融合向量与 BM25 结果
├── reranker.py            # 重排序：CrossEncoder 对候选片段重新打分
├── generator.py           # 生成：拼参考资料 + 调用大模型
├── build_index.py         # 入口①：批量建索引
├── main.py                # 入口②：交互式问答
├── requirements.txt       # 依赖清单
└── .env.example           # 环境变量模板
```

## 工作流程

**建索引（离线，只需跑一次）：**

```
data/ 文档
  └─ loader.py      解析出文本（PDF 保留页码）
  └─ chunker.py     切分为多个 chunk
  └─ embedder.py    每个 chunk 转成向量
  └─ vector_store.py 连原文、向量、元数据一起写入 ChromaDB
```

**问答（在线）：**

```
用户问题
  ├─ retriever.py      稠密检索：问题向量化 -> ChromaDB 取 CANDIDATE_K 个
  ├─ bm25_retriever.py 稀疏检索：jieba 分词 -> BM25 取 CANDIDATE_K 个
  └─ hybrid_retriever.py
       └─ RRF 融合两路结果，按 rrf_score 排序，取 FINAL_K 个候选
  └─ reranker.py       CrossEncoder 对每个候选打分 -> 重排 -> 取 RERANK_K 个
  └─ generator.py      把命中的 chunk 拼成参考资料 -> 交给 DeepSeek 生成回答
  └─ main.py           打印检索结果（Reranker 分数/来源/页码）与 AI 回答
```

向量检索靠语义相似，BM25 靠关键词命中，两者召回的结果有互补性；RRF 只依赖排名、不依赖两路分数是否可比，因此融合时不需要做归一化。

## 快速开始

### 1. 环境要求

- Python 3.x
- 可访问 DeepSeek API 的网络环境
- 首次运行需要联网下载两个模型：
  - Embedding 模型 `paraphrase-multilingual-MiniLM-L12-v2`（约 470 MB）
  - Reranker 模型 `BAAI/bge-reranker-v2-m3`（约 2 GB，`main.py` 会加载）

### 2. 安装依赖

```powershell
pip install -r requirements.txt
```

### 3. 配置 API Key

复制模板并填入自己的 Key（Key 在 <https://platform.deepseek.com> 申请）：

```powershell
Copy-Item .env.example .env
```

`.env` 内容：

```
DEEPSEEK_API_KEY=your_api_key_here
```

> `.env` 已在 `.gitignore` 中，不会被提交到仓库。

### 4. 放入文档

把你的 `.txt` 或 `.pdf` 文件放进 `data/` 目录。

> 目前只识别 `.txt` 和 `.pdf`，其他格式（如 `.docx`）会被静默跳过。

### 5. 建立索引

```powershell
python build_index.py
```

输出示例：

```
ID数量： 42
Chunk数量： 42
Embedding数量： 42
Metadata数量： 42
数据库记录数量： 42
```

重复运行是安全的：写入使用 `upsert`，相同 ID 会覆盖而不是追加。

### 6. 开始问答

```powershell
python main.py
```

```
请输入问题(输入'exit'退出)：旅行要带哪些东西？

检索到相关内容

===== 检索结果 1 =====
Chunk 原文……
Reranker Score：0.9821
来源：travel_notes.txt
Chunk ID：12

AI回答：
（依据参考资料生成的回答）

参考来源
来源：travel_notes.txt
Chunk ID：12
```

输入 `exit` 退出。

> **注意**：`bm25_retriever.py` 在 **import 时**就扫描 `./data` 并构建 BM25 索引，路径是相对当前工作目录的，所以上述脚本都要在项目根目录下执行。

### 7. 运行检索评估（可选）

评测脚本用了包内相对导入，必须用 `-m` 从项目根目录以模块方式运行：

```powershell
python -m evaluation.run_evaluation
```

它会依次跑 Vector、BM25、Hybrid、Hybrid+Reranker 四路检索，对 `evaluation/evaluation_data.py` 里的每个问题打印 Ground Truth 的排名，最后输出平均指标：

```
========== Evaluation Result ==========

当前小规模评测集结果：

| Method | Recall@1 | Recall@3 | Recall@5 | MRR |
| --- | ---: | ---: | ---: | ---: |
| Vector | 0.7500 | 0.7500 | 1.0000 | 0.8000 |
| BM25 | 0.7500 | 1.0000 | 1.0000 | 0.8750 |
| Hybrid | 0.7500 | 0.7500 | 1.0000 | 0.8125 |
| Hybrid + Reranker | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

运行前请确认 `data/test.pdf` 存在且已经跑过 `build_index.py`，否则 Ground Truth 无法命中。
> 当前评测集仅包含 4 个手工标注问题，因此这些结果主要用于验证检索链路和定位排序问题，不代表大规模 benchmark 性能。

## 配置说明

所有可调参数集中在 `config.py`：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | 向量模型，支持中英文 |
| `DB_PATH` | `./chromadb` | 向量库持久化目录 |
| `COLLECTION_NAME` | `pdf_test` | ChromaDB 集合名，换个名字相当于换一个知识库 |
| `CHUNK_SIZE` | `100` | 每块字符数，调大上下文更完整、检索更粗 |
| `CHUNK_OVERLAP` | `25` | 相邻块的重叠字符数，必须小于 `CHUNK_SIZE` |
| `TOP_K` | `3` | 单独调用 Vector / BM25 检索时的默认返回数量（评估脚本显式传参，不受此限） |
| `THRESHOLD` | `0` | 稠密检索相似度下限，低于该值的结果被丢弃 |
| `CANDIDATE_K` | `10` | Hybrid 中向量和 BM25 **各自**召回的候选数量 |
| `FINAL_K` | `10` | RRF 融合后保留、送给 Reranker 的候选数量 |
| `RERANK_K` | `3` | Reranker 最终保留、送给大模型的 Chunk 数量 |

调参小提示：

- `THRESHOLD` 默认为 `0`，即基本不做过滤（只挡掉负相似度），噪声主要交给 Reranker 兜底。想让稠密检索阶段更严格可以调高。
- 召回不够就调大 `CANDIDATE_K` 或 `FINAL_K`；上下文太长、回答变散可以调小 `RERANK_K`。
- 回答太笼统可以调小 `CHUNK_SIZE`；切块太碎导致语义不完整则调大。
- 改完参数后建议重跑 `python -m evaluation.run_evaluation` 对比指标，而不是凭感觉调。

## 模块说明

| 文件 | 关键函数 | 职责 |
| --- | --- | --- |
| `loader.py` | `load_document()` | 按扩展名分发，返回 `[{"text": ..., "page": ...}]`，TXT 的 `page` 为 `None` |
| `chunker.py` | `split_text()` | 定长滑动窗口切块，`start = end - chunk_overlap` 实现重叠 |
| `embedder.py` | `embed_text()` | 模块级加载模型，避免每次调用重复加载 |
| `vector_store.py` | `add_documents()` / `query_documents()` | 集合以 cosine 距离建索引，返回原文、距离、元数据 |
| `retriever.py` | `retrieve()` | 相似度 = `1 - distance`，按阈值过滤后返回 `(文档, 相似度, 元数据)` |
| `bm25_retriever.py` | `retrieve_bm25()` | import 时读 `./data` 建 BM25 索引；中文走 jieba 分词并过滤停用词 |
| `hybrid_retriever.py` | `retrieve_hybrid()` / `reciprocal_rank_fusion()` | 两路各取 `CANDIDATE_K`，按 `1/(60+rank)` 累加 RRF 分数后排序取 `FINAL_K` |
| `reranker.py` | `rerank()` | 构造 `[Question, Chunk]` 对交给 CrossEncoder 打分，按分数重排取 Top-N |
| `generator.py` | `rag_answer()` | 拼接带来源的参考资料，用系统提示词约束模型只能依据资料回答 |
| `evaluation/evaluate.py` | `find_rank()` / `recall_at_k()` / `reciprocal_rank()` | 用 `source + page + chunk_id` 生成 chunk 唯一标识做命中判定 |

`hybrid_retriever.py` 的 RRF 常数 `k=60` 写死在函数签名里，`top_n` 以外的截断由 `config.py` 的 `FINAL_K` / `RERANK_K` 控制。

## 检索评估

`evaluation/` 是一套最小可用的检索评测，用来判断「加 BM25、加 Reranker 到底有没有用」。

- **Ground Truth 的表示方式**：`{"source": "test.pdf", "page": 3, "chunk_id": 0}`，通过 `get_chunk_uid()` 拼成 `test.pdf_page_3_chunk_0` 这类唯一键，再和检索结果的 metadata 比对。
- **指标**：`Recall@K` 只判断有没有命中，`RR`（Reciprocal Rank）额外奖励排得靠前的位置，平均值即 `MRR`。
- **四路对比**：同一批问题分别跑 Vector、BM25、Hybrid、Hybrid+Reranker，输出各自的 Recall@1/3/5 与 MRR，便于定位是召回阶段还是排序阶段的问题。
- **`evaluation/bad_cases.py`**：手工整理的失败案例，记录某条 Ground Truth 在四路中的排名、失效发生在哪个阶段、以及原因分析。
目前记录的一条典型案例是：
- Vector Retrieval：Ground Truth 排名第 5
- BM25：排名第 2
- RRF Hybrid：排名第 4
- Cross-Encoder Reranker：重新提升到第 1

这个案例说明：Dense Retrieval 和 BM25 的召回结果具有互补性，但 RRF 只根据排名进行融合，并不直接判断 Question-Chunk 的深层相关性，因此融合后的正确 Chunk 不一定排名更高；Cross-Encoder Reranker 可以进一步对候选结果进行精排。

## 常见问题

**Q：运行 `main.py` 报 `没有获取到 DEEPSEEK_API_KEY`？**
没有创建 `.env` 或 Key 为空，按上文第 3 步配置。

**Q：第一次运行卡在下载模型？**
`main.py` 会加载约 2 GB 的 `BAAI/bge-reranker-v2-m3`，需要联网且耗时较长。只想先看排序效果可以跑 `python -m evaluation.run_evaluation`，它不依赖 DeepSeek Key，能直接输出各阶段排名。模型下载后缓存在本地，后续启动不再重复下载。

**Q：`python experiments/test_retrieval_pipeline.py` 报 `ModuleNotFoundError: No module named 'hybrid_retriever'`？**
脚本必须从项目根目录以模块方式运行：`python -m experiments.test_retrieval_pipeline`。直接按路径执行时 `sys.path` 指向 `experiments/`，找不到根目录下的模块。

**Q：检索不到任何内容？**
先确认 `build_index.py` 跑成功且 `数据库记录数量` 大于 0；再确认问题和文档语言/主题接近。BM25 依赖分词和关键词重合，问法和原文用词差异过大时只能靠向量那一路召回。

**Q：PDF 里扫不出文字？**
扫描版 PDF 本质是图片，`pymupdf` 提取不到文本，需要先做 OCR。可以看 `build_index.py` 打印的 Chunk 数量是否异常偏少来判断。

**Q：换了文档想重建索引？**
直接删掉 `chromadb/` 目录再跑 `build_index.py`，或者改 `COLLECTION_NAME` 建一个新集合。注意 BM25 索引是运行时从 `data/` 现读现建的，不需要重建，但 `evaluation/evaluation_data.py` 里的 Ground Truth 要同步改。

**Q：回答里出现资料以外的内容？**
系统提示词已约束"只用参考资料"，但仍可能发生。可以调小 `RERANK_K` 减少进入上下文的噪声块，或检查 `THRESHOLD` 是否为 0 导致低质量片段被放进来。

**Q：评估指标看起来不对？**
检查三点：`data/` 里是否有 `test.pdf`、是否跑过 `build_index.py`、`evaluation_data.py` 里的 `page` / `chunk_id` 是否和当前切块结果一致。改了 `CHUNK_SIZE` / `CHUNK_OVERLAP` 后 chunk 编号会整体变化，Ground Truth 需要重新标注。

## 后续可以做的事

- 支持 `.docx`、`.md` 等更多格式
- 切块改为按语义/段落切分，而不是按固定字符数
- 扩充评测集：当前只有 4 个问题，指标波动大，且 Ground Truth 依赖手工标注
- 把 RRF 的 `k`、两路权重做成 `config.py` 里的可调参数
- BM25 索引改为持久化或增量更新，避免每次 import 都重新扫描 `data/`
- 换用更大的向量模型或接向量数据库服务
- 套一层 Web UI（Streamlit / FastAPI）

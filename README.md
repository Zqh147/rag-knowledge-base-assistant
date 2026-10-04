# Knowledge Base Assistant（知识库问答助手）

一个从零手写的 RAG（检索增强生成）小项目：把本地文档切块、向量化后存入向量数据库，提问时先检索相关片段，再交给大模型基于检索结果生成回答，同时展示检索片段的来源信息。

项目没有使用 LangChain 等框架，每个环节都是自己写的独立模块，适合用来理解 RAG 的完整链路。

## 功能特性

- 支持 **TXT / PDF** 文档加载（PDF 按页解析，回答时可定位到页码）
- 滑动窗口文本切块，块之间保留重叠，避免语义被切断
- 多语言向量模型做 Embedding，中英文文档都能检索
- ChromaDB 持久化向量库，余弦相似度检索
- 相似度阈值过滤，检索不到相关内容时不硬答
- 接入 DeepSeek 大模型基于参考资料生成回答，并展示检索结果的来源、页码、Chunk ID 与相似度。
- 命令行交互式问答，输入 `exit` 退出

## 技术栈

| 环节 | 选型 |
| --- | --- |
| 文档解析 | PyMuPDF (`pymupdf`) |
| 向量模型 | `sentence-transformers` / `paraphrase-multilingual-MiniLM-L12-v2` |
| 向量数据库 | ChromaDB（本地持久化） |
| 大模型 | DeepSeek（通过 `openai` SDK 调用） |
| 环境管理 | `python-dotenv` |

## 目录结构

```
knowledge-base-assistant/
├── data/                  # 待入库的文档（放 .txt / .pdf）
├── chromadb/              # ChromaDB 持久化数据（自动生成，已被 git 忽略）
├── config.py              # 全局配置：模型名、路径、切块参数、检索参数
├── loader.py              # 文档加载：txt / pdf -> [{text, page}]
├── chunker.py             # 文本切块：滑动窗口 + 重叠
├── embedder.py            # 向量化：文本 -> 向量
├── vector_store.py        # 向量库封装：写入 / 计数 / 查询
├── retriever.py           # 检索：问题向量化 -> 查询 -> 阈值过滤
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
  └─ retriever.py   问题向量化 -> ChromaDB 检索 Top-K -> 相似度低于阈值则丢弃
  └─ generator.py   把命中的 chunk 拼成参考资料 -> 交给 DeepSeek 生成回答
  └─ main.py        打印检索结果（相似度/来源/页码）与 AI 回答
```

## 快速开始

### 1. 环境要求

- Python 3.x
- 可访问 DeepSeek API 的网络环境
- 首次运行需要联网下载 Embedding 模型
### 2. 安装依赖

```powershell
cd projects/Python/knowledge-base-assistant
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
请输入问题：旅行要带哪些东西？
...
AI回答：
（依据参考资料生成的回答）
```

输入 `exit` 退出。

## 配置说明

所有可调参数集中在 `config.py`：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | 向量模型，支持中英文 |
| `DB_PATH` | `./chromadb` | 向量库持久化目录 |
| `COLLECTION_NAME` | `pdf_test` | ChromaDB 集合名，换个名字相当于换一个知识库 |
| `CHUNK_SIZE` | `100` | 每块字符数，调大上下文更完整、检索更粗 |
| `CHUNK_OVERLAP` | `25` | 相邻块的重叠字符数，必须小于 `CHUNK_SIZE` |
| `TOP_K` | `3` | 每次检索返回的候选块数量 |
| `THRESHOLD` | `0.25` | 相似度下限，低于该值的结果被丢弃 |

调参小提示：实际效果需要结合数据集调节 CHUNK_SIZE、TOP_K 和 THRESHOLD；召回太少就调大 `TOP_K` 或调低 `THRESHOLD`；回答太笼统可以调小 `CHUNK_SIZE`；答非所问则多半要调高 `THRESHOLD`。

## 模块说明

| 文件 | 关键函数 | 职责 |
| --- | --- | --- |
| `loader.py` | `load_document()` | 按扩展名分发，返回 `[{"text": ..., "page": ...}]`，TXT 的 `page` 为 `None` |
| `chunker.py` | `split_text()` | 定长滑动窗口切块，`start = end - chunk_overlap` 实现重叠 |
| `embedder.py` | `embed_text()` | 模块级加载模型，避免每次调用重复加载 |
| `vector_store.py` | `add_documents()` / `query_documents()` | 集合以 cosine 距离建索引，返回原文、距离、元数据 |
| `retriever.py` | `retrieve()` | 相似度 = `1 - distance`，按阈值过滤后返回 `(文档, 相似度, 元数据)` |
| `generator.py` | `rag_answer()` | 拼接带来源的参考资料，用系统提示词约束模型只能依据资料回答 |

## 常见问题

**Q：运行 `main.py` 报 `没有获取到 DEEPSEEK_API_KEY`？**
没有创建 `.env` 或 Key 为空，按上文第 3 步配置。

**Q：检索不到任何内容？**
先确认 `build_index.py` 跑成功且 `数据库记录数量` 大于 0；再确认问题和文档语言/主题接近。仍不行就降低 `THRESHOLD` 观察相似度分布。

**Q：PDF 里扫不出文字？**
扫描版 PDF 本质是图片，`pymupdf` 提取不到文本，需要先做 OCR。可以看 `build_index.py` 打印的 Chunk 数量是否异常偏少来判断。

**Q：换了文档想重建索引？**
直接删掉 `chromadb/` 目录再跑 `build_index.py`，或者改 `COLLECTION_NAME` 建一个新集合。

**Q：回答里出现资料以外的内容？**
系统提示词已约束"只用参考资料"，但仍可能发生。可调高 `THRESHOLD` 减少噪声块进入上下文。

## 后续可以做的事

- 支持 `.docx`、`.md` 等更多格式
- 切块改为按语义/段落切分，而不是按固定字符数
- 加入重排序（rerank）提升召回质量
- 换用更大的向量模型或接向量数据库服务
- 套一层 Web UI（Streamlit / FastAPI）

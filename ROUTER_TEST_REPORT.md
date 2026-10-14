# 路由器场景改造：实际测试报告

日期：2026-10-14。代码基线：GitHub main `252eee215146a21d89f912d4382adecb45fbd767`。

## 结论

完成领域资料、元数据、完整章节分块、双路范围过滤、相关性阈值、引用展示与兼容接口的增量实现。真实检索和 HTTP 适配器已验证。在线生成答案仍未验收，不能把本报告解释为业务回答准确率或全部 Agent 回归。

## 本次运行结果

| 验证 | 实际结果 | 边界 |
|---|---|---|
| pytest | 41 passed | 模型依赖在多数单元测试中以可控函数替代；过滤测试使用真实 Chroma / BM25 |
| 模型建库 | 成功 | 真实 SentenceTransformer + Chroma |
| 实际 HTTP 与项目二适配器 | 13/13 | 服务启动后执行；未运行完整在线 Agent |
| 保留集检索 | 16 道资料内题，6 道库外题 | 校准题不计入此表指标 |
| 在线 DeepSeek 生成 | 未运行 | 本环境没有 API Key |

## 四路检索对比

| 方法 | Recall@3 | MRR |
|---|---:|---:|
| Vector | 0.9375 | 0.9219 |
| BM25 | 0.9375 | 0.9152 |
| Hybrid | 0.9375 | 0.9531 |
| Reranker | 1.0000 | 1.0000 |

阈值通过另外 12 道校准题选择，固定为 raw logit `-1.013655`。保留集经过阈值后的 Recall@3 为 1.0000；库外误接受 0/6，资料内完全误拒绝 0/16。

这里的 Recall 是正确资料片段命中率，MRR 衡量其排序。不能据此宣称答案准确率 100%。手工小样本覆盖有限，校准分数不是置信概率，也不保证证据能回答复合问题的所有部分。

## 已验证的关键行为

- 型号、版本、地区均在向量与 BM25 取候选之前限制，随后 RRF 与原 Cross-Encoder 重排。
- 针对相似型号、其他硬件版本与其他地区的强干扰片段，真实 Chroma 的 Top-1 仍只返回目标范围。
- 缺设备信息追问；未收录型号、硬件版本或地区返回 unsupported_product；问题和参数冲突返回 parameter_conflict。
- 旧请求形状 question + top_k 能解析问题中完整设备信息；旧返回核心字段保留。
- 实际项目二原有 retrieve_from_project1 适配器成功处理证据和 needs_clarification；该链是 HTTP，不是 MCP。
- 检索异常与资料不足分别为 HTTP 503 与 HTTP 200 / no_evidence。
- 引用缺失或越界时拒绝展示操作建议；这是语法检查，不是事实支持检查。
- 索引语料指纹和存储内容校验、超长完整流程拒绝、RRF 不同章节唯一标识均有覆盖。

## 真实运行版本

- Python 3.12.14；CPU。
- torch: 2.14.1+cpu
- sentence-transformers: 6.1.0
- chromadb: 1.5.9
- jieba: 0.42.1
- rank-bm25: 0.2.2
- fastapi: 0.143.0
- pytest: 9.1.1
- Embedding: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2，输入上限设置为 512 token。
- Reranker: BAAI/bge-reranker-v2-m3，raw logit，输入上限 512 token。
- 项目二源码提交：`80c0e10d16b06f92326a49bd465fdefe87e14356`；只读使用其原有适配器，没有改造项目二。

## 资料与已知限制

- 本次选定 US V1 的 AX10 / AX20；官方手册章节和 FAQ 722 来源见 data/router/SOURCES.md。资料为简短中文整理，未收录全部功能与固件。
- 同型号 V2/V1.20 及 EU/CN 尚未收录：没有借用 V1 US 操作。版本差异过滤已实现，跨版本资料扩展仍属后续工作。
- TXT/PDF 旧加载链保留为显式 demo profile；本次路由器数据来自已审核的结构化章节，不声称已有自动 PDF 章节识别或 OCR。
- BM25 每次在受限集合上构建索引，适用于当前本地小库；没有证明大规模并发或部署能力。
- 在线答案的原文支持、注意事项和步骤完整性须人工核对；现象不足时应追问，有相关片段不等于答案充分。
- 未运行 Windows 本机环境、项目二完整 Agent 在线回归、Docker 部署验收。
- 简历尚未修改。没有新增订单、工单、真实用户或企业部署事实。

## 证据文件

- evaluation/router_questions.json：校准与保留题及稳定证据 ID。
- evaluation/router_calibration_results.json / router_holdout_results.json：完整排名、逐题分数与阈值决策。
- evaluation/router_service_results.json：真实 HTTP 返回与适配器验证。

## 本机最后验收

按 README 建库、启动服务和 CLI 后，对 Wi-Fi 修改、AP 模式、恢复出厂、固件升级、无线断连、库外问题各运行一次在线回答，逐项核对事实、完整步骤、引用和追问。此项通过后，再更新简历的业务描述。

## 增量应用脚本验证

基线副本上的完整应用成功；未提交文件冲突时停止且其他文件未被写入；原 .env 保留；重复应用无操作。该验证不计入 pytest 的 41 条结果。

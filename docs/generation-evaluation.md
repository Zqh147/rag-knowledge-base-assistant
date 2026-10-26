# 生成质量评测口径与操作

当前六题来自已经人工检查过的在线验收，是修复后的回归题，不是全新的独立测试集。检索 Recall@3 / MRR 与下面的生成指标分开报告。当前尚无修复后真实生成指标，不要将已有检索成绩填入生成报告。

## 1. 保存实际证据与答案

完成建库和阈值校准后：

```powershell
python -m evaluation.evaluate_generation --capture
```

这会调用真实检索链。有证据时使用 `generator.py` 中的 DeepSeek 客户端生成，证据不足则保存服务的拒答；沿用 `.env` 中的配置，评测报告不记录 API Key。每题的证据、完整答案、语料指纹、提示指纹与错误类型保存到终端打印的 `evaluation/answer_runs/时间戳.json`。

证据预检查不调用生成模型：

```powershell
python -m evaluation.evaluate_generation --evidence-only
```

此模式仅检查要求的证据编号和库外拦截；不能生成答案质量成绩。

## 2. 人工标注

复制真实 capture 报告作为人工审核版本，再编辑每个 row 的 review：

- `covered_point_ids`：对资料内题逐个核对 required_points，把正确覆盖的要点编号写入列表。漏答、错误回答、错误拒答不计为覆盖。每题覆盖率为正确覆盖要点数 / 该题全部必需要点数，最终对资料内题取平均。
- `claims`：对每个生成回答列出可核对的事实陈述，每项为 `{"text": "事实陈述", "supported": true}` 或 false。基于本次保存的 evidence 判定。系统追问、请求补充信息等交互策略不当作设备事实；但若声称官方资料要求这样做，要核对依据。
- `citation_correct`：生成回答的事实与操作引用是否正确对应来源、章节、适用范围。系统追问不要假装引用官方章节；仅编号存在并不代表引用正确。
- `refusal_correct`：仅库外题需要标注，检查没有编造业务流程或声称已执行操作，措辞与服务范围一致。

留空的 null 表示未审核。`claims: []` 只适用于确实没有事实陈述的回答，不能用于跳过审核。错误和未审核记录不会被自动当作通过，需补完审核或重新运行失败案例所在的完整回归集。

## 3. 统计已审核结果

```powershell
python -m evaluation.evaluate_generation --summarize "evaluation/answer_runs/你的审核报告.json"
```

- `mean_required_point_coverage`：资料内题的平均必需要点覆盖率。
- `evidence_support_rate`：所有被审核事实陈述中，得到检索证据支持的比例；报告中附支持数与总陈述数。
- `answers_with_unsupported_claim_rate`：含至少一个无依据陈述的回答数 / 含事实陈述的回答数。这是本项目的回答层面口径，不与陈述层面证据支持率混用。
- `citation_review_pass_rate`：人工检查引用通过的生成回答比例。
- `out_of_corpus_refusal_correct_rate`：人工检查拒答正确的库外题比例。

没有任何事实陈述时，支持率返回 null，不能声称 100% 忠实。无依据不必然意味着现实中事实错误；有依据也不等于已覆盖问题全部要求。

引用这些指标时，应同时注明题集类型、问题数量、审核方式、版本与统计分母。六题修复回归不能代表整体业务准确率；新增独立题集属于后续扩展。

# 在线验收问题修复：增量更新

本补丁基于你已经应用的 router-update，以及保留 OpenAI 1.109.1 / pytest 8.4.2 的共享环境。仅更新资料、提示、拒答措辞和评测文件，不需要重新安装依赖。更新脚本校验文件内容、接受纯 LF/CRLF 换行差异，并在应用前备份。

六类初验已经检查，但并非全部合格。原始定性结果见 evaluation/online_initial_review.json。修订后必须重新验收，不将初版检索成绩当作新版成绩。

## 1. 检查与应用

将补丁解压到 E:\google\router-online-fix。先检查：

```powershell
python "E:\google\router-online-fix\apply_online_fix.py" --target "E:\github\knowledge-base-assistant"
```

确认没有实际文件冲突后，在本地问答程序中输入 exit，并在运行 8001 服务的终端按 Ctrl+C 停止旧服务。然后应用：

```powershell
python "E:\google\router-online-fix\apply_online_fix.py" --target "E:\github\knowledge-base-assistant" --apply
```

只要本机已有 Python，更新脚本就能执行；它不导入项目依赖。

## 2. 使用原共享环境验证

项目一和项目二继续使用 E:\github\LearningHub\projects\Python\day21\.venv。以下例子显式指定解释器，避免终端激活状态的差异：

```powershell
Set-Location "E:\github\knowledge-base-assistant"
$env:RAG_PROFILE = "router"
& "E:\github\LearningHub\projects\Python\day21\.venv\Scripts\python.exe" -m pytest -q
& "E:\github\LearningHub\projects\Python\day21\.venv\Scripts\python.exe" build_index.py
& "E:\github\LearningHub\projects\Python\day21\.venv\Scripts\python.exe" -m evaluation.evaluate_router --split calibration
& "E:\github\LearningHub\projects\Python\day21\.venv\Scripts\python.exe" -m evaluation.evaluate_router --split holdout
& "E:\github\LearningHub\projects\Python\day21\.venv\Scripts\python.exe" -m evaluation.evaluate_generation --evidence-only
```

新语料必须重建索引，不能用旧索引。校准只使用 calibration 题，禁止根据 holdout 成绩反复调阈值。固定 holdout 题已经看过，修订版沿用它作回归检查，不声称是全新的独立泛化测试。恢复/重启复合题的证据标注已补成两条，前后结果不是完全相同标注条件的比较。

## 3. 服务及项目二兼容性

```powershell
& "E:\github\LearningHub\projects\Python\day21\.venv\Scripts\python.exe" -m uvicorn rag_service:app --host 127.0.0.1 --port 8001
```

保持运行，在另一终端的项目一目录执行：

```powershell
& "E:\github\LearningHub\projects\Python\day21\.venv\Scripts\python.exe" -m evaluation.check_service --project2-source "E:\github\agent-assistant-v1"
```

原 /retrieve 请求与核心返回字段保留。HTTP 适配器检查不等于完整在线 Agent 回归，也不是 MCP 检索。

## 4. 在线复测与生成指标

可以继续通过 main.py 逐题检查，也可以运行新的 capture 脚本保存六题完整答案与证据。详见 GENERATION_EVALUATION.md。模板中的人工审核项初始是 null；必须逐项核查，统计器才允许输出生成指标。

补丁中的提示明确要求：系统追问不挂官方引用；证据不足只限定本次检索范围；复合问题逐项回答。它属于提示策略修正，不能以单元测试替代真实生成效果的复测。

只有完成本机复测和审核后，才更新简历中的业务描述与生成质量成绩。继续暂不加入 GitHub 链接或知识库规模。

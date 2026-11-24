---
name: paper-structured-notes
description: 将一篇科研论文转化为“章节对齐、字段化、证据可回链、可复用”的结构化笔记，并生成可编辑学术 PPT 与真实渲染预览。适用于文献总结与结构化笔记类任务（对得上/留得住/找得回/用得上）。
---

# Paper Structured Notes（论文结构化笔记）

把一篇真实论文变成一份**可复核、可复用**的结构化笔记，而不是一段压缩后的通读摘要。核心交付物是：字段化的「论文卡片」+ 逐章「章节笔记」+ 可检索「知识点」+ 每条论断的「证据锚点」，并附带一个可编辑的学术 PPT 与真实渲染预览。

## 1. 输入输出约定

### 输入（执行时已就位）
- `/input/case.json`：案例定义。至少含任务说明、材料/论文位置、以及评分所需的 `output_contract` 字段与 `case_id`。
- `/input/task.md`：本题任务简介。
- 论文文件：**实际 PDF**，无预抽取答案层。先从 `case.json` 里找论文路径（常见键：`paper`、`pdf`、`material`、`document`、`source`、`file`、`path`）；找不到就 `ls /input` 与 `find /input -type f` 定位真正的 PDF，**不要根据文件名标签臆造内容**。

### 输出（写入 `/app/output`）
- `result.json`：最终结构化结果（含 `case_id` 与 `output_contract` 要求的全部字段）。
- `notes.json`：完整结构化笔记（符合 `notes_schema.json`）。
- `notes.md`：人可读的 Markdown 笔记。
- `deck.pptx`：可编辑学术 PPT（含演讲者备注与证据）。
- `deck.pdf`、`deck-*.png`：真实渲染预览（用于人工复核）。

工作过程写入 `/app/work`，不要污染 `/app/output`。

## 2. 执行流程（按序执行）

```bash
# 0) 确认输入
ls -R /input | head -100
cat /input/case.json | head -200

# 1) 抽取正文与章节（确定性脚本，输出 /app/work/paper_text.json）
python3 /skills/weekly-skill/scripts/extract.py \
  --pdf "$PDF" --out /app/work/paper_text.json

# 2) 阅读抽取结果，按下方“方法”逐章生成 notes.json（LLM 语义工作）
#    写 /app/work/notes.json，用 jsonschema 自检后再继续

# 3) 生成可编辑 PPT
python3 /skills/weekly-skill/scripts/build_deck.py \
  --notes /app/work/notes.json --out /app/output/deck.pptx

# 4) 真实渲染预览
python3 /skills/weekly-skill/scripts/render.py \
  --pptx /app/output/deck.pptx --outdir /app/output

# 5) 组装 result.json + notes.md
python3 /skills/weekly-skill/scripts/finalize.py \
  --notes /app/work/notes.json --case /input/case.json \
  --outdir /app/output --status success --status-detail "..."
```

脚本位于 `/skills/weekly-skill/scripts/`（若 Skill 以不同目录安装，按实际路径调用，用 `find /skills -name extract.py` 定位）。所有脚本只做**确定性**工作，不做语义判断；语义内容由你在第 2 步生成。

## 3. 方法：如何写出高质量 notes.json（评分核心）

逐条对照四个验收标准，不要套用通用摘要模板。

### 对得上（章节对齐）
- `sections[].heading` 必须用**论文原文的章节标题**，按原文顺序排列，不合并、不重命名、不遗漏。
- 每章只写该章的内容；`transition` 记录它与前后章的承接关系（例如“由引言提出问题，本章给出实验设计”）。
- 先用 `extract.py` 输出的 `sections` 字段做草稿，再对照 `paper_text.json` 逐页修正，避免把正文行误判成标题。

### 留得住（字段完整）
- `paper_card` 必须填满：研究问题、数据/材料、方法及关键条件、主要发现、局限。**尤其记录让结论成立的前提条件**（样本量、温度、剂量、模型假设、截断条件等）。
- 数值要照原文，不四舍五入改写、不估算缺失值。
- 方法与发现的粒度要能支撑后续写作引用，而不是一句话带过。

### 找得回（证据回链）
- 每条 `key_point`、每个 `knowledge_point`、`paper_card` 都必须有 `evidence`。
- `evidence.page` 用 **PDF 物理页码**（从 1 起）。尽量补 `section`、`paragraph`、`figure`/`table`/`equation` 与 `locator`（如“第 3 页第 2 段，图 2 左侧”）。
- 关键论断加 `quote`（原文短引文），便于复核。**禁止**只写“见原文”“见论文”这类笼统出处。

### 用得上（可检索、可比较、可复用）
- `knowledge_points` 拆成独立条目，`type` 取 `concept|variable|method|finding|limitation|other`；同一概念用 `aliases` 记录缩写/同义表述，避免重复条目、互相矛盾。
- 结果以 JSON + Markdown 双格式落地，字段与 `notes_schema.json` 一致，方便程序化检索与多论文并排比较。

## 4. 诚实与异常处理（可靠体验）

`status` 只能取 `success|partial|failed`，且必须在 `result.json` 的 `status_detail` 与 `uncertainty` 里如实说明。区分四类情况：

- **已报告**（reported）：原文明确陈述，照实记录并给证据。
- **可推断**（inferred）：从原文合理推导，标注 `status=inferred` 并在 description 说明推理依据。
- **未报告/无法判断**：写入 `uncertainty`（`not_reported`/`cannot_judge`），**绝不写成事实**。
- **材料冲突**：`conflict`，并列两条冲突陈述与各自出处。

对异常输入，明确识别并降级处理，不要编造：

| 情况 | 处置 |
|---|---|
| 扫描件 / 无文本层（`scanned_hint` 或 `empty_hint`） | 报告 `scan_issue`，尝试用 OCR 工具；失败则 `status=partial`，说明已提取页码范围与无法抽取的原因 |
| 加密 / 权限受限 | `status=failed`，报告具体错误，不要重试制造假象 |
| 双栏错序 | 用 `-layout` 的页序为准，标注可能的列序风险 |
| 图表、公式、脚注缺失 | 记入 `missing_figure` 等，说明缺失项；不要把公式文字化猜测 |
| 超长论文 | 分章节处理，先保存已完成的 `partial` 结果，再增量补全 |
| 非中文/非英文或乱码 | 记录 `encoding_issue` 与所用编码，报告无法可靠解析的范围 |

预算：约 64 次模型请求、900 秒、单次响应 ≤16384 tokens。**先写部分结果再迭代**，不要等完美才落盘。

## 5. 交付物说明

- 只提交 `SKILL.md` 与必要文本资源；**不提交**预制答案、正式测试案例、白板或虚构的评分/运行日志。
- `deck.pptx` 是可编辑 Office 交付物，必须同时有 `deck.pdf`/`deck-*.png` 真实预览；若渲染失败，如实写进 `status_detail`，不要贴一张假图。
- 正式案例与对照由平台提供；你只负责让 Skill 在给定案例上真实运行。

## 6. 最小调用示例（示意，非正式案例结果）

输入 `/input/case.json`（示意）：
```json
{"case_id":"case-0000","paper":"/input/paper.pdf",
 "task":"总结该论文的研究问题、方法与主要结论，并给出证据位置",
 "output_contract":["research_question","methods","key_findings","evidence_summary"]}
```

调用：
```bash
python3 /skills/weekly-skill/scripts/extract.py --pdf /input/paper.pdf --out /app/work/paper_text.json
# LLM 生成 /app/work/notes.json（示意）
python3 /skills/weekly-skill/scripts/build_deck.py --notes /app/work/notes.json --out /app/output/deck.pptx
python3 /skills/weekly-skill/scripts/render.py --pptx /app/output/deck.pptx --outdir /app/output
python3 /skills/weekly-skill/scripts/finalize.py --notes /app/work/notes.json --case /input/case.json --outdir /app/output
```

示意 `notes.json`（片段，标注为示例）：
```json
{"paper_card":{"title":"示例论文（示意）","research_question":"…",
  "evidence":{"section":"Abstract","page":1,"locator":"第1页摘要"}},
 "sections":[{"id":"sec-1","heading":"Introduction","purpose":"…","content":"…",
  "key_points":[{"text":"示例结论（示意）","evidence":{"page":1,"paragraph":2}}]}],
 "knowledge_points":[],"uncertainty":[],"change_log":[]}
```
以上均为**示意**，不代表任何真实案例的答案。

# paper-structured-notes

将一篇科研论文转化为「章节对齐、字段化、证据可回链、可复用」的结构化笔记，并生成可编辑学术 PPT 与真实渲染预览。

## 设计思路（对应四个验收标准）

| 验收标准 | 本 Skill 的做法 |
|---|---|
| 对得上 | `sections[]` 严格采用论文原文章节标题并按原文顺序排列；`extract.py` 先做启发式章节检测，再由 LLM 逐页校正 |
| 留得住 | `paper_card` 统一字段记录研究问题、数据、方法条件、主要发现、局限；`key_findings`/`methods` 粒度可支撑引用 |
| 找得回 | 每条 `key_point`/`knowledge_point`/`paper_card` 都带 `evidence`：页码、段落、图表/公式、可读 `locator` 与原文 `quote` |
| 用得上 | `knowledge_points` 为独立可检索条目，带 `type` 与 `aliases` 去重；JSON + Markdown 双格式落地，可并排比较多篇论文 |

## 目录结构

```
submission/
├── SKILL.md               # 主指令（含 YAML frontmatter）
├── README.md              # 本文件：使用与方法说明
├── notes_schema.json      # 结构化笔记的 JSON Schema
└── scripts/
    ├── extract.py         # PDF→带页码正文 + 章节检测（确定性）
    ├── build_deck.py      # notes.json → deck.pptx（可编辑，含备注与证据）
    ├── render.py          # deck.pptx → deck.pdf / deck-*.png（真实渲染）
    └── finalize.py        # notes.json + case.json → result.json + notes.md
```

## 依赖与安装

- Python 3.8+；`python-pptx`（`pip install python-pptx`，仅 `build_deck.py` 需要）。
- `pdftotext`（`extract.py`）、`soffice`/`libreoffice` 与 `pdftoppm`（`render.py`）。
- 平台运行环境已声明 `pdf-text-tool`、`pdf-render-tool`、`office-renderer`、`scientific-python`。

任一脚本依赖缺失时，脚本会返回非零状态或 `ok:false` 并给出原因，**不伪造输出**；`finalize.py` 用 `status` 如实记录。

## 调用步骤（运行时）

见 `SKILL.md` 第 2 节。输入为 `/input/case.json` + `/input/task.md` + 论文 PDF；输出全部写入 `/app/output`。

## 字段字典（`notes_schema.json` 要点）

- `paper_card`：`title/authors/year/venue/doi`、`research_question`、`data`、`methods[]`、`key_findings[]`、`limitations[]`、`evidence`。
- `sections[]`：`id/heading/page_range/purpose/content/results/conclusion/transition/key_points[]/evidence`。
- `knowledge_points[]`：`id/term/definition/type/aliases[]/evidence/status`。
- `uncertainty[]`：`kind/description/evidence`，`kind` 取值 `not_reported|cannot_judge|conflict|missing_figure|scan_issue|encoding_issue|other`。
- `evidence`：`section/page/paragraph/figure/table/equation/locator/quote`。

## 锚点格式

`evidence.page` 一律为 **PDF 物理页码**（1 起）；`locator` 为人类可读定位（如“第 3 页第 2 段，图 2 左侧”）；`quote` 为原文短引文。关键论断必须带锚点，禁止笼统出处。

## 适用场景与限制

- 适用：有文本层的期刊/会议论文、预印本，中英文皆可；目标是产出可引用、可检索的阅读笔记。
- 限制：扫描件/加密/权限受限 PDF、双栏错序、图表公式缺失、超长文、非中英文乱码，需按 `SKILL.md` 第 4 节降级处理并如实标注，不保证完整解析。

## 失败处理

- 抽取失败 → `status=failed`，报告具体错误与可人工接管位置。
- 部分章节无法判断 → `status=partial`，在 `uncertainty` 与 `status_detail` 说明范围。
- 渲染失败 → 保留 `deck.pptx`，`status_detail` 说明无预览，不贴假图。

## 自查清单

1. `notes.json` 通过 `notes_schema.json` 校验（可用 `jsonschema` 或人工核对必填字段）。
2. 每个 `sections[].heading` 都能在 `paper_text.json` 对应页找到原文。
3. 每条 `key_point`/`knowledge_point` 都有 `evidence.page`。
4. `result.json` 含 `case_id`、`status`、`output_contract` 字段、`sources`、`uncertainty`、`change_log`。
5. `deck.pptx` 可打开，且 `deck.pdf`/PNG 已真实生成。

## 版本

- 0.1.0（初版）：章节对齐 + 论文卡片 + 知识点 + 证据回链 + 可编辑 PPT + 渲染预览。

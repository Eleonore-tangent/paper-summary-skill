#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 notes.json 生成可编辑的学术 PPT（.pptx）。

- 标题页、论文卡片页、逐章节页、知识点页、局限/不确定页。
- 每页的“演讲者备注”写入详细文本 + 证据锚点（页级证据映射）。
- 依赖 python-pptx。若缺失：pip install python-pptx。
"""
import argparse, json, sys

CJK_FONT = "Noto Sans CJK SC"
BODY_FONT = "Noto Sans CJK SC"

MAX_BULLET = 220   # 幻灯片上每条截断长度；完整内容在备注里


def _cjk(run, name=CJK_FONT):
    run.font.name = name
    try:
        from pptx.oxml.ns import qn
        rPr = run._r.get_or_add_rPr()
        ea = rPr.find(qn("a:ea"))
        if ea is None:
            ea = rPr.makeelement(qn("a:ea"), {})
            rPr.append(ea)
        ea.set("typeface", name)
    except Exception:
        pass


def _trunc(s, n=MAX_BULLET):
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _add_bullets(tf, items):
    tf.clear()
    first = True
    for it in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.text = _trunc(it)
        p.level = 0
        for r in p.runs:
            _cjk(r)


def _notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def _evid(e):
    if not e:
        return ""
    parts = []
    if e.get("section"):
        parts.append(f"§ {e['section']}")
    if e.get("page"):
        parts.append(f"p.{e['page']}")
    if e.get("paragraph"):
        parts.append(f"para {e['paragraph']}")
    if e.get("figure"):
        parts.append(f"Fig.{e['figure']}")
    if e.get("table"):
        parts.append(f"Table {e['table']}")
    if e.get("equation"):
        parts.append(f"Eq.{e['equation']}")
    if e.get("locator"):
        parts.append(e["locator"])
    if e.get("quote"):
        parts.append(f"“{e['quote']}”")
    return " | ".join(str(x) for x in parts if x)


def build(notes, out_path):
    try:
        from pptx import Presentation
        from pptx.util import Pt
    except ImportError:
        raise SystemExit("python-pptx not installed; run: pip install python-pptx")

    prs = Presentation()
    prs.slide_width = 12192000  # 16:9 (13.333in x 7.5in)
    prs.slide_height = 6858000

    title_layout = prs.slide_layouts[0]
    content_layout = prs.slide_layouts[1]

    card = notes.get("paper_card") or {}
    sections = notes.get("sections") or []
    kps = notes.get("knowledge_points") or []
    unc = notes.get("uncertainty") or []

    # ---- 1) 标题页 ----
    s = prs.slides.add_slide(title_layout)
    s.shapes.title.text = _trunc(card.get("title") or "未命名论文", 180)
    sub = s.placeholders[1]
    sub.text = "文献结构化笔记（章节对齐 · 证据回链）"
    for r in sub.text_frame.paragraphs[0].runs:
        _cjk(r)
    _notes(s, "本页为标题页。完整结构化笔记见 result.json / notes.json / notes.md。")

    # ---- 2) 论文卡片页 ----
    s = prs.slides.add_slide(content_layout)
    s.shapes.title.text = "论文卡片"
    lines = [
        f"研究问题：{_trunc(card.get('research_question') or '未报告')}",
        f"数据/材料：{_trunc(card.get('data') or '未报告')}",
    ]
    for m in (card.get("methods") or []):
        lines.append(f"方法：{_trunc(m)}")
    for f in (card.get("key_findings") or []):
        lines.append(f"发现：{_trunc(f)}")
    for l in (card.get("limitations") or []):
        lines.append(f"局限：{_trunc(l)}")
    _add_bullets(s.placeholders[1].text_frame, lines)
    _notes(s, "\n".join([
        "论文卡片（完整）",
        f"标题：{card.get('title')}",
        f"作者：{card.get('authors')}  年份：{card.get('year')}  出处：{card.get('venue')}",
        f"研究问题：{card.get('research_question')}",
        f"数据：{card.get('data')}",
        "方法：" + "；".join(card.get('methods') or []),
        "发现：" + "；".join(card.get('key_findings') or []),
        "局限：" + "；".join(card.get('limitations') or []),
        f"证据：{_evid(card.get('evidence'))}",
    ]))

    # ---- 3) 逐章节页 ----
    for i, sec in enumerate(sections, 1):
        s = prs.slides.add_slide(content_layout)
        s.shapes.title.text = _trunc(f"{sec.get('heading') or '未命名章节'}", 120)
        lines = []
        if sec.get("purpose"):
            lines.append(f"目的：{_trunc(sec['purpose'])}")
        if sec.get("content"):
            lines.append(f"内容：{_trunc(sec['content'])}")
        if sec.get("results"):
            lines.append(f"结果：{_trunc(sec['results'])}")
        if sec.get("conclusion"):
            lines.append(f"结论：{_trunc(sec['conclusion'])}")
        for kp in (sec.get("key_points") or [])[:5]:
            lines.append(f"• {_trunc(kp.get('text',''))}  [{_evid(kp.get('evidence'))}]")
        _add_bullets(s.placeholders[1].text_frame, lines)
        note_lines = [
            f"章节：{sec.get('heading')}",
            f"目的：{sec.get('purpose')}",
            f"内容：{sec.get('content')}",
            f"结果：{sec.get('results')}",
            f"结论：{sec.get('conclusion')}",
            f"承接：{sec.get('transition')}",
            f"证据：{_evid(sec.get('evidence'))}",
            "关键点：",
        ]
        for kp in (sec.get("key_points") or []):
            note_lines.append(f"  - {kp.get('text')}  [{_evid(kp.get('evidence'))}]")
        _notes(s, "\n".join(note_lines))

    # ---- 4) 知识点页 ----
    if kps:
        s = prs.slides.add_slide(content_layout)
        s.shapes.title.text = "可检索知识点"
        lines = []
        for kp in kps[:10]:
            aliases = "/".join(kp.get("aliases") or [])
            lines.append(f"{kp.get('term')}{('（'+aliases+'）') if aliases else ''} [{kp.get('type')}]：{_trunc(kp.get('definition'))}  [{_evid(kp.get('evidence'))}]")
        _add_bullets(s.placeholders[1].text_frame, lines)
        note_lines = ["可检索知识点（完整，含状态）"]
        for kp in kps:
            note_lines.append(
                f"{kp.get('id')} {kp.get('term')} ({kp.get('type')},{kp.get('status')})："
                f"{kp.get('definition')}  别名：{'、'.join(kp.get('aliases') or [])}  证据：{_evid(kp.get('evidence'))}"
            )
        _notes(s, "\n".join(note_lines))

    # ---- 5) 局限/不确定页 ----
    if unc:
        s = prs.slides.add_slide(content_layout)
        s.shapes.title.text = "局限与不确定项"
        _add_bullets(s.placeholders[1].text_frame,
                      [f"[{u.get('kind')}] {_trunc(u.get('description'))}" for u in unc])
        note_lines = ["局限与不确定项（完整）"]
        for u in unc:
            note_lines.append(f"[{u.get('kind')}] {u.get('description')}  证据：{_evid(u.get('evidence'))}")
        _notes(s, "\n".join(note_lines))

    prs.save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--notes", required=True, help="notes.json 路径")
    ap.add_argument("--out", required=True, help="输出 deck.pptx 路径")
    args = ap.parse_args()
    with open(args.notes, encoding="utf-8") as f:
        notes = json.load(f)
    path = build(notes, args.out)
    print(json.dumps({"ok": True, "pptx": path}, ensure_ascii=False))


if __name__ == "__main__":
    main()

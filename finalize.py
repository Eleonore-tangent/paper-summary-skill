#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 notes.json + case.json 组装 result.json，并生成 notes.md。

result.json 包含：
  case_id、status、status_detail、output_contract 要求的字段（尽力回填）、
  structured_notes（完整结构化笔记）、sources、uncertainty、change_log。
"""
import argparse, json, os, sys


def find_case_id(case):
    for k in ("case_id", "id", "challenge_id", "task_id"):
        v = case.get(k)
        if v:
            return str(v)
    return None


def find_output_contract(case):
    for k in ("output_contract", "output_schema", "contract", "output_fields", "answer_fields"):
        v = case.get(k)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            return list(v.keys())
    return []


def field_lookup(notes):
    card = notes.get("paper_card") or {}
    secs = notes.get("sections") or []
    kps = notes.get("knowledge_points") or []
    # 先透传 paper_card 的全部字段（title/research_question/data/methods/key_findings/limitations/...），
    # 保证 output_contract 里与 paper_card 同名的字段能直接按名回填。
    vals = dict(card)
    vals.update({
        "question": card.get("research_question"),
        "method": card.get("methods"),
        "findings": card.get("key_findings"),
        "results": card.get("key_findings"),
        "summary": [{"heading": s.get("heading"), "content": s.get("content"),
                     "conclusion": s.get("conclusion")} for s in secs],
        "sections": secs,
        "knowledge_points": kps,
        "notes": notes,
    })
    return vals


def _sources(notes):
    out = []
    card = notes.get("paper_card") or {}
    if card.get("evidence"):
        out.append({"kind": "paper_card", "evidence": card["evidence"]})
    for s in notes.get("sections") or []:
        for kp in (s.get("key_points") or []):
            out.append({"kind": "section_key_point", "heading": s.get("heading"),
                        "text": kp.get("text"), "evidence": kp.get("evidence")})
    for kp in notes.get("knowledge_points") or []:
        out.append({"kind": "knowledge_point", "term": kp.get("term"),
                    "evidence": kp.get("evidence")})
    return out


def write_notes_md(notes, path):
    card = notes.get("paper_card") or {}
    lines = [f"# {card.get('title') or '论文结构化笔记'}", ""]
    if card.get("authors"):
        lines.append(f"- 作者：{card.get('authors')}")
    if card.get("year") or card.get("venue"):
        lines.append(f"- 年份/出处：{card.get('year')} {card.get('venue')}".strip())
    lines += ["", "## 论文卡片", "",
              f"- 研究问题：{card.get('research_question')}",
              f"- 数据：{card.get('data')}"]
    for m in (card.get("methods") or []):
        lines.append(f"- 方法：{m}")
    for f in (card.get("key_findings") or []):
        lines.append(f"- 发现：{f}")
    for l in (card.get("limitations") or []):
        lines.append(f"- 局限：{l}")
    lines += ["", "## 章节笔记", ""]
    for s in notes.get("sections") or []:
        lines.append(f"### {s.get('heading')}")
        if s.get("purpose"):
            lines.append(f"- 目的：{s.get('purpose')}")
        if s.get("content"):
            lines.append(f"- 内容：{s.get('content')}")
        if s.get("results"):
            lines.append(f"- 结果：{s.get('results')}")
        if s.get("conclusion"):
            lines.append(f"- 结论：{s.get('conclusion')}")
        for kp in (s.get("key_points") or []):
            e = kp.get("evidence") or {}
            loc = "、".join(str(x) for x in [e.get("page"), e.get("locator")] if x)
            lines.append(f"  - {kp.get('text')}（{loc}）")
    if notes.get("knowledge_points"):
        lines += ["", "## 可检索知识点", ""]
        for kp in notes["knowledge_points"]:
            lines.append(f"- **{kp.get('term')}**（{kp.get('type')}/{kp.get('status')}）：{kp.get('definition')}")
    if notes.get("uncertainty"):
        lines += ["", "## 不确定与未报告项", ""]
        for u in notes["uncertainty"]:
            lines.append(f"- [{u.get('kind')}] {u.get('description')}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--notes", required=True)
    ap.add_argument("--case", required=True, help="/input/case.json")
    ap.add_argument("--outdir", required=True, help="例如 /app/output")
    ap.add_argument("--status", default="success",
                    choices=["success", "partial", "failed"])
    ap.add_argument("--status-detail", default="")
    args = ap.parse_args()

    with open(args.notes, encoding="utf-8") as f:
        notes = json.load(f)
    with open(args.case, encoding="utf-8") as f:
        case = json.load(f)

    os.makedirs(args.outdir, exist_ok=True)
    case_id = find_case_id(case)
    contract_fields = find_output_contract(case)
    lookup = field_lookup(notes)

    result = {
        "case_id": case_id,
        "status": args.status,
        "status_detail": args.status_detail or ("success" if args.status == "success" else ""),
        "structured_notes": notes,
        "sources": _sources(notes),
        "uncertainty": notes.get("uncertainty") or [],
        "change_log": notes.get("change_log") or [],
    }
    unfilled = []
    for fld in contract_fields:
        if fld in ("case_id", "status"):
            continue
        v = lookup.get(fld)
        if v is None:
            v = lookup.get(fld.lower())
        result[fld] = v
        if v is None:
            unfilled.append(fld)
    if unfilled:
        result["_unfilled_contract_fields"] = unfilled

    out_json = os.path.join(args.outdir, "result.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    out_md = write_notes_md(notes, os.path.join(args.outdir, "notes.md"))

    print(json.dumps({
        "ok": True, "case_id": case_id, "status": args.status,
        "result_json": out_json, "notes_md": out_md,
        "contract_fields": contract_fields, "unfilled": unfilled,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

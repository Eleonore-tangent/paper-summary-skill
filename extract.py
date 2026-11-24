#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 PDF 抽取带页码的正文，并做章节标题启发式检测。

输出 paper_text.json：
  {
    "source": "...pdf", "num_pages": N, "extractor": "pdftotext ...",
    "scanned_hint": bool, "empty_hint": bool,
    "pages": [ {"page": 1, "text": "...", "chars": N}, ... ],
    "sections": [ {"heading": "...", "page": N}, ... ]
  }

依赖：pdftotext（PDF 文本抽取）。不依赖 PyMuPDF。
"""
import argparse, json, re, subprocess, sys

SECTION_PATTERNS = [
    # 编号标题：1 / 1.1 / 2.3.4（后面必须跟标题文字）
    re.compile(r"^\s*\d+(?:\.\d+)*\.?\s+\S.*$"),
    # 英文常用章节（整行，短行）
    re.compile(r"^\s*(Abstract|Keywords?|Introduction|Background|Related\s+Work|"
               r"Methods?|Methodology|Materials?\s+and\s+Methods?|Experimental\s+(Setup|Design)?|"
               r"Results?(?:\s+and\s+Discussion)?|Discussion|Conclusions?|"
               r"References|Bibliography|Acknowledgments?|Acknowledgements|Appendix|"
               r"Supplementary(?:\s+Material)?)\s*$", re.IGNORECASE),
    # 中文常用章节
    re.compile(r"^\s*(摘要|关键词|引言|绪论|背景|相关工作|方法|材料与方法|实验|"
               r"结果|结果与讨论|讨论|结论|参考文献|致谢|附录|补充材料)\s*$"),
]

# 标题行一般较短；正文段落通常较长。这个上限用于过滤明显是正文的行。
HEADING_MAX_LEN = 80


def run_pdftotext(pdf):
    try:
        out = subprocess.run(
            ["pdftotext", "-layout", pdf, "-"],
            check=True, capture_output=True, text=True, timeout=300,
        )
        return out.stdout
    except FileNotFoundError:
        raise SystemExit("pdftotext not found; is pdf-text-tool installed?")
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"pdftotext failed: {e.stderr.strip()[:400]}")


def split_pages(text):
    # pdftotext 用换页符 \f 分页
    parts = text.split("\f")
    pages = []
    for i, p in enumerate(parts, 1):
        body = p.strip("\n")
        pages.append({"page": i, "text": body, "chars": len(body)})
    # 末尾可能多出一个空页
    while pages and pages[-1]["chars"] == 0:
        pages.pop()
    return pages


def detect_sections(pages):
    sections = []
    for pg in pages:
        for line in pg["text"].splitlines():
            s = line.strip()
            if not s or len(s) > HEADING_MAX_LEN:
                continue
            if any(pat.match(s) for pat in SECTION_PATTERNS):
                # 去重：同一标题只保留最早出现的页码
                if not sections or sections[-1]["heading"] != s:
                    sections.append({"heading": s, "page": pg["page"]})
    return sections


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True, help="输出 paper_text.json 的路径")
    args = ap.parse_args()

    raw = run_pdftotext(args.pdf)
    pages = split_pages(raw)
    sections = detect_sections(pages)

    total_chars = sum(p["chars"] for p in pages)
    empty_pages = sum(1 for p in pages if p["chars"] < 20)
    result = {
        "source": args.pdf,
        "num_pages": len(pages),
        "extractor": "pdftotext -layout",
        "total_chars": total_chars,
        "empty_hint": total_chars == 0,
        "scanned_hint": (empty_pages / max(len(pages), 1)) > 0.6,
        "sections": sections,
        "pages": pages,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({
        "ok": True,
        "num_pages": len(pages),
        "total_chars": total_chars,
        "empty_hint": result["empty_hint"],
        "scanned_hint": result["scanned_hint"],
        "sections_detected": len(sections),
        "out": args.out,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

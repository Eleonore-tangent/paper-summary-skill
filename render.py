#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 .pptx 渲染成 PDF 和 PNG 预览（真实渲染，用于复核）。

依赖：soffice（LibreOffice，office-renderer）与 pdftoppm（pdf-render-tool）。
任一缺失时输出 honest 状态，不伪造预览。
"""
import argparse, json, os, subprocess, sys


def _run(cmd, timeout=600):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return None, "", "command not found"
    except subprocess.TimeoutExpired:
        return -9, "", "timeout"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pptx", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--dpi", type=int, default=100)
    ap.add_argument("--max-pages", type=int, default=6, help="只渲染前 N 页为 PNG 预览")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    pptx = os.path.abspath(args.pptx)
    result = {"ok": True, "pptx": pptx, "files": [], "errors": []}

    soffice = "soffice"
    for cand in ("soffice", "libreoffice"):
        rc, _, _ = _run([cand, "--version"], timeout=60)
        if rc == 0:
            soffice = cand
            break
    else:
        soffice = None

    if soffice is None:
        result["ok"] = False
        result["errors"].append("soffice not found; no PDF/PNG preview rendered")
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)

    rc, so, se = _run([soffice, "--headless", "--convert-to", "pdf",
                       "--outdir", args.outdir, pptx])
    if rc != 0:
        result["ok"] = False
        result["errors"].append(f"soffice pdf convert failed: {se.strip()[:300]}")
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)

    pdf = os.path.join(args.outdir, os.path.splitext(os.path.basename(pptx))[0] + ".pdf")
    if os.path.exists(pdf):
        result["files"].append(pdf)

    # PNG 预览
    rc, _, se = _run(["pdftoppm", "-png", "-r", str(args.dpi),
                      "-f", "1", "-l", str(args.max_pages), pdf,
                      os.path.join(args.outdir, "deck")])
    if rc == 0:
        for fn in sorted(os.listdir(args.outdir)):
            if fn.startswith("deck-") and fn.endswith(".png"):
                result["files"].append(os.path.join(args.outdir, fn))
    elif rc is None:
        result["errors"].append("pdftoppm not found; no PNG preview")
    else:
        result["errors"].append(f"pdftoppm failed: {se.strip()[:300]}")

    result["rendered"] = bool(result["files"])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

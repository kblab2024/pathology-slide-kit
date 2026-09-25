# -*- coding: utf-8 -*-
"""把撰寫工作流的各批結果（batch_{k}.json）合併成 written.json，並把各批的 glossary_additions 併進課程 glossary.md。

用法：python merge_written.py --course immune --dir <written 資料夾> --blueprint <blueprint.json> [--no-glossary]
輸出：<dir>/written.json（依藍圖順序）、<dir>/issues.md（各批 issues 與 changelog 摘要，給教師裁決清單用）
glossary 新增：只加中文尚未存在的詞，欄位「| 中文 | English | 縮寫 | 首見頁 | 禁用變體 | 依據 |」，依據寫「撰寫階段新增」。
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_course  # noqa: E402
from style_check import load_glossary  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--blueprint", required=True)
    ap.add_argument("--no-glossary", action="store_true")
    a = ap.parse_args()
    c = load_course(a.course)
    order = [s["slug"] for s in json.load(open(a.blueprint, encoding="utf-8"))["slides"]]
    got, adds, issues = {}, [], []
    files = sorted(glob.glob(os.path.join(a.dir, "batch_*.json")),
                   key=lambda p: int(re.search(r"batch_(\d+)\.json$", p).group(1)) if re.search(r"batch_(\d+)\.json$", p) else 0)
    files = [f for f in files if re.search(r"batch_\d+\.json$", f)]
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        for s in d.get("slides", []):
            got[s["slug"]] = s
        adds += d.get("glossary_additions") or []
        for x in d.get("issues") or []:
            issues.append((os.path.basename(f), x))
    miss = [s for s in order if s not in got]
    extra = [s for s in got if s not in order]
    out = {"slides": [got[s] for s in order if s in got]}
    json.dump(out, open(os.path.join(a.dir, "written.json"), "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=1)
    print(f"batches {len(files)}；slides {len(out['slides'])}/{len(order)}；缺 {miss[:10]}；多 {extra[:10]}")
    if not a.no_glossary and adds:
        gp = c.path("glossary")
        have = {g["zh"] for g in load_glossary(gp)}
        new, seen = [], set()
        for x in adds:
            zh = (x.get("zh") or "").strip()
            en = (x.get("en") or "").strip()
            if not zh or not en or zh in have or zh in seen:
                continue
            seen.add(zh)
            new.append(f"| {zh} | {en} | {x.get('abbr', '') or ''} | {x.get('page', '') or '—'} |  | 撰寫階段新增 |")
        if new:
            with open(gp, "a", encoding="utf-8", newline="\n") as fh:
                fh.write("\n" + "\n".join(new) + "\n")
        print(f"glossary 新增 {len(new)} 詞（候選 {len(adds)}）")
    L = ["# 撰寫階段提出的問題（issues）", ""]
    for f, x in issues:
        L.append(f"- {f}：{json.dumps(x, ensure_ascii=False) if not isinstance(x, str) else x}")
    open(os.path.join(a.dir, "issues.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    return 1 if miss else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

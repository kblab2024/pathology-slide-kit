# -*- coding: utf-8 -*-
"""把分段抽取並經裁決的教科書事實（facts/seg/S??_final.json）合併成 facts_R.json，
把查核過的文獻主張（_archive/gather/lit/*_verified.json）合併成 facts_X.json，並產生人讀版 facts.md。

用法：python merge_facts.py --course immune
輸出（路徑見 course.yaml paths.facts_R / facts_X）：
  facts_R.json  {"source": 教科書, "facts":[…], "figures":[…], "tables":[…], "headings":[…], "contradictions":[…]}
  facts_X.json  {"claims":[…只收 verified=true…], "rejected":[…], "conflicts":[…]}
  facts.md      依章節列出 R 層（附印刷頁）與 X 層（附出處），給教師與撰寫者翻閱
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_course  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", required=True)
    a = ap.parse_args()
    c = load_course(a.course)
    seg_dir = os.path.join(c["dir"], "facts", "seg")
    R = {"source": c["textbook"]["ref"], "facts": [], "figures": [], "tables": [], "headings": [],
         "contradictions": [], "segments": []}
    for p in sorted(glob.glob(os.path.join(seg_dir, "S??_final.json"))):
        d = json.load(open(p, encoding="utf-8"))
        R["segments"].append({"segment": d.get("segment"), "adjudication": d.get("adjudication")})
        for k in ("facts", "figures", "tables", "headings", "contradictions"):
            R[k] += d.get(k) or []
    seen, dup = set(), []
    for f in R["facts"]:
        if f["id"] in seen:
            dup.append(f["id"])
        seen.add(f["id"])
    R["facts"].sort(key=lambda f: (f.get("page") or 0, f["id"]))
    json.dump(R, open(c.path("facts_R"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    X = {"claims": [], "rejected": [], "conflicts": []}
    lit_dir = os.path.join(c["dir"], "_archive", "gather", "lit")
    for p in sorted(glob.glob(os.path.join(lit_dir, "*_verified.json"))):
        d = json.load(open(p, encoding="utf-8"))
        for cl in d.get("claims", []):
            cl["topic"] = d.get("topic")
            (X["claims"] if cl.get("verified") else X["rejected"]).append(cl)
        X["conflicts"] += [dict(x, topic=d.get("topic")) for x in d.get("conflicts", [])]
    json.dump(X, open(c.path("facts_X"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    L = [f"# 事實帳：{c['topic']}", "", f"R 層＝{R['source']}（唯一正典）；X 層＝文獻補充（必引出處，不得蓋過 R 層）。", "",
         f"R 層 {len(R['facts'])} 條、圖 {len(R['figures'])}、表 {len(R['tables'])}；X 層 {len(X['claims'])} 條（剔除 {len(X['rejected'])}、衝突 {len(X['conflicts'])}）。", ""]
    cur = None
    for f in R["facts"]:
        h = (f.get("heading") or "").split(">")[0].strip()
        if h != cur:
            L += ["", f"## {h}（R）", ""]
            cur = h
        L.append(f"- `{f['id']}` p.{f.get('page')}｜{f.get('zh') or ''}｜{f.get('en') or ''}")
    L += ["", "## 文獻補充（X）", ""]
    for cl in X["claims"]:
        L.append(f"- `{cl['id']}`｜{cl.get('claim_zh')}｜{cl.get('slide_cite')}")
    if X["conflicts"] or R["contradictions"]:
        L += ["", "## 衝突與矛盾（交教師裁決）", ""]
        L += [f"- Robbins 自身：{x}" for x in R["contradictions"]]
        L += [f"- 文獻 vs Robbins（{x.get('topic')}）：Robbins「{x.get('robbins')}」／文獻「{x.get('paper')}」" for x in X["conflicts"]]
    open(os.path.join(c["dir"], "facts", "facts.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print(f"R {len(R['facts'])}（重複 id {len(dup)}）、figures {len(R['figures'])}、tables {len(R['tables'])}、"
          f"X {len(X['claims'])}／剔除 {len(X['rejected'])}／衝突 {len(X['conflicts'])}；segments {len(R['segments'])}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

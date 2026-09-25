# -*- coding: utf-8 -*-
"""檢查藍圖 JSON：欄位、slug 唯一、segment 對得上、圖檔存在、國考題 key 在題庫、框架圖有定義、各節張數與分鐘、有圖率。

用法：python validate_blueprint.py --course immune <blueprint.json> [--diagrams diagrams.yaml]
  --diagrams：尚未併入 course.yaml 的框架圖定義（yaml：{名稱: {nodes, rows, groups}}）
結束碼：有 RED 為 1。輸出最後一行是 JSON 摘要（給工作流代理讀）。
"""
import argparse
import json
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_course, load_questions  # noqa: E402

TYPES = {"title", "divider", "left", "flash", "big", "pair", "robbins", "table3", "quiz", "stats", "diagram"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", required=True)
    ap.add_argument("blueprint")
    ap.add_argument("--diagrams", default=None)
    ap.add_argument("--deck", default=None)
    a = ap.parse_args()
    c = load_course(a.course)
    deck = a.deck or c["deck_order"][0]
    B = json.load(open(a.blueprint, encoding="utf-8"))
    dia = dict(c["diagrams"])
    if a.diagrams and os.path.exists(a.diagrams):
        dia.update(yaml.safe_load(open(a.diagrams, encoding="utf-8")) or {})
    qs = load_questions(c, deck)
    reds, warns = [], []
    seg2sec = {}
    for sec in B.get("sections", []):
        for g in sec.get("segments", []):
            seg2sec[g["id"]] = sec["label"]
    seen = set()
    per = {}
    mins = {}
    content = img = 0
    for s in B.get("slides", []):
        for k in ("slug", "segment", "type", "brief"):
            if not s.get(k):
                reds.append(f"{s.get('slug')} 缺欄位 {k}")
        if s.get("slug") in seen:
            reds.append(f"slug 重複 {s['slug']}")
        seen.add(s.get("slug"))
        if s.get("type") not in TYPES:
            reds.append(f"{s.get('slug')} type 不合法：{s.get('type')}")
        sec = seg2sec.get(s.get("segment"))
        if not sec:
            reds.append(f"{s.get('slug')} segment {s.get('segment')} 不在 sections")
        per[sec] = per.get(sec, 0) + 1
        mins[sec] = mins.get(sec, 0) + float(s.get("minutes") or 0)
        for im in s.get("img") or []:
            p = im["path"] if os.path.isabs(im["path"]) else os.path.join(c["dir"], im["path"])
            if not os.path.exists(p):
                reds.append(f"{s['slug']} 圖檔不存在 {im['path']}")
        if s.get("type") == "quiz" and s.get("quiz") not in qs:
            reds.append(f"{s['slug']} 國考題 key 不在題庫：{s.get('quiz')}")
        if s.get("type") == "diagram" and s.get("diagram") not in dia:
            reds.append(f"{s['slug']} 框架圖未定義：{s.get('diagram')}")
        if s.get("type") == "pair" and len(s.get("img") or []) != 2:
            warns.append(f"{s['slug']} pair 應有 2 張圖（現 {len(s.get('img') or [])}）")
        if s.get("type") not in ("title", "divider", "quiz"):
            content += 1
            if s.get("img") or s.get("type") == "diagram":
                img += 1
    lo, hi = c.deck(deck).get("per_section", [0, 10 ** 6])
    for sec, n in per.items():
        if not (lo <= n <= hi):
            warns.append(f"{sec} {n} 張，超出 {lo}–{hi}")
        if mins.get(sec) and mins[sec] > 42:
            warns.append(f"{sec} 估計 {mins[sec]:.0f} 分鐘，超過 40 分鐘目標")
    rate = img / content if content else 0
    if rate < c.sizes["img_rate_min"]:
        warns.append(f"有圖率 {img}/{content}＝{rate:.0%} 低於 {c.sizes['img_rate_min']:.0%}")
    nq = sum(1 for s in B.get("slides", []) if s.get("type") == "quiz")
    for m in warns:
        print("[WARN]", m)
    for m in reds:
        print("[RED]", m)
    summary = {"slides": len(B.get("slides", [])), "per_section": per, "minutes": mins, "img_rate": round(rate, 3),
               "quiz": nq, "red": len(reds), "warn": len(warns)}
    print(json.dumps(summary, ensure_ascii=False))
    return 1 if reds else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

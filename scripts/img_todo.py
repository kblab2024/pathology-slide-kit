# -*- coding: utf-8 -*-
"""產出「待補圖清單」：素材池裡標了 img_wanted（或 IMG 檔案不存在）的張，依節與張號列出，給教師自己補圖。

用法：python img_todo.py --course immune [--deck dent]
輸出：course.yaml 的 paths.img_todo（例：成品/待補圖清單.md）
每列：節｜張號｜標題｜想要的圖（img_wanted）｜素材池寫了但找不到的圖檔
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import build_deck, load_course, strip_markup  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", required=True)
    ap.add_argument("--deck", default=None)
    a = ap.parse_args()
    c = load_course(a.course)
    deck = a.deck or c["deck_order"][0]
    built = build_deck(c, deck)
    rows = []
    for s in built["slides"]:
        missing = [i["path"] for i in s["imgs"] if not i["exists"]]
        has = any(i["exists"] for i in s["imgs"])
        if (not has and s.get("img_wanted")) or missing:
            rows.append((s["section"], s["num"], strip_markup(s["title"]), s.get("img_wanted") or "",
                         "；".join(missing)))
    L = [f"# 待補圖清單（{c['topic']}｜{built['name']}）", "",
         f"共 {len(rows)} 張。投影片上這些位置留白（不畫佔位框）；補圖後把檔案放進 assets/images/ 並在素材池加 IMG 行即可重產。", "",
         "| 節 | 張號 | 標題 | 想要的圖 | 素材池寫了但找不到的檔 |", "|---|---|---|---|---|"]
    L += [f"| {a_} | {b} | {t} | {w} | {m} |" for a_, b, t, w, m in rows]
    out = c.path("img_todo")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print(f"{len(rows)} 張 -> {out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

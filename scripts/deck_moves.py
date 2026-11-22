#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""國考題張、融合張、移到參考資料的張：照一份 json 改素材池與選單（硬規則 19；可以重跑，結果一樣）。

教師 2026-11-22：「把110 國考15-18 兩小時的課三節 三小時的課四節 寫進鐵律」；中醫系講義：
「我要的是融合進原內容且符合張數跟時間限制 不是另外教中醫喔」「融合部分要少但精 不要耽誤到正課內容」。
做法與範例見 docs/中醫系講義流程.md；第一個用的是 uro-kidney-b2 L1（2026-11-22 草稿4–7）。

json（預設 <課程>/_archive/build/deck_moves_<deck>.json）：
  quiz：[{slug, key, after, note, why, ref}]      國考題張：素材池加一張 <!-- type: quiz -->，放在 after 那張後面
                                                  （同一張後面有幾題照 json 的順序）；已經有就更新題下那一行（note）
  fuse_slides：[{slug, after, why}]               融合張：內容在 --fuse-src（素材池的格式、帶 <!-- fuse: yes -->），
                                                  接在 after 那張與它後面的國考題張之後
  move_to_ref：[{slug, why}]                      選單拿掉（素材池留著、字不動），原文另存 moved_<deck>.md 給參考資料
  （fuse_inline、fusion_excluded 是 fuse_prepare.py 的紀錄，這支不讀）
json 裡拿掉的國考題張、融合張，素材池與選單也一起拿掉。拿掉以後沒有張的「### 段」標題一起拿掉。
命名約定：國考題張的 slug 含 -q-，融合張的 slug 含 -fuse-。

用法：python deck_moves.py --course <課程> --deck <deck> [--moves <json>] [--fuse-src <md>] [--pool <素材池>]
素材池是從批檔組裝出來的課（例 uro-kidney-b2 的 assemble_written.py），每次組裝後都要再跑這一支。
"""
import argparse
import glob
import json
import os
import re
import sys

import common

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--course", required=True)
ap.add_argument("--deck", required=True)
ap.add_argument("--moves", help="預設 <課程>/_archive/build/deck_moves_<deck>.json")
ap.add_argument("--fuse-src", help="融合張的內容，預設 <課程>/_archive/written/w_fuse_<deck>.md")
ap.add_argument("--pool", help="素材池，預設 <課程>/sources/ 裡唯一的 *-pool.md")
ap.add_argument("--moved-out", help="移走的張的原文快照，預設 <課程>/_archive/build/moved_<deck>.md")
a = ap.parse_args()

cd = common.load_course(a.course)["dir"]
deck = a.deck
mp = a.moves or os.path.join(cd, "_archive", "build", f"deck_moves_{deck}.json")
moves = json.load(open(mp, encoding="utf-8"))
pools = [a.pool] if a.pool else sorted(glob.glob(os.path.join(cd, "sources", "*-pool.md")))
if len(pools) != 1:
    sys.exit(f"素材池要剛好一個（找到 {len(pools)} 個）；用 --pool 指定")
pool_p = pools[0]
deck_p = os.path.join(cd, "sources", "decks", f"{deck}.md")

raw = open(pool_p, encoding="utf-8").read()
head, *blocks = re.split(r"(?m)^(?=## 投影片 )", raw)


def slug_of(b):
    return re.match(r"## 投影片 ([^｜\s]+)", b).group(1)


errs = []
fuse_src = a.fuse_src or os.path.join(cd, "_archive", "written", f"w_fuse_{deck}.md")
fuse_blocks = {}
if os.path.exists(fuse_src):
    _, *fb = re.split(r"(?m)^(?=## 投影片 )", open(fuse_src, encoding="utf-8").read())
    fuse_blocks = {slug_of(b): b.rstrip("\n") + "\n\n" for b in fb}
fuse_pos = moves.get("fuse_slides", [])

# 0. json 裡已經拿掉的國考題張與融合張：素材池與選單都拿掉
want = {q["slug"] for q in moves.get("quiz", [])} | {f["slug"] for f in fuse_pos}
gone = [slug_of(b) for b in blocks
        if f"<!-- aud: {deck} -->" in b and ("<!-- type: quiz -->" in b or "-fuse-" in slug_of(b)) and slug_of(b) not in want]
blocks = [b for b in blocks if slug_of(b) not in gone]

# 1. 素材池：國考題張
for q in moves.get("quiz", []):
    note = q.get("note", "").strip()
    if ">" in note or "-->" in note:
        errs.append(f"{q['slug']}: 題下那一行不能有 >（寫全形 ＞）")
    blk = (f"## 投影片 {q['slug']}｜\n<!-- type: quiz -->\n<!-- aud: {deck} -->\n"
           f"<!-- quiz: {q['key']}" + (f" ｜ {note}" if note else "") + " -->\n\n")
    slugs = [slug_of(b) for b in blocks]
    if q["slug"] in slugs:
        blocks[slugs.index(q["slug"])] = blk
        continue
    if q["after"] not in slugs:
        errs.append(f"{q['slug']}: 素材池沒有 {q['after']}")
        continue
    i = slugs.index(q["after"]) + 1
    while i < len(blocks) and "<!-- type: quiz -->" in blocks[i]:
        i += 1
    if not blocks[i - 1].endswith("\n\n"):
        blocks[i - 1] = blocks[i - 1].rstrip("\n") + "\n\n"
    blocks.insert(i, blk)

# 1b. 素材池：融合張
for f in fuse_pos:
    if f["slug"] not in fuse_blocks:
        errs.append(f"{f['slug']}: {os.path.basename(fuse_src)} 裡沒有這一張")
        continue
    blk = fuse_blocks[f["slug"]]
    slugs = [slug_of(b) for b in blocks]
    if f["slug"] in slugs:
        blocks[slugs.index(f["slug"])] = blk
        continue
    if f["after"] not in slugs:
        errs.append(f"{f['slug']}: 素材池沒有 {f['after']}")
        continue
    i = slugs.index(f["after"]) + 1
    while i < len(blocks) and ("<!-- type: quiz -->" in blocks[i] or "-fuse-" in slug_of(blocks[i])):
        i += 1
    if not blocks[i - 1].endswith("\n\n"):
        blocks[i - 1] = blocks[i - 1].rstrip("\n") + "\n\n"
    blocks.insert(i, blk)

# 移走的張：素材池原文存檔
moved = moves.get("move_to_ref", [])
by_slug = {slug_of(b): b for b in blocks}
snap = [by_slug[m["slug"]].rstrip() + "\n" for m in moved if m["slug"] in by_slug]
for m in moved:
    if m["slug"] not in by_slug:
        errs.append(f"{m['slug']}: 素材池沒有這一張（移到參考資料要用它的原文）")
if errs:
    print("\n".join(errs))
    sys.exit(1)
open(pool_p, "w", encoding="utf-8", newline="\n").write(head + "".join(blocks))
mo = a.moved_out or os.path.join(cd, "_archive", "build", f"moved_{deck}.md")
os.makedirs(os.path.dirname(mo), exist_ok=True)
with open(mo, "w", encoding="utf-8", newline="\n") as f:
    f.write(f"# {deck}：移到參考資料的張（素材池原文；deck_moves.py 產生，不要手改）\n\n" + "\n".join(snap))

# 2. 選單
lines = open(deck_p, encoding="utf-8").read().split("\n")
drop = {m["slug"] for m in moved} | set(gone)
lines = [ln for ln in lines if not (ln.startswith("- ") and ln[2:].strip() in drop)]
for q in moves.get("quiz", []):
    items = [ln[2:].strip() if ln.startswith("- ") else None for ln in lines]
    if q["slug"] in items:
        continue
    if q["after"] not in items:
        print(f"[注意] 選單沒有 {q['after']}，{q['slug']} 沒有插進去")
        continue
    i = items.index(q["after"]) + 1
    while i < len(lines) and lines[i].startswith("- ") and "-q-" in lines[i]:
        i += 1
    lines.insert(i, f"- {q['slug']}")
for f in fuse_pos:
    items = [ln[2:].strip() if ln.startswith("- ") else None for ln in lines]
    if f["slug"] in items:
        continue
    if f["after"] not in items:
        print(f"[注意] 選單沒有 {f['after']}，{f['slug']} 沒有插進去")
        continue
    i = items.index(f["after"]) + 1
    while i < len(lines) and lines[i].startswith("- ") and ("-q-" in lines[i] or "-fuse-" in lines[i]):
        i += 1
    lines.insert(i, f"- {f['slug']}")
out = []
for i, ln in enumerate(lines):
    if ln.startswith("### "):
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j >= len(lines) or lines[j].startswith("#"):
            continue
    out.append(ln)
open(deck_p, "w", encoding="utf-8", newline="\n").write("\n".join(out))
n = sum(1 for ln in out if ln.startswith("- "))
print(f"deck_moves：國考題 {len(moves.get('quiz', []))} 題、融合張 {len(fuse_pos)} 張、移到參考資料 {len(moved)} 張；選單 {n} 張"
      + (f"；拿掉舊的國考題或融合張 {len(gone)} 張" if gone else ""))

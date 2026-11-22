#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中醫系講義：把融合對照表（方劑與關鍵組成 → 證型 → 西醫病理；fuse_<deck>.json）放進講義（硬規則 19）。

教師 2026-11-22：「我要的是融合進原內容且符合張數跟時間限制 不是另外教中醫喔」「融合部分要少但精 不要耽誤到正課內容
可以因為融合的關係放寬到115」；同一天又說「我覺得中醫融到10張試試看」「我覺得你要用模型能力發揮一點想像力 想像一下有那些疾病
可以對應到證型」。做法、版面限制與範例見 docs/中醫系講義流程.md（第一個用的是 uro-kidney-b2 L1 草稿6、草稿7）。

做四件事（字是我們的；之後由 Gemini 融合包用它自己的話重寫）：
  1. 融合張（new_slides）→ <課程>/_archive/written/w_fuse_<deck>.md（素材池格式，帶 <!-- fuse: yes -->），
     位置寫進 deck_moves_<deck>.json 的 fuse_slides（deck_moves.py 插進素材池與選單）。
     已經在 w_fuse_<deck>.md 的張保留原樣（主 session 為版面精簡過、或 Gemini 融合包套回過）；json 那一張寫 "replace": true 才換掉。
  2. 原來的張加一行（inline）→ course.yaml rewrite.src 列的批檔裡，那一張最後一條條列後面加一條
     （記在 <課程>/_archive/written/main_session_edits.md）；deck_moves json 的 fuse_inline 已經有的張保留現在的字，不再加。
  3. 國考題下面那一行（quiz）→ deck_moves json 的 quiz[].note（舊的留在 note_草稿5）。
  4. Gemini 融合包的設定 → <課程>/_archive/revoice/fuse_pack_<deck>.json（給 rewrite_pack.py make --fuse）。
可以重跑。--notes 另寫參考資料的「融合中醫的對照」一節（張號讀 成品/<PPTX 檔名>_layout.json，要先產檔）。

用法：python fuse_prepare.py --course <課程> --deck <deck> <fuse_<deck>.json> [--max-slides 5] [--max-inline 5] [--notes]
json 格式：{new_slides:[{slug, after, type, title, bullets[], rows[[...]], src, why, materials[{fact, source}]}],
           inline:[{slug, why, materials, suggest, extra_chars, extra_lines}], quiz:[{slug, key, note, materials}], excluded:[{what, why}]}
"""
import argparse
import json
import os
import re

import yaml

import common

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--course", required=True)
ap.add_argument("--deck", required=True)
ap.add_argument("fuse_json")
ap.add_argument("--max-slides", type=int, default=5, help="融合張上限（預設 5；張數還要符合 course.yaml decks.<deck>.cap）")
ap.add_argument("--max-inline", type=int, default=5, help="加一行的張數上限（預設 5）")
ap.add_argument("--moves", help="預設 <課程>/_archive/build/deck_moves_<deck>.json（沒有就新建）")
ap.add_argument("--notes", action="store_true", help="另寫 <課程>/_archive/build/fuse_notes_<deck>.md：參考資料的融合那一節")
a = ap.parse_args()

course = common.load_course(a.course)
cd, deck = course["dir"], a.deck
fz = json.load(open(a.fuse_json, encoding="utf-8"))
mp = a.moves or os.path.join(cd, "_archive", "build", f"deck_moves_{deck}.json")
moves = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
cfg = yaml.safe_load(open(os.path.join(cd, "course.yaml"), encoding="utf-8"))
srcs = [os.path.join(cd, p) for p in (cfg.get("rewrite") or {}).get("src", [])]

new = fz.get("new_slides", [])[:a.max_slides]
inline = fz.get("inline", [])[:a.max_inline]
quiz = fz.get("quiz", [])
if len(fz.get("new_slides", [])) > a.max_slides or len(fz.get("inline", [])) > a.max_inline:
    print(f"[注意] 融合張 {len(fz.get('new_slides', []))} 張、加一行 {len(fz.get('inline', []))} 張，"
          f"超過的不用（上限 {a.max_slides}、{a.max_inline}）")


def cell(x):
    return str(x).replace("|", "／").strip()


# 1. 融合張
wf = os.path.join(cd, "_archive", "written", f"w_fuse_{deck}.md")
old_blocks = {}
if os.path.exists(wf):
    _, *ob = re.split(r"(?m)^(?=## 投影片 )", open(wf, encoding="utf-8").read())
    old_blocks = {re.match(r"## 投影片 ([^｜\s]+)", b).group(1): b.rstrip("\n") + "\n\n" for b in ob}
out = [f"# {deck}：融合張（方劑、證型、病理；fuse_prepare.py 從融合對照表產生，Gemini 融合包套回時會改這個檔）\n\n"]
for f in new:
    if f["slug"] in old_blocks and not f.get("replace"):
        out.append(old_blocks[f["slug"]])
        continue
    blk = [f"## 投影片 {f['slug']}｜{f['title']}", f"<!-- type: {f.get('type', 'table3')} -->", f"<!-- aud: {deck} -->", "<!-- fuse: yes -->"]
    if f.get("type", "table3") == "table3":
        blk.append("<!-- tbl: style=clean; pad=tight -->")
    if f.get("src"):
        blk.append(f"<!-- src: {f['src']} -->")
    for b in f.get("bullets") or []:
        blk.append(f"- {b}")
    rows = f.get("rows") or []
    if rows:
        blk.append("")
        blk.append("| " + " | ".join(cell(c) for c in rows[0]) + " |")
        blk.append("|" + "---|" * len(rows[0]))
        for r in rows[1:]:
            blk.append("| " + " | ".join(cell(c) for c in r) + " |")
    out.append("\n".join(blk) + "\n\n")
os.makedirs(os.path.dirname(wf), exist_ok=True)
open(wf, "w", encoding="utf-8", newline="\n").write("".join(out).rstrip("\n") + "\n")
moves["fuse_slides"] = [{"slug": f["slug"], "after": f["after"], "why": f.get("why", "")} for f in new]

# 2. 原來的張加一行
log = []
had = {x["slug"]: x for x in moves.get("fuse_inline", [])}
for it in inline:
    if it["slug"] in had:
        it["suggest"] = had[it["slug"]]["suggest"]
        continue
    done = False
    for p in srcs:
        if not os.path.exists(p):
            continue
        lines = open(p, encoding="utf-8").read().split("\n")
        idx = next((i for i, ln in enumerate(lines) if re.match(rf"^## 投影片 {re.escape(it['slug'])}｜", ln)), None)
        if idx is None:
            continue
        end = next((j for j in range(idx + 1, len(lines)) if lines[j].startswith("## 投影片 ") or lines[j].startswith("### 投影片 ")), len(lines))
        body = lines[idx + 1:end]
        if any(ln.strip() == f"- {it['suggest']}" for ln in body):
            done = True
            break
        bl = [idx + 1 + k for k, ln in enumerate(body) if ln.startswith("- ")]
        at = (bl[-1] + 1) if bl else next((idx + 1 + k for k, ln in enumerate(body) if ln.startswith("|")), end)
        lines.insert(at, f"- {it['suggest']}")
        open(p, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
        log.append(f"- `{it['slug']}`（{os.path.basename(p)}）：加一條「{it['suggest']}」。理由：{it.get('why', '')}")
        done = True
        break
    if not done:
        print(f"[注意] 批檔（course.yaml rewrite.src）裡找不到 {it['slug']}，沒有加")
if log:
    me = os.path.join(cd, "_archive", "written", "main_session_edits.md")
    with open(me, "a", encoding="utf-8", newline="\n") as f:
        f.write("\n\n## 融合中醫的對照：原來的張加一行（fuse_prepare.py；之後由 Gemini 融合包重寫）\n\n" + "\n".join(log) + "\n")
moves["fuse_inline"] = [{"slug": it["slug"], "suggest": it["suggest"], "why": it.get("why", "")} for it in inline]

# 3. 國考題下面那一行
byslug = {q["slug"]: q for q in quiz}
for q in moves.get("quiz", []):
    if q["slug"] in byslug and byslug[q["slug"]].get("note"):
        q.setdefault("note_草稿5", q["note"])
        q["note"] = byslug[q["slug"]]["note"].replace(">", "＞")
moves["fusion_excluded"] = fz.get("excluded", [])
os.makedirs(os.path.dirname(mp), exist_ok=True)
json.dump(moves, open(mp, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)

# 4. 融合包的設定
pack = {"new_slides": [{"slug": f["slug"], "materials": f.get("materials", [])} for f in new],
        "inline": [{"slug": it["slug"], "materials": it.get("materials", []), "suggest": "", "extra_chars": 0, "extra_lines": 0} for it in inline],
        "quiz": [{"slug": q["slug"], "key": q.get("key", ""), "note": q.get("note", ""), "materials": q.get("materials", [])} for q in quiz]}
pp = os.path.join(cd, "_archive", "revoice", f"fuse_pack_{deck}.json")
os.makedirs(os.path.dirname(pp), exist_ok=True)
json.dump(pack, open(pp, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
print(f"融合張 {len(new)} 張 → {wf}；加一行 {len(log)} 張（這次新加的）；國考題說明 {sum(1 for q in moves.get('quiz', []) if q['slug'] in byslug)} 題；融合包設定 → {pp}")

# 5. 參考資料的融合那一節（--notes）
if a.notes:
    lay_p = os.path.join(cd, "成品", common.deck_filename(course, deck) + "_layout.json")
    num = {}
    if os.path.exists(lay_p):
        num = {s: v["num"] for s, v in json.load(open(lay_p, encoding="utf-8"))["slides"].items()}
    else:
        print(f"[注意] 沒有 {os.path.basename(lay_p)}（還沒產檔），張號寫「?」")
    titles = {}
    for p in srcs:
        if os.path.exists(p):
            for m in re.finditer(r"(?m)^## 投影片 ([^｜\s]+)｜(.*)$", open(p, encoding="utf-8").read()):
                titles[m.group(1)] = m.group(2).replace("⏎", "")
    mats = {x["slug"]: x.get("materials", []) for x in pack["new_slides"] + pack["inline"]}
    L = ["## 融合中醫的對照（方劑、證型、病理）", "",
         "融合張與加一行的地方；每一條素材附研究報告的節與文獻編號，或 Robbins 頁碼與事實帳編號。", ""]
    for f in moves["fuse_slides"]:
        L += [f"### 第 {num.get(f['slug'], '?')} 張｜融合張：{titles.get(f['slug'], f['slug'])}", "",
              f"- 接在：第 {num.get(f['after'], '?')} 張（{titles.get(f['after'], f['after'])}）", f"- 為什麼放：{f.get('why', '')}"]
        L += [f"- 素材：{m.get('fact', '')}（{m.get('source', '')}）" for m in mats.get(f["slug"], [])] + [""]
    for it in moves["fuse_inline"]:
        L += [f"### 第 {num.get(it['slug'], '?')} 張｜加一行：{titles.get(it['slug'], it['slug'])}", "",
              f"- 加的那一行：{it.get('suggest', '').replace('⏎', '')}", f"- 為什麼加：{it.get('why', '')}"]
        L += [f"- 素材：{m.get('fact', '')}（{m.get('source', '')}）" for m in mats.get(it["slug"], [])] + [""]
    if moves.get("fusion_excluded"):
        L += ["### 想過、但沒有放的", ""] + [f"- {e['what']}：{e['why']}" for e in moves["fusion_excluded"]] + [""]
    np_ = os.path.join(cd, "_archive", "build", f"fuse_notes_{deck}.md")
    open(np_, "w", encoding="utf-8", newline="\n").write("\n".join(L).rstrip() + "\n")
    print(f"參考資料的融合那一節 → {np_}")

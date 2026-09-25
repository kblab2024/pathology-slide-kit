# -*- coding: utf-8 -*-
"""把藍圖（結構）＋撰寫結果（文字）組裝成三個來源檔：素材池 pool.md、講稿 script.md、選單 decks/<deck>.md。

用法：python assemble.py --course immune <blueprint.json> <written.json> [--dry-run]
有任何 RED 就不寫檔；寫檔前把舊來源檔複製到 <課程>/_archive/sources_backup_<序號>/。

blueprint.json（schema 見 templates/blueprint.schema.json）：
  {"sections":[{"label":"第一節","title":"正常免疫複習與過敏","segments":[{"id":"S1-02","title":"正常免疫複習"}]}],
   "slides":[{"slug":"imm-...","segment":"S1-02","type":"left","aud":"dent","build":"組名或空",
              "img":[{"path":"assets/images/…","src":"Robbins Fig. 6.13","label":"H&E"}],
              "img_wanted":"找不到圖時寫要什麼圖","quiz":"113-1#45","diagram":"hyper","diagram_bright":["第一型"],
              "fact_ids":["S04-012"],"lit_ids":["hae_dental-2"],"brief":"這張要講什麼"}]}
  aud 可省：只有一套 deck 時不寫，素材池就不寫 aud 行（該張屬於 course.yaml deck_order 的全部 deck）；
  多套時寫 deck 名（字串 "med,dent" 或陣列），不在 course.yaml decks 裡的名稱判 RED。
written.json：{"slides":[{"slug":…,"title":…,"bullets":["…","  - 子層"],"table_rows":[["表頭",…],[…]],
                          "src":["J Periodontol. 2019;90(1):23-30."],"notes":"備註","handout":["完整書目…"]}]}
"""
import argparse
import json
import os
import re
import shutil
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_course, load_questions, strip_markup  # noqa: E402

MARK_OK = re.compile(r"\[\[(藍|紅|橘|青|灰)[:：][^\[\]]+?\]\]")


def clean(t):
    return re.sub(r"[ \t]+", " ", (t or "").replace("\r", "")).rstrip()


def _aud_list(bp):
    """藍圖的 aud（字串 "med,dent" 或陣列）→ deck 名清單；沒寫回傳 []。"""
    a = bp.get("aud")
    if not a:
        return []
    if isinstance(a, str):
        a = re.split(r"[,，、\s]+", a)
    return [x.strip() for x in a if str(x).strip()]


def pool_block(bp, w):
    L = [f"## 投影片 {bp['slug']}｜{clean(w['title']).strip()}", f"<!-- type: {bp['type']} -->"]
    aud = _aud_list(bp)
    if aud:  # 沒寫 aud 的張屬於 course.yaml deck_order 的全部 deck（common.parse_pool）
        L.append(f"<!-- aud: {','.join(aud)} -->")
    if bp.get("quiz"):
        note = clean(w.get("quiz_note") or "").strip()
        L.append(f"<!-- quiz: {bp['quiz']}" + (f" ｜ {note}" if note else "") + " -->")
    if bp.get("diagram"):
        br = ",".join(bp.get("diagram_bright") or ["全部"])
        L.append(f"<!-- diagram: {bp['diagram']} | 亮:{br} -->")
    if bp.get("build"):
        L.append(f"<!-- build: {bp['build']} -->")
    src = [clean(x).strip() for x in (w.get("src") or []) if clean(x).strip()]
    if src:
        L.append(f"<!-- src: {' ｜ '.join(src)} -->")
    for im in bp.get("img") or []:
        extra = "".join(f" ｜ {k}：{im[v]}" for k, v in (("出處", "src"), ("標籤", "label"), ("內容", "desc"))
                        if im.get(v))
        L.append(f"<!-- IMG: {im['path']}{extra} -->")
    if not bp.get("img") and bp.get("img_wanted"):
        L.append(f"<!-- img_wanted: {clean(bp['img_wanted']).strip()} -->")
    if bp.get("fact_ids") or bp.get("lit_ids"):
        L.append(f"<!-- facts: {' '.join((bp.get('fact_ids') or []) + (bp.get('lit_ids') or []))} -->")
    for b in w.get("bullets") or []:
        b = clean(b)
        if not b.strip():
            continue
        m = re.match(r"^(\s*)-?\s*(.*)$", b)
        lvl = len(m.group(1)) // 2
        L.append("  " * lvl + "- " + m.group(2).strip())
    rows = [[clean(c).strip().replace("|", "／") for c in r] for r in (w.get("table_rows") or []) if any(r)]
    if rows:
        L.append("| " + " | ".join(rows[0]) + " |")
        L.append("|" + "---|" * len(rows[0]))
        L += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(L) + "\n"


def script_block(bp, w):
    L = [f"### 投影片 {bp['slug']}｜{clean(w['title']).strip()}", "", "【講稿】", clean(w.get("notes") or "").strip(), ""]
    hb = [clean(x).strip() for x in (w.get("handout") or []) if clean(x).strip()]
    if hb:
        L += ["【講義補充】"] + [f"- {x}" for x in hb] + [""]
    return "\n".join(L) + "\n"


def validate(course, B, W, deck):
    S = course.sizes
    reds, warns = [], []
    slugs = [s["slug"] for s in B["slides"]]
    dup = {x for x in slugs if slugs.count(x) > 1}
    if dup:
        reds.append(f"藍圖 slug 重複：{sorted(dup)[:8]}")
    miss = [s for s in slugs if s not in W]
    if miss:
        reds.append(f"撰寫結果缺 {len(miss)} 張：{miss[:8]}")
    segs = {g["id"] for sec in B["sections"] for g in sec["segments"]}
    badseg = [s["slug"] for s in B["slides"] if s["segment"] not in segs]
    if badseg:
        reds.append(f"segment 不在 sections 裡：{badseg[:8]}")
    qs = load_questions(course, deck)
    for s in B["slides"]:
        bad = [x for x in _aud_list(s) if x not in course["decks"]]
        if bad:
            reds.append(f"{s['slug']} aud 含 course.yaml decks 沒有的 deck：{bad}")
        if s["type"] == "quiz" and s.get("quiz") not in qs:
            reds.append(f"{s['slug']} 國考題 key {s.get('quiz')} 查無題庫")
        if s["type"] == "diagram" and s.get("diagram") not in course["diagrams"]:
            reds.append(f"{s['slug']} 框架圖 {s.get('diagram')} 不在 course.yaml diagrams")
        for im in s.get("img") or []:
            p = im["path"] if os.path.isabs(im["path"]) else os.path.join(course["dir"], im["path"])
            if not os.path.exists(p):
                warns.append(f"{s['slug']} 圖檔不存在：{im['path']}")
    grp = defaultdict(set)
    for s in B["slides"]:
        if s.get("build") and s["slug"] in W:
            grp[s["build"]].add(clean(W[s["slug"]]["title"]).strip())
    for k, v in grp.items():
        if len(v) > 1:
            reds.append(f"同標題連張組 {k} 標題不一致：{list(v)[:3]}")
    for s in B["slides"]:
        w = W.get(s["slug"])
        if not w:
            continue
        allt = [w.get("title", "")] + list(w.get("bullets") or [])
        for t in allt:
            left = MARK_OK.sub("", t)
            if "[[" in left or "]]" in left:
                reds.append(f"{s['slug']} 強調標記格式錯：{t[:40]}")
        if s["type"] in ("quiz", "title", "divider"):
            continue
        txt = strip_markup("".join(allt))
        n = len(re.sub(r"\s", "", txt))
        if n > S["char_red"]:
            reds.append(f"{s['slug']} 字元 {n} > {S['char_red']}")
        elif n > S["char_warn"]:
            warns.append(f"{s['slug']} 字元 {n} > {S['char_warn']}")
        if len(w.get("bullets") or []) > 5:
            warns.append(f"{s['slug']} 條列 {len(w['bullets'])} 條（新寫的張以 0–3 條為度）")
        if len(strip_markup(w.get("title", ""))) > S["title_warn_chars"]:
            warns.append(f"{s['slug']} 標題 {len(w['title'])} 字")
    return reds, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", required=True)
    ap.add_argument("blueprint")
    ap.add_argument("written")
    ap.add_argument("--deck", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    course = load_course(a.course)
    deck = a.deck or course["deck_order"][0]
    B = json.load(open(a.blueprint, encoding="utf-8"))
    W = {s["slug"]: s for s in json.load(open(a.written, encoding="utf-8"))["slides"]}
    reds, warns = validate(course, B, W, deck)
    by_sec = defaultdict(int)
    seg2sec = {g["id"]: sec["label"] for sec in B["sections"] for g in sec["segments"]}
    for s in B["slides"]:
        by_sec[seg2sec.get(s["segment"], "?")] += 1
    print("各節張數：", dict(by_sec), "合計", len(B["slides"]))
    for m in warns[:40]:
        print("[WARN]", m)
    if len(warns) > 40:
        print(f"[WARN] …另 {len(warns) - 40} 條")
    for m in reds:
        print("[RED]", m)
    if reds:
        print("===== 有 RED，不寫檔 =====")
        return 1
    if a.dry_run:
        print("===== dry-run 通過，未寫檔 =====")
        return 0
    pool_p, script_p = course.path("pool"), course.path("script")
    deck_p = os.path.join(course.path("decks_dir"), f"{deck}.md")
    if any(os.path.exists(p) for p in (pool_p, script_p, deck_p)):
        k = 1
        while os.path.exists(os.path.join(course["dir"], "_archive", f"sources_backup_{k:02d}")):
            k += 1
        bk = os.path.join(course["dir"], "_archive", f"sources_backup_{k:02d}")
        os.makedirs(bk)
        for p in (pool_p, script_p, deck_p):
            if os.path.exists(p):
                shutil.copy2(p, bk)
        print("舊來源檔備份到", bk)
    os.makedirs(os.path.dirname(pool_p), exist_ok=True)
    os.makedirs(os.path.dirname(deck_p), exist_ok=True)
    head = (f"# {course['topic']}-pool.md\n\n> 素材池：每張一個 slug。由 scripts/assemble.py 從藍圖＋撰寫結果產生；"
            "要改內容可直接改這裡（之後別再用舊 JSON 重組，會蓋掉）。\n\n")
    open(pool_p, "w", encoding="utf-8", newline="\n").write(head + "\n".join(pool_block(s, W[s["slug"]]) for s in B["slides"]))
    open(script_p, "w", encoding="utf-8", newline="\n").write(
        f"# {course['topic']}-script.md\n\n> 備註：【講稿】進投影片備註欄；【講義補充】放完整書目。\n\n"
        + "\n".join(script_block(s, W[s["slug"]]) for s in B["slides"]))
    L = [f"# {course.deck(deck)['name']}選單", ""]
    for sec in B["sections"]:
        L.append(f"## {sec['label']}｜{sec['title']}")
        for g in sec["segments"]:
            ids = [s["slug"] for s in B["slides"] if s["segment"] == g["id"]]
            if ids:
                L.append(f"### {g['title']}")
                L += [f"- {i}" for i in ids]
        L.append("")
    open(deck_p, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print("寫入", pool_p, script_p, deck_p, sep="\n  ")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

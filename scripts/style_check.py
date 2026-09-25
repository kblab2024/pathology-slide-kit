# -*- coding: utf-8 -*-
"""文字風格檢查：讀 style/rules.yaml（全課程共用規則）＋課程 glossary（逐張中英對照）。

用法：python style_check.py --course immune [--deck dent] [--rules ../style/rules.yaml] [--quiet]
  規則類型（rules.yaml 的 kind）：phrase 字面、regex 正則、count 全套計數上限；scope：slide／title／notes／all。
  中英對照（glossary.md 表格「| 中文 | English | 縮寫 | 首見頁 | 禁用變體 |」），範圍由 course.yaml 的 bilingual 決定：
    per_slide（該課有「每張中英」明令時，例 immune；指南 TERM-34）：
      - 一張投影片出現 glossary 的中文詞卻沒有它的英文（或縮寫）→ RED
      - 出現英文詞卻沒有中文 → RED（白名單：course.yaml 的 bilingual_whitelist，例如 H&E、CD4、IgE）
    first_per_deck（沒寫 bilingual 時的預設；指南 TERM-07）：
      - 術語在這一套第一次出現的那張要有英文；首見率 < 70% → WARN，並列出首見沒有英文的詞
    off：不檢查中英對照
    三種模式都檢查「禁用變體」→ RED。
  國考題張的題幹是官方原文，不檢查中英對照與用語。
結束碼：有 RED 為 1。
"""
import argparse
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, build_deck, bullet_level, load_course, parse_script, strip_markup  # noqa: E402


def load_glossary(path):
    if not os.path.exists(path):
        return []
    out = []
    for ln in open(path, encoding="utf-8"):
        st = ln.strip()
        if not st.startswith("|") or re.match(r"^\|[\s\-:|]+\|?$", st):
            continue
        cells = [c.strip() for c in st.strip("|").split("|")]
        if len(cells) < 2 or cells[0] in ("中文", "") or cells[1] in ("English", ""):
            continue
        out.append({"zh": cells[0], "en": cells[1], "abbr": cells[2] if len(cells) > 2 else "",
                    "bad": [x.strip() for x in re.split(r"[、,，]", cells[4]) if x.strip()] if len(cells) > 4 else []})
    return out


def slide_text(s):
    parts = [s["title"]] + [bullet_level(b)[1] for b in s["bullets"]]
    for r in s.get("table") or []:
        parts += r
    return strip_markup("\n".join(parts))


def en_present(entry, text_lc):
    cands = [entry["en"]] + ([entry["abbr"]] if entry["abbr"] else [])
    for c in cands:
        for alt in c.split("/"):
            alt = alt.strip().lower()
            if alt and alt in text_lc:
                return True
    return False


def check_bilingual(slides, gloss, whitelist):
    reds = []
    # 長詞優先：避免「T 細胞」在「調節性 T 細胞」裡重複報
    gloss = sorted(gloss, key=lambda g: -len(g["zh"]))
    for s in slides:
        if s["type"] in ("quiz",):
            continue
        t = slide_text(s)
        lc = t.lower()
        masked = t
        for g in gloss:
            if g["zh"] in masked:
                if not en_present(g, lc):
                    reds.append(f"#{s['num']} {s['id']}：「{g['zh']}」沒有英文（{g['en']}）")
                masked = masked.replace(g["zh"], "□" * len(g["zh"]))
            for bad in g["bad"]:
                if bad and bad in t:
                    reds.append(f"#{s['num']} {s['id']}：禁用變體「{bad}」→ 用「{g['zh']}」")
        for g in gloss:
            en = g["en"].lower()
            if len(en) < 4 or en in whitelist:
                continue
            if re.search(r"(?<![a-z])" + re.escape(en) + r"(?![a-z])", lc) and g["zh"] not in t:
                reds.append(f"#{s['num']} {s['id']}：英文「{g['en']}」沒有中文（{g['zh']}）")
        for g in gloss:
            ab = g["abbr"]
            if not ab or ab.lower() in whitelist:
                continue
            if re.search(r"(?<![A-Za-z0-9])" + re.escape(ab) + r"(?![A-Za-z0-9])", t) and g["zh"] not in t:
                reds.append(f"#{s['num']} {s['id']}：縮寫「{ab}」沒有中文（{g['zh']}）")
    return reds


BILINGUAL_MODES = ("per_slide", "first_per_deck", "off")
FIRST_RATE_WARN = 0.70   # TERM-07：首見率門檻


def bilingual_mode(course):
    """course.yaml 的 bilingual；沒寫就是 first_per_deck（指南的一般規則，不外推某課的明令）。"""
    m = str(course.get("bilingual") or "first_per_deck").strip()
    if m not in BILINGUAL_MODES:
        raise ValueError(f"course.yaml bilingual 只能是 {'／'.join(BILINGUAL_MODES)}，現在是 {m!r}")
    return m


def banned_variants(slides, gloss):
    reds = []
    for s in slides:
        if s["type"] in ("quiz",):
            continue
        t = slide_text(s)
        for g in gloss:
            for bad in g["bad"]:
                if bad and bad in t:
                    reds.append(f"#{s['num']} {s['id']}：禁用變體「{bad}」→ 用「{g['zh']}」")
    return reds


def first_use_rate(slides, gloss):
    """TERM-07 首見率：這一套出現過英文的 glossary 術語中，第一次出現（中文）那張就有英文的比例。
    回傳 (有標數, 分母, [(術語, 張號, slug)] 首見沒標的)。"""
    gloss = sorted(gloss, key=lambda g: -len(g["zh"]))
    first, seen_en = {}, set()
    for s in slides:
        if s["type"] in ("quiz",):
            continue
        t = slide_text(s)
        lc = t.lower()
        masked = t
        for g in gloss:
            if g["zh"] in masked:
                has = en_present(g, lc)
                if has:
                    seen_en.add(g["zh"])
                if g["zh"] not in first:
                    first[g["zh"]] = (has, s["num"], s["id"])
                masked = masked.replace(g["zh"], "□" * len(g["zh"]))
    den = [z for z in first if z in seen_en]
    ok = [z for z in den if first[z][0]]
    miss = [(z, first[z][1], first[z][2]) for z in den if not first[z][0]]
    return len(ok), len(den), miss


def check_bilingual_mode(slides, gloss, whitelist, mode):
    """依 course.yaml bilingual 檢查；回傳 (reds, warns)。"""
    if mode == "per_slide":
        return check_bilingual(slides, gloss, whitelist), []
    reds = banned_variants(slides, gloss)
    warns = []
    if mode == "first_per_deck":
        ok, den, miss = first_use_rate(slides, gloss)
        if den and ok / den < FIRST_RATE_WARN:
            eg = "、".join(f"{z}(#{n})" for z, n, _ in miss[:15])
            warns.append(f"TERM-07 首見率 {ok}/{den}＝{ok / den:.0%} < {FIRST_RATE_WARN:.0%}；首見沒有英文：{eg}"
                         + ("…" if len(miss) > 15 else ""))
    return reds, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", required=True)
    ap.add_argument("--deck", default=None)
    ap.add_argument("--rules", default=os.path.join(ROOT, "style", "rules.yaml"))
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    course = load_course(a.course)
    deck = a.deck or course["deck_order"][0]
    built = build_deck(course, deck)
    script = parse_script(course)
    rules = yaml.safe_load(open(a.rules, encoding="utf-8"))["rules"]
    reds, warns = [], []
    slides = [s for s in built["slides"] if s["type"] != "quiz"]
    for r in rules:
        pat = re.compile(re.escape(r["pattern"]) if r["kind"] == "phrase" else r["pattern"]) \
            if r["kind"] in ("phrase", "regex") else None
        sink = reds if r["level"] == "RED" else warns
        if r["kind"] == "count":
            n = sum(slide_text(s).count(r["pattern"]) for s in slides)
            if n > r["max"]:
                sink.append(f"{r['id']} {r['message']}：{n} 次")
            continue
        for s in slides:
            texts = []
            if r["scope"] in ("slide", "all"):
                texts.append(("投影片", slide_text(s)))
            if r["scope"] == "title":
                texts.append(("標題", strip_markup(s["title"])))
            if r["scope"] in ("notes", "all"):
                e = script.get(s["id"].split("~")[0])
                if e:
                    texts.append(("備註", "\n".join(e["jiang"].values()) + "\n".join(e["bullets"])))
            for where, t in texts:
                m = pat.search(t)
                if m:
                    sink.append(f"{r['id']} #{s['num']} {s['id']}（{where}）「{m.group(0)}」：{r['message']}")
    gloss = load_glossary(course.path("glossary"))
    wl = {x.lower() for x in course.get("bilingual_whitelist", [])}
    mode = bilingual_mode(course)
    if gloss:
        r2, w2 = check_bilingual_mode(built["slides"], gloss, wl, mode)
        reds += r2
        warns += w2
    elif mode != "off":
        warns.append(f"找不到 glossary：{course.path('glossary')}（中英對照未檢查）")
    if not a.quiet:
        for m in warns:
            print("[WARN]", m)
    for m in reds:
        print("[RED]", m)
    print(f"===== style_check：RED {len(reds)}、WARN {len(warns)}（{len(built['slides'])} 張，glossary {len(gloss)} 詞，中英對照 {mode}）=====")
    return 1 if reds else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

# -*- coding: utf-8 -*-
"""撰寫階段的自我檢查：對「一批撰寫結果 JSON」套用 style/rules.yaml、glossary 逐張中英對照、字數與條數上限。
不必先組裝素材池，撰寫代理寫完一批就能跑。

用法：python check_written.py --course immune --blueprint <blueprint.json> <batch.json> [<batch2.json> …]
輸出：每張的 RED／WARN；最後一行 JSON 摘要 {"red":n,"warn":n}。結束碼：有 RED 為 1。
檢查項：
  - rules.yaml 的 phrase／regex 規則（scope slide＝標題＋條列＋表格；title；notes＝notes＋handout）
  - glossary（依 course.yaml bilingual）：per_slide＝中文詞無英文、英文詞無中文、縮寫無中文、禁用變體；
    first_per_deck（預設）與 off＝只查禁用變體（首見率要整套才算得出，組裝後由 style_check.py 查）；國考題張除外
  - 可見字元 > char_red RED、> char_warn WARN（表格、封面、divider、國考題不算）
  - 條列 > 3 WARN、> 5 RED；flash／pair／robbins 說明 > 2 條 WARN；標題 > title_warn_chars WARN
  - 強調標記格式 [[藍:…]]；Markdown 殘留
  - 藍圖裡有、批次裡沒寫的 slug（或反之）
"""
import argparse
import json
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, load_course, strip_markup  # noqa: E402
from style_check import banned_variants, bilingual_mode, check_bilingual, load_glossary  # noqa: E402

MARK_OK = re.compile(r"\[\[(藍|紅|橘|青|灰)[:：][^\[\]]+?\]\]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", required=True)
    ap.add_argument("--blueprint", required=True)
    ap.add_argument("batches", nargs="+")
    ap.add_argument("--rules", default=os.path.join(ROOT, "style", "rules.yaml"))
    a = ap.parse_args()
    c = load_course(a.course)
    S = c.sizes
    bp = {s["slug"]: s for s in json.load(open(a.blueprint, encoding="utf-8"))["slides"]}
    rules = yaml.safe_load(open(a.rules, encoding="utf-8"))["rules"]
    gloss = load_glossary(c.path("glossary"))
    wl = {x.lower() for x in c.get("bilingual_whitelist", [])}
    mode = bilingual_mode(c)
    reds, warns = [], []
    slides = []
    for p in a.batches:
        for w in json.load(open(p, encoding="utf-8"))["slides"]:
            slides.append(w)
    for w in slides:
        sid = w["slug"]
        b = bp.get(sid)
        if not b:
            reds.append(f"{sid}：不在藍圖")
            continue
        typ = b["type"]
        bullets = [re.sub(r"^\s*-\s*", "", x) for x in (w.get("bullets") or [])]
        table = w.get("table_rows") or []
        text = strip_markup("\n".join([w.get("title", "")] + bullets + [c2 for r in table for c2 in r]))
        notes = "\n".join([w.get("notes") or ""] + list(w.get("handout") or []))
        for t in [w.get("title", "")] + bullets:
            if "[[" in MARK_OK.sub("", t) or "]]" in MARK_OK.sub("", t):
                reds.append(f"{sid}：強調標記格式錯「{t[:30]}」")
        if typ != "quiz":
            for r in rules:
                if r["kind"] not in ("phrase", "regex"):
                    continue
                pat = re.compile(re.escape(r["pattern"]) if r["kind"] == "phrase" else r["pattern"])
                targets = []
                if r["scope"] in ("slide", "all"):
                    targets.append(("投影片", text))
                if r["scope"] == "title":
                    targets.append(("標題", strip_markup(w.get("title", ""))))
                if r["scope"] in ("notes", "all"):
                    targets.append(("備註", notes))
                for where, t in targets:
                    m = pat.search(t)
                    if m:
                        (reds if r["level"] == "RED" else warns).append(
                            f"{sid}（{where}）{r['id']}「{m.group(0)}」：{r['message']}")
            fake = {"num": 0, "id": sid, "type": typ, "title": w.get("title", ""), "bullets": bullets, "table": table}
            chk = check_bilingual([fake], gloss, wl) if mode == "per_slide" else banned_variants([fake], gloss)
            reds += [x.replace("#0 ", "") for x in chk]
        if typ in ("quiz", "title", "divider"):
            continue
        body = strip_markup("".join([w.get("title", "")] + bullets))
        n = len(re.sub(r"\s", "", body))
        if n > S["char_red"]:
            reds.append(f"{sid}：可見字元 {n} > {S['char_red']}")
        elif n > S["char_warn"]:
            warns.append(f"{sid}：可見字元 {n} > {S['char_warn']}")
        if len(bullets) > 5:
            reds.append(f"{sid}：條列 {len(bullets)} 條 > 5")
        elif len(bullets) > 3:
            warns.append(f"{sid}：條列 {len(bullets)} 條（新寫的張 0–3 條）")
        if typ in ("flash", "pair", "robbins") and len(bullets) > 2:
            warns.append(f"{sid}：{typ} 版型說明 {len(bullets)} 條（最多 2）")
        if len(strip_markup(w.get("title", ""))) > S["title_warn_chars"]:
            warns.append(f"{sid}：標題 {len(strip_markup(w['title']))} 字")
        if typ == "table3" and not table:
            reds.append(f"{sid}：table3 沒有 table_rows")
    for m in warns:
        print("[WARN]", m)
    for m in reds:
        print("[RED]", m)
    print(json.dumps({"slides": len(slides), "red": len(reds), "warn": len(warns), "bilingual": mode}, ensure_ascii=False))
    return 1 if reds else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

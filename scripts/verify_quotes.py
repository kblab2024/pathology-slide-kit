# -*- coding: utf-8 -*-
"""逐字核對風格指南裡的引句：格式「原文」（語料代號 #張號），原文必須出現在 <語料>/decks/<代號>.json 該張的文字或備註裡。

用法：python verify_quotes.py [<指南資料夾或檔案> …]（預設 <工具包>/style/guide）
語料位置（common.corpus_dir）：環境變數 SLIDEKIT_CORPUS → <教材庫>/corpus → <工具包>/style/corpus。
語料（教師投影片逐張傾印）只在私有教材庫；找不到語料資料夾時直接報錯（結束碼 2）。
比對時忽略空白、換行記號（↵、⏎）與全半形括號差異；找不到該代號、該張，或原文不在該張，都列為 FAIL。
代稱：公開指南把第三人的真名換成代稱（例：同事甲）。<語料>/pseudonyms.tsv（只在私有教材庫；每行「真名<TAB>代稱」）
  存在時，比對前先把語料文字裡的真名換成代稱，所以引句裡的代稱照樣核對得到。
輸出每檔的通過／失敗數與失敗清單；最後一行 JSON 摘要。結束碼：有 FAIL 為 1。
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, corpus_dir  # noqa: E402

CORPUS = corpus_dir()
DECKS = os.path.join(CORPUS, "decks")
PAT = re.compile(r"「([^」]{2,300})」\s*[（(]\s*([0-9A-Za-z_一-鿿\-]+)\s*#\s*(\d+)\s*[）)]")
_cache = {}


def load_pseudonyms(corpus=CORPUS):
    """<語料>/pseudonyms.tsv →[(真名, 代稱)]，長的真名先換。"""
    p = os.path.join(corpus, "pseudonyms.tsv")
    if not os.path.exists(p):
        return []
    out = []
    for ln in open(p, encoding="utf-8"):
        ln = ln.rstrip("\r\n")
        if not ln.strip() or ln.startswith("#") or "\t" not in ln:
            continue
        real, alias = ln.split("\t", 1)
        if real.strip():
            out.append((real.strip(), alias.strip()))
    return sorted(out, key=lambda x: -len(x[0]))


PSEUDO = load_pseudonyms()


def pseudonymize(t):
    for real, alias in PSEUDO:
        t = t.replace(real, alias)
    return t


def norm(t):
    t = re.sub(r"\s+", "", (t or "").replace("↵", "").replace("⏎", "").replace(" / ", ""))
    return t.replace("（", "(").replace("）", ")").replace("：", ":").replace("，", ",")


def slide_texts(code):
    if code in _cache:
        return _cache[code]
    p = os.path.join(DECKS, code + ".json")
    if not os.path.exists(p):
        _cache[code] = None
        return None
    d = json.load(open(p, encoding="utf-8"))
    out = {}

    def walk(shs):
        for sh in shs:
            yield sh
            yield from walk(sh.get("children", []))
    for s in d["slides"]:
        parts = [s.get("title", ""), s.get("notes", "")]
        for sh in walk(s["shapes"]):
            parts += [p["text"] for p in sh.get("paras", [])]
            for row in sh.get("table", []):
                parts += [c["text"] for c in row]
        out[s["n"]] = norm(pseudonymize("\n".join(parts)))
    _cache[code] = out
    return out


def _rel(f):
    try:
        return os.path.relpath(f, ROOT)
    except ValueError:  # Windows 不同磁碟
        return f


def main():
    ap = argparse.ArgumentParser(description="逐字核對風格指南引句「原文」（語料代號 #張號）與語料傾印")
    ap.add_argument("targets", nargs="*", help="指南資料夾或 .md 檔（預設 <kit>/style/guide）")
    a = ap.parse_args()
    if not os.path.isdir(DECKS):
        print(f"找不到語料 {DECKS}：設 SLIDEKIT_CORPUS，或把 pathology-slide-materials（含 corpus/）放在工具包同層",
              file=sys.stderr)
        return 2
    print(f"語料：{DECKS}" + (f"（代稱對照 {len(PSEUDO)} 條）" if PSEUDO else ""))
    targets = a.targets or [os.path.join(ROOT, "style", "guide")]
    files = []
    for t in targets:
        files += glob.glob(os.path.join(t, "**", "*.md"), recursive=True) if os.path.isdir(t) else [t]
    tot_ok = tot_bad = 0
    for f in sorted(files):
        txt = open(f, encoding="utf-8").read()
        ok, bad = 0, []
        for m in PAT.finditer(txt):
            q, code, n = m.group(1), m.group(2), int(m.group(3))
            sl = slide_texts(code)
            if sl is None:
                bad.append(f"代號不存在 {code}：「{q[:30]}」")
            elif n not in sl:
                bad.append(f"{code} 沒有第 {n} 張：「{q[:30]}」")
            elif norm(q) not in sl[n]:
                bad.append(f"{code} #{n} 找不到原文：「{q[:40]}」")
            else:
                ok += 1
        tot_ok += ok
        tot_bad += len(bad)
        rel = _rel(f)
        print(f"{rel}: 通過 {ok}、失敗 {len(bad)}")
        for b in bad[:15]:
            print("   FAIL", b)
    print(json.dumps({"files": len(files), "ok": tot_ok, "fail": tot_bad}, ensure_ascii=False))
    return 1 if tot_bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

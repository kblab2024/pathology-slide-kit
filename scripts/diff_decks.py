# -*- coding: utf-8 -*-
"""比對兩份 dump_pptx.py 的 JSON（通常是「我的毛胚」→「教師親手改稿」），輸出逐張差異 Markdown。

對齊方式：以每張全文（去空白）做相似度配對（≥0.35 視為同一張），其餘為刪除／新增。
輸出段落：刪除的張、新增的張、順序（新#→原#）、對應張的變更（文字 diff、字級、圖片數、版面、備註）。
備註若帶「投影片 N｜」表頭，另列表頭張號，方便回灌到素材池 slug。

用法：python diff_decks.py <mine.json> <his.json> <out.md> [--range 1-101] [--layout <交件檔>_layout.json]
  --range：只取 mine 的第 a–b 張（例如毛胚 200 張只比前半）
  --layout：gen_pptx.py 交件時一起產的 <檔名>_layout.json；給了就在每個「原#N」後面標出素材池 slug，
            並多一段「新#→原#→slug」對照表，回灌時直接照 slug 改 pool.md（配對本身仍以全文相似度做，要人工確認）
"""
import argparse
import difflib
import json
import re
import sys


def walk(shapes):
    for sh in shapes:
        yield sh
        yield from walk(sh.get("children", []))


def texts(s):
    out = []
    for sh in walk(s["shapes"]):
        for p in sh.get("paras", []):
            out.append(p["text"].strip())
        for row in sh.get("table", []):
            out.append(" | ".join(c["text"].replace("\n", " ") for c in row))
    return [t for t in out if t]


def sizes(s):
    z = set()
    for sh in walk(s["shapes"]):
        for p in sh.get("paras", []):
            for r in p["runs"]:
                if r["sz"]:
                    z.add(r["sz"])
    return sorted(z)


def colored(s):
    out = []
    for sh in walk(s["shapes"]):
        for p in sh.get("paras", []):
            for r in p["runs"]:
                if r.get("col") and r["col"] not in ("000000", "1E2A35", "14263B", "3B3838") and r["t"].strip():
                    out.append(f"{r['col']}「{r['t'].strip()}」")
    return out


def key(s):
    return re.sub(r"\s", "", "".join(texts(s)))


def ratio(x, y):
    return difflib.SequenceMatcher(None, x, y).ratio()


def load_slugs(path):
    """_layout.json 的 slides {slug: {num: n}} → {n: slug}；拆張的「slug~2」照原樣保留。"""
    if not path:
        return {}
    d = json.load(open(path, encoding="utf-8"))
    return {v["num"]: k for k, v in (d.get("slides") or {}).items()}


def main():
    ap = argparse.ArgumentParser(description="逐張比對兩份 dump_pptx.py 傾印（我的毛胚 → 教師改稿），輸出 Markdown")
    ap.add_argument("mine", help="我交的版本的傾印 .json")
    ap.add_argument("his", help="他改後版本的傾印 .json")
    ap.add_argument("out", help="輸出的 .md")
    ap.add_argument("--range", default=None, help="只取 mine 的第 a-b 張，例 1-101")
    ap.add_argument("--layout", default=None, help="交件時 gen_pptx.py 產的 <檔名>_layout.json（標出每張的 slug）")
    args = ap.parse_args()
    a_path, b_path, out = args.mine, args.his, args.out
    rng = None
    if args.range:
        lo, hi = args.range.split("-")
        rng = (int(lo), int(hi))
    slug = load_slugs(args.layout)
    tag = (lambda n: f"（{slug[n]}）" if n in slug else "") if slug else (lambda n: "")
    A = json.load(open(a_path, encoding="utf-8"))
    B = json.load(open(b_path, encoding="utf-8"))
    sa = A["slides"] if not rng else [s for s in A["slides"] if rng[0] <= s["n"] <= rng[1]]
    sb = B["slides"]
    ka = [key(s) for s in sa]
    kb = [key(s) for s in sb]
    match, used = {}, set()
    for j, k in enumerate(kb):
        best, bi = 0, None
        for i, k0 in enumerate(ka):
            if i in used or not k0:
                continue
            r = ratio(k0, k)
            if r > best:
                best, bi = r, i
        if bi is not None and best >= 0.35:
            match[j] = (bi, best)
            used.add(bi)
    L = [f"# 改稿比對：{A['file']}（{len(sa)} 張）→ {B['file']}（{len(sb)} 張）", ""]
    deleted = [i for i in range(len(ka)) if i not in used]
    L.append(f"## 他刪除的張（{len(deleted)} 張）")
    for i in deleted:
        s = sa[i]
        L.append(f"- 原#{s['n']}{tag(s['n'])} [{s['layout']}] 圖{s['pics']}「{s['title'][:60]}」｜{' ／ '.join(texts(s))[:200]}")
    added = [j for j in range(len(sb)) if j not in match]
    L += ["", f"## 他新增的張（{len(added)} 張）"]
    for j in added:
        s = sb[j]
        L.append(f"- 新#{s['n']} [{s['layout']}] 圖{s['pics']} 字級{sizes(s)}\n  文字：{' ／ '.join(texts(s))[:500]}"
                 + (f"\n  強調色：{'；'.join(colored(s))[:300]}" if colored(s) else "")
                 + (f"\n  備註：{s['notes'][:300]}" if s["notes"].strip() else ""))
    L += ["", "## 順序（新#→原#）", " ".join(f"{sb[j]['n']}→{sa[match[j][0]]['n']}" for j in sorted(match))]
    if slug:
        L += ["", "## 新#→原#→slug（回灌用；相似度 < 0.6 的列要人工確認）", "", "| 新# | 原# | slug | 相似 |", "|---|---|---|---|"]
        L += [f"| {sb[j]['n']} | {sa[match[j][0]]['n']} | {slug.get(sa[match[j][0]]['n'], '（layout 查無）')} | {match[j][1]:.2f} |"
              for j in sorted(match)]
    L += ["", "## 對應張的變更"]
    same = 0
    for j in sorted(match):
        i, r = match[j]
        a, b = sa[i], sb[j]
        ch = []
        ta, tb = texts(a), texts(b)
        if ta != tb:
            d = [l for l in difflib.unified_diff(ta, tb, lineterm="", n=0)
                 if l[:1] in "+-" and l[:3] not in ("+++", "---")]
            ch.append("文字：\n" + "\n".join("    " + l for l in d))
        if a["notes"].strip() != b["notes"].strip():
            ch.append("備註：有變更")
        if sizes(a) != sizes(b):
            ch.append(f"字級：{sizes(a)} → {sizes(b)}")
        if a["pics"] != b["pics"]:
            ch.append(f"圖片數：{a['pics']} → {b['pics']}")
        if colored(a) != colored(b):
            ch.append(f"強調色：{'；'.join(colored(a))[:200]} → {'；'.join(colored(b))[:200]}")
        if a["layout"] != b["layout"]:
            ch.append(f"版面：{a['layout']} → {b['layout']}")
        if ch:
            L.append(f"### 新#{b['n']} ← 原#{a['n']}{tag(a['n'])}（相似 {r:.2f}）「{b['title'][:50]}」\n" + "\n".join(ch) + "\n")
        else:
            same += 1
    L.insert(2, f"統計：刪 {len(deleted)}、增 {len(added)}、對應 {len(match)}（其中原樣 {same}、有改 {len(match) - same}）\n")
    open(out, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(f"deleted {len(deleted)} added {len(added)} matched {len(match)} unchanged {same}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

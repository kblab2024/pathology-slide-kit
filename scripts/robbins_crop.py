# -*- coding: utf-8 -*-
"""從 Robbins 掃描 PDF 自動切出每張圖（Fig.）與表（TABLE），並產 contact sheet 供目視核對。

找圖說：讀 render_pdf_pages.py 產的 Tesseract TSV（頁圖 pNN_PPP.png 或 .jpg，200dpi），找行首「Fig. N.M」「TABLE N.M」。
（PDF 文字層是 PUA 自訂編碼的版本，例如 lung 的掃描檔，要先解碼 chr(288-(code&0xff)) 再找圖說；本工具未收錄該模式。）
切圖規則（Robbins 版面：兩欄內文、圖在圖說正上方、表在表題正下方且底色為淡黃）：
  圖：水平範圍依圖說寬度判定（>55% 頁寬＝跨欄，否則所在欄）；上緣＝圖說上方最近一條「內文整行」（≥6 字詞且寬 ≥ 欄寬 80%）的下緣；
      下緣＝圖說上緣。再裁掉白邊，以 --dpi（預設 300）從 PDF 重新算圖。多面板以白色縫（≥12px）切成 _1、_2…。
  表：從表題往下，一直到淡黃底色結束。
  圖說在圖側（例：Fig 6.10）或反白（例：Fig 6.35）等特例：用 --ovr JSON 指定 {"6.10": [pdf頁, x0, y0, x1, y1]}（200dpi 像素座標）。
  --ovr 其他鍵：
    "T6.3": [pdf頁, x0, y0, x1, y1]          表格手動座標（含表題行、表註；自動偵測對跨欄表常切成半邊）
    "6.24": [pdf頁, x0, y0, x1, y1, [[mx0, my0, mx1, my1], …]]  第 6 元素＝要塗白的矩形（例：圖說嵌在面板旁）
    "_drop_panels": ["fig6_1_2.png", …]      自動分割出的無意義碎片，不輸出也不記入 index
    "_panel_gap": {"6.24": 4}                照片拼版圖面板間白縫窄（~6px）：改遞迴切割、白縫門檻 4px
    "_panels": {"6.33": [[x0, y0, x1, y1], …]}  手動面板座標（圖文混排、標籤框與圖分離時）
    "_captions": {"6.35": "Fig. 6.35 …"}     OCR 讀不到的圖說（反白字）補進 index.json
  手動座標的圖同樣會自動分面板；輸出資料夾裡不在 index 內的 fig*/table* 舊檔會被刪除。
輸出：<out>/fig{章}_{號}.png、fig…_{k}.png（面板）、table{章}_{號}.png、index.json、contact_*.png；並列出找不到的圖號。
沒有 PDF（例如雲端只有教材庫的頁圖）時，直接從 200dpi 頁圖裁切，--dpi 無效，index.json 記 "dpi": 200。

用法：python robbins_crop.py --course immune --chapter 6 --out <資料夾> [--expect 46] [--ovr ovr.json] [--dpi 300]
      python robbins_crop.py --pdf robbinsimmune.pdf --pages-dir <頁圖資料夾> --chapter 6 --offset 166 --out <資料夾>
  --course     從 course.yaml 的 textbook.pdf、textbook.pages_dir、textbook.page_offset 補齊沒給的 --pdf／--pages-dir／--offset
  --pages-dir  頁圖＋TSV 資料夾（pNN_PPP.png|jpg＋pNN_PPP.tsv）
  --out 裡不在 index 內的 fig*/table* 舊檔會被刪除：不要指到別的用途的資料夾。
"""
import argparse
import csv
import glob
import json
import os
import re
import sys

import fitz
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
BASE_DPI = 200
PAGE_EXTS = (".png", ".jpg", ".jpeg")


def page_file(pages_dir, stem):
    """頁圖檔路徑：stem＋.png／.jpg／.jpeg，找不到回傳 None。"""
    for ext in PAGE_EXTS:
        p = os.path.join(pages_dir, stem + ext)
        if os.path.isfile(p):
            return p
    return None


def page_stem(pages_dir, pno):
    """PDF 頁 pno 對應的頁圖 stem（pNN_PPP，不含 _a／_b 半頁）。"""
    for p in sorted(glob.glob(os.path.join(pages_dir, f"p{pno:02d}_*"))):
        stem, ext = os.path.splitext(os.path.basename(p))
        if ext.lower() in PAGE_EXTS and re.fullmatch(r"p\d+_\d+", stem):
            return stem
    raise FileNotFoundError(f"找不到第 {pno} 頁的頁圖（p{pno:02d}_PPP.png|jpg）：{pages_dir}")


class PageSource:
    """切圖來源：有 PDF 就以 dpi 從 PDF 重新算圖；沒有 PDF 就直接裁 200dpi 頁圖（jpg／png）。"""

    def __init__(self, pdf, pages_dir):
        self.doc = fitz.open(pdf) if pdf and os.path.isfile(pdf) else None
        self.pages_dir = pages_dir
        self._cache = (None, None)

    def dpi(self, want):
        return want if self.doc is not None else BASE_DPI

    def page(self, pno):
        if self._cache[0] != pno:
            self._cache = (pno, Image.open(page_file(self.pages_dir, page_stem(self.pages_dir, pno))).convert("RGB"))
        return self._cache[1]

    def clip(self, pno, box, dpi):
        """回傳 PIL RGB 圖（box 為 200dpi 頁面座標）。"""
        if self.doc is None:
            return self.page(pno).crop(tuple(int(round(v)) for v in box))
        k = 72.0 / BASE_DPI
        r = fitz.Rect(box[0] * k, box[1] * k, box[2] * k, box[3] * k)
        pix = self.doc[pno - 1].get_pixmap(dpi=dpi, clip=r)
        return Image.frombytes("RGB" if pix.n < 4 else "RGBA", (pix.width, pix.height), pix.samples).convert("RGB")


def read_tsv(path):
    lines = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        rd = csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        for r in rd:
            if r.get("level") != "5" or not (r.get("text") or "").strip():
                continue
            key = (int(r["block_num"]), int(r["par_num"]), int(r["line_num"]))
            w = {"t": r["text"], "x0": int(r["left"]), "y0": int(r["top"]),
                 "x1": int(r["left"]) + int(r["width"]), "y1": int(r["top"]) + int(r["height"]),
                 "conf": float(r["conf"])}
            lines.setdefault(key, []).append(w)
    out = []
    for k, ws in lines.items():
        ws.sort(key=lambda w: w["x0"])
        out.append({"key": k, "words": ws, "text": " ".join(w["t"] for w in ws),
                    "x0": min(w["x0"] for w in ws), "x1": max(w["x1"] for w in ws),
                    "y0": min(w["y0"] for w in ws), "y1": max(w["y1"] for w in ws),
                    "conf": sum(w["conf"] for w in ws) / len(ws)})
    return sorted(out, key=lambda l: (l["y0"], l["x0"]))


def caption_blocks(lines, chapter):
    """回傳 [(kind, 編號, 圖說行們)]。kind = fig | table。"""
    pat_fig = re.compile(r"^Fig\.?$", re.I)
    pat_num = re.compile(r"^%d\.(\d+)\.?$" % chapter)
    out = []
    for i, l in enumerate(lines):
        ws = l["words"]
        if len(ws) < 2:
            continue
        kind = None
        if pat_fig.match(ws[0]["t"]) and pat_num.match(ws[1]["t"]):
            kind = "fig"
        elif ws[0]["t"].upper() == "TABLE" and pat_num.match(ws[1]["t"]):
            kind = "table"
        if not kind:
            continue
        num = f"{chapter}.{pat_num.match(ws[1]['t']).group(1)}"
        blk = l["key"][0]
        cap = [x for x in lines if x["key"][0] == blk and x["y0"] >= l["y0"] - 5]
        # 同一 block 內圖說下方連續的行（行距 < 1.8 行高）
        cap.sort(key=lambda x: x["y0"])
        keep = [cap[0]]
        for x in cap[1:]:
            if x["y0"] - keep[-1]["y1"] < 1.8 * (keep[-1]["y1"] - keep[-1]["y0"]):
                keep.append(x)
        out.append((kind, num, keep))
    return out


def is_body_line(l, colw):
    """內文整行：≥6 字詞、寬 ≥ 欄寬 80%、且至少 5 個 ≥3 字母的英文字（排除圖內座標軸數字與標籤）。"""
    alpha = sum(1 for w in l["words"] if re.fullmatch(r"[A-Za-z][A-Za-z,.;:()'\-]{2,}", w["t"]))
    return len(l["words"]) >= 6 and (l["x1"] - l["x0"]) >= 0.8 * colw and l["conf"] >= 60 and alpha >= 5


def trim(img, box, thr=250, pad=6):
    x0, y0, x1, y1 = box
    crop = img.crop(box).convert("L")
    w, h = crop.size
    px = crop.load()
    rows = [y for y in range(h) if any(px[x, y] < thr for x in range(0, w, 2))]
    cols = [x for x in range(w) if any(px[x, y] < thr for y in range(0, h, 2))]
    if not rows or not cols:
        return None
    return (max(0, x0 + cols[0] - pad), max(0, y0 + rows[0] - pad),
            min(img.width, x0 + cols[-1] + pad), min(img.height, y0 + rows[-1] + pad))


def white_gaps(img, box, axis, min_gap=12, thr=250):
    """回傳沿 axis（'x' 或 'y'）的白縫中點列表。"""
    crop = img.crop(box).convert("L")
    w, h = crop.size
    px = crop.load()
    n = w if axis == "x" else h
    blank = []
    for i in range(n):
        if axis == "x":
            b = all(px[i, y] >= thr for y in range(0, h, 2))
        else:
            b = all(px[x, i] >= thr for x in range(0, w, 2))
        blank.append(b)
    gaps, run = [], 0
    for i, b in enumerate(blank + [False]):
        if b:
            run += 1
        else:
            if run >= min_gap and i - run > 0 and i < n:
                gaps.append(i - run // 2)
            run = 0
    return gaps


def split_rec(img, box, gap, minarea, depth=0):
    """遞迴切割（先縱縫後橫縫，切到沒有白縫為止）；照片拼版圖用。白縫門檻放寬到 240 以容忍 JPEG 雜訊。"""
    for axis in ("x", "y") if depth < 6 else ():
        g = white_gaps(img, box, axis, min_gap=gap, thr=240)
        if not g:
            continue
        n = box[2] - box[0] if axis == "x" else box[3] - box[1]
        cuts = [0] + g + [n]
        subs = []
        for a, b in zip(cuts, cuts[1:]):
            sub = (box[0] + a, box[1], box[0] + b, box[3]) if axis == "x" else (box[0], box[1] + a, box[2], box[1] + b)
            sub = trim(img, sub, thr=240, pad=2)
            if sub:
                subs.append(sub)
        if len(subs) < 2:
            continue
        out = []
        for sub in subs:
            out += split_rec(img, sub, gap, minarea, depth + 1)
        return out
    return [box] if (box[2] - box[0]) * (box[3] - box[1]) > minarea else []


def reading_order(boxes, tol=60):
    """面板依閱讀順序（由上而下分列、列內由左而右）排序，使 _1、_2… 對應 A、B…。"""
    rows = []
    for b in sorted(boxes, key=lambda b: b[1]):
        if rows and b[1] - rows[-1][0][1] < tol:
            rows[-1].append(b)
        else:
            rows.append([b])
    return [b for r in rows for b in sorted(r, key=lambda b: b[0])]


def panels(img, box, gap=None):
    """預設：先縱縫（≥12px）再橫縫（≥14px）切一層。gap 有值（ovr 的 _panel_gap）＝照片拼版圖，改用遞迴切割。"""
    x0, y0, x1, y1 = box
    if gap:
        out = split_rec(img, tuple(box), gap, 0.04 * (x1 - x0) * (y1 - y0))
        return reading_order(out) if len(out) >= 2 else []
    out = []
    xs = [0] + white_gaps(img, box, "x", min_gap=gap or 12) + [x1 - x0]
    for a, b in zip(xs, xs[1:]):
        sub = trim(img, (x0 + a, y0, x0 + b, y1))
        if not sub:
            continue
        ys = [0] + white_gaps(img, sub, "y", min_gap=gap or 14) + [sub[3] - sub[1]]
        for c, d in zip(ys, ys[1:]):
            s2 = trim(img, (sub[0], sub[1] + c, sub[2], sub[1] + d))
            if s2 and (s2[2] - s2[0]) * (s2[3] - s2[1]) > 0.06 * (x1 - x0) * (y1 - y0):
                out.append(s2)
    return out if len(out) >= 2 else []


def table_region(img, cap, W):
    """表題往下到淡黃底色結束。"""
    y = cap[-1]["y1"] + 2
    x0, x1 = 60, W - 60
    im = img.convert("RGB")
    px = im.load()
    tinted_seen, gap, last = False, 0, y
    for yy in range(y, img.height - 40):
        cnt = 0
        tot = 0
        for xx in range(x0, x1, 8):
            r, g, b = px[xx, yy]
            tot += 1
            if r > 200 and g > 180 and b < 225 and (r - b) > 25:
                cnt += 1
        if cnt / tot > 0.35:
            tinted_seen, gap, last = True, 0, yy
        elif tinted_seen:
            gap += 1
            if gap > 25:
                break
    if not tinted_seen:
        return None
    return (x0, cap[0]["y0"] - 8, x1, last + 4)


def save_clip(src, pno, box, dpi, path, masks=()):
    """從 PDF 以 dpi 重新算圖（沒有 PDF 則裁頁圖）存檔；masks（200dpi 頁面座標）範圍塗白。回傳 [寬, 高]。"""
    im = src.clip(pno, box, src.dpi(dpi))
    if masks:
        from PIL import ImageDraw
        s = src.dpi(dpi) / BASE_DPI
        dr = ImageDraw.Draw(im)
        for mx0, my0, mx1, my1 in masks:
            dr.rectangle([(mx0 - box[0]) * s, (my0 - box[1]) * s, (mx1 - box[0]) * s, (my1 - box[1]) * s],
                         fill="white")
    im.save(path)
    return [im.width, im.height]


def page_image(pages_dir, pno, masks=()):
    img = Image.open(page_file(pages_dir, page_stem(pages_dir, pno))).convert("RGB")
    if masks:
        from PIL import ImageDraw
        dr = ImageDraw.Draw(img)
        for m in masks:
            dr.rectangle(list(m), fill="white")
    return img


def save_panels(src, pno, img, box, key, a, drop, masks=()):
    """分面板並存檔：ovr 的 _panels 有手動面板座標就用它，否則自動切（_panel_gap 可調白縫寬）。
    _drop_panels 列出的碎片不輸出。編號維持原序（刪掉的號碼留空）。"""
    num = key[3:].replace("_", ".")
    if num in a.panel_boxes:
        ps = [trim(img, tuple(b), pad=2) or tuple(b) for b in a.panel_boxes[num]]
    else:
        ps = panels(img, box, a.panel_gap.get(num))
    out = []
    for i, pb in enumerate(ps, 1):
        name = f"{key}_{i}.png"
        if name in drop:
            continue
        px = save_clip(src, pno, pb, a.dpi, os.path.join(a.out, name), masks)
        out.append({"file": name, "box200": list(pb), "px": px})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", default=None)
    ap.add_argument("--pdf", default=None)
    ap.add_argument("--pages-dir", default=None)
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--offset", type=int, default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect", type=int, default=0)
    ap.add_argument("--ovr", default=None)
    ap.add_argument("--dpi", type=int, default=300)
    a = ap.parse_args()
    if a.course:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from common import load_course
        c = load_course(a.course)
        a.pdf = a.pdf or c.textbook_path("pdf")
        a.pages_dir = a.pages_dir or c.textbook_path("pages_dir")
        if a.offset is None and (c.get("textbook") or {}).get("page_offset") is not None:
            a.offset = int(c["textbook"]["page_offset"])
    if not a.pages_dir or not os.path.isdir(a.pages_dir):
        ap.error(f"找不到頁圖資料夾：{a.pages_dir}（給 --pages-dir，或 course.yaml 的 textbook.pages_dir）")
    if a.offset is None:
        ap.error("缺少 --offset（或 course.yaml 的 textbook.page_offset）")
    os.makedirs(a.out, exist_ok=True)
    src = PageSource(a.pdf, a.pages_dir)
    if src.doc is None:
        print(f"[warn] 沒有 PDF（{a.pdf}），改從 {BASE_DPI}dpi 頁圖裁切；--dpi 無效", file=sys.stderr)
    ovr = json.load(open(a.ovr, encoding="utf-8")) if a.ovr else {}
    drop = set(ovr.get("_drop_panels", []))
    a.panel_gap = ovr.get("_panel_gap", {})
    a.panel_boxes = ovr.get("_panels", {})
    a.captions = ovr.get("_captions", {})
    ovr = {k: v for k, v in ovr.items() if not k.startswith("_")}
    index = {}
    cap_text = {}
    for tsv in sorted(glob.glob(os.path.join(a.pages_dir, "p*_*.tsv"))):
        stem = os.path.basename(tsv)[:-4]
        pno = int(stem.split("_")[0][1:])
        pf = page_file(a.pages_dir, stem)
        if not pf:
            print(f"[warn] {stem}.tsv 沒有對應的頁圖（.png／.jpg），略過", file=sys.stderr)
            continue
        img = Image.open(pf)
        W = img.width
        colw = W / 2 - 130
        lines = read_tsv(tsv)
        caps = caption_blocks(lines, a.chapter)
        cap_bottoms = [c[2][-1]["y1"] for c in caps]
        for kind, num, cap in caps:
            key = ("fig" if kind == "fig" else "table") + num.replace(".", "_")
            cap_text.setdefault(key, " ".join(l["text"] for l in cap)[:600])
            if (kind == "fig" and num in ovr) or (kind == "table" and "T" + num in ovr):
                continue
            cx0, cx1 = min(l["x0"] for l in cap), max(l["x1"] for l in cap)
            cy0 = min(l["y0"] for l in cap)
            if kind == "table":
                box = table_region(img, cap, W)
                if box and cx0 >= W / 2 - 40:
                    box = (int(W / 2 - 10), box[1], box[2], box[3])
                elif box and cx1 < W / 2 + 40:
                    box = (box[0], box[1], int(W / 2 + 10), box[3])
            else:
                if cx1 - cx0 > 0.55 * W:
                    fx0, fx1 = 70, W - 70
                elif cx0 >= W / 2 - 40:
                    fx0, fx1 = W / 2 - 10, W - 70
                else:
                    fx0, fx1 = 70, W / 2 + 10
                above = [l for l in lines if l["y1"] < cy0 - 4 and l["x1"] > fx0 and l["x0"] < fx1
                         and is_body_line(l, colw)]
                cand = [l["y1"] for l in above if l["y1"] < cy0 - 120]
                cand += [b for b in cap_bottoms if b < cy0 - 120]
                top = max(cand + [215]) + 10
                box = (int(fx0), int(top), int(fx1), int(cy0 - 4))
                if box[3] - box[1] < 60:
                    box = None
            if not box:
                index[key] = {"kind": kind, "num": num, "page_pdf": pno, "page": pno + a.offset, "error": "no region"}
                continue
            tb = trim(img, box) or box
            out = os.path.join(a.out, key + ".png")
            px = save_clip(src, pno, tb, a.dpi, out)
            rec = {"kind": kind, "num": num, "page_pdf": pno, "page": pno + a.offset, "box200": tb,
                   "file": os.path.basename(out), "px": px, "dpi": src.dpi(a.dpi),
                   "caption": " ".join(l["text"] for l in cap)[:600]}
            if kind == "fig":
                rec["panels"] = save_panels(src, pno, img, tb, key, a, drop)
            old = index.get(key)
            if old and "px" in old and old["px"][0] * old["px"][1] > rec["px"][0] * rec["px"][1]:
                continue
            index[key] = rec
    for num, spec in ovr.items():
        kind = "table" if num.startswith("T") else "fig"
        num = num.lstrip("T")
        key = kind + num.replace(".", "_")
        pno, box, masks = spec[0], tuple(spec[1:5]), [tuple(m) for m in (spec[5] if len(spec) > 5 else [])]
        img = page_image(a.pages_dir, pno, masks)
        tb = trim(img, box) or box
        px = save_clip(src, pno, tb, a.dpi, os.path.join(a.out, key + ".png"), masks)
        index[key] = {"kind": kind, "num": num, "page_pdf": pno, "page": pno + a.offset,
                      "box200": list(tb), "file": key + ".png", "px": px, "dpi": src.dpi(a.dpi),
                      "caption": cap_text.get(key) or a.captions.get(("T" if kind == "table" else "") + num, ""),
                      "ovr": True}
        if masks:
            index[key]["masks200"] = [list(m) for m in masks]
        if kind == "fig":
            index[key]["panels"] = save_panels(src, pno, img, tb, key, a, drop, masks)
    keep = {v["file"] for v in index.values() if "file" in v}
    keep |= {p["file"] for v in index.values() for p in v.get("panels", [])}
    for f in os.listdir(a.out):
        if re.fullmatch(r"(fig|table)\d+_\d+(_\w+)?\.png", f) and f not in keep:
            os.remove(os.path.join(a.out, f))
    json.dump(index, open(os.path.join(a.out, "index.json"), "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    figs = sorted(int(k.split("_")[1]) for k, v in index.items() if v["kind"] == "fig" and "file" in v)
    tabs = sorted(int(k.split("_")[1]) for k, v in index.items() if v["kind"] == "table" and "file" in v)
    print(f"圖 {len(figs)} 張、表 {len(tabs)} 張")
    if a.expect:
        miss = [n for n in range(1, a.expect + 1) if n not in figs]
        print("找不到的圖：", miss)
    errs = [k for k, v in index.items() if "error" in v]
    if errs:
        print("有圖說但切不到範圍：", errs)
    write_list(a.out, index)
    contact(a.out, index)


AUTO_MARK = "<!-- robbins_crop.py 自動產生；手改前先把這一行刪掉，否則下次重跑會蓋掉 -->"


def write_list(outdir, index):
    """圖片清單.md：給藍圖代理找圖用（檔案、圖號、印刷頁、面板、圖說開頭）。
    已有手寫的圖片清單.md（第一行不是 AUTO_MARK）時不覆蓋，改寫 圖片清單_auto.md。"""
    items = [(k, v) for k, v in sorted(index.items(), key=lambda kv: (kv[1]["kind"], float(kv[1]["num"].split(".")[1])))
             if "file" in v]
    L = [AUTO_MARK, "", "# 教科書切圖清單", "",
         "圖說只取開頭，供找圖；投影片上的出處寫「Robbins Fig. N.M」，不要照抄圖說原文。", "",
         "| 檔案 | 圖表 | 印刷頁 | 面板 | 圖說（開頭） |", "|---|---|---|---|---|"]
    for k, v in items:
        label = ("Table " if v["kind"] == "table" else "Fig. ") + v["num"]
        panels = "、".join(p["file"] for p in v.get("panels", [])) or ""
        cap = re.sub(r"\s+", " ", v.get("caption") or "")[:80].replace("|", "／")
        L.append(f"| {v['file']} | {label} | {v.get('page', '')} | {panels} | {cap} |")
    p = os.path.join(outdir, "圖片清單.md")
    if os.path.exists(p):
        first = open(p, encoding="utf-8").readline().strip()
        if first != AUTO_MARK:
            p = os.path.join(outdir, "圖片清單_auto.md")
            print("已有手寫的 圖片清單.md，不覆蓋；自動清單寫到", p)
    open(p, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")


def contact(outdir, index, per=12, cell=420):
    items = [(k, v) for k, v in sorted(index.items(), key=lambda kv: (kv[1]["kind"], float(kv[1]["num"].split(".")[1])))
             if "file" in v]
    for s in range(0, len(items), per):
        chunk = items[s:s + per]
        cols = 4
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * (cell + 30)), "white")
        from PIL import ImageDraw
        dr = ImageDraw.Draw(sheet)
        for i, (k, v) in enumerate(chunk):
            im = Image.open(os.path.join(outdir, v["file"])).convert("RGB")
            im.thumbnail((cell - 10, cell - 10))
            x, y = (i % cols) * cell, (i // cols) * (cell + 30)
            sheet.paste(im, (x + 5, y + 30))
            dr.text((x + 5, y + 5), f"{k} p{v['page']} panels={len(v.get('panels', []))}", fill=(200, 0, 0))
        sheet.save(os.path.join(outdir, f"contact_{s // per + 1:02d}.png"))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

# -*- coding: utf-8 -*-
r"""實排檢查：拿 PPTX 與它算出來的 PDF（LibreOffice 或 PowerPoint），量每個文字框的字實際排在哪裡。

用法：python check_render.py <in.pptx> <in.pdf> [--json <out.json>] [--warn-pt 2]
  RED   框架圖格子的字超出圓角框；兩段字互相壓到（例：條列壓到資料來源行、圖說壓到出處）；字超出投影片
  WARN  框架圖格子的字離格子上下邊不到 --warn-pt（預設 2 pt，看起來貼邊）；字超出自己的文字框 3 pt 以上但沒壓到別的字
  （表格的格子只用來配對，不查溢出：LibreOffice 的表格列高比 PowerPoint 略高）
結束碼：有 RED 就 1，否則 0。

為什麼要有：gen_pptx 的 check_deck 是估算（n_lines × line_h），框架圖格子、粗體節點格會少估；
export_pdf.py 的 LibreOffice 路徑斷行與 PowerPoint 相同（2026-10-20 對照過），所以量 PDF 就是量實排。
表格（graphicFrame）不逐格量（LibreOffice 的表格列高比 PowerPoint 略高），只查有沒有壓到別的字。
"""
import argparse
import json
import re
import sys
import unicodedata

import fitz
from pptx import Presentation
from pptx.util import Emu

EMU_PT = 12700.0


def norm(t):
    t = unicodedata.normalize("NFKC", t or "")
    return re.sub(r"\s+", "", t)


def shape_rects(slide):
    """回傳 [(kind, text, x0, y0, x1, y1, anchor)]，單位 pt。kind：text／box（文字框底下有圓角框）／credit。"""
    out = []

    def walk(shapes):
        for sh in shapes:
            if sh.shape_type == 6:  # group
                walk(sh.shapes)
                continue
            if getattr(sh, "has_table", False) and sh.has_table:
                # 表格的每一格也當成框（位置照設定的欄寬、列高；實排列高可能較高），只用來把字配對到正確的格子，不查溢出
                y = sh.top / EMU_PT
                for row in sh.table.rows:
                    x = sh.left / EMU_PT
                    for j, cell in enumerate(row.cells):
                        w = sh.table.columns[j].width / EMU_PT
                        if cell.text.strip():
                            out.append(["cell", cell.text, x, y, x + w, y + row.height / EMU_PT, ""])
                        x += w
                    y += row.height / EMU_PT
                continue
            if not getattr(sh, "has_text_frame", False) or not sh.text_frame.text.strip():
                continue
            x0, y0 = sh.left / EMU_PT, sh.top / EMU_PT
            x1, y1 = x0 + sh.width / EMU_PT, y0 + sh.height / EMU_PT
            txt = sh.text_frame.text
            kind = "credit" if txt.lstrip().startswith(("資料來源", "圖：")) and "資料來源" in txt else "text"
            anchor = str(sh.text_frame.vertical_anchor or "")
            out.append([kind, txt, x0, y0, x1, y1, anchor])

    walk(slide.shapes)
    # 底下有圓角框（框架圖格子）的文字框標成 box：圓角框比文字框各邊大約 0.03–0.07 in
    rects = [(sh.left / EMU_PT, sh.top / EMU_PT, (sh.left + sh.width) / EMU_PT, (sh.top + sh.height) / EMU_PT)
             for sh in slide.shapes if sh.shape_type == 1 and "Rounded" in sh.name]
    for r in out:
        for (a, b, c, d) in rects:
            if a - 0.5 <= r[2] <= a + 8 and c - 8 <= r[4] <= c + 0.5 and b - 0.5 <= r[3] <= b + 4 and d - 4 <= r[5] <= d + 0.5:
                r[0] = "box"
                r.append((a, b, c, d))
                break
    return out


def pdf_lines(page):
    res = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            t = "".join(sp["text"] for sp in ln["spans"])
            if norm(t):
                # 用字的實際高度（span 的 bbox 含行距上下緣）：取 size 估字身，置中於 bbox
                x0, y0, x1, y1 = ln["bbox"]
                res.append({"t": t, "n": norm(t), "bbox": (x0, y0, x1, y1),
                            "size": max(sp["size"] for sp in ln["spans"])})
    return res


def assign(lines, shapes):
    """每一行配給文字含這一行、水平範圍蓋住它、而且垂直位置在框內或框邊 40 pt 以內的文字框（多個時取垂直距離最近的）。
    表格（graphicFrame）的字不在 shapes 裡，配不到就是 None，只參加「兩段字互相壓到」的檢查。
    （2026-10-20：原本只看文字與水平範圍，表頭與標題、引言同字時會配錯，報假的 WARN。）"""
    for ln in lines:
        x0, y0, x1, y1 = ln["bbox"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        best, bd = None, 40.0
        for k, sh in enumerate(shapes):
            if not (sh[2] - 4 <= cx <= sh[4] + 4):
                continue
            if ln["n"] not in norm(sh[1]):
                continue
            d = max(0.0, sh[3] - cy, cy - sh[5])
            if d < bd:
                best, bd = k, d
        ln["shape"] = best


def check(pptx, pdf, warn_pt=2.0):
    prs = Presentation(pptx)
    doc = fitz.open(pdf)
    W, H = prs.slide_width / EMU_PT, prs.slide_height / EMU_PT
    issues = []
    for i, (slide, page) in enumerate(zip(prs.slides, doc), 1):
        sx, sy = page.rect.width / W, page.rect.height / H
        shapes = shape_rects(slide)
        lines = pdf_lines(page)
        for ln in lines:  # PDF 座標換成 PPTX 的 pt
            x0, y0, x1, y1 = ln["bbox"]
            ln["bbox"] = (x0 / sx, y0 / sy, x1 / sx, y1 / sy)
        assign(lines, shapes)
        for ln in lines:  # 字身：行框上下各扣 (行框高 − 字級) / 2，避免把字型的上下緣留白當成溢出
            x0, y0, x1, y1 = ln["bbox"]
            pad = max(0.0, (y1 - y0 - ln["size"]) / 2)
            ln["ink"] = (x0, y0 + pad, x1, y1 - pad)
        for k, sh in enumerate(shapes):
            mine = [ln for ln in lines if ln.get("shape") == k]
            if not mine:
                continue
            top, bot = min(ln["ink"][1] for ln in mine), max(ln["ink"][3] for ln in mine)
            label = re.sub(r"\s+", " ", sh[1])[:24]
            if sh[0] == "box":
                a, b, c, d = sh[7]
                if top < b - 1.0 or bot > d + 1.0:
                    issues.append({"slide": i, "level": "RED", "what": "字超出框架圖格子", "text": label,
                                   "over_pt": round(max(b - top, bot - d), 1)})
                elif min(top - b, d - bot) < warn_pt:
                    issues.append({"slide": i, "level": "WARN", "what": "格子的字貼邊", "text": label,
                                   "gap_pt": round(min(top - b, d - bot), 1)})
            elif sh[0] == "text" and (top < sh[3] - 3 or bot > sh[5] + 3):
                issues.append({"slide": i, "level": "WARN", "what": "字超出自己的文字框（沒壓到別的字）", "text": label,
                               "over_pt": round(max(sh[3] - top, bot - sh[5]), 1)})
            if bot > H + 0.5 or top < -0.5:
                issues.append({"slide": i, "level": "RED", "what": "字超出投影片", "text": label})
        # 不同文字框（或表格）的字互相壓到
        for p_, q in [(p_, q) for p_ in range(len(lines)) for q in range(p_ + 1, len(lines))]:
            A, B = lines[p_], lines[q]
            if A.get("shape") == B.get("shape") and A.get("shape") is not None:
                continue
            ax0, ay0, ax1, ay1 = A["ink"]
            bx0, by0, bx1, by1 = B["ink"]
            ov_x = min(ax1, bx1) - max(ax0, bx0)
            ov_y = min(ay1, by1) - max(ay0, by0)
            if ov_x > 2 and ov_y > 1.5:
                issues.append({"slide": i, "level": "RED", "what": "兩段字互相壓到",
                               "text": A["t"][:16] + "／" + B["t"][:16], "over_pt": round(ov_y, 1)})
    return issues, len(prs.slides)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        fitz.TOOLS.mupdf_display_errors(False)
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx")
    ap.add_argument("pdf")
    ap.add_argument("--json")
    ap.add_argument("--warn-pt", type=float, default=2.0)
    a = ap.parse_args()
    issues, n = check(a.pptx, a.pdf, a.warn_pt)
    for it in issues:
        extra = ", ".join(f"{k}={v}" for k, v in it.items() if k not in ("slide", "level", "what", "text"))
        print(f"[{it['level']}] #{it['slide']} {it['what']}：「{it['text']}」{('（' + extra + '）') if extra else ''}")
    red = sum(1 for it in issues if it["level"] == "RED")
    warn = len(issues) - red
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(issues, f, ensure_ascii=False, indent=1)
    print(f"===== 實排檢查：RED {red}、WARN {warn}（{n} 張）=====")
    sys.exit(1 if red else 0)

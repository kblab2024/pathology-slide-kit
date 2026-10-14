# -*- coding: utf-8 -*-
"""實驗講義 PPTX：讀 deck.json，照教師 2026 自製實驗講義（〈病理學實驗_A1_發炎〉）的版型產 16:9 PPTX。

用法：python gen_lab_pptx.py <deck.json> --out <輸出.pptx> [--report <報告.json>] [--no-notes]

deck.json（實驗講義工作流的輸出）：
  {"cover": "病理學實驗 骨與關節",
   "sections": [{"section": 1,
                 "divider": {"label": "Section 1", "title_lines": ["…", "(…)"], "slides_line": "MC01"},
                 "slides": [{"id": "MC01-1", "title": "…", "text": ["句子1", "句子2"], "text_side": "right",
                             "img": {"slot": "left", "mag": "低倍(2x)", "capture": "…"}, "sources": ["…"]}]}]}

版型（幾何取自教師的發炎講義，單位吋，投影片 13.33×7.5）：
  封面      一行 54pt，置中
  分隔張    藍底 143F9C、白字：「Section N」13.5pt，主題 45pt（一到兩行），玻片行 42pt；左緣 1.24、寬 10.86
  內容張    標題一行 30pt 置中（y 0.44）；圖框 6.14×5.32 在 (0.52,1.66)（左）或 (6.67,1.66)（右），
            另一邊放 20.2pt 說明句（寬 5.58、垂直置中）
  字型一律微軟正黑體（common.FONT）。
每個圖框放一張不含任何字的淡灰空圖，教師用 PowerPoint「變更圖片」換截圖，大小位置不變。
截圖要拍的倍率與視野、資料來源寫進備註欄（--no-notes 不寫）。

量字：沿用 gen_pptx 的字型量測（Windows 微軟正黑體；Mac 用 PowerPoint 內建的 MSJH；雲端 Noto Sans CJK TC）。
報出：
  overflow  放不下（說明句總高超過圖框高、分隔張主題或玻片行超過一行）
  rule      違反版型規則但仍放得下（標題超過一行、說明句超過 6 行）
有 overflow 時結束碼 1。
"""
import argparse
import io
import json
import os
import sys

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_pptx import _font, line_h, measure_font_info, n_lines  # noqa: E402

SW, SH = 13.33, 7.5
BLUE = "143F9C"
INK = "000000"
WHITE = "FFFFFF"
GREY = (230, 230, 230)
SZ = {"cover": 54, "label": 13.5, "theme": 45, "glass": 42, "title": 30, "body": 20.2}
IMG_W, IMG_H, IMG_Y = 6.14, 5.32, 1.66
IMG_X = {"left": 0.52, "right": 6.67}
TXT_W = 5.58
TXT_X = {"right": 7.2, "left": 0.55}   # 說明句在右（圖在左）／在左（圖在右）
DIV_X, DIV_W = 1.24, 10.86
TITLE_Y, TITLE_W = 0.44, 12.93
BODY_MAX_LINES = 6
SPACE_AFTER = 6  # pt


def textbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, 0)
    return tf


def add_para(tf, text, size, color, align=PP_ALIGN.LEFT, first=False, space_after=0):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.line_spacing = 1.0
    if space_after:
        p.space_after = Pt(space_after)
    r = p.add_run()
    r.text = text
    _font(r, size, color, False)
    r.font.color.rgb = RGBColor.from_string(color)
    return p


def set_bg(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor.from_string(color)


def grey_png():
    """不含任何字的淡灰空圖（像素比例同教師講義的截圖 590×511）。"""
    buf = io.BytesIO()
    Image.new("RGB", (1180, 1022), GREY).save(buf, "PNG")
    return buf.getvalue()


class Report:
    def __init__(self):
        self.items = []

    def add(self, kind, where, what, need, avail, text):
        self.items.append({"kind": kind, "slide": where, "what": what, "need": need, "avail": avail, "text": text})


def build(deck, out, notes=True):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(SW), Inches(SH)
    blank = prs.slide_layouts[6]
    png = grey_png()
    rep = Report()
    n = 0

    # 封面
    s = prs.slides.add_slide(blank)
    n += 1
    cover = deck.get("cover", "")
    tf = textbox(s, 0.5, 3.04, SW - 1.0, 0.9, MSO_ANCHOR.MIDDLE)
    add_para(tf, cover, SZ["cover"], INK, PP_ALIGN.CENTER, first=True)
    k = n_lines(cover, SZ["cover"], SW - 1.0)
    if k > 1:
        rep.add("overflow", f"#{n} 封面", "封面超過一行", k, 1, cover)

    shots = 0
    for sec in deck.get("sections", []):
        d = sec.get("divider", {})
        s = prs.slides.add_slide(blank)
        n += 1
        set_bg(s, BLUE)
        where = f"#{n} {d.get('label', '')}"
        tf = textbox(s, DIV_X, 2.52, DIV_W, 0.24)
        add_para(tf, d.get("label", ""), SZ["label"], WHITE, first=True)
        y = 2.91
        for line in d.get("title_lines", []):
            tf = textbox(s, DIV_X, y, DIV_W, 0.66)
            add_para(tf, line, SZ["theme"], WHITE, first=True)
            k = n_lines(line, SZ["theme"], DIV_W)
            if k > 1:
                rep.add("overflow", where, "分隔張主題超過一行", k, 1, line)
            y += 0.75
        if len(d.get("title_lines", [])) > 2:
            rep.add("rule", where, "分隔張主題超過兩行", len(d["title_lines"]), 2, " / ".join(d["title_lines"]))
        glass = d.get("slides_line", "")
        tf = textbox(s, DIV_X, y - 0.07, DIV_W, 0.78)
        add_para(tf, glass, SZ["glass"], WHITE, first=True)
        k = n_lines(glass, SZ["glass"], DIV_W)
        if k > 1:
            rep.add("overflow", where, "分隔張玻片行超過一行", k, 1, glass)

        for c in sec.get("slides", []):
            s = prs.slides.add_slide(blank)
            n += 1
            where = f"#{n} {c.get('id', '')}"
            title = c.get("title", "")
            tk = n_lines(title, SZ["title"], TITLE_W)
            tf = textbox(s, (SW - TITLE_W) / 2, TITLE_Y, TITLE_W, 0.47 if tk <= 1 else 0.93)
            add_para(tf, title, SZ["title"], INK, PP_ALIGN.CENTER, first=True)
            if tk > 1:
                rep.add("rule" if tk == 2 else "overflow", where, "標題超過一行", tk, 1, title)

            img = c.get("img") or {}
            side = img.get("slot") or ("left" if c.get("text_side", "right") == "right" else "right")
            if side not in IMG_X:
                side = "left"
            pic = s.shapes.add_picture(io.BytesIO(png), Inches(IMG_X[side]), Inches(IMG_Y), Inches(IMG_W), Inches(IMG_H))
            pic.name = f"截圖待補 {c.get('id', '')}"
            shots += 1

            text = [t for t in (c.get("text") or []) if str(t).strip()]
            tside = "left" if side == "right" else "right"
            tf = textbox(s, TXT_X[tside], IMG_Y, TXT_W, IMG_H, MSO_ANCHOR.MIDDLE)
            lines = 0
            for i, t in enumerate(text):
                add_para(tf, t, SZ["body"], INK, first=(i == 0), space_after=SPACE_AFTER if i < len(text) - 1 else 0)
                lines += n_lines(t, SZ["body"], TXT_W)
            need = lines * line_h(SZ["body"], 1.0) + SPACE_AFTER / 72.0 * max(0, len(text) - 1)
            if need > IMG_H + 0.05:
                rep.add("overflow", where, "說明句放不下", round(need, 2), IMG_H, " / ".join(text))
            elif lines > BODY_MAX_LINES:
                rep.add("rule", where, f"說明句超過 {BODY_MAX_LINES} 行", lines, BODY_MAX_LINES, " / ".join(text))

            if notes:
                parts = []
                if img:
                    parts.append(f"截圖：{img.get('mag', '')}｜{img.get('capture', '')}")
                if c.get("sources"):
                    parts.append("來源：" + "；".join(c["sources"]))
                if parts:
                    s.notes_slide.notes_text_frame.text = "\n".join(parts)

    prs.save(out)
    return n, shots, rep


def main():
    ap = argparse.ArgumentParser(description="實驗講義 deck.json → PPTX（教師 2026 實驗講義版型）")
    ap.add_argument("deck")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", help="放不下與版型問題寫成 JSON（預設：<輸出>_layout.json）")
    ap.add_argument("--no-notes", action="store_true", help="備註欄不寫截圖說明與來源")
    a = ap.parse_args()
    deck = json.load(open(a.deck, encoding="utf-8"))
    print("量字字型：" + measure_font_info())
    if os.path.exists(a.out):
        print(f"[注意] 覆寫既有檔：{a.out}")
    n, shots, rep = build(deck, a.out, notes=not a.no_notes)
    rp = a.report or os.path.splitext(a.out)[0] + "_layout.json"
    with open(rp, "w", encoding="utf-8") as f:
        json.dump({"measure_font": measure_font_info(), "slides": n, "image_slots": shots, "issues": rep.items},
                  f, ensure_ascii=False, indent=1)
    print(f"OK {n} 張（圖框 {shots} 格）-> {a.out}")
    ov = [i for i in rep.items if i["kind"] == "overflow"]
    for i in rep.items:
        print(f"  [{i['kind']}] {i['slide']} {i['what']}（{i['need']} > {i['avail']}）：{i['text'][:60]}")
    print(f"放不下 {len(ov)}、版型提醒 {len(rep.items) - len(ov)}；報告 {rp}")
    return 1 if ov else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

# -*- coding: utf-8 -*-
"""實驗講義 PPTX：讀 deck.json，產 16:9 PPTX。

版面模式（2026-11-24 教師：「把以後的實驗講義都改成這個mode」）：
  rd（預設）  大堂課新預設的版面、字大一號（呼吸二重設計版；kit templates/course.template.yaml）：
              標題靠左粗體 32pt、左邊藍色直條、下面淡色細線；內容張冰藍灰底；截圖與圖加白邊細框；
              說明句 24pt；背景張條列 28pt、表格 26pt（medical 樣式：淡冰藍表頭、首欄赤棕粗字、頂底深藍線、列間細線）；
              出處 16pt；封面與分隔張深藍底、右側色塊、橘色直條（封面 44pt、分隔張主題 40pt、玻片行 28pt）。
              截圖註記（紅箭頭、紅圈、24pt 標籤）不變。
  classic     照教師 2026 自製實驗講義（〈病理學實驗_A1_發炎〉）的原樣（下面「版型」那一段）。
              2026-11-24 以前交的講義重產要原來的樣子：deck.json 寫 "style": "classic"，或加 --style classic。

用法：python gen_lab_pptx.py <deck.json> --out <輸出.pptx> [--report <報告.json>] [--src-list <清單.md>] [--notes] [--bg-pt N]
                              [--style rd|classic] [--img-max-side 1600] [--jpeg-quality 82]
      python gen_lab_pptx.py --fit <deck.json 或節檔.json> [--bg-pt N] [--bullets] [--style rd|classic]
        只量字、不產檔：逐張印出需要的高度對可用高度（撰寫代理自查用；量法和正式產檔同一套）

deck.json（實驗講義工作流的輸出）：
  {"cover": "病理學實驗 骨與關節",
   "sections": [{"section": 1,
                 "divider": {"label": "Section 1", "title_lines": ["…", "(…)"], "slides_line": "MC01"},
                 "slides": [{"id": "MC01-1", "kind": "shot", "title": "…", "text": ["句子1", "句子2"],
                             "text_side": "right", "img": {"slot": "left", "mag": "低倍(2x)", "capture": "…"},
                             "sources": ["…"]}]}]}

每張內容張的 kind（沒寫就是 shot；2026-10-15 教師：「實驗講義不可以只有截圖，要有背景知識跟形態學示意圖」）：
  shot  截圖張：有 img.path 就放那張截圖（wsi_crop.py 從掃描檔切、annotate_shot.py 加註記；2026-10-21 起）；
        沒有就放不含任何字的淡灰空圖（形狀名「截圖待補 <id>」），教師用 PowerPoint「變更圖片」換截圖；
        要拍的倍率與視野寫在 --src-list 的清單
        img.marks（annotate_shot.py 的格式：circle／arrow／span／line／label，座標是圖寬、圖高的 0–1）疊成 PowerPoint
        原生圖形：紅色直線箭頭、紅圈、深灰底白字 24pt 標籤，不群組、每個有名字，教師可以點選、拖曳、改字
        （2026-10-27 教師：箭頭燒進圖裡，錯了他不能改）；img.path 指沒加註記的原始截圖，用 merge_annot.py 從 annot.json 帶入
  bg    背景知識張：沒有圖，標題下全寬條列（--bg-pt，預設 24pt；「  - 」開頭是第二層）；
        可加 "table": [[表頭…], [列…], …]（第一列是表頭、第一欄粗體），表格放不下就接續一張同標題、重複表頭
  gx    大體／影像張：img.path 的圖等比放進圖框（不拉伸、置中），圖下 14pt 出處行 img.credit；
        沒有圖檔就放淡灰空圖（形狀名「圖待補 <id>」）
  sc    形態學示意圖張：img.path 有圖就照 gx 放；沒有就放淡灰空圖（形狀名「示意圖待換 <id>」，
        之後由 lab_swap_images.py 換成加好標籤的圖）
  img.path 相對 deck.json 所在的資料夾。gx、sc、shot 的說明句都放圖框另一邊（20.2pt）。
某一節寫 "divider": null 就不放分隔張（例：封面後直接放一張玻片編號對照）。
deck.json 最上層 "panel": true：圖框與說明句底下各墊一塊淺灰底（EAE9E6，6.14×5.32 吋），照教師發炎講義的原樣；
  沒寫就不墊（骨與關節實驗講義是不墊的版本）。"bullets": true：說明句每段前加「•」（懸掛縮排 0.27 吋、段距 14pt），
  也是發炎講義的原樣。--fit 量 deck.json 時照檔裡的 bullets 量；量單張或節檔時用 --bullets。

classic 的版型（幾何取自教師的發炎講義，單位吋，投影片 13.33×7.5；rd 的圖框與說明句位置相同）：
  封面      一行 54pt，置中
  分隔張    藍底 143F9C、白字：「Section N」13.5pt，主題 45pt（一到兩行），玻片行 42pt；左緣 1.24、寬 10.86
  內容張    標題一行 30pt 置中（y 0.44）；圖框 6.14×5.32 在 (0.52,1.66)（左）或 (6.67,1.66)（右），
            另一邊放 20.2pt 說明句（寬 5.58、垂直置中）
  背景張    標題同上；條列區 (0.52,1.35) 起、寬 12.29、高 5.75
  字型一律微軟正黑體（common.FONT）。
備忘稿（講者備註欄）預設不寫字：教師 2026-11-21「備忘稿全清掉 我不用那個東西 也不要讓學生看到」（AGENTS.md 硬規則 18）。
截圖要拍的倍率與視野、每張的資料來源改寫到 --src-list 指定的清單（給教師看、不發給學生；和講義一起交）。
--notes 才照舊寫進備忘稿（給別的老師用這套工具時的選項）；舊指令的 --no-notes 還收，等於預設。

量字：沿用 gen_pptx 的字型量測（Windows 微軟正黑體；Mac 用 PowerPoint 內建的 MSJH；雲端 Noto Sans CJK TC）。
報出：
  overflow  放不下（說明句或背景條列總高超過可用高度、表格單列放不下、分隔張主題或玻片行超過一行）
  rule      違反版型規則但仍放得下（classic：標題超過一行、說明句超過 6 行；rd：說明句超過 8 行，標題到兩行都可以、三行算放不下）
標題裡的「\n」是手動換行（例：「DS22 瀰漫性大 B 細胞淋巴瘤\n(DIFFUSE LARGE B-CELL LYMPHOMA)低倍」），兩行仍算 rule。
有 overflow 時結束碼 1。報告另寫 ids（id → 張號；背景張接續時寫第一張）與各種圖位的格數。
"""
import argparse
import copy
import io
import json
import os
import sys

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import bullet_level, clear_doc_props  # noqa: E402
from gen_pptx import (NO_GRID_STYLE, TABLE_LINE_K, _TOK, _font, _w, cell_borders, em, line_h,  # noqa: E402
                      measure_font_info, n_lines)

SW, SH = 13.33, 7.5
BLUE = "143F9C"
INK = "000000"
WHITE = "FFFFFF"
GREYTXT = "595959"
TINT = "EEF2FA"
GREY = (230, 230, 230)
PANEL = "EAE9E6"   # 教師發炎講義圖框與說明句底下的淺灰底
BUL_IND, BUL_SPC = 0.266, 14   # 發炎講義說明句的「•」懸掛縮排（吋）與段距（pt）
STYLE = {"bullets": False}
SZ = {"cover": 54, "label": 13.5, "theme": 45, "glass": 42, "title": 30, "body": 20.2, "credit": 14}
IMG_W, IMG_H, IMG_Y = 6.14, 5.32, 1.66
IMG_X = {"left": 0.52, "right": 6.67}
TXT_W = 5.58
TXT_X = {"right": 7.2, "left": 0.55}   # 說明句在右（圖在左）／在左（圖在右）
DIV_X, DIV_W = 1.24, 10.86
TITLE_Y, TITLE_W = 0.44, 12.93
BODY_MAX_LINES = 6
SPACE_AFTER = 6  # pt
BG_X, BG_Y, BG_W, BG_H = 0.52, 1.35, SW - 2 * 0.52, 5.75
BG_LINE, BG_SPACE = 1.1, 10   # 背景條列的行距倍數、段後 pt
BG_IND = 0.36                 # 條列第一層的懸掛縮排（吋）；每多一層加 0.40
TBL_GAP = 0.15
IMG_MAX_SIDE = 1600
KINDS = ("shot", "bg", "gx", "sc")
SLOT_NAME = {"shot": "截圖待補", "gx": "圖待補", "sc": "示意圖待換"}

# ---------------- 版面模式（2026-11-24 教師：「把以後的實驗講義都改成這個mode」） ----------------
SZ_CLASSIC = dict(SZ)
SZ_RD = {"cover": 44, "label": 20, "theme": 40, "glass": 28, "title": 32, "body": 24, "credit": 16, "table": 26}
RDC = {"canvas": "F4F8FB", "title": "10243A", "bar": "2563A8", "rule": "D6E0EB", "ink": "1E2631", "grey": "64748B",
       "bullet": "2563A8", "deep": "14263B", "block": "182D45", "accent": "E06B1F", "sub": "CBD5E1",
       "tbl_head": "E8EFF7", "tbl_line": "D6E0EB", "tbl_first": "9A4618", "mat": "CFD9E5"}   # 同 kit 課程範本的 design
RD = {"on": False}
GEO = {"bg_line": BG_LINE, "max_lines": BODY_MAX_LINES}   # rd 說明句上限 8 行：24pt 八行約等於 20.2pt 六行的字數
MAT_PAD, MAT_W = 0.08, 0.75     # 照片白邊（吋）、細框與標題細線（pt）
RD_TITLE_X, RD_TITLE_Y = 0.52, 0.30


def use_style(name):
    """設定版面模式（沒寫＝rd）；回傳實際用的名字。"""
    on = (name or "rd") != "classic"
    RD["on"] = on
    SZ.clear()
    SZ.update(SZ_RD if on else SZ_CLASSIC)
    GEO["bg_line"] = 1.3 if on else BG_LINE
    GEO["max_lines"] = 8 if on else BODY_MAX_LINES
    return "rd" if on else "classic"


def default_bg_pt():
    return 28 if RD["on"] else 24


def textbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, 0)
    return tf


def add_para(tf, text, size, color, align=PP_ALIGN.LEFT, first=False, space_after=0, line=1.0, bold=False):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.line_spacing = line
    if space_after:
        p.space_after = Pt(space_after)
    r = p.add_run()
    r.text = text
    _font(r, size, color, bold)
    r.font.color.rgb = RGBColor.from_string(color)
    return p


def set_bg(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor.from_string(color)


def add_panel(slide, x, y, w, h):
    from pptx.enum.shapes import MSO_SHAPE
    sp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sp.fill.solid()
    sp.fill.fore_color.rgb = RGBColor.from_string(PANEL)
    sp.line.fill.background()
    sp.shadow.inherit = False
    st = sp._element.find("{http://schemas.openxmlformats.org/presentationml/2006/main}style")
    if st is not None:                       # 拿掉主題樣式（effectRef 會帶陰影；LibreOffice 不管 effectLst）
        sp._element.remove(st)
    sp.name = "淺灰底"
    return sp


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


# ---------------- 量字（產檔與 --fit 共用） ----------------
def kind_of(c):
    k = c.get("kind") or "shot"
    return k if k in KINDS else "shot"


def slot_side(c):
    img = c.get("img") or {}
    side = img.get("slot") or ("left" if c.get("text_side", "right") == "right" else "right")
    return side if side in IMG_X else "left"


def side_text(c):
    return [t for t in (c.get("text") or []) if str(t).strip()]


def side_need(text):
    w = TXT_W - (BUL_IND if STYLE["bullets"] else 0)
    gap = BUL_SPC if STYLE["bullets"] else SPACE_AFTER
    lines = sum(n_lines(t, SZ["body"], w) for t in text)
    need = lines * line_h(SZ["body"], 1.0) + gap / 72.0 * max(0, len(text) - 1)
    return lines, need


def title_lines(title):
    """標題行數；標題裡的「\n」是手動換行（例：長的英文全名自己成一行，不讓「低倍」單獨掉到第二行）。"""
    return sum(n_lines(seg, SZ["title"], title_w(), bold=RD["on"]) for seg in str(title).split("\n"))


def title_w():
    return SW - 2 * RD_TITLE_X - 0.26 if RD["on"] else TITLE_W


def bg_area(title):
    """背景張條列區的 (y, 高)：classic 固定；rd 的標題下有細線，兩行標題時往下移。"""
    if not RD["on"]:
        return BG_Y, BG_H
    rule_y = RD_TITLE_Y + title_lines(title) * line_h(SZ["title"], 1.1) + 0.12
    y = max(BG_Y, rule_y + 0.30)
    return y, BG_Y + BG_H - y


def check_title(rep, where, title):
    tk = title_lines(title)
    if RD["on"]:     # rd：兩行標題還在細線與圖框之間，三行才壓到圖
        if tk > 2:
            rep.add("overflow", where, "標題超過兩行", tk, 2, title)
    elif tk > 1:
        rep.add("rule" if tk == 2 else "overflow", where, "標題超過一行", tk, 1, title)
    return tk


def check_side(rep, where, text):
    lines, need = side_need(text)
    if need > IMG_H + 0.05:
        rep.add("overflow", where, "說明句放不下", round(need, 2), IMG_H, " / ".join(text))
    elif lines > GEO["max_lines"]:
        rep.add("rule", where, f"說明句超過 {GEO['max_lines']} 行", lines, GEO["max_lines"], " / ".join(text))
    return lines, need


def bullets_need(bullets, size):
    need = 0.0
    for b in bullets:
        lvl, t = bullet_level(b)
        need += n_lines(t, size, BG_W - (BG_IND + 0.40 * lvl)) * line_h(size, GEO["bg_line"]) + BG_SPACE / 72.0
    return need


def table_layout(rows, size):
    """欄寬照字數比例（同 gen_pptx.L_table3）；列高＝最多行的那格 × 行高 × TABLE_LINE_K ＋ 0.14。"""
    ncol = max(len(r) for r in rows)
    rows = [[str(x) for x in (list(r) + [""] * ncol)[:ncol]] for r in rows]
    wr = [max(em(r[j]) for r in rows) for j in range(ncol)]
    tot = sum(max(4, x) for x in wr)
    widths = [max(1.3, BG_W * max(4, x) / tot) for x in wr]
    k = BG_W / sum(widths)
    widths = [x * k for x in widths]
    # 每欄至少放得下最長的一個英文字（表頭與第一欄是粗體）：只照字數比例分，粗體的 synaptophysin 會被斷成兩行
    # （2026-10-27 泌尿實驗講義 CMP67 實排）。不夠寬的欄補足，從其他欄依比例扣回，總寬不變。
    minw = [max((_w(tok, i == 0 or j == 0) * size / 72.0 + 0.3 for i, r in enumerate(rows)
                 for tok in _TOK.findall(r[j]) if not tok.isspace()), default=0.0) for j in range(ncol)]
    short = [j for j in range(ncol) if widths[j] < minw[j]]
    if short and sum(minw) <= BG_W:
        extra = sum(minw[j] - widths[j] for j in short)
        for j in short:
            widths[j] = minw[j]
        flex = [j for j in range(ncol) if j not in short]
        room = sum(widths[j] - minw[j] for j in flex)
        for j in flex:
            widths[j] -= extra * (widths[j] - minw[j]) / room if room > 0 else extra / len(flex)
    row_h = [max(n_lines(r[j], size, widths[j] - 0.2, bold=(i == 0 or j == 0)) for j in range(ncol))
             * line_h(size, 1.1) * TABLE_LINE_K + 0.14 for i, r in enumerate(rows)]
    return rows, widths, row_h


def plan_bg(c, size, rep, where):
    """背景張分頁：第一頁放條列（＋放得下的表格列），表格剩下的列接續成同標題的下一張（重複表頭）。
    回傳 [{"bullets": [...], "rows": [列索引…], "need": 高度}]，rows 不含表頭（表頭每頁都放）。"""
    bullets = side_text(c)
    tbl = [r for r in (c.get("table") or []) if r]
    _, bh = bg_area(c.get("title", ""))
    need_b = bullets_need(bullets, size) if bullets else 0.0
    if need_b > bh + 0.05:
        rep.add("overflow", where, "背景條列放不下", round(need_b, 2), round(bh, 2), " / ".join(bullets))
    pages = [{"bullets": bullets, "rows": [], "need": need_b}]
    if len(tbl) < 2:
        return pages, None
    tsize = SZ.get("table", size) if RD["on"] else size
    rows, widths, row_h = table_layout(tbl, tsize)
    head = row_h[0]
    cur = pages[0]
    used = need_b + (TBL_GAP if bullets else 0.0)   # 這一頁表格之前已用掉的高度
    for i in range(1, len(rows)):
        h = row_h[i]
        if head + h > bh + 0.05:
            rep.add("overflow", where, f"表格第 {i} 列一頁放不下", round(head + h, 2), round(bh, 2), " / ".join(rows[i]))
        add_h = h + (0.0 if cur["rows"] else head)          # 這頁第一列要連表頭一起放
        empty = not cur["rows"] and not cur["bullets"]       # 空白頁：再高也先放（放不下已報 overflow）
        if used + add_h <= bh + 0.05 or empty:
            cur["rows"].append(i)
            used += add_h
            cur["need"] = used
        else:
            cur = {"bullets": [], "rows": [i], "need": head + h}
            pages.append(cur)
            used = head + h
    return pages, (rows, widths, row_h, tsize)


# ---------------- 產檔 ----------------
def _rect(s, x, y, w, h, color, name=None, line=None):
    """實心矩形（不帶主題樣式與陰影）；line＝(粗細 pt, 色) 時畫細框。"""
    sp = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    _plain_shape(sp)
    sp.fill.solid()
    sp.fill.fore_color.rgb = RGBColor.from_string(color)
    if line:
        sp.line.color.rgb = RGBColor.from_string(line[1])
        sp.line.width = Pt(line[0])
    else:
        sp.line.fill.background()
    if name:
        sp.name = name
    return sp


def add_title_rd(s, title):
    """rd 的標題：左邊藍色直條、靠左粗體、下面一條淡色細線（同大堂課 gen_pptx 的 content_title）。"""
    h = title_lines(title) * line_h(SZ["title"], 1.1)
    _rect(s, RD_TITLE_X, RD_TITLE_Y + 0.06, 0.085, max(0.3, h - 0.04), RDC["bar"], "標題 直條")
    tf = textbox(s, RD_TITLE_X + 0.26, RD_TITLE_Y, title_w(), h + 0.1)
    segs = str(title).split("\n")
    p = add_para(tf, segs[0], SZ["title"], RDC["title"], first=True, line=1.1, bold=True)
    for seg in segs[1:]:
        p.add_line_break()
        r = p.add_run()
        r.text = seg
        _font(r, SZ["title"], RDC["title"], True)
        r.font.color.rgb = RGBColor.from_string(RDC["title"])
    _rect(s, RD_TITLE_X, RD_TITLE_Y + h + 0.12, SW - 2 * RD_TITLE_X, MAT_W / 72.0, RDC["rule"], "標題 分隔線")


def add_title(s, title):
    if RD["on"]:
        return add_title_rd(s, title)
    tk = title_lines(title)
    tf = textbox(s, (SW - TITLE_W) / 2, TITLE_Y, TITLE_W, 0.47 if tk <= 1 else 0.93)
    segs = str(title).split("\n")
    p = add_para(tf, segs[0], SZ["title"], INK, PP_ALIGN.CENTER, first=True)
    for seg in segs[1:]:
        p.add_line_break()
        r = p.add_run()
        r.text = seg
        _font(r, SZ["title"], INK, False)
        r.font.color.rgb = RGBColor.from_string(INK)


def add_side_text(s, side, text):
    tside = "left" if side == "right" else "right"
    tf = textbox(s, TXT_X[tside], IMG_Y, TXT_W, IMG_H, MSO_ANCHOR.MIDDLE)
    bul = STYLE["bullets"]
    for i, t in enumerate(text):
        p = add_para(tf, t, SZ["body"], RDC["ink"] if RD["on"] else INK, first=(i == 0),
                     space_after=0 if bul else (SPACE_AFTER if i < len(text) - 1 else 0))
        if bul:
            from lxml import etree
            pPr = p._p.get_or_add_pPr()
            pPr.set("marL", str(int(BUL_IND * 914400)))
            pPr.set("indent", str(int(-BUL_IND * 914400)))
            if i > 0:
                p.space_before = Pt(BUL_SPC)
            ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
            for tag in ("buSzPct", "buChar"):
                for old in pPr.findall(f"{{{ns}}}{tag}"):
                    pPr.remove(old)
            bs = etree.SubElement(pPr, f"{{{ns}}}buSzPct")
            bs.set("val", "100000")
            bc = etree.SubElement(pPr, f"{{{ns}}}buChar")
            bc.set("char", "•")


IMG_OPT = {"max_side": IMG_MAX_SIDE, "quality": None}   # --img-max-side、--jpeg-quality


def img_bytes(path):
    """圖檔讀進記憶體；長邊超過 max_side 就縮（照片存 JPEG，有透明或 PNG 示意圖存 PNG）。
    給了 --jpeg-quality：沒有透明的圖一律重存 JPEG（截圖多的實驗講義用，150 張從 100 MB 壓到約 35 MB）。"""
    im = Image.open(path)
    im.load()
    w, h = im.size
    ms, q = IMG_OPT["max_side"], IMG_OPT["quality"]
    alpha = im.mode in ("RGBA", "LA", "P") and (im.mode != "P" or "transparency" in im.info)
    if max(w, h) <= ms and (q is None or alpha):
        return open(path, "rb").read(), (w, h)
    if max(w, h) > ms:
        r = ms / max(w, h)
        im = im.resize((max(1, int(w * r)), max(1, int(h * r))), Image.LANCZOS)
    buf = io.BytesIO()
    if alpha or (q is None and path.lower().endswith(".png")):
        im.save(buf, "PNG", optimize=True)
    else:
        im.convert("RGB").save(buf, "JPEG", quality=q or 88)
    return buf.getvalue(), im.size


def add_real_image(s, path, side, credit_text, cid):
    data, (iw, ih) = img_bytes(path)
    x, y, w, h = IMG_X[side], IMG_Y, IMG_W, IMG_H
    pad = MAT_PAD if RD["on"] else 0.0          # rd：圖外一圈白邊細框，圖往內縮
    x, y, w, h = x + pad, y + pad, w - 2 * pad, h - 2 * pad
    clh = 0.28 if RD["on"] else 0.25            # 出處一行的高（16pt／14pt）
    t = ""
    if credit_text:
        t = credit_text if credit_text.startswith(("圖", "資料來源", "示意圖")) else "圖：" + credit_text
        k = n_lines(t, SZ["credit"], w)
        h = min(h, SH - 0.08 - clh * k - 0.04 - y - pad)   # 出處行放圖下，不壓圖（2026-10-16 實排：兩行出處壓到直式圖的下緣）
    if iw / ih > w / h:
        dw, dh = w, w * ih / iw
    else:
        dw, dh = h * iw / ih, h
    dx, dy = x + (w - dw) / 2, y + (h - dh) / 2
    if pad:
        _rect(s, dx - pad, dy - pad, dw + 2 * pad, dh + 2 * pad, WHITE, f"白邊 {cid}", line=(MAT_W, RDC["mat"]))
    pic = s.shapes.add_picture(io.BytesIO(data), Inches(dx), Inches(dy), Inches(dw), Inches(dh))
    pic.name = f"圖 {cid}"
    if t:
        tf = textbox(s, x, dy + dh + pad + 0.04, w, clh * k)
        add_para(tf, t, SZ["credit"], RDC["grey"] if RD["on"] else GREYTXT, first=True)
    return pic


# ---------------- 截圖註記：PowerPoint 原生圖形（2026-10-27） ----------------
MARK_RED = "E8241A"     # 同 annotate_shot.py
MARK_BOX = "2B2B2B"
MARK_BOX_ALPHA = 88     # 標籤底色不透明度 %（annotate_shot 的 225/255）
MARK_LW = 2.5           # 線寬 pt（annotate_shot 約 0.035 吋）
MARK_LABEL_PT = 24


def text_w_in(text, size):
    """一行字的寬度（吋），用 gen_pptx 的量字字型。"""
    return sum(_w(tok, False) for tok in _TOK.findall(str(text))) * size / 72.0


def label_lines(m):
    if m.get("lines"):
        return [str(x) for x in m["lines"]]
    if m.get("text"):
        return [str(m["text"])]
    return [str(m.get("zh", "")), f"({m.get('en', '')})"]


def marks_layout(marks, dx, dy, dw, dh, label_pt=MARK_LABEL_PT):
    """annotate_shot 格式的 marks（座標是圖寬、圖高的 0–1）→ 投影片上的圖形（吋）。PPTX 與 HTML 版共用。
    標籤照 annotate_shot：框的中心在 at，超出圖就移進圖內（留 1% 邊）。回傳 (圖形清單, 問題清單)。"""
    P = lambda p: (dx + float(p[0]) * dw, dy + float(p[1]) * dh)
    shapes, problems, boxes = [], [], []
    if label_pt < 24:
        problems.append(f"標籤字級 {label_pt}pt 低於 24pt")
    pad = label_pt * 0.32 / 72.0
    lh = line_h(label_pt, 1.0)
    for m in marks or []:
        t = m.get("type")
        col = str(m.get("color", MARK_RED)).lstrip("#")
        if t == "circle":
            (cx, cy), rx, ry = P(m["c"]), float(m["r"][0]) * dw, float(m["r"][1]) * dh
            shapes.append({"t": "circle", "x": cx - rx, "y": cy - ry, "w": 2 * rx, "h": 2 * ry, "color": col})
        elif t in ("arrow", "span", "line"):
            (x1, y1), (x2, y2) = P(m["from"]), P(m["to"])
            shapes.append({"t": t, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "color": col,
                           "head": t == "span", "tail": t in ("arrow", "span"), "dash": bool(m.get("dash"))})
        elif t == "label":
            lines = label_lines(m)
            bw = max(text_w_in(s, label_pt) for s in lines) + 2 * pad + 0.04
            bh = lh * len(lines) + 2 * pad
            cx, cy = P(m["at"])
            x0, y0 = cx - bw / 2, cy - bh / 2
            mx, my = dw * 0.01, dh * 0.01
            if bw + 2 * mx <= dw:
                x0 = min(max(x0, dx + mx), dx + dw - mx - bw)
            if bh + 2 * my <= dh:
                y0 = min(max(y0, dy + my), dy + dh - my - bh)
            name = m.get("text") or m.get("zh") or " ".join(m.get("lines", []))
            r = (x0, y0, x0 + bw, y0 + bh)
            if r[0] < dx - 0.01 or r[1] < dy - 0.01 or r[2] > dx + dw + 0.01 or r[3] > dy + dh + 0.01:
                problems.append(f"標籤「{name}」超出圖")
            for n2, r2 in boxes:
                if not (r[2] <= r2[0] or r2[2] <= r[0] or r[3] <= r2[1] or r2[3] <= r[1]):
                    problems.append(f"標籤「{name}」和「{n2}」重疊")
            boxes.append((name, r))
            shapes.append({"t": "label", "x": x0, "y": y0, "w": bw, "h": bh, "lines": lines, "name": name,
                           "bg": str(m.get("bg", MARK_BOX)).lstrip("#"), "pt": label_pt, "pad": pad})
        else:
            problems.append(f"不認得的 mark type：{t}")
    return shapes, problems


def _plain_shape(sp):
    """拿掉 python-pptx 預設的主題樣式（effectRef 會帶陰影、fontRef 會改字色），顏色全部明寫。"""
    st = sp._element.find(qn("p:style"))
    if st is not None:
        sp._element.remove(st)


def _ln_end(ln, tag):
    e = ln.makeelement(qn(f"a:{tag}"), {"type": "triangle", "w": "lg", "len": "lg"})
    ln.append(e)


def _add_line(s, x1, y1, x2, y2):
    """直線用一般圖形（p:sp、prstGeom line），不用接點（p:cxnSp）：LibreOffice 會把端點剛好落在標籤框邊中點的接點
    吸附到框上、改畫成直角折線（2026-10-27 骨與關節舊片講義實測）；一般的線在 PowerPoint 一樣可以拖兩端。"""
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    el = c._element
    sp = el.makeelement(qn("p:sp"), {})
    nv = el.makeelement(qn("p:nvSpPr"), {})
    nv.append(copy.deepcopy(el.find(qn("p:nvCxnSpPr")).find(qn("p:cNvPr"))))
    nv.append(el.makeelement(qn("p:cNvSpPr"), {}))
    nv.append(el.makeelement(qn("p:nvPr"), {}))
    sp.append(nv)
    sp.append(copy.deepcopy(el.find(qn("p:spPr"))))
    el.addprevious(sp)
    el.getparent().remove(el)
    return s.shapes[len(s.shapes) - 1]


def add_marks(s, cid, marks, pic, label_pt=MARK_LABEL_PT):
    """在截圖上疊 PowerPoint 原生圖形（教師 2026-10-27：箭頭燒進圖裡，錯了他不能改）。
    不群組；每個圖形有名字（「註記 MC03-2 箭頭1」「標籤 MC03-2 透明細胞」），教師可以直接點選、拖曳、改字、刪除。"""
    emu = 914400.0
    dx, dy, dw, dh = pic.left / emu, pic.top / emu, pic.width / emu, pic.height / emu
    shapes, problems = marks_layout(marks, dx, dy, dw, dh, label_pt)
    cnt = {}
    zh = {"circle": "圈", "arrow": "箭頭", "span": "範圍", "line": "線"}
    for g in shapes:
        t = g["t"]
        cnt[t] = cnt.get(t, 0) + 1
        if t == "circle":
            sp = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(g["x"]), Inches(g["y"]), Inches(g["w"]), Inches(g["h"]))
            _plain_shape(sp)
            sp.fill.background()
            sp.line.color.rgb = RGBColor.from_string(g["color"])
            sp.line.width = Pt(MARK_LW)
            sp.name = f"註記 {cid} {zh[t]}{cnt[t]}"
        elif t in ("arrow", "span", "line"):
            sp = _add_line(s, g["x1"], g["y1"], g["x2"], g["y2"])
            sp.line.color.rgb = RGBColor.from_string(g["color"])
            sp.line.width = Pt(MARK_LW)
            if g["dash"]:
                sp.line.dash_style = MSO_LINE_DASH_STYLE.DASH
            ln = sp.line._get_or_add_ln()
            if g["head"]:
                _ln_end(ln, "headEnd")
            if g["tail"]:
                _ln_end(ln, "tailEnd")
            sp.name = f"註記 {cid} {zh[t]}{cnt[t]}"
        else:
            sp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(g["x"]), Inches(g["y"]),
                                    Inches(g["w"]), Inches(g["h"]))
            _plain_shape(sp)
            sp.adjustments[0] = min(0.5, g["pt"] * 0.18 / 72.0 / min(g["w"], g["h"]))
            sp.fill.solid()
            sp.fill.fore_color.rgb = RGBColor.from_string(g["bg"])
            clr = sp.fill._xPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
            clr.append(clr.makeelement(qn("a:alpha"), {"val": str(MARK_BOX_ALPHA * 1000)}))
            sp.line.fill.background()
            tf = sp.text_frame
            tf.word_wrap = False
            tf.auto_size = MSO_AUTO_SIZE.NONE
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
                setattr(tf, side, Inches(g["pad"] if side in ("margin_left", "margin_right") else 0))
            for i, line in enumerate(g["lines"]):
                add_para(tf, line, g["pt"], WHITE, PP_ALIGN.CENTER, first=(i == 0))
            sp.name = f"標籤 {cid} {g['name']}"
    return len(shapes), problems


def add_bg_page(s, page, layout, size, area=None):
    by, bh = area or (BG_Y, BG_H)
    y = by
    if page["bullets"]:
        tf = textbox(s, BG_X, by, BG_W, bh)
        for i, b in enumerate(page["bullets"]):
            lvl, t = bullet_level(b)
            ind = BG_IND + 0.40 * lvl
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.line_spacing = GEO["bg_line"]
            p.space_after = Pt(BG_SPACE)
            pPr = p._p.get_or_add_pPr()
            pPr.set("hangingPunct", "0")
            pPr.set("marL", str(int(ind * 914400)))
            pPr.set("indent", str(int(-0.32 * 914400)))
            r = p.add_run()
            r.text = "• " if lvl == 0 else "– "
            if RD["on"]:
                _font(r, size, RDC["bullet"] if lvl == 0 else RDC["grey"], True)
            else:
                _font(r, size, BLUE if lvl == 0 else GREYTXT, True)
            r = p.add_run()
            r.text = t
            _font(r, size, RDC["ink"] if RD["on"] else INK, False)
        y = by + bullets_need(page["bullets"], size) + TBL_GAP
    if page["rows"] and layout:
        rows, widths, row_h, tsize = layout
        idx = [0] + page["rows"]
        hs = [row_h[i] for i in idx]
        t = s.shapes.add_table(len(idx), len(widths), Inches(BG_X), Inches(y), Inches(BG_W), Inches(sum(hs))).table
        t.first_row = False
        t.horz_banding = False
        if RD["on"]:     # medical 樣式：不要內建的格線
            sid = t._tbl.tblPr.find(qn("a:tableStyleId"))
            if sid is not None:
                sid.text = NO_GRID_STYLE
        for j, wj in enumerate(widths):
            t.columns[j].width = Inches(wj)
        for k, (i, hh) in enumerate(zip(idx, hs)):
            t.rows[k].height = Inches(max(0.3, hh))
            last = k == len(idx) - 1
            for j, txt in enumerate(rows[i]):
                cell = t.cell(k, j)
                cell.fill.solid()
                if RD["on"]:
                    cell.fill.fore_color.rgb = RGBColor.from_string(RDC["tbl_head"] if i == 0 else WHITE)
                else:
                    cell.fill.fore_color.rgb = RGBColor.from_string(BLUE if i == 0 else (WHITE if k % 2 else TINT))
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                cell.margin_left, cell.margin_right = Inches(0.10), Inches(0.08)
                cell.margin_top, cell.margin_bottom = Inches(0.04), Inches(0.04)
                tf = cell.text_frame
                tf.word_wrap = True
                if RD["on"]:
                    col = RDC["title"] if i == 0 else (RDC["tbl_first"] if j == 0 else RDC["ink"])
                else:
                    col = WHITE if i == 0 else INK
                p = add_para(tf, txt, tsize, col, first=True, line=1.1, bold=(i == 0 or j == 0))
                p._p.get_or_add_pPr().set("hangingPunct", "0")   # 全形標點不懸到格外（2026-10-16 實排）
                if RD["on"]:   # 頂、底 1.5pt 深藍線，表頭下 0.75pt，列與列之間 0.6pt 淡線，沒有直線
                    if i == 0:
                        cell_borders(cell, L=None, R=None, T=(1.5, RDC["title"]), B=(0.75, RDC["title"]))
                    else:
                        cell_borders(cell, L=None, R=None, T=None,
                                     B=((1.5, RDC["title"]) if last else (0.6, RDC["tbl_line"])))


def add_divider_text(s, d, rep, where):
    """分隔張的字：Section N、主題一到兩行、玻片行。"""
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


def add_divider_rd(s, d, rep, where):
    """rd 的分隔張：深藍底、右側色塊、橘色直條（同大堂課 gen_pptx 的分隔張）；Section N、主題一到兩行、玻片行。"""
    set_bg(s, RDC["deep"])
    _rect(s, SW * 0.64, 0, SW * 0.36, SH, RDC["block"], "色塊")
    lines = d.get("title_lines", [])
    th = line_h(SZ["theme"], 1.15)
    y0 = 2.15 if len(lines) > 1 else 2.55
    _rect(s, DIV_X - 0.32, y0 + 0.55, 0.10, max(0.8, th * max(1, len(lines))), RDC["accent"], "直條")
    tf = textbox(s, DIV_X, y0, DIV_W, 0.45)
    add_para(tf, d.get("label", ""), SZ["label"], RDC["sub"], first=True, bold=True)
    y = y0 + 0.55
    for line in lines:
        tf = textbox(s, DIV_X, y, DIV_W, th + 0.05)
        add_para(tf, line, SZ["theme"], WHITE, first=True, bold=True)
        k = n_lines(line, SZ["theme"], DIV_W, bold=True)
        if k > 1:
            rep.add("overflow", where, "分隔張主題超過一行", k, 1, line)
        y += th
    if len(lines) > 2:
        rep.add("rule", where, "分隔張主題超過兩行", len(lines), 2, " / ".join(lines))
    glass = d.get("slides_line", "")
    tf = textbox(s, DIV_X, y + 0.2, DIV_W, line_h(SZ["glass"], 1.1) + 0.05)
    add_para(tf, glass, SZ["glass"], RDC["sub"], first=True)
    k = n_lines(glass, SZ["glass"], DIV_W)
    if k > 1:
        rep.add("overflow", where, "分隔張玻片行超過一行", k, 1, glass)


def build(deck, out, notes=False, base_dir=".", bg_pt=None, style=None):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(SW), Inches(SH)
    blank = prs.slide_layouts[6]
    png = grey_png()
    rep = Report()
    ids = {}
    slots = {"shot": 0, "shot_image": 0, "gx_image": 0, "gx_placeholder": 0, "sc_image": 0, "sc_placeholder": 0, "bg": 0,
             "marks": 0}
    n = 0
    use_style(style or deck.get("style"))
    if bg_pt is None:
        bg_pt = default_bg_pt()

    # 封面
    s = prs.slides.add_slide(blank)
    n += 1
    cover = deck.get("cover", "")
    if RD["on"]:
        set_bg(s, RDC["deep"])
        _rect(s, SW * 0.62, 0, SW * 0.38, SH, RDC["block"], "色塊")
        _rect(s, 0.6, 3.0, 0.10, 1.1, RDC["accent"], "直條")
        cw = SW - 0.92 - 0.6
        tf = textbox(s, 0.92, 3.0, cw, 1.1, MSO_ANCHOR.MIDDLE)
        add_para(tf, cover, SZ["cover"], WHITE, first=True, bold=True)
        k = n_lines(cover, SZ["cover"], cw, bold=True)
    else:
        tf = textbox(s, 0.5, 3.04, SW - 1.0, 0.9, MSO_ANCHOR.MIDDLE)
        add_para(tf, cover, SZ["cover"], INK, PP_ALIGN.CENTER, first=True)
        k = n_lines(cover, SZ["cover"], SW - 1.0)
    if k > 1:
        rep.add("overflow", f"#{n} 封面", "封面超過一行", k, 1, cover)

    shots = 0
    panel = bool(deck.get("panel"))
    STYLE["bullets"] = bool(deck.get("bullets"))
    for sec in deck.get("sections", []):
        d = sec.get("divider", {})
        if d is not None:          # "divider": null＝這一節不放分隔張（例：封面後直接放玻片編號對照）
            s = prs.slides.add_slide(blank)
            n += 1
            if RD["on"]:
                add_divider_rd(s, d, rep, f"#{n} {d.get('label', '')}")
            else:
                set_bg(s, BLUE)
                add_divider_text(s, d, rep, f"#{n} {d.get('label', '')}")

        for c in sec.get("slides", []):
            kind = kind_of(c)
            cid = c.get("id", "")
            title = c.get("title", "")
            src_note = ("來源：" + "；".join(c["sources"])) if c.get("sources") else ""

            if kind == "bg":
                pages, layout = plan_bg(c, bg_pt, rep, f"#{n + 1} {cid}")
                for pi, page in enumerate(pages):
                    s = prs.slides.add_slide(blank)
                    n += 1
                    if RD["on"]:
                        set_bg(s, RDC["canvas"])
                    if pi == 0:
                        ids[cid] = n
                        check_title(rep, f"#{n} {cid}", title)
                    add_title(s, title)
                    add_bg_page(s, page, layout, bg_pt, bg_area(title))
                    slots["bg"] += 1
                    if notes and src_note:
                        s.notes_slide.notes_text_frame.text = src_note
                continue

            s = prs.slides.add_slide(blank)
            n += 1
            if RD["on"]:
                set_bg(s, RDC["canvas"])
            ids[cid] = n
            where = f"#{n} {cid}"
            check_title(rep, where, title)
            add_title(s, title)

            img = c.get("img") or {}
            side = slot_side(c)
            path = img.get("path")
            apath = os.path.normpath(os.path.join(base_dir, path)) if path else None
            if panel and not RD["on"]:      # rd 不墊淺灰底（照片有白邊細框）
                add_panel(s, IMG_X[side], IMG_Y, IMG_W, IMG_H)
                add_panel(s, IMG_X["right" if side == "left" else "left"], IMG_Y, IMG_W, IMG_H)
            if apath and os.path.exists(apath):
                pic = add_real_image(s, apath, side, img.get("credit", ""), cid)
                if img.get("marks"):
                    k, probs = add_marks(s, cid, img["marks"], pic, float(img.get("label_pt", MARK_LABEL_PT)))
                    slots["marks"] += k
                    for p in probs:
                        rep.add("rule", where, "截圖註記：" + p, 0, 0, title)
                if kind == "shot":
                    shots += 1
                    slots["shot_image"] += 1
                else:
                    slots[kind + "_image"] += 1
            else:
                if path:
                    rep.add("rule", where, "圖檔不存在，先放淡灰空圖", 0, 0, path)
                if RD["on"]:
                    _rect(s, IMG_X[side], IMG_Y, IMG_W, IMG_H, WHITE, f"白邊 {cid}", line=(MAT_W, RDC["mat"]))
                    pic = s.shapes.add_picture(io.BytesIO(png), Inches(IMG_X[side] + MAT_PAD), Inches(IMG_Y + MAT_PAD),
                                               Inches(IMG_W - 2 * MAT_PAD), Inches(IMG_H - 2 * MAT_PAD))
                else:
                    pic = s.shapes.add_picture(io.BytesIO(png), Inches(IMG_X[side]), Inches(IMG_Y), Inches(IMG_W), Inches(IMG_H))
                pic.name = f"{SLOT_NAME[kind]} {cid}"
                if kind == "shot":
                    shots += 1
                    slots["shot"] += 1
                else:
                    slots[kind + "_placeholder"] += 1

            text = side_text(c)
            add_side_text(s, side, text)
            check_side(rep, where, text)

            if notes:
                parts = []
                if kind == "shot" and img:
                    parts.append(f"截圖：{img.get('mag', '')}｜{img.get('capture', '')}")
                if src_note:
                    parts.append(src_note)
                if parts:
                    s.notes_slide.notes_text_frame.text = "\n".join(parts)

    clear_doc_props(prs)
    prs.save(out)
    return n, shots, rep, ids, slots


# ---------------- --fit：只量字 ----------------
def fit_slides(obj):
    if isinstance(obj, list):
        return obj
    if "sections" in obj:
        return [c for sec in obj["sections"] for c in sec.get("slides", [])]
    if "slides" in obj:
        return obj["slides"]
    return [obj]


def fit(path, bg_pt, bullets=False, style=None):
    obj = json.load(open(path, encoding="utf-8"))
    st = use_style(style or (obj.get("style") if isinstance(obj, dict) else None))
    if bg_pt is None:
        bg_pt = default_bg_pt()
    STYLE["bullets"] = bool(obj.get("bullets")) if isinstance(obj, dict) and "bullets" in obj else bullets
    rep = Report()
    print(f"量字字型：{measure_font_info()}；版面 {st}；背景張 {bg_pt}pt、說明句 {SZ['body']}pt、標題 {SZ['title']}pt")
    print("id｜kind｜標題行數｜需要高度/可用（吋）｜行數")
    for c in fit_slides(obj):
        kind = kind_of(c)
        cid = c.get("id", "?")
        where = cid
        tk = check_title(rep, where, c.get("title", ""))
        if kind == "bg":
            pages, layout = plan_bg(c, bg_pt, rep, where)
            for pi, p in enumerate(pages):
                print(f"{cid}{'' if pi == 0 else f'（接續 {pi + 1}）'}｜bg｜{tk}｜{p['need']:.2f}/{bg_area(c.get('title', ''))[1]:.2f}｜"
                      f"條列 {len(p['bullets'])} 條、表格 {len(p['rows'])} 列")
            if len(pages) > 1:
                rep.add("rule", where, "背景張接續成多張", len(pages), 1, c.get("title", ""))
        else:
            lines, need = check_side(rep, where, side_text(c))
            print(f"{cid}｜{kind}｜{tk}｜{need:.2f}/{IMG_H}｜{lines} 行（上限 {GEO['max_lines']}）")
    ov = [i for i in rep.items if i["kind"] == "overflow"]
    for i in rep.items:
        print(f"  [{i['kind']}] {i['slide']} {i['what']}（{i['need']} > {i['avail']}）：{i['text'][:60]}")
    print(f"放不下 {len(ov)}、版型提醒 {len(rep.items) - len(ov)}")
    return 1 if ov else 0


def write_src_list(deck, ids, path, pptx_name=""):
    """截圖說明與來源清單：以前寫在備忘稿的字（要拍的倍率與視野、每張的資料來源）改寫到這份 Markdown。
    給教師看，不發給學生。ids＝build() 回傳的 {id: 張號}。回傳列數。"""
    def cell(t):
        return str(t or "").replace("|", "／").replace("\n", " ").strip()

    rows = []
    for sec in deck.get("sections", []):
        for c in sec.get("slides", []):
            img = c.get("img") or {}
            shot = ""
            if kind_of(c) == "shot" and img:
                shot = "｜".join(x for x in (cell(img.get("mag")), cell(img.get("capture"))) if x)
            src = "；".join(cell(x) for x in (c.get("sources") or []))
            if shot or src:
                rows.append(f"| {ids.get(c.get('id', ''), '')} | {cell(c.get('id'))} | {cell(c.get('title'))} | {shot} | {src} |")
    head = ["# 截圖說明與來源清單" + (f"：{pptx_name}" if pptx_name else ""), "",
            "這份清單給教師看，不發給學生。講義的備忘稿（講者備註欄）不放字，原本寫在那裡的字列在這裡。", "",
            "| 張 | 編號 | 標題 | 截圖（倍率｜視野） | 來源 |", "|---|---|---|---|---|"]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(head + rows) + "\n")
    return len(rows)


def main():
    ap = argparse.ArgumentParser(description="實驗講義 deck.json → PPTX（教師 2026 實驗講義版型）")
    ap.add_argument("deck", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--report", help="放不下與版型問題寫成 JSON（預設：<輸出>_layout.json）")
    ap.add_argument("--notes", action="store_true", help="把截圖說明與來源寫進備忘稿（預設不寫：硬規則 18，學生會看到）")
    ap.add_argument("--no-notes", action="store_true", help="舊選項，等於預設（備忘稿不寫字）")
    ap.add_argument("--src-list", metavar="MD", help="截圖說明與來源另寫成一份清單（給教師看，不發給學生）")
    ap.add_argument("--bg-pt", type=float, default=None, help="背景知識張的條列字級（預設 rd 28、classic 24；classic 的表格同字級）")
    ap.add_argument("--style", choices=("rd", "classic"), default=None,
                    help="版面模式（預設 rd＝大堂課新預設的版面、字大一號；2026-11-24 以前交的講義要原樣用 classic）；不給就看 deck.json 的 style")
    ap.add_argument("--fit", metavar="JSON", help="只量字、不產檔（deck.json、節檔或張的清單）")
    ap.add_argument("--bullets", action="store_true", help="--fit 量單張或節檔時照「•」懸掛縮排量（deck.json 以檔裡的 bullets 為準）")
    ap.add_argument("--img-max-side", type=int, default=IMG_MAX_SIDE, help=f"放進 PPTX 的圖長邊上限 px（預設 {IMG_MAX_SIDE}）")
    ap.add_argument("--jpeg-quality", type=int, default=None, help="給了就把沒有透明的圖都重存成這個品質的 JPEG（例 82）")
    a = ap.parse_args()
    if a.fit:
        return fit(a.fit, a.bg_pt, a.bullets, a.style)
    if not a.deck or not a.out:
        ap.error("要給 deck.json 與 --out（或用 --fit 只量字）")
    deck = json.load(open(a.deck, encoding="utf-8"))
    IMG_OPT.update(max_side=a.img_max_side, quality=a.jpeg_quality)
    print("量字字型：" + measure_font_info())
    if os.path.exists(a.out):
        print(f"[注意] 覆寫既有檔：{a.out}")
    base = os.path.dirname(os.path.abspath(a.deck))
    n, shots, rep, ids, slots = build(deck, a.out, notes=a.notes and not a.no_notes, base_dir=base, bg_pt=a.bg_pt,
                                      style=a.style)
    if a.src_list:
        k = write_src_list(deck, ids, a.src_list, os.path.basename(a.out))
        print(f"截圖說明與來源清單 {k} 列 -> {a.src_list}")
    rp = a.report or os.path.splitext(a.out)[0] + "_layout.json"
    with open(rp, "w", encoding="utf-8") as f:
        json.dump({"measure_font": measure_font_info(), "style": "rd" if RD["on"] else "classic", "slides": n,
                   "image_slots": shots, "slots": slots,
                   "ids": ids, "issues": rep.items}, f, ensure_ascii=False, indent=1)
    print(f"OK {n} 張（版面 {'rd' if RD['on'] else 'classic'}；截圖圖框 {shots} 格；{slots}）-> {a.out}")
    ov = [i for i in rep.items if i["kind"] == "overflow"]
    for i in rep.items:
        print(f"  [{i['kind']}] {i['slide']} {i['what']}（{i['need']} > {i['avail']}）：{i['text'][:60]}")
    print(f"放不下 {len(ov)}、版型提醒 {len(rep.items) - len(ov)}；報告 {rp}")
    return 1 if ov else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

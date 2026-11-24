# -*- coding: utf-8 -*-
"""流程圖畫成 PowerPoint 原生圖形（圓角框、箭頭、文字方塊），教師在 PowerPoint 裡可以直接改字、拖框、刪箭頭。

教師 2026-11-12（docs/教師偏好與決策.md 第 4 節）：「目前很多流程圖是用圖檔 我不能接受 流程圖跟圖表盡量用powerpoint可編輯的排版
因為目前來講claude的語句我還是必須要修很多」。所以程式寫的字不燒進圖：流程圖、框架圖、表格都用 PowerPoint 的圖形與表格；
照片、教科書原圖、影像模型的母圖才是圖檔（母圖上的中英標籤另見 label_image.py）。

規格檔和 draw_flow.py 同一份（JSON，格式見 draw_flow.py 的 docstring）。素材池在該張寫：
    <!-- flow: _archive/build/flow_specs.json#圖名 ｜ 出處：依 Robbins 11e p.586 繪製 -->
gen_pptx 看到 flow 就在這張的圖區畫原生圖形（flash／robbins／big 是全寬圖區，left 是右欄）；出處沒寫就用同張第一個 IMG 的出處。
同張可以留著 draw_flow.py 畫的 PNG（<!-- IMG: … -->）：PPTX 不放它，HTML 版（html_deck.py）才用；規格改了記得重畫 PNG。

排法（和 draw_flow.py 的圖同一個樣子）：節點框由上而下、同寬、靠左；箭頭在框的左段，說明寫在箭頭右邊；
{"inhibit": …} 畫成紅色 T 字線頂住箭頭。字級從 28 往下試到 24（節點第一行大 2pt），取放得進圖區的最大一級；
24pt 還放不下就照樣畫並記進 _layout.json（check_deck 會報），要改規格（拆行、拆張），不縮字。
每個圖形都有名字（「流程圖 框1」「流程圖 箭頭1 說明」），dump_pptx.py 傾印後回灌時看得出是哪一格。
"""
import copy
import json
import math
import os
import re

from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

SIZES = ((30, 28), (28, 26), (26, 24), (24, 24))   # （節點第一行, 其他字）由大到小試
PADX, PADY = 0.14, 0.07        # 節點框內距（in）
ARROW_X = 0.50                 # 箭頭離框左緣（in）
TEXT_DX = 0.30                 # 說明離箭頭（in）
INHIBIT_DX = 0.36              # 抑制說明比一般說明再縮進（in），前面放 T 字線
GAP_MIN = 0.42                 # 沒有字的箭頭至少這麼長（in）
STYLE = {None: (False, "ink"), "b": (True, "ink"), "o": (True, "or"), "red": (True, "red"), "blue": (True, "blue")}


def load_fig(spec_path, name):
    """讀規格檔的一張圖；找不到回 None。"""
    try:
        return (json.load(open(spec_path, encoding="utf-8")).get("figures") or {}).get(name)
    except Exception:
        return None


def _runs(line):
    """箭頭說明的一行 → [(文字, 樣式)]；行可以是字串、run 的 list，或 {"inhibit": …}。"""
    if isinstance(line, dict):
        line = line.get("inhibit", [])
    if isinstance(line, str):
        line = [line]
    return [(r, None) if isinstance(r, str) else (r.get("t", ""), r.get("s")) for r in line]


def flow_text(fig):
    """這張流程圖的全部文字（一格一行），給 style_check 查中英對照與用語。"""
    if is_stages(fig):
        return stages_text(fig)
    out = []
    for it in (fig or {}).get("items", []):
        if "node" in it:
            out += list(it["node"])
        else:
            out += ["".join(t for t, _ in _runs(ln)) for ln in it.get("arrow", [])]
    return [t for t in out if t]


# ---------------- 分段路徑圖（"kind": "stages"）----------------
# 教師 2026-11-22（中醫系講義的國考題；docs/中醫系講義流程.md 3.8）：辨證路徑「臨床疾病 → 證型 → 方劑」，證型那一段要寫出
# 「症狀=>望診=>脈診=>證型，類似history => PE => impression」；「主內容就好 其他東西我會口頭講」，框裡不加灰色小字或出處。
# 上層：一條分段的箭頭帶（第一段五邊形、其後 V 形，越後面越深；"muted": true 的段用灰色，例：還沒有西醫診斷）。
# 下層：每段一個白底細框，和上面那一段同寬。有 steps 的段在框裡由上往下排「標籤＋內容」，標籤之間用細線和小三角接起來，
# 最後一列 result 用橘色；其他段寫 head（粗體）與 lines。欄寬照內容量（每一行都不換行），多的寬照比例分給各段。
# 規格：{"kind": "stages", "stages": [{"label": "臨床疾病", "muted": false, "head": "…", "lines": ["…"]},
#        {"label": "辨證", "steps": [{"tag": "症狀", "lines": ["…"]}, …], "result": {"tag": "證型", "text": "…"}},
#        {"label": "方劑", "head": "…", "lines": ["…"]}]}
ST = {"band_h": 0.6, "notch": 0.18, "gap": 0.12, "band_gap": 0.25, "pad": 0.25, "tag_w": 1.0, "tag_h": 0.5,
      "tag_gap": 0.3, "row_gap": 0.36, "line": 1.05, "label": 24, "head": 28, "base": 24, "tag": 24, "result": 30}
ST_HEX = {"muted": "9AA4AE", "box": "C9CFD6", "tag": "ECF0F7", "conn": "B4C0D6", "white": "FFFFFF"}


def is_stages(fig):
    return isinstance(fig, dict) and fig.get("kind") == "stages"


def stages_text(fig):
    out = []
    for st in fig.get("stages", []):
        out += [st.get("label", ""), st.get("head", "")] + list(st.get("lines", []))
        for sp in st.get("steps", []):
            out += [sp.get("tag", "")] + list(sp.get("lines", []))
        if st.get("result"):
            out += [st["result"].get("tag", ""), st["result"].get("text", "")]
    return [t for t in out if t]


def stages_fill(blue, i, n, muted=False):
    """第 i 段箭頭帶的底色：課程的藍往白色混（第一段混 45%、最後一段原色）；muted 用灰。"""
    if muted:
        return ST_HEX["muted"]
    t = 0.45 * (1 - i / max(1, n - 1))
    return "".join(f"{round(v + (255 - v) * t):02X}" for v in (int(blue[k:k + 2], 16) for k in (0, 2, 4)))


def stages_plan(fig, w, wfun):
    """版面（吋）。wfun(字, 粗體) 回傳該行字在 1pt 字級下的寬（em）。只認一段 steps。
    回傳 dict：widths 各段寬、xs 各段左緣（相對圖區左緣）、rows steps 那一段每一列的高（最後一列是 result）、
    body_h 框高、fh 整張圖高、need_w 每行都不換行要的總寬、avail_w 可用的寬。"""
    P = ST
    tw = lambda t, size, bold: wfun(t, bold) * size / 72.0 * 1.03 + 0.04
    lh = lambda size: size * 1.2 * P["line"] / 72.0
    stages = fig.get("stages", [])
    nat = []
    for st in stages:
        if st.get("steps"):
            body = [tw(t, P["base"], False) for sp in st["steps"] for t in sp.get("lines", [])]
            body.append(tw((st.get("result") or {}).get("text", ""), P["result"], True))
            nat.append(2 * P["pad"] + P["tag_w"] + P["tag_gap"] + max(body))
        else:
            body = [tw(st.get("head", ""), P["head"], True)] + [tw(t, P["base"], False) for t in st.get("lines", [])]
            nat.append(2 * P["pad"] + max(body))
        nat[-1] = max(nat[-1], tw(st.get("label", ""), P["label"], True) + 2 * P["notch"] + 0.3)
    avail = w - P["gap"] * (len(stages) - 1)
    need = sum(nat) or 1.0
    widths = [n * avail / need for n in nat]
    xs, cx = [], 0.0
    for wd in widths:
        xs.append(cx)
        cx += wd + P["gap"]
    nl = lambda t, size, bold, room: max(1, math.ceil(tw(t, size, bold) / room - 0.03))   # tw 已多留 3%，差一點點不算換行
    rows, hs = [], []
    for st, wd in zip(stages, widths):
        if st.get("steps") and not rows:
            room = wd - 2 * P["pad"] - P["tag_w"] - P["tag_gap"]
            for sp in st["steps"]:
                rows.append(max(P["tag_h"], sum(nl(t, P["base"], False, room) for t in sp.get("lines", [])) * lh(P["base"])))
            rows.append(max(P["tag_h"], nl((st.get("result") or {}).get("text", ""), P["result"], True, room) * lh(P["result"])))
            hs.append(2 * P["pad"] + sum(rows) + P["row_gap"] * len(st["steps"]))
        else:
            room = wd - 2 * P["pad"]
            hs.append(2 * P["pad"] + nl(st.get("head", ""), P["head"], True, room) * lh(P["head"])
                      + sum(nl(t, P["base"], False, room) for t in st.get("lines", [])) * lh(P["base"]))
    body_h = max(hs) if hs else 0.0
    return {"widths": widths, "xs": xs, "rows": rows, "body_h": body_h,
            "fh": P["band_h"] + P["band_gap"] + body_h, "need_w": sum(nat), "avail_w": avail}


def place_stages(g, slide, s, x, y, w, h):
    """在 (x, y, w, h) 畫分段路徑圖（is_stages）。回傳圖的底緣 y。不畫出處（硬規則 20：我們畫的圖不寫出處）。"""
    G, P = g.G, ST
    fig = s["flow"]["fig"]
    floor = G.SH - getattr(G, "src_h", 0.0) - 0.10
    avail = max(0.8, min(y + h, floor) - y)
    plan = stages_plan(fig, w, lambda t, b: g._w(g.strip_markup(t), b))
    g.note_fit(s, plan["fh"], avail, "流程圖")
    G.layout[s["id"]][-1]["pt"] = P["base"]
    if plan["need_w"] > plan["avail_w"] + 0.05:
        g.note_fit(s, plan["need_w"], plan["avail_w"], "流程圖的欄寬（有字會換行，減字或拆行）")
    blue, orange, ink = G.EMPH.get("藍", "143F9C"), G.EMPH.get("橘", "ED7D31"), G.D["ink"]
    stages = fig.get("stages", [])
    n = len(stages)

    def shape(kind, sx, sy, sw, sh, fill, line=None, name=""):
        shp = slide.shapes.add_shape(kind, Inches(sx), Inches(sy), Inches(sw), Inches(sh))
        _plain(shp)
        shp.fill.solid()
        shp.fill.fore_color.rgb = g.C(fill)
        if line:
            shp.line.color.rgb = g.C(line)
            shp.line.width = Pt(0.75)
        else:
            shp.line.fill.background()
        shp.name = name
        return shp

    def label(shp, t, size, color):
        tf = _frame(shp, MSO_ANCHOR.MIDDLE, 0.04, 0.0, wrap=False)
        g.para(tf, t, size, color=color, bold=True, align=PP_ALIGN.CENTER, first=True, line=1.0, space_after=0)

    by, bh = y + P["band_h"] + P["band_gap"], plan["body_h"]
    for i, st in enumerate(stages):
        sx, sw = x + plan["xs"][i], plan["widths"][i]
        segw = sw + P["gap"] + P["notch"] - 0.05 if i < n - 1 else sw
        seg = shape(MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON, sx, y, segw, P["band_h"],
                    stages_fill(blue, i, n, st.get("muted")), name=f"路徑 段{i + 1}")
        seg.adjustments[0] = P["notch"] / P["band_h"]
        label(seg, st.get("label", ""), P["label"], "FFFFFF")
        shape(MSO_SHAPE.RECTANGLE, sx, by, sw, bh, ST_HEX["white"], ST_HEX["box"], name=f"路徑 段{i + 1} 框")
        if not st.get("steps"):
            tb, tf = g.textbox(slide, sx + P["pad"], by + P["pad"], sw - 2 * P["pad"], bh - 2 * P["pad"])
            g.para(tf, st.get("head", ""), P["head"], color=ink, bold=True, first=True, line=P["line"], space_after=0)
            for ln in st.get("lines", []):
                g.para(tf, ln, P["base"], color=ink, line=P["line"], space_after=0)
            tb.name = f"路徑 段{i + 1} 文字"
            continue
        tx = sx + P["pad"]
        cx = tx + P["tag_w"] + P["tag_gap"]
        cw = sw - (cx - sx) - P["pad"]
        cy = by + P["pad"]
        steps = list(st["steps"]) + [dict(st.get("result") or {}, _result=True)]
        for k, sp in enumerate(steps):
            rh = plan["rows"][k]
            last = sp.get("_result", False)
            tag = shape(MSO_SHAPE.ROUNDED_RECTANGLE, tx, cy, P["tag_w"], P["tag_h"], orange if last else ST_HEX["tag"],
                        name=f"路徑 段{i + 1} 標籤{k + 1}")
            tag.adjustments[0] = 0.22
            label(tag, sp.get("tag", ""), P["tag"], "FFFFFF" if last else blue)
            if last:
                tb, tf = g.textbox(slide, cx, cy - 0.06, cw, P["tag_h"] + 0.12, anchor=MSO_ANCHOR.MIDDLE)
                g.para(tf, sp.get("text", ""), P["result"], color=orange, bold=True, first=True, line=1.0, space_after=0)
                tb.name = f"路徑 段{i + 1} 結果"
                break
            tb, tf = g.textbox(slide, cx, cy + 0.045, cw, rh)
            for q, ln in enumerate(sp.get("lines", [])):
                g.para(tf, ln, P["base"], color=ink, first=(q == 0), line=P["line"], space_after=0)
            tb.name = f"路徑 段{i + 1} 內容{k + 1}"
            top, bot, mid = cy + P["tag_h"] + 0.04, cy + rh + P["row_gap"] - 0.04, tx + P["tag_w"] / 2
            shape(MSO_SHAPE.RECTANGLE, mid - 0.0125, top, 0.025, max(0.02, bot - top - 0.1), ST_HEX["conn"],
                  name=f"路徑 段{i + 1} 連線{k + 1}")
            tri = shape(MSO_SHAPE.ISOSCELES_TRIANGLE, mid - 0.08, bot - 0.12, 0.16, 0.12, ST_HEX["conn"],
                        name=f"路徑 段{i + 1} 箭頭{k + 1}")
            tri.rotation = 180
            cy += rh + P["row_gap"]
    return by + bh


def _line_shape(slide, x1, y1, x2, y2):
    """直線用一般圖形（p:sp），不用接點（p:cxnSp）：LibreOffice 會把接點吸到旁邊的框上、畫成折線（gen_lab_pptx 同一個做法）。"""
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
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
    return slide.shapes[len(slide.shapes) - 1]


def _plain(shp):
    """拿掉 python-pptx 預設的主題樣式（會帶陰影、改字色），顏色全部明寫。"""
    st = shp._element.find(qn("p:style"))
    if st is not None:
        shp._element.remove(st)


def _frame(shp, anchor, mx, my, wrap=True):
    tf = shp.text_frame
    tf.word_wrap = wrap
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(mx)
    tf.margin_top = tf.margin_bottom = Inches(my)
    return tf


def _lh(size):
    """行距 100% 的微軟正黑體，實排每行 1.2 × 字級（gen_pptx._cell_need 的校正）。"""
    return size * 1.2 / 72.0


def _tw(g, text, size, bold):
    """一行字的寬（in），多留 3%＋0.04 in，免得實排早一個字斷行。"""
    return g._w(g.strip_markup(text), bold) * size / 72.0 * 1.03 + 0.04


def _plan(g, fig, w, head, base):
    """照字級算版面。回傳 dict：bw 節點框寬、fw 整張圖寬、fh 整張圖高、rows 每個 item 的高度與行數、wrapped 有沒有被迫換行。"""
    items = fig.get("items", [])
    nodes = [it["node"] for it in items if "node" in it]
    nat = max([_tw(g, t, head if i == 0 else base, True) for n in nodes for i, t in enumerate(n)] or [1.0]) + 2 * PADX
    bw = min(nat, w)
    wrapped = nat > w + 1e-6
    off = ARROW_X + TEXT_DX
    a_nat = 0.0
    for it in items:
        for ln in it.get("arrow", []) if "arrow" in it else []:
            rs = _runs(ln)
            wid = sum(_tw(g, t, base, STYLE.get(s, STYLE[None])[0]) for t, s in rs)
            a_nat = max(a_nat, wid + (INHIBIT_DX if isinstance(ln, dict) else 0.0))
    fw = min(max(bw, off + a_nat), w)
    aw = w - off                       # 說明可用的寬（畫到圖區右緣）
    wrapped = wrapped or off + a_nat > w + 1e-6
    rows, fh = [], 0.0
    for it in items:
        if "node" in it:
            n = [g.n_lines(t, head if i == 0 else base, bw - 2 * PADX, bold=True) for i, t in enumerate(it["node"])]
            h = sum(k * _lh(head if i == 0 else base) for i, k in enumerate(n)) + 2 * PADY
            rows.append({"h": h, "n": n})
        else:
            n = []
            for ln in it.get("arrow", []):
                txt = "".join(t for t, _ in _runs(ln))
                n.append(g.n_lines(txt, base, aw - (INHIBIT_DX if isinstance(ln, dict) else 0.0),
                                   bold=any(STYLE.get(s, STYLE[None])[0] for _, s in _runs(ln))))
            h = max(GAP_MIN, sum(n) * _lh(base) + 0.16)
            rows.append({"h": h, "n": n})
        fh += rows[-1]["h"]
    return {"bw": bw, "fw": fw, "fh": fh, "rows": rows, "wrapped": wrapped, "head": head, "base": base}


# ---------------- 雙軸式（course.yaml layout.flow_style: axis；2026-11-24 rs2 重設計，Gemini 的設計規範）----------------
# 左欄：節點由上而下，白底細框、左緣一條藍色直條，最後一個節點淡冰藍底、粗字；節點之間是直的箭頭（在節點欄的正中）。
# 右欄：每個箭頭的說明，從箭頭中點拉一條水平細引線過去。沒有圓角、陰影、漸層。字級 26 或 24（取放得下的最大一級）。
AX = {"bar": 0.07, "padl": 0.22, "padr": 0.14, "pady": 0.07, "col_gap": 0.55, "gap_min": 0.34,
      "node_line": "CFD9E5", "last_fill": "E6EEF8", "arrow": "64748B", "leader": "A9B9CB"}


def _axis_plan(g, fig, w, base, frac=0.62):
    items = fig.get("items", [])
    nodes = [it["node"] for it in items if "node" in it]
    nat = max([_tw(g, t, base, n is nodes[-1]) for n in nodes for t in n] or [1.0]) + AX["bar"] + AX["padl"] + AX["padr"]
    nw = min(nat, w * frac)
    lab_nat = 0.0
    for it in items:
        for ln in it.get("arrow", []) if "arrow" in it else []:
            lab_nat = max(lab_nat, sum(_tw(g, t, base, False) for t, _ in _runs(ln)))
    if lab_nat == 0.0:
        nw = min(nat, w * 0.75)
    lw = max(1.5, min(lab_nat, w - nw - AX["col_gap"])) if lab_nat else 0.0
    hs, kinds, labh = [], [], []
    for it in items:
        if "node" in it:
            n = [g.n_lines(t, base, nw - AX["bar"] - AX["padl"] - AX["padr"], bold=True) for t in it["node"]]
            hs.append(sum(n) * _lh(base) + 2 * AX["pady"])
            kinds.append(("node", n))
            labh.append(0.0)
        else:
            n = [g.n_lines("".join(t for t, _ in _runs(ln)), base, lw) for ln in it.get("arrow", [])] if lw else []
            hs.append(AX["gap_min"])
            kinds.append(("arrow", n))
            labh.append(sum(n) * _lh(base))
    # 說明的中心在箭頭中點；相鄰兩段說明至少隔 0.08 in，不夠就把兩個箭頭各拉長一半
    arrows = [i for i, k in enumerate(kinds) if k[0] == "arrow" and labh[i] > 0]
    for _ in range(3):
        for p, q in zip(arrows, arrows[1:]):
            dist = hs[p] / 2 + sum(hs[p + 1:q]) + hs[q] / 2
            need = (labh[p] + labh[q]) / 2 + 0.04
            if dist < need:
                hs[p] += (need - dist) / 2
                hs[q] += (need - dist) / 2
    rows = [{"h": h, "n": k[1], "lab_h": lh} for h, k, lh in zip(hs, kinds, labh)]
    fw = nw + (AX["col_gap"] + lw if lw else 0.0)
    return {"nw": nw, "lw": lw, "fw": fw, "fh": sum(hs), "rows": rows, "base": base}


def place_flow_axis(g, slide, s, x, y, w, h):
    G = g.G
    fig = s["flow"]["fig"]
    floor = G.SH - getattr(G, "src_h", 0.0) - 0.10
    avail = max(0.8, min(y + h, floor) - y)
    # 先試 26pt、節點欄 62%；放不下就 24pt，再把節點欄加寬（節點少折行；說明欄窄、說明可以延伸到節點旁邊）
    plans = [_axis_plan(g, fig, w, b, f) for b, f in ((26, 0.62), (24, 0.62), (24, 0.70), (24, 0.78))
             if b >= min(24, G.S.get("label", 24))]
    plan = next((p for p in plans if p["fh"] <= avail), min(plans, key=lambda p: p["fh"]))
    g.note_fit(s, plan["fh"], avail, "流程圖")
    G.layout[s["id"]][-1]["pt"] = plan["base"]
    base, nw, lw, rows = plan["base"], plan["nw"], plan["lw"], plan["rows"]
    items = fig.get("items", [])
    extra = max(0.0, avail - plan["fh"])
    n_gap = sum(1 for it in items if "arrow" in it)
    add_gap = min(0.25, extra / n_gap) if n_gap else 0.0
    blue, ink = G.EMPH.get("藍", "143F9C"), G.D["ink"]
    bar = G.D.get("title_bar") or G.D["cobalt"]
    col = {"blue": blue, "or": G.EMPH.get("橘", "ED7D31"), "red": G.EMPH.get("紅", "FF0000"), "ink": ink}
    fx = x + max(0.0, (w - plan["fw"]) / 2)
    cx = fx + nw / 2
    lx = fx + nw + AX["col_gap"]
    cy = y
    kn = ka = 0
    n_nodes = sum(1 for it in items if "node" in it)
    for it, row in zip(items, rows):
        if "node" in it:
            kn += 1
            last = kn == n_nodes
            hh = row["h"]
            box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(fx), Inches(cy), Inches(nw), Inches(hh))
            _plain(box)
            box.fill.solid()
            box.fill.fore_color.rgb = g.C(AX["last_fill"] if last else "FFFFFF")
            box.line.color.rgb = g.C(AX["node_line"])
            box.line.width = Pt(0.75)
            box.name = f"流程圖 框{kn}"
            b_ = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(fx), Inches(cy), Inches(AX["bar"]), Inches(hh))
            _plain(b_)
            b_.fill.solid()
            b_.fill.fore_color.rgb = g.C(bar)
            b_.line.fill.background()
            b_.name = f"流程圖 框{kn} 直條"
            tb, tf = g.textbox(slide, fx + AX["bar"] + AX["padl"], cy, nw - AX["bar"] - AX["padl"] - AX["padr"], hh,
                               anchor=MSO_ANCHOR.MIDDLE)
            for i, t in enumerate(it["node"]):
                g.para(tf, t, base, color=blue, bold=last, first=(i == 0), line=1.0, space_after=0)
            tb.name = f"流程圖 框{kn} 文字"
            cy += hh
            continue
        ka += 1
        hh = row["h"] + add_gap
        ln = _line_shape(slide, cx, cy + 0.04, cx, cy + hh - 0.04)
        ln.line.color.rgb = g.C(AX["arrow"])
        ln.line.width = Pt(1.5)
        e = ln.line._get_or_add_ln()
        e.append(e.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
        ln.name = f"流程圖 箭頭{ka}"
        lines = it.get("arrow", [])
        if lines and lw:
            my = cy + hh / 2
            ld = _line_shape(slide, cx + 0.10, my, lx - 0.12, my)
            ld.line.color.rgb = g.C(AX["leader"])
            ld.line.width = Pt(0.75)
            ld.name = f"流程圖 箭頭{ka} 引線"
            th = row["lab_h"]
            tb, tf = g.textbox(slide, lx, my - th / 2, lw, th, anchor=MSO_ANCHOR.MIDDLE)
            for q, line in enumerate(lines):
                p = tf.paragraphs[0] if q == 0 else tf.add_paragraph()
                p.alignment = PP_ALIGN.LEFT
                p._p.get_or_add_pPr().set("hangingPunct", "0")
                p.space_after = Pt(0)
                p.line_spacing = 1.0
                for t, st in _runs(line):
                    bold, ck = STYLE.get(st, STYLE[None])
                    if isinstance(line, dict):
                        ck = "red"
                    r = p.add_run()
                    r.text = t
                    g._font(r, base, col[ck], bold and ck != "ink")
            tb.name = f"流程圖 箭頭{ka} 說明"
        cy += hh
    return cy


def place_flow(g, slide, s, x, y, w, h):
    """在 (x, y, w, h) 畫 s["flow"]["fig"]。g＝gen_pptx 模組（借它的量字、文字、出處行與 G 設定）。回傳圖的底緣 y。"""
    G = g.G
    fl = s["flow"]
    fig = fl["fig"]
    if is_stages(fig):
        return place_stages(g, slide, s, x, y, w, h)
    if (getattr(G, "L", None) or {}).get("flow_style") == "axis":
        return place_flow_axis(g, slide, s, x, y, w, h)
    cred = fl.get("src") or next((i.get("src") for i in s.get("imgs", []) if i.get("src")), "")
    ctext = cred if cred.startswith(("圖", "資料來源")) else "圖：" + cred
    ch = (g.n_lines(ctext, G.S["credit"], max(w, 4.5)) * 0.25 + 0.06) if cred else 0.0
    floor = G.SH - getattr(G, "src_h", 0.0) - 0.10 - ch
    avail = max(0.8, min(y + h, floor) - y)
    floor_pt = G.S.get("label", 24)
    cands = [(a, b) for a, b in SIZES if b >= floor_pt] or [SIZES[-1]]
    plans = [_plan(g, fig, w, a, b) for a, b in cands]
    plan = next((p for p in plans if not p["wrapped"] and p["fh"] <= avail),
                next((p for p in plans if p["fh"] <= avail), plans[-1]))
    g.note_fit(s, plan["fh"], avail, "流程圖")
    G.layout[s["id"]][-1]["pt"] = plan["base"]
    head, base, bw, rows = plan["head"], plan["base"], plan["bw"], plan["rows"]
    items = fig.get("items", [])
    # 圖比圖區矮：多的高度先給箭頭（每個最多加 0.30 in），再給節點框（每個最多加 0.12 in），看起來不擠
    extra = max(0.0, avail - plan["fh"])
    n_gap = sum(1 for it in items if "arrow" in it)
    n_node = len(items) - n_gap
    add_gap = min(0.30, extra / n_gap) if n_gap else 0.0
    extra -= add_gap * n_gap
    add_node = min(0.12, extra / n_node) if n_node else 0.0
    col = {"blue": G.EMPH.get("藍", "143F9C"), "or": G.EMPH.get("橘", "ED7D31"), "red": G.EMPH.get("紅", "FF0000"),
           "grey": G.EMPH.get("灰", G.D["grey"]), "ink": G.D["ink"]}
    fx = x + (w - plan["fw"]) / 2
    ax, tx = fx + ARROW_X, fx + ARROW_X + TEXT_DX
    cy = y
    kn = ka = ki = 0
    for it, row in zip(items, rows):
        if "node" in it:
            kn += 1
            hh = row["h"] + add_node
            shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(fx), Inches(cy), Inches(bw), Inches(hh))
            _plain(shp)
            shp.adjustments[0] = min(0.5, 0.10 / min(bw, hh))
            shp.fill.solid()
            shp.fill.fore_color.rgb = g.C("FFFFFF")
            shp.line.color.rgb = g.C(col["blue"])
            shp.line.width = Pt(1.5)
            shp.name = f"流程圖 框{kn}"
            tf = _frame(shp, MSO_ANCHOR.MIDDLE, PADX, PADY)
            for i, t in enumerate(it["node"]):
                g.para(tf, t, head if i == 0 else base, color=col["blue"], bold=True, align=PP_ALIGN.CENTER,
                       first=(i == 0), line=1.0, space_after=0)
            cy += hh
            continue
        ka += 1
        hh = row["h"] + add_gap
        ln = _line_shape(slide, ax, cy + 0.03, ax, cy + hh - 0.03)
        ln.line.color.rgb = g.C(col["grey"])
        ln.line.width = Pt(2.25)
        e = ln.line._get_or_add_ln()
        e.append(e.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
        ln.name = f"流程圖 箭頭{ka}"
        lines = it.get("arrow", [])
        ty = cy + (hh - sum(row["n"]) * _lh(base)) / 2
        k = 0
        while k < len(lines):
            inh = isinstance(lines[k], dict)
            j = k + 1
            while not inh and j < len(lines) and not isinstance(lines[j], dict):
                j += 1                                   # 連續的一般說明放同一個文字方塊，抑制說明各自一個
            bh = sum(row["n"][k:j]) * _lh(base)
            bx = tx + (INHIBIT_DX if inh else 0.0)
            tb, tf = g.textbox(slide, bx, ty, x + w - bx, bh, anchor=MSO_ANCHOR.MIDDLE)
            for q, line in enumerate(lines[k:j]):
                p = tf.paragraphs[0] if q == 0 else tf.add_paragraph()
                p.alignment = PP_ALIGN.LEFT
                p._p.get_or_add_pPr().set("hangingPunct", "0")
                p.space_after = Pt(0)
                p.line_spacing = 1.0
                for t, st in _runs(line):
                    bold, ck = STYLE.get(st, STYLE[None])
                    r = p.add_run()
                    r.text = t
                    g._font(r, base, col[ck], bold)
            if inh:
                ki += 1
                my = ty + bh / 2
                for nm, (rx, ry, rw, rh) in (("線", (ax + 0.07, my - 0.02, bx - 0.06 - (ax + 0.07), 0.04)),
                                             ("頭", (ax + 0.05, my - 0.15, 0.045, 0.30))):
                    r_ = g.rect(slide, rx, ry, rw, rh, hexc=col["red"])
                    _plain(r_)
                    r_.name = f"流程圖 抑制{ki} {nm}"
                tb.name = f"流程圖 抑制{ki} 說明"
            else:
                tb.name = f"流程圖 箭頭{ka} 說明" + ("" if k == 0 else f"{k + 1}")
            ty += bh
            k = j
        cy += hh
    if cred:
        cw = max(plan["fw"], min(w, 4.5))
        g.credit(slide, cred, fx if cw <= plan["fw"] + 1e-6 else x + (w - cw) / 2, cw, cy + 0.04)
    return cy


def parse_ref(inner, course_dir):
    """素材池 <!-- flow: 規格檔#圖名 ｜ 出處：… --> 的內容 → dict；規格檔相對課程資料夾。"""
    ref = re.split(r"[｜|\n]", inner)[0].strip()
    path, _, name = ref.partition("#")
    absp = path if os.path.isabs(path) else os.path.join(course_dir, path)
    src = re.search(r"出處：\s*([^｜|\n]+)", inner)
    fig = load_fig(absp, name.strip()) if path.strip().lower().endswith(".json") and os.path.exists(absp) else None
    return {"spec": path.strip(), "name": name.strip(), "abspath": absp, "fig": fig,
            "src": src.group(1).strip() if src else ""}

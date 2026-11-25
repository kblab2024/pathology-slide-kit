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
2026-11-25 起另有六種排法（規格的 "style"；教師：「各種方式交替使用」「都不要號碼」「拆兩張的時候項目應該要有重疊」），見下面
「新樣式」那一段的說明與 AGENTS.md 硬規則 22。上面這一段講的是最早的排法（規格與 course.yaml 都沒指定時用）。
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


# ---------------- 新樣式（2026-11-25；規格的 "style" 或 course.yaml layout.flow_style：timeline｜spine｜stack｜steps｜merge｜fork）----------------
# 教師 2026-11-25 給了兩批設計參考（一份流程圖改版的網頁、三張 Runway 的樣張），說「各種方式交替使用」「張數可以微微放寬」，
# 接著：「無論你用哪一種 都不要號碼!」「是叫你設計 不是叫你編1 2 3」「gemini跟runway不知道為什麼都喜歡編號 拜託不要」。
# 所以三種都沒有編號。共同的做法：說明（箭頭上的字）不再拉到右邊窄欄（窄欄會把 cardiovascular 拆成兩行），改成實心的膠囊；
# 流程的最後一格用實心深色、白字；括號裡的英文不變淡（他說「括號裡的英文拜託不要變淡」）；全部是原生圖形，字 ≥24pt，沒有陰影與漸層。
#   stack    直式卡片：同寬的白底細框由上往下排，左緣一條色帶，卡片之間一個小三角，說明膠囊在三角旁邊。一頁 2–3 格。
#   steps    橫向兩格：左右各一格等高的白底細框，中間一支粗箭頭，說明膠囊在兩格上方。只給剛好兩格的圖，其他退回 stack。
#   timeline 時間軸：左邊一條直線，節點不加框，線上一個圓點、字在右邊；說明膠囊掛在線上。四格也放得下一頁。
#   spine    中軸式：同寬的白底細框置中由上往下排，框與框之間一條中軸線，說明是掛在中軸線正中央的空心膠囊（橘框、深橘字）；
#            最後一格淡底粗框。（Gemini 參考的方案 B，去掉編號）
#   merge    匯流：第一個節點的每一行各成一格，疊在左邊；右邊一格是它們共同的結果（實心）。例：兩個機轉造成同一個結果。
#   fork     分流：左邊一格，右邊把第二個節點的每一行各排成一格。例：一個原因造成兩個結果。（Gemini 參考的方案 C，句子不改）
#   steps 的說明預設放在兩格上方（Runway 的排法）；規格寫 "pill": "mid" 就放在兩格中間、箭頭上方（Gemini 的方案 A）。
# 規格可以另寫："end": false（這一頁的最後一格不是整個流程的終點，不用實心）、"stack_en": true（英文收到節點最後一行）、
#   "carry": 1（第一格是上一頁的最後一格，重畫一次、用灰色）。教師 2026-11-25：「當你拆兩張的時候項目應該要有重疊
#   不然學生沒辦法記得之前發生什麼事」：同一個流程拆成兩頁時，第二頁一定從上一頁的最後一格開始（他自己拆肺氣腫的致病機轉就是這樣）。
#   steps 與 merge 遇到「carry 的一格＋兩個節點」會把重複的那一格畫成左邊較窄的灰色格。
NS = {"line": "CBD5E1", "pill_pad": 0.26, "pill_h_pad": 0.07}
_EN_IN = re.compile(r"[（(]([^（）()一-鿿]*[A-Za-z][^（）()一-鿿]*)[)）]")


def _ns_colors(g):
    G = g.G
    return {"ink": G.D["ink"], "navy": G.D.get("cover_block") or G.D.get("deep", "14263B"), "blue": G.D.get("title_bar") or G.D["cobalt"],
            "orange": G.EMPH.get("橘", "ED7D31"), "en": G.D.get("grey", "64748B"), "line": NS["line"]}


def _ns_lines(node, base, stack):
    """節點要畫的行：[(字, 字級, 'zh'|'en')]。stack：括號裡的英文收到最後一行，用「 · 」隔開。"""
    if not stack:
        return [(t, base, "zh") for t in node]
    out, ens = [], []
    for t in node:
        for e in _EN_IN.findall(t):
            if e.strip() not in ens:
                ens.append(e.strip())
        out.append((_EN_IN.sub("", t), base, "zh"))
    if ens:
        out.append((" · ".join(ens), max(24, base - 2), "en"))
    return out


def _ns_label(lines):
    """箭頭的說明 → 一行一個字串（膠囊裡用白字，不分色）。"""
    return ["".join(t_ for t_, _ in _runs(ln)) for ln in lines]


def _ns_shape(g, slide, kind, x, y, w, h, fill, line=None, lw=0.75, name="", radius=None):
    shp = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    _plain(shp)
    if radius is not None and kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        shp.adjustments[0] = min(0.5, radius / max(0.01, min(w, h)))
    if fill:
        shp.fill.solid()
        shp.fill.fore_color.rgb = g.C(fill)
    else:
        shp.fill.background()
    if line:
        shp.line.color.rgb = g.C(line)
        shp.line.width = Pt(lw)
    else:
        shp.line.fill.background()
    shp.name = name
    return shp


def _ns_pill(g, slide, lines, x, y, w, size, col, name, center=True):
    """實心膠囊（橘底白字粗體）。x, y 是左上角；回傳 (寬, 高)。w＝最大寬。"""
    nat = max(_tw(g, t_, size, True) for t_ in lines) + 2 * NS["pill_pad"]
    pw = min(nat, w)
    n = sum(g.n_lines(t_, size, pw - 2 * NS["pill_pad"], bold=True) for t_ in lines)
    ph = n * _lh(size) + 2 * NS["pill_h_pad"]
    shp = _ns_shape(g, slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, pw, ph, col["orange"], name=name + "框", radius=ph / 2)
    tb, tf = g.textbox(slide, x + NS["pill_pad"], y, pw - 2 * NS["pill_pad"], ph, anchor=MSO_ANCHOR.MIDDLE)
    for q, t_ in enumerate(lines):
        g.para(tf, t_, size, color="FFFFFF", bold=True, align=PP_ALIGN.CENTER if center else PP_ALIGN.LEFT, first=(q == 0),
               line=1.0, space_after=0)
    tb.name = name
    return pw, ph


def _ns_pill_size(g, lines, w, size):
    nat = max(_tw(g, t_, size, True) for t_ in lines) + 2 * NS["pill_pad"]
    pw = min(nat, w)
    n = sum(g.n_lines(t_, size, pw - 2 * NS["pill_pad"], bold=True) for t_ in lines)
    return pw, n * _lh(size) + 2 * NS["pill_h_pad"]


def _ns_text(g, tf, lines, col, solid, bold_zh):
    for q, (t_, sz, kind) in enumerate(lines):
        if kind == "en":
            g.para(tf, t_, sz, color=("DCE7F5" if solid else col["en"]), bold=False, first=(q == 0), line=1.05, space_after=0, markup=False, mute=False)
        else:
            g.para(tf, t_, sz, color=("FFFFFF" if solid else col["ink"]), bold=bold_zh or solid, first=(q == 0), line=1.05,
                   space_after=(4 if q < len(lines) - 1 else 0), markup=not solid)


def _ns_fit(cands, avail):
    """cands：[(字級, 高, 折行數, 其他…)]。放得下的裡面挑折行最少、字最大的；都放不下挑最矮的。"""
    fit = [c for c in cands if c[1] <= avail + 1e-6]
    return min(fit, key=lambda c: (c[2], -c[0])) if fit else min(cands, key=lambda c: c[1])


def _ns_avail(g, y, h):
    G = g.G
    return max(0.8, min(y + h, G.SH - getattr(G, "src_h", 0.0) - 0.10) - y)


def _ns_opt(g, fig):
    G = g.G
    opt = dict(G.L.get("flow_opts") if isinstance(G.L.get("flow_opts"), dict) else {})
    opt.update({k: fig[k] for k in ("stack_en", "end", "pill", "carry") if k in fig})
    return opt


GHOST = {"fill": "EEF2F6", "ink": "64748B", "bar": "A8B4C3"}       # 上一頁重複的那一格：淡灰底、灰字


def _orphan(g, text, size, width_in, bold=True):
    """這一段字折行以後，最後一行是不是只剩一兩個字（孤字）。回傳 1 或 0。量法和 gen_pptx.n_lines 相同。"""
    if g.SOFT_BREAK in (text or ""):               # 段內手動換行（⏎）：每一段各自量
        return 1 if any(_orphan(g, t_, size, width_in, bold) for t_ in text.split(g.SOFT_BREAK)) else 0
    cap = max(1.0, width_in * 72.0 / size)
    lines, cur = 1, 0.0
    for tok in g._TOK.findall(g.strip_markup(text or "")):
        w_ = g._w(tok, bold)
        if tok.isspace():
            if cur > 0:
                cur += w_
            continue
        if cur + w_ <= cap:
            cur += w_
        else:
            lines += 1
            cur = w_ if w_ <= cap else w_ % cap
    return 1 if (lines > 1 and cur <= 2.3) else 0


def _ns_fit_cards(cands, avail):
    """卡片類（steps、merge、fork）挑字級：cands＝[(字級, 高, 最多行數, …, 孤字數)]，由大到小；
    先挑放得下、每段不超過 3 行（其次 4 行）而且沒有孤字的最大字級，再放寬到有孤字的，都放不下就最小的。"""
    fit = [c for c in cands if c[1] <= avail + 1e-6]
    for lim in (3, 4):
        ok = [c for c in fit if c[2] <= lim and c[-1] == 0]
        if ok:
            return ok[0]
    for lim in (3, 4):
        ok = [c for c in fit if c[2] <= lim]
        if ok:
            return ok[0]
    return (fit or [cands[-1]])[0]


def place_flow_stack(g, slide, s, x, y, w, h):
    """直式卡片。"""
    G = g.G
    fig = s["flow"]["fig"]
    items = fig.get("items", [])
    opt = _ns_opt(g, fig)
    col = _ns_colors(g)
    avail = _ns_avail(g, y, h)
    PADX, BAR = 0.30, 0.12
    cands = []
    for base in (30, 28, 26, 24):
        for pady, gap in ((0.16, 0.50), (0.10, 0.40), (0.07, 0.32)):
            nls = [_ns_lines(it["node"], base, opt.get("stack_en")) for it in items if "node" in it]
            nat = max([_tw(g, t_, sz, True) for nl in nls for t_, sz, _ in nl] or [1.0]) + 2 * PADX + BAR
            nw = min(max(nat, w * 0.60), w * 0.94)
            tw = nw - 2 * PADX - BAR
            hs, wraps, k = [], 0, 0
            for it in items:
                if "node" in it:
                    nl = nls[k]; k += 1
                    n = [g.n_lines(t_, sz, tw, bold=True) for t_, sz, _ in nl]
                    wraps += sum(c - 1 for c in n)
                    hs.append(sum(c * _lh(sz) * 1.05 for c, (_, sz, _) in zip(n, nl)) + 2 * pady + 0.06)
                else:
                    lab = _ns_label(it.get("arrow", []))
                    hs.append(max(gap, (_ns_pill_size(g, lab, w * 0.55, 24)[1] + 0.16) if lab else 0.0))
            cands.append((base, sum(hs), wraps, pady, gap, nls, nw, hs))
    base, fh, _, pady, gap, nls, nw, hs = _ns_fit(cands, avail)
    g.note_fit(s, fh, avail, "流程圖")
    G.layout[s["id"]][-1]["pt"] = base
    fx = x + max(0.0, (w - nw) / 2)
    cx = fx + nw * 0.5
    cy = y + max(0.0, min(0.35, (avail - fh) * 0.25))
    n_nodes = len(nls)
    kn = ka = 0
    for it, hh in zip(items, hs):
        if "node" in it:
            kn += 1
            solid = kn == n_nodes and n_nodes > 1 and opt.get("end", True)
            ghost = kn <= int(opt.get("carry", 0) or 0)
            _ns_shape(g, slide, MSO_SHAPE.RECTANGLE, fx, cy, nw, hh, col["navy"] if solid else (GHOST["fill"] if ghost else "FFFFFF"),
                      None if solid else col["line"], 0.75, f"流程圖 框{kn}" + ("（承上頁）" if ghost else ""))
            _ns_shape(g, slide, MSO_SHAPE.RECTANGLE, fx, cy, BAR, hh, col["orange"] if solid else (GHOST["bar"] if ghost else col["blue"]), name=f"流程圖 框{kn} 色帶")
            tb, tf = g.textbox(slide, fx + BAR + PADX, cy, nw - BAR - 2 * PADX, hh, anchor=MSO_ANCHOR.MIDDLE)
            _ns_text(g, tf, nls[kn - 1], dict(col, ink=GHOST["ink"]) if ghost else col, solid, bold_zh=False)
            tb.name = f"流程圖 框{kn} 文字"
            cy += hh
            continue
        ka += 1
        lab = _ns_label(it.get("arrow", []))
        tri = _ns_shape(g, slide, MSO_SHAPE.ISOSCELES_TRIANGLE, cx - 0.17, cy + hh / 2 - 0.10, 0.34, 0.20, col["blue"], name=f"流程圖 箭頭{ka}")
        tri.rotation = 180
        if lab:
            pw, ph = _ns_pill_size(g, lab, w * 0.55, 24)
            px = min(cx + 0.42, x + w - pw)
            _ns_pill(g, slide, lab, px, cy + (hh - ph) / 2, w * 0.55, 24, col, f"流程圖 箭頭{ka} 說明")
        cy += hh
    return cy


def place_flow_steps(g, slide, s, x, y, w, h):
    """橫向兩格（"carry": 1 時最左邊多一格較窄的灰色格＝上一頁的最後一格）。節點數不合的圖退回直式卡片。"""
    G = g.G
    fig = s["flow"]["fig"]
    items = fig.get("items", [])
    opt = _ns_opt(g, fig)
    carry = int(opt.get("carry", 0) or 0)
    nodes = [it["node"] for it in items if "node" in it]
    if len(nodes) != 2 + carry or carry > 1:
        return place_flow_stack(g, slide, s, x, y, w, h)
    col = _ns_colors(g)
    avail = _ns_avail(g, y, h)
    # 說明：labs[i]＝第 i 個節點「前面」那個箭頭的字（i=0 是第一格之前）
    labs, k, pend = {}, 0, []
    for it in items:
        if "node" in it:
            if pend:
                labs[k] = pend
            pend = []
            k += 1
        else:
            pend = _ns_label(it.get("arrow", []))
    main = nodes[carry:]
    lab_i = next((i for i in sorted(labs)), None)                 # 這種版面只放一個說明（第一個）
    lab = labs.get(lab_i, [])
    GAP, PADX, PADY, ACC = 1.15, 0.34, 0.34, 0.09
    in_mid = bool(lab) and not carry and lab_i == 1 and opt.get("pill") == "mid"       # 說明放在兩格中間（箭頭上方）
    if in_mid:
        GAP = min(4.0, max(1.8, max(_tw(g, t_, 24, True) for t_ in lab) + 2 * NS["pill_pad"] + 0.30))
    GW, GG = (2.55, 0.58) if carry else (0.0, 0.0)                # 灰色格的寬、它和第一格之間的間隔
    if carry:
        GAP = 0.95
    cw = (w - GAP - GW - GG) / 2
    ph_band = (_ns_pill_size(g, lab, w * 0.9, 24)[1] + 0.30) if (lab and not in_mid) else 0.0
    cands = []
    for base in (32, 30, 28, 26, 24):
        nls = [_ns_lines(n, base, opt.get("stack_en")) for n in main]
        ns_ = [[g.n_lines(t_, sz, cw - 2 * PADX, bold=True) for t_, sz, _ in nl] for nl in nls]
        ch = max(sum(c * _lh(sz) * 1.05 + 4 / 72.0 for c, (_, sz, _) in zip(n, nl)) for n, nl in zip(ns_, nls)) + 2 * PADY + ACC + 0.22
        if carry:
            gn = sum(g.n_lines(t_, 24, GW - 0.44) for t_ in nodes[0])
            ch = max(ch, gn * _lh(24) * 1.05 + 0.5)
        orph = sum(_orphan(g, t_, sz, cw - 2 * PADX) for nl in nls for t_, sz, kd in nl if kd == "zh")
        cands.append((base, ch + ph_band, max(c for n in ns_ for c in n), nls, ch, orph))
    base, fh, _, nls, ch, _ = _ns_fit_cards(cands, avail)
    g.note_fit(s, fh, avail, "流程圖")
    G.layout[s["id"]][-1]["pt"] = base
    ch = min(avail - ph_band, max(ch, min((avail - ph_band) * 0.70, 2.7)))
    top = y + max(0.0, (avail - ph_band - ch) * 0.30)
    x0 = x + GW + GG                                              # 第一格（不算灰色格）的左緣
    if lab and not in_mid:
        pw, ph = _ns_pill_size(g, lab, w * 0.9, 24)
        if lab_i == carry:                                        # 說明在第一格之前：靠第一格的左緣
            px = min(x0, x + w - pw)
        else:                                                     # 說明在兩格之間：置中在兩格的間隔上
            px = min(max(x, x0 + cw + GAP / 2 - pw / 2), x + w - pw)
        _ns_pill(g, slide, lab, px, top, w * 0.9, 24, col, "流程圖 箭頭1 說明")
        top += ph_band

    def harrow(x1, x2, ay, name, pt=3.5, color=None):
        ln = _line_shape(slide, x1, ay, x2, ay)
        ln.line.color.rgb = g.C(color or col["navy"])
        ln.line.width = Pt(pt)
        e = ln.line._get_or_add_ln()
        e.append(e.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
        ln.name = name

    if carry:
        _ns_shape(g, slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, top, GW, ch, GHOST["fill"], col["line"], 0.75, "流程圖 框1（承上頁）", radius=0.10)
        tb, tf = g.textbox(slide, x + 0.22, top, GW - 0.44, ch, anchor=MSO_ANCHOR.MIDDLE)
        for q, t_ in enumerate(nodes[0]):
            g.para(tf, t_, 24, color=GHOST["ink"], first=(q == 0), line=1.05, space_after=0, mute=False)
        tb.name = "流程圖 框1 文字"
        harrow(x + GW + 0.16, x0 - 0.16, top + ch / 2, "流程圖 箭頭1", pt=2.5, color=GHOST["bar"])
    for i, nl in enumerate(nls):
        solid = i == 1 and opt.get("end", True)
        bx = x0 + i * (cw + GAP)
        k = i + 1 + carry
        _ns_shape(g, slide, MSO_SHAPE.ROUNDED_RECTANGLE, bx, top, cw, ch, col["navy"] if solid else "FFFFFF", None if solid else col["line"], 1.0,
                  f"流程圖 框{k}", radius=0.10)
        _ns_shape(g, slide, MSO_SHAPE.RECTANGLE, bx + PADX, top + PADY, 0.9, ACC, col["orange"] if solid else col["blue"], name=f"流程圖 框{k} 色條")
        tb, tf = g.textbox(slide, bx + PADX, top + PADY + ACC + 0.22, cw - 2 * PADX, ch - 2 * PADY - ACC - 0.22)
        _ns_text(g, tf, nl, col, solid, bold_zh=False)
        tb.name = f"流程圖 框{k} 文字"
    ay = top + ch / 2
    if in_mid:
        pw, ph = _ns_pill_size(g, lab, GAP - 0.30, 24)
        _ns_pill(g, slide, lab, x0 + cw + (GAP - pw) / 2, ay - ph - 0.10, GAP - 0.30, 24, col, "流程圖 箭頭1 說明")
        ay += 0.28
    harrow(x0 + cw + 0.22, x0 + cw + GAP - 0.22, ay, f"流程圖 箭頭{1 + carry}")
    return top + ch


def place_flow_timeline(g, slide, s, x, y, w, h):
    """時間軸：節點不加框。"""
    G = g.G
    fig = s["flow"]["fig"]
    items = fig.get("items", [])
    opt = _ns_opt(g, fig)
    col = _ns_colors(g)
    avail = _ns_avail(g, y, h)
    LX, TX = 0.55, 1.10                       # 線與文字離圖區左緣
    tw = w - TX - 0.2
    cands = []
    for base in (30, 28, 26, 24):
        for gapn, gapl in ((0.42, 0.20), (0.30, 0.14), (0.20, 0.10)):
            nls = [_ns_lines(it["node"], base, opt.get("stack_en")) for it in items if "node" in it]
            hs, wraps, k = [], 0, 0
            for it in items:
                if "node" in it:
                    nl = nls[k]; k += 1
                    n = [g.n_lines(t_, sz, tw, bold=(k == len(nls))) for t_, sz, _ in nl]
                    wraps += sum(c - 1 for c in n)
                    hs.append(sum(c * _lh(sz) * 1.05 for c, (_, sz, _) in zip(n, nl)) + 0.06)
                else:
                    lab = _ns_label(it.get("arrow", []))
                    hs.append((_ns_pill_size(g, lab, tw, 24)[1] + 2 * gapl) if lab else gapn)
            cands.append((base, sum(hs), wraps, nls, hs))
    base, fh, _, nls, hs = _ns_fit(cands, avail)
    g.note_fit(s, fh, avail, "流程圖")
    G.layout[s["id"]][-1]["pt"] = base
    nat = max([_tw(g, t_, sz, True) for nl in nls for t_, sz, _ in nl] or [1.0])
    fx = x + max(0.0, min((w - TX - nat) / 2 - 0.4, w * 0.16))          # 整組稍微往中間靠，不貼左緣
    cy = y + max(0.0, min(0.35, (avail - fh) * 0.25))
    n_nodes = len(nls)
    # 先算每個節點的中心，畫線，再畫點與字（線在最下面）
    ys, yy, k = [], cy, 0
    for it, hh in zip(items, hs):
        if "node" in it:
            first_h = _lh(nls[k][0][1]) * 1.05
            ys.append(yy + first_h / 2 + 0.03)
            k += 1
        yy += hh
    cont = not opt.get("end", True)
    y1 = ys[0] if "node" in items[0] else cy
    y2 = (cy + fh + 0.10) if cont else ys[-1]
    ln = _line_shape(slide, fx + LX, y1, fx + LX, y2)
    ln.line.color.rgb = g.C(col["navy"])
    ln.line.width = Pt(2.5)
    if cont:
        e = ln.line._get_or_add_ln()
        e.append(e.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
    ln.name = "流程圖 時間軸"
    kn = ka = 0
    yy = cy
    for it, hh in zip(items, hs):
        if "node" in it:
            kn += 1
            last = kn == n_nodes and n_nodes > 1 and opt.get("end", True)
            ghost = kn <= int(opt.get("carry", 0) or 0)
            r = 0.19 if last else 0.11
            _ns_shape(g, slide, MSO_SHAPE.OVAL, fx + LX - r, ys[kn - 1] - r, 2 * r, 2 * r, col["orange"] if last else ("FFFFFF" if ghost else col["navy"]),
                      GHOST["bar"] if ghost else "FFFFFF", 1.5, f"流程圖 點{kn}")
            tb, tf = g.textbox(slide, fx + TX, yy, tw - (fx - x), hh)
            for q, (t_, sz, kind) in enumerate(nls[kn - 1]):
                if kind == "en":
                    g.para(tf, t_, sz, color=col["en"], first=(q == 0), line=1.05, space_after=0, markup=False, mute=False)
                else:
                    g.para(tf, t_, sz, color=(GHOST["ink"] if ghost else col["ink"]), bold=last, first=(q == 0), line=1.05, space_after=0, mute=not ghost)
            tb.name = f"流程圖 框{kn} 文字"
            yy += hh
            continue
        ka += 1
        lab = _ns_label(it.get("arrow", []))
        if lab:
            pw, ph = _ns_pill_size(g, lab, tw, 24)
            _ns_pill(g, slide, lab, fx + LX - 0.16, yy + (hh - ph) / 2, tw, 24, col, f"流程圖 箭頭{ka} 說明", center=False)
        yy += hh
    return cy + fh


def place_flow_spine(g, slide, s, x, y, w, h):
    """中軸式：置中的白底細框，中軸線上掛空心膠囊。"""
    G = g.G
    fig = s["flow"]["fig"]
    items = fig.get("items", [])
    opt = _ns_opt(g, fig)
    col = _ns_colors(g)
    avail = _ns_avail(g, y, h)
    PADX = 0.34
    tag_ink = G.D.get("tbl_first", "9A4618")
    cands = []
    for base in (30, 28, 26, 24):
        for pady, gap in ((0.16, 0.44), (0.10, 0.34), (0.07, 0.26)):
            nls = [_ns_lines(it["node"], base, opt.get("stack_en")) for it in items if "node" in it]
            nat = max([_tw(g, t_, sz, True) for nl in nls for t_, sz, _ in nl] or [1.0]) + 2 * PADX
            nw = min(max(nat, w * 0.56), w * 0.90)
            hs, wraps, k = [], 0, 0
            for it in items:
                if "node" in it:
                    nl = nls[k]; k += 1
                    n = [g.n_lines(t_, sz, nw - 2 * PADX, bold=True) for t_, sz, _ in nl]
                    wraps += sum(c - 1 for c in n)
                    hs.append(sum(c * _lh(sz) * 1.05 for c, (_, sz, _) in zip(n, nl)) + 2 * pady + 0.06)
                else:
                    lab = _ns_label(it.get("arrow", []))
                    hs.append((_ns_pill_size(g, lab, w * 0.9, 24)[1] + gap * 0.9) if lab else gap)
            cands.append((base, sum(hs), wraps, pady, nls, nw, hs))
    base, fh, _, pady, nls, nw, hs = _ns_fit(cands, avail)
    g.note_fit(s, fh, avail, "流程圖")
    G.layout[s["id"]][-1]["pt"] = base
    fx = x + max(0.0, (w - nw) / 2)
    cx = fx + nw / 2
    cy = y + max(0.0, min(0.35, (avail - fh) * 0.25))
    n_nodes, kn, ka = len(nls), 0, 0

    def vline(y1, y2, head, name):
        ln = _line_shape(slide, cx, y1, cx, y2)
        ln.line.color.rgb = g.C(col["navy"])
        ln.line.width = Pt(2.0)
        if head:
            e = ln.line._get_or_add_ln()
            e.append(e.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
        ln.name = name

    for it, hh in zip(items, hs):
        if "node" in it:
            kn += 1
            last = kn == n_nodes and n_nodes > 1 and opt.get("end", True)
            ghost = kn <= int(opt.get("carry", 0) or 0)
            _ns_shape(g, slide, MSO_SHAPE.ROUNDED_RECTANGLE, fx, cy, nw, hh, "E6EEF8" if last else (GHOST["fill"] if ghost else "FFFFFF"),
                      col["blue"] if last else col["line"], 1.75 if last else 0.75, f"流程圖 框{kn}" + ("（承上頁）" if ghost else ""), radius=0.08)
            tb, tf = g.textbox(slide, fx + PADX, cy, nw - 2 * PADX, hh, anchor=MSO_ANCHOR.MIDDLE)
            for q, (t_, sz, kind) in enumerate(nls[kn - 1]):
                if kind == "en":
                    g.para(tf, t_, sz, color=col["en"], align=PP_ALIGN.CENTER, first=(q == 0), line=1.05, space_after=0, markup=False, mute=False)
                else:
                    g.para(tf, t_, sz, color=(GHOST["ink"] if ghost else col["ink"]), bold=last, align=PP_ALIGN.CENTER, first=(q == 0), line=1.05,
                           space_after=0, mute=not ghost)
            tb.name = f"流程圖 框{kn} 文字"
            cy += hh
            continue
        ka += 1
        lab = _ns_label(it.get("arrow", []))
        if lab:
            pw, ph = _ns_pill_size(g, lab, w * 0.9, 24)
            ty = cy + (hh - ph) / 2
            if cy > y + 0.01 or kn:
                vline(cy + 0.02, ty, False, f"流程圖 箭頭{ka} 上段")
            vline(ty + ph, cy + hh - 0.03, True, f"流程圖 箭頭{ka}")
            _ns_shape(g, slide, MSO_SHAPE.ROUNDED_RECTANGLE, cx - pw / 2, ty, pw, ph, "FFFFFF", col["orange"], 1.25, f"流程圖 箭頭{ka} 說明框", radius=ph / 2)
            tb, tf = g.textbox(slide, cx - pw / 2 + NS["pill_pad"], ty, pw - 2 * NS["pill_pad"], ph, anchor=MSO_ANCHOR.MIDDLE)
            for q, t_ in enumerate(lab):
                g.para(tf, t_, 24, color=tag_ink, bold=True, align=PP_ALIGN.CENTER, first=(q == 0), line=1.0, space_after=0)
            tb.name = f"流程圖 箭頭{ka} 說明"
        else:
            vline(cy + 0.03, cy + hh - 0.03, True, f"流程圖 箭頭{ka}")
        cy += hh
    return cy


def _place_flow_branch(g, slide, s, x, y, w, h, fork):
    """merge（多格 → 一格）與 fork（一格 → 多格）。多的一邊把那個節點的每一行各排成一格。
    merge 可以帶 "carry": 1：最左邊多一格較窄的灰色格（上一頁的最後一格）→ 多格 → 結果。"""
    G = g.G
    fig = s["flow"]["fig"]
    items = fig.get("items", [])
    opt = _ns_opt(g, fig)
    carry = 0 if fork else int(opt.get("carry", 0) or 0)
    nodes = [it["node"] for it in items if "node" in it]
    body = nodes[carry:]
    multi = (body[1] if fork else body[0]) if len(body) == 2 else []
    if len(body) != 2 or len(multi) < 2 or carry > 1:
        return place_flow_stack(g, slide, s, x, y, w, h)
    col = _ns_colors(g)
    avail = _ns_avail(g, y, h)
    lab = next((_ns_label(it["arrow"]) for it in items if "arrow" in it and it.get("arrow")), [])
    single = body[0] if fork else body[1]
    GAP, PADX, PADY, BAR, VG = 1.05, 0.28, 0.20, 0.12, 0.26
    GW, GG = (2.55, 0.56) if carry else (0.0, 0.0)
    if carry:
        GAP = 0.90
    inner = w - GAP - GW - GG
    mw = inner * (0.54 if carry else 0.56)                       # 多格那一邊的寬
    sw = inner - mw
    ph_band = (_ns_pill_size(g, lab, w * 0.9, 24)[1] + 0.28) if lab else 0.0
    cands = []
    for base in (30, 28, 26, 24):
        m_n = [g.n_lines(t_, base, mw - 2 * PADX - BAR, bold=True) for t_ in multi]
        m_h = [c * _lh(base) * 1.05 + 2 * PADY + 0.04 for c in m_n]
        s_n = [g.n_lines(t_, base, sw - 2 * PADX, bold=True) for t_ in single]
        s_h = sum(c * _lh(base) * 1.05 + 4 / 72.0 for c in s_n) + 2 * (PADY + 0.10)
        fh = max(sum(m_h) + VG * (len(multi) - 1), s_h) + ph_band
        orph = sum(_orphan(g, t_, base, mw - 2 * PADX - BAR) for t_ in multi) + sum(_orphan(g, t_, base, sw - 2 * PADX) for t_ in single)
        cands.append((base, fh, max(m_n + s_n), m_h, s_h, orph))
    base, fh, _, m_h, s_h, _ = _ns_fit_cards(cands, avail)
    g.note_fit(s, fh, avail, "流程圖")
    G.layout[s["id"]][-1]["pt"] = base
    top = y + max(0.0, min(0.6, (avail - fh) * 0.30))
    x0 = x + GW + GG
    if lab:
        pw, ph = _ns_pill_size(g, lab, w * 0.9, 24)
        _ns_pill(g, slide, lab, x0 + (inner + GAP - pw) / 2, top, w * 0.9, 24, col, "流程圖 箭頭1 說明")
        top += ph_band
    body_h = max(sum(m_h) + VG * (len(multi) - 1), s_h)
    mx = (x0 + sw + GAP) if fork else x0
    sx = x0 if fork else (x0 + mw + GAP)
    solid = (not fork) and opt.get("end", True)

    def harrow(x1, x2, ay, name, pt=3.5, color=None):
        ln = _line_shape(slide, x1, ay, x2, ay)
        ln.line.color.rgb = g.C(color or col["navy"])
        ln.line.width = Pt(pt)
        e = ln.line._get_or_add_ln()
        e.append(e.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
        ln.name = name

    if carry:
        gh = min(body_h, max(1.6, sum(g.n_lines(t_, 24, GW - 0.44) for t_ in nodes[0]) * _lh(24) * 1.05 + 0.5))
        gy = top + (body_h - gh) / 2
        _ns_shape(g, slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, gy, GW, gh, GHOST["fill"], col["line"], 0.75, "流程圖 框1（承上頁）", radius=0.10)
        tb, tf = g.textbox(slide, x + 0.22, gy, GW - 0.44, gh, anchor=MSO_ANCHOR.MIDDLE)
        for q, t_ in enumerate(nodes[0]):
            g.para(tf, t_, 24, color=GHOST["ink"], first=(q == 0), line=1.05, space_after=0, mute=False)
        tb.name = "流程圖 框1 文字"
        harrow(x + GW + 0.14, x0 - 0.14, top + body_h / 2, "流程圖 箭頭1", pt=2.5, color=GHOST["bar"])
    # 單格那一邊：置中；merge 的結果格和多格那一疊等高
    sh_ = max(s_h, body_h * (0.62 if fork else 1.0))
    sy = top + (body_h - sh_) / 2
    kk = (1 if fork else len(multi) + 1) + carry
    _ns_shape(g, slide, MSO_SHAPE.ROUNDED_RECTANGLE, sx, sy, sw, sh_, col["navy"] if solid else "FFFFFF", None if solid else col["line"], 1.0,
              f"流程圖 框{kk}", radius=0.10)
    tb, tf = g.textbox(slide, sx + PADX, sy, sw - 2 * PADX, sh_, anchor=MSO_ANCHOR.MIDDLE)
    _ns_text(g, tf, [(t_, base, "zh") for t_ in single], col, solid, bold_zh=fork)
    tb.name = f"流程圖 框{kk} 文字"
    cy = top + (body_h - (sum(m_h) + VG * (len(multi) - 1))) / 2
    for i, (t_, hh) in enumerate(zip(multi, m_h)):
        k = ((i + 2) if fork else (i + 1)) + carry
        _ns_shape(g, slide, MSO_SHAPE.RECTANGLE, mx, cy, mw, hh, "FFFFFF", col["line"], 0.75, f"流程圖 框{k}")
        _ns_shape(g, slide, MSO_SHAPE.RECTANGLE, mx, cy, BAR, hh, col["blue"] if i % 2 == 0 else col["orange"], name=f"流程圖 框{k} 色帶")
        tb, tf = g.textbox(slide, mx + BAR + PADX, cy, mw - BAR - 2 * PADX, hh, anchor=MSO_ANCHOR.MIDDLE)
        _ns_text(g, tf, [(t_, base, "zh")], col, False, bold_zh=False)
        tb.name = f"流程圖 框{k} 文字"
        cy += hh + VG
    x1 = (x0 + sw) if fork else (x0 + mw)
    harrow(x1 + 0.20, x1 + GAP - 0.20, top + body_h / 2, f"流程圖 箭頭{1 + carry}")
    return top + body_h


def place_flow_merge(g, slide, s, x, y, w, h):
    return _place_flow_branch(g, slide, s, x, y, w, h, fork=False)


def place_flow_fork(g, slide, s, x, y, w, h):
    return _place_flow_branch(g, slide, s, x, y, w, h, fork=True)



def place_flow(g, slide, s, x, y, w, h):
    """在 (x, y, w, h) 畫 s["flow"]["fig"]。g＝gen_pptx 模組（借它的量字、文字、出處行與 G 設定）。回傳圖的底緣 y。"""
    G = g.G
    fl = s["flow"]
    fig = fl["fig"]
    if is_stages(fig):
        return place_stages(g, slide, s, x, y, w, h)
    # 樣式：這張圖的規格寫了 "style"（axis｜spine｜steps｜classic）就照它，沒寫照 course.yaml 的 layout.flow_style
    #（教師 2026-11-25 看了三種樣張：「各種方式交替使用」，所以同一份講義的流程圖可以一張一種）
    style = fig.get("style") or (getattr(G, "L", None) or {}).get("flow_style")
    if style == "axis":
        return place_flow_axis(g, slide, s, x, y, w, h)
    if style == "stack":
        return place_flow_stack(g, slide, s, x, y, w, h)
    if style == "spine":
        return place_flow_spine(g, slide, s, x, y, w, h)
    if style == "merge":
        return place_flow_merge(g, slide, s, x, y, w, h)
    if style == "fork":
        return place_flow_fork(g, slide, s, x, y, w, h)
    if style == "steps":
        return place_flow_steps(g, slide, s, x, y, w, h)
    if style == "timeline":
        return place_flow_timeline(g, slide, s, x, y, w, h)
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

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
    out = []
    for it in (fig or {}).get("items", []):
        if "node" in it:
            out += list(it["node"])
        else:
            out += ["".join(t for t, _ in _runs(ln)) for ln in it.get("arrow", [])]
    return [t for t in out if t]


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


def place_flow(g, slide, s, x, y, w, h):
    """在 (x, y, w, h) 畫 s["flow"]["fig"]。g＝gen_pptx 模組（借它的量字、文字、出處行與 G 設定）。回傳圖的底緣 y。"""
    G = g.G
    fl = s["flow"]
    fig = fl["fig"]
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

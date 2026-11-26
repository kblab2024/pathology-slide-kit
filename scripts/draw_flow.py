# -*- coding: utf-8 -*-
"""程式畫的流程圖（由上而下：階段框 → 箭頭旁寫變化 → 下一個框），給機轉、病程、治療流程這類張用。

教師 2026-10-14 明令（docs/教師偏好與決策.md 第 4 節）：「這種東西的名詞沒有中英對照是很危險的」「寧可多花一點張數，
也要把中英對照做好」。所以規格檔裡每個框、每行說明的專有名詞都寫「中文(English)」；一張放不下就拆成好幾張圖（每張一個 PNG），
不拿掉英文、不縮字。

排版單位 EM＝圖放進投影片版位後 24pt 的像素數（100 px）。版位寬預設 9.0 吋（big／flash 張的全寬圖區；left 張的圖欄約 4.4 吋），
高由每張圖的 slot_h 決定。畫完印出每種字放到投影片上的實際 pt；最小 < 24pt、或字超出畫布時印「要改」，要改規格（拆行、拆張）重畫。
字型：微軟正黑體（Windows 的 msjh／msjhbd，或 PowerPoint for Mac 內建的 MSJH／MSJHBD），找不到才用 PingFang。
配色：預設 kit 的 emphasis（藍 143F9C 給框、橘 ED7D31 給考點、紅 FF0000、灰 2E414F 給箭頭、ink 1E2A35）；給 --course 時改讀
該課 course.yaml 的 emphasis 藍／橘／紅／灰。橘每張 1–3 處（指南 14 的關鍵字份量）。

規格檔（JSON）：
{"slot_w": 9.0,
 "figures": {
   "<圖名>": {"slot_h": 6.05, "items": [
      {"node": ["前列腺上皮內腫瘤", "(prostatic intraepithelial neoplasia; PIN)"]},   框：第一行 26pt 粗，其餘 24pt 粗
      {"arrow": [                                                                    箭頭：右邊每個元素是一行
          ["p27 缺失(loss)"],                                                         一行＝一串 run；字串＝一般字
          [{"t": "TMPRSS2::ETS 融合基因(fusion gene)", "s": "o"}],                    s：b 粗、o 橘、red 紅、blue 藍
          {"inhibit": [{"t": "5α-還原酶抑制劑(5α-reductase inhibitor)", "s": "red"}]} 紅色 T 字線頂住箭頭（抑制）
      ]}]}}}
2026-11-25 起規格可以另寫："style"（timeline｜spine｜stack｜steps｜merge｜fork｜axis；slate 另有 cycle｜diamond｜sieve）、
"end": false（這一頁的最後一格不是終點）、"carry": 1（第一格是上一頁的最後一格）、"pill": "mid"、"stack_en": true；節點一律不編號
（AGENTS.md 硬規則 22，scripts/README.md「流程圖與表格的排法」）。最早的圓角框樣子不看這些；slate 樣子照它們畫（見下一段）。
2026-11-12 起（教師：「流程圖跟圖表盡量用powerpoint可編輯的排版」）：這支畫的 PNG 只給 HTML 版（html_deck.py）用；PPTX 上的流程圖由 gen_pptx 照同一份規格
畫成 PowerPoint 原生圖形（flow_shapes.py；素材池寫 <!-- flow: 規格.json#圖名 -->），教師可以直接改字。規格改了，兩邊都要重產。

slate 樣子（2026-11-26；course.yaml 的 layout.flow_look: slate，或 decks.<deck>.layout 只蓋那一講；docs/設計系統.md 第 4 節）：
HTML 版的流程圖要和 PPTX 長得一樣，所以這支不自己排版，而是叫 flow_shapes.place_flow 在一張暫時的投影片上畫原生圖形
（顏色、字級、排法、承上頁、膠囊都和 gen_pptx 同一套程式），再把那些圖形照座標畫成 PNG。九種排法都照規格的 "style"；
沒寫 style 用 layout.flow_style。底色用那一講的底色（decks.<deck>.background 或 slide.background），HTML 版上才不會多一塊白框。
圖區寬用規格的 "w"，沒寫就是投影片扣掉兩邊邊界（16:9 是 12.33 吋，和 PPTX 的 flash 張同寬；slot_w 只給最早的圓角框），高用 slot_h；
印出的字級、「要改」和 PPTX 的 check_deck 同一個意思（排不進 slot_h、放進圖區後小於 24pt；16pt 的「承上頁」不算）。
哪一張用哪一套：給 --course 時，每張圖照「用到它的那一講」的設定（sources/decks/<deck>.md 有那張的 flow 行）；幾講都用到而設定不同、
或沒有一講用到，照 --deck 那一講，沒給 --deck 就照課程的 layout。--look slate／classic 強制全部用一種。
沒開 slate 的課，畫出來的 PNG 和 2026-11-26 以前逐位元相同。中醫的辨證路徑（"kind": "stages"）不受影響。

用法：python draw_flow.py <規格.json> <輸出資料夾> [--course <課程>] [--deck <deck>] [--look slate|classic] [--only 圖名 …]
範例：uro-a3 的 _archive/build/flow_specs.json（#45–49 拆成三張、#77 睪固酮 → DHT）。
"""
import argparse
import copy
import json
import math
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont

ap = argparse.ArgumentParser(description="程式畫的中英對照流程圖")
ap.add_argument("spec"); ap.add_argument("outdir")
ap.add_argument("--course", help="讀該課 course.yaml 的 emphasis 配色")
ap.add_argument("--deck", help="照這一講的設定（decks.<deck>.layout／design／emphasis／background）畫它用到的圖；幾講共用的圖也照它")
ap.add_argument("--look", choices=["slate", "classic"], help="強制全部用這種樣子（slate＝2026-11-26 的設計，要配 --course；classic＝最早的圓角框）")
ap.add_argument("--only", nargs="*", default=[])
A = ap.parse_args()

hexc = lambda h: tuple(int(str(h).strip().lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
COL = {"blue": hexc("143F9C"), "or": hexc("ED7D31"), "red": hexc("FF0000"), "grey": hexc("2E414F"), "ink": hexc("1E2A35")}
if A.course:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import common
    emp = (common.load_course(A.course).get("emphasis") or {})
    for zh, k in (("藍", "blue"), ("橘", "or"), ("紅", "red"), ("灰", "grey")):
        if emp.get(zh):
            COL[k] = hexc(emp[zh])
TINT = hexc("EEF2FA") if COL["blue"] == hexc("143F9C") else tuple(round(255 - (255 - c) * 0.08) for c in COL["blue"])   # 框底色：藍的極淡色

FD = "/Applications/Microsoft PowerPoint.app/Contents/Resources/DFonts/"
WF = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
FB = next(p for p in [os.path.join(WF, "msjhbd.ttc"), FD + "MSJHBD.ttf", "/System/Library/Fonts/PingFang.ttc"] if os.path.exists(p))
FR = next(p for p in [os.path.join(WF, "msjh.ttc"), FD + "MSJH.ttf", "/System/Library/Fonts/PingFang.ttc"] if os.path.exists(p))
EM = 100
F = {"node": ImageFont.truetype(FB, int(EM * 26 / 24)), "node2": ImageFont.truetype(FB, EM),
     "r": ImageFont.truetype(FR, EM), "b": ImageFont.truetype(FB, EM)}
STYLE = {None: ("r", "ink"), "b": ("b", "ink"), "o": ("b", "or"), "red": ("b", "red"), "blue": ("b", "blue")}

SPEC = json.load(open(A.spec, encoding="utf-8"))
SLOT_W = float(SPEC.get("slot_w", 9.0))
W = int(SLOT_W * 3 * EM)
LINE = int(EM * 1.3)
X0 = int(EM * 0.3)                  # 框左緣
AX = X0 + int(EM * 1.2)             # 箭頭的 x（框靠左，箭頭在框的左段，說明寫在箭頭右邊）
LX = AX + int(EM * 0.7)             # 說明左緣


def runs_of(line):
    out = []
    for r in line:
        if isinstance(r, str):
            r = {"t": r}
        fk, ck = STYLE[r.get("s")]
        out.append((r["t"], F[fk], COL[ck]))
    return out


def draw_stages(name, spec):
    """分段路徑圖（"kind": "stages"，例：中醫系講義的辨證路徑）的 PNG，只給 HTML 版用。
    版面和 PPTX 的原生圖形同一份計算（flow_shapes.stages_plan）；規格可寫 "w"（圖寬，吋，預設 12.33＝16:9 投影片扣掉兩邊 0.5 吋）。"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import flow_shapes as fs
    P, PX = fs.ST, 3 * EM                      # 每吋 3×EM px（24pt 的字＝EM px，和 draw_fig 同一個比例）
    fnt = lambda size, bold: ImageFont.truetype(FB if bold else FR, int(round(EM * size / 24)))
    w_in = float(spec.get("w", 12.33))
    plan = fs.stages_plan(spec, w_in, lambda t, b: (F["b"] if b else F["r"]).getlength(t) / EM)
    m = 0.15
    im = Image.new("RGB", (int((w_in + 2 * m) * PX), int((plan["fh"] + 2 * m) * PX)), "white")
    d = ImageDraw.Draw(im)
    p = lambda v: int(round((v + m) * PX))
    hx = lambda c: tuple(int(c[k:k + 2], 16) for k in (0, 2, 4))
    blue = "%02X%02X%02X" % COL["blue"]
    stages = spec.get("stages", [])
    n, bh_, nt = len(stages), P["band_h"], P["notch"]
    by, bh = bh_ + P["band_gap"], plan["body_h"]
    lh = lambda size: size * 1.2 * P["line"] / 72.0
    for i, st in enumerate(stages):
        sx, sw = plan["xs"][i], plan["widths"][i]
        segw = sw + P["gap"] + nt - 0.05 if i < n - 1 else sw
        pts = [(sx, 0), (sx + segw - nt, 0), (sx + segw, bh_ / 2), (sx + segw - nt, bh_), (sx, bh_)]
        if i:
            pts.append((sx + nt, bh_ / 2))
        d.polygon([(p(a), p(b)) for a, b in pts], fill=hx(fs.stages_fill(blue, i, n, st.get("muted"))))
        d.text((p(sx + (segw + (nt if i else 0)) / 2 - nt / 2), p(bh_ / 2)), st.get("label", ""), font=fnt(P["label"], True),
               fill="white", anchor="mm")
        d.rectangle([p(sx), p(by), p(sx + sw), p(by + bh)], fill="white", outline=hx(fs.ST_HEX["box"]), width=3)
        if not st.get("steps"):
            yy = by + P["pad"]
            d.text((p(sx + P["pad"]), p(yy + lh(P["head"]) / 2)), st.get("head", ""), font=fnt(P["head"], True),
                   fill=COL["ink"], anchor="lm")
            yy += lh(P["head"])
            for ln in st.get("lines", []):
                d.text((p(sx + P["pad"]), p(yy + lh(P["base"]) / 2)), ln, font=fnt(P["base"], False), fill=COL["ink"], anchor="lm")
                yy += lh(P["base"])
            continue
        tx = sx + P["pad"]
        cx = tx + P["tag_w"] + P["tag_gap"]
        cy = by + P["pad"]
        steps = list(st["steps"]) + [dict(st.get("result") or {}, _result=True)]
        for k, sp in enumerate(steps):
            rh, last = plan["rows"][k], sp.get("_result", False)
            d.rounded_rectangle([p(tx), p(cy), p(tx + P["tag_w"]), p(cy + P["tag_h"])], radius=int(0.11 * PX),
                                fill=COL["or"] if last else hx(fs.ST_HEX["tag"]))
            d.text((p(tx + P["tag_w"] / 2), p(cy + P["tag_h"] / 2)), sp.get("tag", ""), font=fnt(P["tag"], True),
                   fill="white" if last else COL["blue"], anchor="mm")
            if last:
                d.text((p(cx), p(cy + P["tag_h"] / 2)), sp.get("text", ""), font=fnt(P["result"], True), fill=COL["or"], anchor="lm")
                break
            for q, ln in enumerate(sp.get("lines", [])):
                d.text((p(cx), p(cy + 0.045 + (q + 0.5) * lh(P["base"]))), ln, font=fnt(P["base"], False), fill=COL["ink"], anchor="lm")
            top, bot, mid = cy + P["tag_h"] + 0.04, cy + rh + P["row_gap"] - 0.04, tx + P["tag_w"] / 2
            d.rectangle([p(mid - 0.0125), p(top), p(mid + 0.0125), p(bot - 0.1)], fill=hx(fs.ST_HEX["conn"]))
            d.polygon([(p(mid - 0.08), p(bot - 0.12)), (p(mid + 0.08), p(bot - 0.12)), (p(mid), p(bot))], fill=hx(fs.ST_HEX["conn"]))
            cy += rh + P["row_gap"]
    out = os.path.join(A.outdir, name + ".png")
    im.save(out, optimize=True)
    warn = [] if plan["need_w"] <= plan["avail_w"] + 0.05 else [f"欄寬不夠（要 {plan['need_w']:.2f} 吋、只有 {plan['avail_w']:.2f}；減字或拆行）"]
    print(f"-> {out} {im.size}；分段路徑圖 {w_in:.2f}x{plan['fh']:.2f} 吋", "OK" if not warn else "要改：" + "；".join(warn))
    return not warn


def _no_soft_breaks(spec):
    """規格裡的段內換行「⏎」（flow_shapes.py 畫 PPTX 時用來指定框裡在哪裡折行）：這支畫 PNG 時，節點裡的當成另起一行，
    箭頭說明裡的換成空格（2026-11-25；原來會把這個字畫成方框、整行超出畫布）。不改傳進來的規格。"""
    SB = "\u23ce"

    def run(r):
        if isinstance(r, str):
            return r.replace(SB, " ")
        if isinstance(r, dict):
            return {k: (run(v) if k == "t" else ([run(x) for x in v] if k == "inhibit" and isinstance(v, list) else v)) for k, v in r.items()}
        if isinstance(r, list):
            return [run(x) for x in r]
        return r

    items = []
    for it in spec.get("items", []):
        if "node" in it:
            items.append({**it, "node": [p for t in it["node"] for p in str(t).split(SB) if p != ""]})
        else:
            items.append({**it, "arrow": [run(ln) for ln in it.get("arrow", [])]})
    return {**spec, "items": items}


# ---------------- slate 樣子（2026-11-26）----------------
# 做法：flow_shapes.place_flow 在暫時的投影片上畫原生圖形 → 逐個圖形照 XML 的座標、填色、框線、虛線、箭頭、文字畫進 PIL。
# 字的換行照 gen_pptx.n_lines 同一套切法（中文逐字、英文單字不拆），另外照 PowerPoint 不讓「，。）」這類標點落在行首。
PXI = 3 * EM                 # 每吋幾 px（24pt 的字＝EM px；和 draw_fig、draw_stages 同一個比例）
SS = 2                       # 先畫兩倍大再縮回來，框線與圓角比較不鋸齒
_FC = {}
_COURSE = []
_KIN = set("，。、；：！？）」』〉》】,.;:!?)]%")          # 不放在行首的標點


def _course():
    if not _COURSE:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import common
        _COURSE.append(common.load_course(A.course))
    return _COURSE[0]


def _deck_cfg(c, deck):
    return ((c.get("decks") or {}).get(deck) or {}) if deck else {}


def _look_of(c, deck):
    """這一講（deck＝None 就是課程本身）的 flow_look 是不是 slate。合併法和 gen_pptx.build_pptx 相同。"""
    L = dict(c.get("layout") or {})
    dk = _deck_cfg(c, deck)
    if isinstance(dk.get("layout"), dict):
        L.update(dk["layout"])
    return "slate" if L.get("flow_look") == "slate" else None


def resolve_looks(names):
    """{圖名: (樣子, deck)}；樣子是 "slate" 或 None（最早的圓角框）。規則見檔頭「slate 樣子」那一段。"""
    if A.look:
        if A.look == "slate" and not A.course:
            sys.exit("--look slate 要配 --course（顏色讀那門課的 course.yaml）")
        return {n: ("slate" if A.look == "slate" else None, A.deck) for n in names}
    if not A.course:
        return {n: (None, None) for n in names}
    c = _course()
    decks = list(c.get("decks") or {})
    if A.deck and A.deck not in decks:
        sys.exit(f"course.yaml 沒有 deck {A.deck}（有：{'、'.join(decks)}）")
    if not any(_look_of(c, d) for d in [None] + decks):
        return {n: (None, None) for n in names}           # 這門課沒有一講開 slate：照舊，不必展開選單
    import common
    used = {}
    for d in decks:
        try:
            used[d] = {s["flow"]["name"] for s in common.build_deck(c, d)["slides"] if s.get("flow")}
        except Exception as e:                            # 還沒有選單的講（例：還沒開工）
            print(f"[注意] deck {d} 的選單展不開（{e}），不算它用到的圖", file=sys.stderr)
            used[d] = set()
    out = {}
    for n in names:
        users = [d for d in decks if n in used[d]]
        if A.deck and A.deck in users:
            d = A.deck
        elif users and len({_look_of(c, u) for u in users}) == 1:
            d = users[0]
        elif not users and A.deck:
            d = A.deck
        else:
            d = None
        out[n] = (_look_of(c, d), d)
    return out


def _gen(deck):
    """gen_pptx 模組，G 照課程與這一講的設定填好（合併法和 gen_pptx.build_pptx 相同），flow_look 設成 slate。"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gen_pptx as g
    c = _course()
    g.setup(c)
    dk = _deck_cfg(c, deck)
    if isinstance(dk.get("layout"), dict):
        g.G.L = {**g.G.L, **dk["layout"]}
    if isinstance(dk.get("design"), dict):
        g.G.D = {**g.G.D, **dk["design"]}
    if isinstance(dk.get("emphasis"), dict):
        g.G.EMPH = {**g.G.EMPH, **dk["emphasis"]}
    if dk.get("background"):
        g.G.BG = str(dk["background"])
    g.G.L = {**g.G.L, "flow_look": "slate"}
    g.G.layout, g.G.src_h = {}, 0.0
    return g


def _pil_font(bold, px):
    k = (bold, int(px))
    if k not in _FC:
        _FC[k] = ImageFont.truetype(FB if bold else FR, max(1, int(px)))
    return _FC[k]


def _emu(v):
    return int(v) / 914400.0


def _solid(parent, qn):
    """parent 底下直接的 a:solidFill/a:srgbClr → (r, g, b)；a:noFill 或沒寫 → None。"""
    if parent is None:
        return None
    sf = parent.find(qn("a:solidFill"))
    c = sf.find(qn("a:srgbClr")) if sf is not None else None
    return hexc(c.get("val")) if c is not None else None


def _outline_pts(prst, w, h, adj):
    """形狀的外框（形狀自己的座標，吋）。認得 rect、roundRect、ellipse、triangle、homePlate、chevron；其他當方框。"""
    if prst == "roundRect":
        r = max(0.0, min(min(w, h) * adj.get("adj", 16667) / 100000.0, w / 2, h / 2))
        if r <= 1e-6:
            return [(0, 0), (w, 0), (w, h), (0, h)], True
        pts = []
        for cx, cy, a0 in ((w - r, r, -90), (w - r, h - r, 0), (r, h - r, 90), (r, r, 180)):
            for i in range(13):
                a = math.radians(a0 + 90 * i / 12)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        return pts, True
    if prst == "ellipse":
        return [(w / 2 + w / 2 * math.cos(2 * math.pi * i / 96), h / 2 + h / 2 * math.sin(2 * math.pi * i / 96)) for i in range(96)], True
    if prst == "triangle":
        ax = w * adj.get("adj", 50000) / 100000.0
        return [(ax, 0), (w, h), (0, h)], True
    if prst in ("homePlate", "chevron"):
        a = min(w, h) * adj.get("adj", 50000) / 100000.0
        pts = [(0, 0), (w - a, 0), (w, h / 2), (w - a, h), (0, h)]
        return (pts + [(a, h / 2)] if prst == "chevron" else pts), True
    return [(0, 0), (w, 0), (w, h), (0, h)], prst == "rect"


def _dashed(d, pts, col, lw, on, off):
    """沿著折線畫虛線（線段長 on、間隔 off，px）。"""
    draw_on, left = True, on
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        seg = math.hypot(x2 - x1, y2 - y1)
        t = 0.0
        while t < seg - 1e-9:
            step = min(left, seg - t)
            if draw_on:
                d.line([(x1 + (x2 - x1) * t / seg, y1 + (y2 - y1) * t / seg),
                        (x1 + (x2 - x1) * (t + step) / seg, y1 + (y2 - y1) * (t + step) / seg)], fill=col, width=lw)
            t += step
            left -= step
            if left <= 1e-9:
                draw_on = not draw_on
                left = on if draw_on else off


def _head(d, tip, frm, lw, col):
    """線端的三角箭頭（PowerPoint 的 triangle、med 約是線寬的 3 倍；LibreOffice 算圖畫得大一點，這裡取 3.5 倍）。
    回傳線該畫到哪裡（不從箭頭尖端穿出去）。"""
    dx, dy = tip[0] - frm[0], tip[1] - frm[1]
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n
    ln_, hw = 3.5 * lw, 1.75 * lw
    bx, by = tip[0] - ux * ln_, tip[1] - uy * ln_
    d.polygon([tip, (bx - uy * hw, by + ux * hw), (bx + uy * hw, by - ux * hw)], fill=col)
    return (bx + ux * ln_ * 0.3, by + uy * ln_ * 0.3)


def _draw_text(d, g, body, box, S, used, warns, name):
    """txBody 的字：照 bodyPr 的內距、垂直對齊，段落的對齊、行距、段後距，run 的字級、粗細、顏色畫。"""
    qn = _QN[0]
    bp = body.find(qn("a:bodyPr"))
    ins = lambda k, dv: _emu(bp.get(k, dv)) if bp is not None else _emu(dv)
    li, ti, ri, bi = ins("lIns", 91440), ins("tIns", 45720), ins("rIns", 91440), ins("bIns", 45720)
    anchor = (bp.get("anchor") if bp is not None else None) or "t"
    wrap = (bp.get("wrap") if bp is not None else None) != "none"
    x, y, w, h = box
    aw = (w - li - ri) * S
    paras = []
    for p in body.findall(qn("a:p")):
        ppr = p.find(qn("a:pPr"))
        algn = (ppr.get("algn") if ppr is not None else None) or "l"
        spc, aft, bef, abs_pt = 1.0, 0.0, 0.0, None
        if ppr is not None:
            ls = ppr.find(qn("a:lnSpc"))
            if ls is not None and ls.find(qn("a:spcPct")) is not None:
                spc = int(ls.find(qn("a:spcPct")).get("val")) / 100000.0
            elif ls is not None and ls.find(qn("a:spcPts")) is not None:
                abs_pt = int(ls.find(qn("a:spcPts")).get("val")) / 100.0
            for tag, k in (("a:spcAft", "aft"), ("a:spcBef", "bef")):
                e = ppr.find(qn(tag))
                pts_ = e.find(qn("a:spcPts")) if e is not None else None
                if pts_ is not None:
                    v = int(pts_.get("val")) / 100.0 / 72.0 * S
                    aft, bef = (v, bef) if k == "aft" else (aft, v)
        toks = []
        for el in p:
            if el.tag == qn("a:r"):
                rpr = el.find(qn("a:rPr"))
                tt = el.findtext(qn("a:t")) or ""
                pt = int(rpr.get("sz", "1800")) / 100.0 if rpr is not None else 18.0
                bold = rpr is not None and rpr.get("b") in ("1", "true")
                col = _solid(rpr, qn) or (0, 0, 0)
                f = _pil_font(bold, round(pt * PXI / 72.0 * SS))
                if tt.strip() and tt.strip() != "承上頁":          # 「承上頁」是 16pt 的小標（check_deck 也放行），不算進最小字級
                    used.append(pt)
                toks += [(t_, f, col, pt, bold) for t_ in g._TOK.findall(tt)]
            elif el.tag == qn("a:br"):
                toks.append(None)
        epr = p.find(qn("a:endParaRPr"))
        end_pt = int(epr.get("sz", "1800")) / 100.0 if epr is not None else 18.0
        lines, cur, cw = [], [], 0.0
        for tk in toks:
            if tk is None:
                lines.append(cur)
                cur, cw = [], 0.0
                continue
            tw = g._w(tk[0], tk[4]) * tk[3] / 72.0 * S     # 和 gen_pptx.n_lines 同一把尺，框的高才對得上
            if tk[0].isspace():
                if cur:
                    cur.append((tk, tw))
                    cw += tw
                continue
            if wrap and tw > aw + 1e-6 and len(tk[0]) > 1:   # 比一整行還長的詞：先換行再逐字斷（PowerPoint 與 n_lines 都這樣）
                while cur and cur[-1][0][0].isspace():
                    cur.pop()
                if cur:
                    lines.append(cur)
                cur, cw = [], 0.0
                for ch in tk[0]:
                    chw = g._w(ch, tk[4]) * tk[3] / 72.0 * S
                    if cur and cw + chw > aw + 1e-6:
                        lines.append(cur)
                        cur, cw = [], 0.0
                    cur.append(((ch,) + tk[1:], chw))
                    cw += chw
                continue
            if not cur or not wrap or cw + tw <= aw + 1e-6:
                cur.append((tk, tw))
                cw += tw
                continue
            carry = []
            if tk[0][0] in _KIN and len(cur) > 1 and not cur[-1][0][0].isspace():
                carry = [cur.pop()]                      # 標點不落在行首：前一個字跟著換行
            while cur and cur[-1][0][0].isspace():
                cur.pop()
            lines.append(cur)
            cur = carry + [(tk, tw)]
            cw = sum(v for _, v in cur)
        lines.append(cur)
        paras.append((algn, spc, abs_pt, bef, aft, lines, end_pt))
    rows, total = [], 0.0
    for i, (algn, spc, abs_pt, bef, aft, lines, end_pt) in enumerate(paras):
        total += bef
        for ln in lines:
            while ln and ln[-1][0][0].isspace():
                ln.pop()
            pmax = max([tk[3] for tk, _ in ln] or [end_pt])
            pitch = (abs_pt / 72.0 if abs_pt else pmax * 1.2 * spc / 72.0) * S
            rows.append((algn, ln, total, pitch))
            total += pitch
        if i < len(paras) - 1:
            total += aft
    room = (h - ti - bi) * S
    if anchor == "ctr":
        y0 = (y + ti) * S + (room - total) / 2
    elif anchor == "b":
        y0 = (y + h - bi) * S - total
    else:
        y0 = (y + ti) * S
    if total > room + 0.10 * S:
        warns.append(f"{name}：框裡的字比框高 {(total - room) / S:.2f} 吋")
    for algn, ln, top, pitch in rows:
        if not ln:
            continue
        lw = sum(v for _, v in ln)
        if lw > aw + 2:
            warns.append(f"{name}：有一行字比框寬 {(lw - aw) / S:.2f} 吋")
        x0 = (x + li) * S + ((aw - lw) / 2 if algn == "ctr" else ((aw - lw) if algn == "r" else 0.0))
        fmax = max((tk[1] for tk, _ in ln), key=lambda f: f.size)
        asc, dsc = fmax.getmetrics()
        base = y0 + top + (pitch - (asc + dsc)) / 2 + asc
        for (t_, f, col, _, _), tw in ln:
            if not t_.isspace():
                d.text((x0, base), t_, font=f, fill=col, anchor="ls")
            x0 += tw


_QN = []


def _draw_sp(d, g, sp, S, used, warns):
    """一個 p:sp（框、線、文字方塊）畫進 PIL。"""
    qn = _QN[0]
    spPr = sp.find(qn("p:spPr"))
    xf = spPr.find(qn("a:xfrm")) if spPr is not None else None
    if xf is None:
        return
    off, ext = xf.find(qn("a:off")), xf.find(qn("a:ext"))
    x, y, w, h = _emu(off.get("x")), _emu(off.get("y")), _emu(ext.get("cx")), _emu(ext.get("cy"))
    rot = math.radians(int(xf.get("rot", "0")) / 60000.0)
    fh, fv = xf.get("flipH") == "1", xf.get("flipV") == "1"
    pg = spPr.find(qn("a:prstGeom"))
    prst = pg.get("prst") if pg is not None else "rect"
    adj = {}
    for gd in (pg.iter(qn("a:gd")) if pg is not None else []):
        try:
            adj[gd.get("name")] = int(gd.get("fmla").split()[1])
        except Exception:
            pass
    nm = sp.find(qn("p:nvSpPr")).find(qn("p:cNvPr")).get("name", "") if sp.find(qn("p:nvSpPr")) is not None else ""
    fill = _solid(spPr, qn)
    ln = spPr.find(qn("a:ln"))
    lcol = _solid(ln, qn) if (ln is not None and ln.find(qn("a:noFill")) is None) else None
    lw = max(1, round(_emu(ln.get("w", "12700")) * S)) if ln is not None else 1
    dash = None
    if ln is not None and ln.find(qn("a:prstDash")) is not None:
        dash = {"dash": (4, 3), "sysDash": (3, 1), "lgDash": (8, 3), "sysDot": (1, 1), "dot": (1, 1)}.get(ln.find(qn("a:prstDash")).get("val"))

    def place(px_, py_):                                   # 形狀座標（吋）→ 畫布 px：翻轉、旋轉（繞中心、順時針）、平移
        if fh:
            px_ = w - px_
        if fv:
            py_ = h - py_
        if rot:
            cx, cy = w / 2, h / 2
            px_, py_ = (cx + (px_ - cx) * math.cos(rot) - (py_ - cy) * math.sin(rot),
                        cy + (px_ - cx) * math.sin(rot) + (py_ - cy) * math.cos(rot))
        return ((x + px_) * S, (y + py_) * S)

    if prst == "line":
        a, b = place(0, 0), place(w, h)
        if lcol:
            tail = ln.find(qn("a:tailEnd")) if ln is not None else None
            headE = ln.find(qn("a:headEnd")) if ln is not None else None
            if tail is not None and tail.get("type", "none") != "none":
                b = _head(d, b, a, lw, lcol)
            if headE is not None and headE.get("type", "none") != "none":
                a = _head(d, a, b, lw, lcol)
            if dash:
                _dashed(d, [a, b], lcol, lw, dash[0] * lw, dash[1] * lw)
            else:
                d.line([a, b], fill=lcol, width=lw)
    elif w > 0 and h > 0:
        pts, known = _outline_pts(prst, w, h, adj)
        if not known and (fill or lcol):
            warns.append(f"{nm}：不認得的形狀 {prst}，當方框畫")
        poly = [place(px_, py_) for px_, py_ in pts]
        if fill:
            d.polygon(poly, fill=fill)
        if lcol:
            if dash:
                _dashed(d, poly + [poly[0]], lcol, lw, dash[0] * lw, dash[1] * lw)
            else:
                d.line(poly + [poly[0]], fill=lcol, width=lw, joint="curve")
    body = sp.find(qn("p:txBody"))
    if body is not None and "".join(t_.text or "" for t_ in body.iter(qn("a:t"))).strip():
        _draw_text(d, g, body, (x, y, w, h), S, used, warns, nm)


def draw_slate(name, spec, deck):
    """slate 樣子：照 flow_shapes 的排法畫原生圖形，再畫成 PNG（見檔頭「slate 樣子」）。"""
    from PIL.PngImagePlugin import PngInfo
    from pptx import Presentation
    from pptx.oxml.ns import qn
    from pptx.util import Inches
    _QN[:] = [qn]
    g = _gen(deck)
    import flow_shapes as fs
    G = g.G
    # 圖區的寬：規格的 "w"（吋），沒寫就是投影片扣掉兩邊邊界（16:9 是 12.33，和 PPTX 的 flash／big 張同寬，字級與折行才會一樣；
    # 和 draw_stages 同一個慣例）。slot_w 是最早的圓角框用的，不看。圖區的高＝slot_h（flow_shapes 用 G.SH 算可以用多高）。
    m, w_in, h_in = 0.2, float(spec.get("w") or (G.SW - 2 * G.M)), float(spec.get("slot_h", 5.0))
    G.SH = m + h_in + 0.10
    cw_in, ch_in = w_in + 2 * m + 1.5, h_in + 2 * m + 1.5
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(cw_in), Inches(ch_in)
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    s = {"id": name, "title": name, "flow": {"fig": copy.deepcopy(spec), "src": "", "name": name}, "imgs": []}
    fs.place_flow(g, slide, s, m, m, w_in, h_in)
    bg = hexc(G.BG)
    S = PXI * SS
    im = Image.new("RGB", (int(cw_in * S), int(ch_in * S)), bg)
    d = ImageDraw.Draw(im)
    used, warns = [], []
    for sp in slide.shapes._spTree.iterchildren(qn("p:sp")):
        _draw_sp(d, g, sp, S, used, warns)
    im = im.reduce(SS)
    Wc, Hc = im.size
    bbox = ImageChops.difference(im, Image.new("RGB", im.size, bg)).getbbox() or (0, 0, Wc, Hc)
    if bbox[2] >= Wc - 2 or bbox[3] >= Hc - 2:
        warns.append("圖超出暫時的畫布（拆行或拆張）")
    for e in G.layout.get(name, []):
        if e.get("overflow"):
            warns.append(f"排不進 {h_in} 吋高（要 {e['need_in']} 吋；拆行或拆張）")
    mm = int(EM * 0.3)
    # 放進圖區（w_in × h_in）後的字級：用圖本身的範圍量（不含四周的留白；框線多出圖區 0.05 吋以內不算），和 PPTX 的字級同一個意思
    k = min((w_in + 0.05) * PXI / (bbox[2] - bbox[0]), (h_in + 0.05) * PXI / (bbox[3] - bbox[1]))
    pts = sorted({round(p * k, 1) for p in used})
    if pts and min(pts) < 24:
        warns.append(f"最小 {min(pts)}pt（拆行或拆張）")
    im = im.crop((max(0, bbox[0] - mm), max(0, bbox[1] - mm), min(Wc, bbox[2] + mm), min(Hc, bbox[3] + mm)))
    out = os.path.join(A.outdir, name + ".png")
    info = PngInfo()
    info.add_text("flow_look", "slate")                     # html_deck.py 用它認出這張已經是 slate 樣子
    info.add_text("deck", deck or "")
    im.save(out, optimize=True, pnginfo=info)
    style = spec.get("style") or (G.L.get("flow_style") or "最早的排法")
    print(f"-> {out} {im.size}；slate {style}（{'deck ' + deck if deck else '課程設定'}）；放進 {w_in:.2f}x{h_in} 吋顯示 "
          f"{(bbox[2] - bbox[0]) * k / PXI:.2f}x{(bbox[3] - bbox[1]) * k / PXI:.2f} 吋；字級 pt {pts}",
          "OK" if not warns else "要改：" + "；".join(warns))
    return not warns


def draw_fig(name, spec):
    if spec.get("kind") == "stages":
        return draw_stages(name, spec)
    look, deck = LOOK.get(name, (None, None))
    if look == "slate":
        return draw_slate(name, spec, deck)
    spec = _no_soft_breaks(spec)
    H = int(spec["slot_h"] * 3 * EM * 1.6)
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    used = []

    def tw(t, f):
        l, tp, rr, bb = d.textbbox((0, 0), t, font=f)
        return rr - l

    def put(x, y, rs):
        for t, f, c in rs:
            l, tp, rr, bb = d.textbbox((0, 0), t, font=f)
            d.text((x - l, y), t, font=f, fill=c)
            x += rr - l
            used.append(f.size)

    nodes = [it["node"] for it in spec["items"] if "node" in it]
    BW = max(tw(t, F["node" if i == 0 else "node2"]) for n in nodes for i, t in enumerate(n)) + int(EM * 1.0)
    y = int(EM * 0.3)
    for it in spec["items"]:
        if "node" in it:
            fs = [F["node" if i == 0 else "node2"] for i in range(len(it["node"]))]
            hs = [int(f.size * 1.25) for f in fs]
            bh = sum(hs) + int(EM * 0.45)
            d.rounded_rectangle((X0, y, X0 + BW, y + bh), radius=int(EM * 0.3), outline=COL["blue"], width=int(EM * 0.08), fill=TINT)
            yy = y + int(EM * 0.22)
            for t, f, h in zip(it["node"], fs, hs):
                l, tp, rr, bb = d.textbbox((0, 0), t, font=f)
                d.text((X0 + BW / 2 - (rr - l) / 2 - l, yy + (h - (bb - tp)) / 2 - tp), t, font=f, fill=COL["blue"])
                used.append(f.size)
                yy += h
            y += bh
        else:
            lines = it["arrow"]
            gap = len(lines) * LINE + int(EM * 0.5)
            y0, y1 = y + EM * 0.08, y + gap - EM * 0.08
            d.line((AX, y0, AX, y1 - EM * 0.25), fill=COL["grey"], width=int(EM * 0.1))
            L, sp = EM * 0.38, math.radians(28)
            d.polygon([(AX, y1), (AX - L * math.sin(sp), y1 - L * math.cos(sp)), (AX + L * math.sin(sp), y1 - L * math.cos(sp))], fill=COL["grey"])
            ly = y + int(EM * 0.25)
            for k, line in enumerate(lines):
                yy = ly + k * LINE
                if isinstance(line, dict) and "inhibit" in line:
                    cy = yy + EM * 0.62
                    d.line((AX + EM * 0.12, cy, LX + EM * 0.2, cy), fill=COL["red"], width=int(EM * 0.1))
                    d.line((AX + EM * 0.12, cy - EM * 0.32, AX + EM * 0.12, cy + EM * 0.32), fill=COL["red"], width=int(EM * 0.12))
                    put(LX + EM * 0.4, yy, runs_of(line["inhibit"]))
                else:
                    put(LX, yy, runs_of(line))
            y += gap
    bbox = ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()
    warn = ["字超出畫布右緣（拆行）"] if bbox[2] >= W - 2 else []
    if bbox[3] >= H - 2:
        warn.append("超出畫布下緣（拆張）")
    m = int(EM * 0.3)
    im = im.crop((max(0, bbox[0] - m), max(0, bbox[1] - m), min(W, bbox[2] + m), min(H, bbox[3] + m)))
    out = os.path.join(A.outdir, name + ".png")
    im.save(out, optimize=True)
    w_px, h_px = im.size
    k = min(SLOT_W / w_px, spec["slot_h"] / h_px)
    pts = sorted({round(px * k * 72, 1) for px in used})
    if min(pts) < 24:
        warn.append(f"最小 {min(pts)}pt（拆行或拆張）")
    print(f"-> {out} {im.size}；放進 {SLOT_W}x{spec['slot_h']} 吋顯示 {w_px * k:.2f}x{h_px * k:.2f} 吋；字級 pt {pts}",
          "OK" if not warn else "要改：" + "；".join(warn))
    return not warn


os.makedirs(A.outdir, exist_ok=True)
LOOK = resolve_looks([n for n in SPEC["figures"] if not A.only or n in A.only])
bad = [n for n, s in SPEC["figures"].items() if (not A.only or n in A.only) and not draw_fig(n, s)]
sys.exit(1 if bad else 0)

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
2026-11-25 起規格可以另寫（只有 flow_shapes.py 畫 PPTX 時看；這支畫 PNG 時不看）："style"（timeline｜spine｜stack｜steps｜merge｜fork｜axis）、
"end": false（這一頁的最後一格不是終點）、"carry": 1（第一格是上一頁的最後一格）、"pill": "mid"、"stack_en": true；節點一律不編號
（AGENTS.md 硬規則 22，scripts/README.md「流程圖與表格的排法」）。
2026-11-12 起（教師：「流程圖跟圖表盡量用powerpoint可編輯的排版」）：這支畫的 PNG 只給 HTML 版（html_deck.py）用；PPTX 上的流程圖由 gen_pptx 照同一份規格
畫成 PowerPoint 原生圖形（flow_shapes.py；素材池寫 <!-- flow: 規格.json#圖名 -->），教師可以直接改字。規格改了，兩邊都要重產。

用法：python draw_flow.py <規格.json> <輸出資料夾> [--course <課程>] [--only 圖名 …]
範例：uro-a3 的 _archive/build/flow_specs.json（#45–49 拆成三張、#77 睪固酮 → DHT）。
"""
import argparse
import json
import math
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont

ap = argparse.ArgumentParser(description="程式畫的中英對照流程圖")
ap.add_argument("spec"); ap.add_argument("outdir")
ap.add_argument("--course", help="讀該課 course.yaml 的 emphasis 配色")
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


def draw_fig(name, spec):
    if spec.get("kind") == "stages":
        return draw_stages(name, spec)
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
bad = [n for n, s in SPEC["figures"].items() if (not A.only or n in A.only) and not draw_fig(n, s)]
sys.exit(1 if bad else 0)

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


def draw_fig(name, spec):
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

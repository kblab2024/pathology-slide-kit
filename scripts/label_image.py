# -*- coding: utf-8 -*-
"""示意圖加標籤（標準做法：Runway 只產沒有字的母圖，標籤由做投影片的代理設計、用這支程式疊上）。

教師 2026-10-14 明令（docs/教師偏好與決策.md 第 4 節）：
  - 「先 Runway 產母圖，之後由 Claude 設計並加上文字 label 的作法字最清晰，請把這種作法設為標準」（headneck-dent 的經驗）。
  - 專有名詞一律「中文(English)」。所以每個標籤兩行：第一行中文、第二行（English），同字級；標題一行「中文(English)」。
不讓影像模型寫字：模型的字常錯、會糊；這支用微軟正黑體畫，字永遠清楚、可改。

做法：
  1. 讀母圖（PNG／JPG，沒有字），依 margins 在四周加白邊（標籤放白邊，不壓在組織上）。
  2. 字級以投影片上的大小換算：px＝pt／72 × 輸出圖寬 px ÷ 版位寬吋（slot_w）。預設標籤 24pt、標題 28pt；低於 24pt 拒絕。
  3. 每個標籤：文字框靠在指定的邊（left／right／top／bottom 白邊，或 at 指定位置），引線從文字框邊緣拉到 point（母圖上的構造，
     以母圖寬高的比例 0–1 表示），終點畫實心圓點；引線可有一個轉折（elbow）。壓在組織上的標籤用 box: true（白色圓角底）。
  4. 檢查：標籤彼此重疊、超出畫布、引線交叉、字級 < 24pt，都印「要改」並以結束碼 1 結束（圖仍會輸出，方便看哪裡要調）。

規格（JSON）：
{"image": "<母圖>", "out": "<輸出.png>", "slot_w": 9.0,
 "margins": {"left": 0.22, "right": 0.22, "top": 0.10, "bottom": 0.0},   白邊，各為母圖寬（左右）或高（上下）的比例
 "label_pt": 24, "title_pt": 28,
 "halo": false,                                                          true：引線與圓點底下墊白邊（壓在深色組織上、例如骨髓，引線才看得清楚）
 "titles": [{"text": "帽狀期(cap stage)", "x": 0.25, "y": -0.05}],      x、y：母圖座標比例（y 負值＝上方白邊），文字置中
 "labels": [
   {"zh": "琺瑯器", "en": "enamel organ", "point": [0.31, 0.52], "side": "left", "y": 0.50},
   {"zh": "真皮", "en": "dermis", "at": [0.30, 0.88], "box": true}           at：文字框中心（母圖座標比例），不畫引線
 ]}
  at 的標籤預設墊白色圓角底；放在圖的空白處、不需要墊底時寫 "box": false。
  at 加 point：文字框放在 at，再從文字框的邊拉一條直線到 point（程式畫的圖在圖裡留空白放標籤時用，不必加白邊）。
  每個標籤可以另寫 "pt"（字級，不得低於 24）、"bold": true、"color": "六碼色碼"（例：圖上的編號 1–5、算式 3+4=7 用大一點的粗體）。
  "brackets": [{"text": "a", "x": -0.03, "y0": 0.10, "y1": 0.92, "side": "left", "color": "C0392B"}]：括線（豎線在 x、從 y0 到 y1，
    兩端各一小橫指向圖、長 tick 吋（預設 0.14），字在 side 那一側；可寫 zh/en 代替 text、pt、bold（預設粗體）、dy（字沿豎線上下移，
    以括線長度的比例）），例：Reid 指數的 a（上皮到軟骨）與 b（腺體層）。
  同一份規格也可以畫成 PowerPoint 原生的文字方塊（文字方塊版）：素材池寫 <!-- labels: 規格.json -->，見 label_shapes.py。
  side＝left／right：文字框貼左／右白邊、垂直中心在 y；side＝top／bottom：文字框水平中心在 x、貼上／下白邊。
  elbow：true（預設）＝引線先水平再斜；false＝直線。
用法：python label_image.py <規格.json> [--preview <縮圖.png>]
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser(description="示意圖加中英對照標籤（引線＋圓點），字級以投影片版位換算")
ap.add_argument("spec")
ap.add_argument("--preview", help="另存一張長邊 1600 px 的縮圖")
A = ap.parse_args()
S = json.load(open(A.spec, encoding="utf-8"))
base = os.path.dirname(os.path.abspath(A.spec))
P = lambda p: p if os.path.isabs(p) else os.path.join(base, p)

FD = "/Applications/Microsoft PowerPoint.app/Contents/Resources/DFonts/"
WF = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
FR = next(p for p in [os.path.join(WF, "msjh.ttc"), FD + "MSJH.ttf", "/System/Library/Fonts/PingFang.ttc"] if os.path.exists(p))
FB = next(p for p in [os.path.join(WF, "msjhbd.ttc"), FD + "MSJHBD.ttf", "/System/Library/Fonts/PingFang.ttc"] if os.path.exists(p))
INK = (0x1E, 0x2A, 0x35)

src = Image.open(P(S["image"])).convert("RGBA")
bg = Image.new("RGBA", src.size, "white")
src = Image.alpha_composite(bg, src).convert("RGB")          # 透明背景一律鋪白
w0, h0 = src.size
M = {k: float((S.get("margins") or {}).get(k, 0)) for k in ("left", "right", "top", "bottom")}
L, R, T, B = int(w0 * M["left"]), int(w0 * M["right"]), int(h0 * M["top"]), int(h0 * M["bottom"])
W, H = w0 + L + R, h0 + T + B
im = Image.new("RGB", (W, H), "white")
im.paste(src, (L, T))
d = ImageDraw.Draw(im)

slot_w = float(S.get("slot_w", 9.0))
px_per_pt = W / slot_w / 72.0
lab_pt, tit_pt = float(S.get("label_pt", 24)), float(S.get("title_pt", 28))
problems = []
if lab_pt < 24 or tit_pt < 24:
    problems.append(f"字級設定低於 24pt（label {lab_pt}、title {tit_pt}）")
f_lab = ImageFont.truetype(FR, max(8, round(lab_pt * px_per_pt)))
f_tit = ImageFont.truetype(FB, max(8, round(tit_pt * px_per_pt)))
LINE = round(f_lab.size * 1.18)
PAD = round(f_lab.size * 0.35)
LW = max(2, round(f_lab.size * 0.06))
DOT = max(4, round(f_lab.size * 0.16))
HALO = max(2, round(LW * 1.2)) if S.get("halo") else 0      # 白邊寬（每側）

to_px = lambda x, y: (L + x * w0, T + y * h0)                # 母圖比例 → 畫布像素


def text_box(lines, font, line=None):
    line = line or LINE
    ws = [d.textbbox((0, 0), t, font=font) for t in lines]
    return max(b[2] - b[0] for b in ws), line * len(lines)


def draw_lines(x0, y0, lines, font, align="left", wbox=None, line=None, fill=INK):
    line = line or LINE
    for i, t in enumerate(lines):
        l, tp, r, b = d.textbbox((0, 0), t, font=font)
        tw = r - l
        x = x0 if align == "left" else (x0 + (wbox - tw) if align == "right" else x0 + (wbox - tw) / 2)
        d.text((x - l, y0 + i * line + (line - (b - tp)) / 2 - tp), t, font=font, fill=fill)


def hexcolor(c):
    c = str(c or "")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) if len(c) == 6 and all(ch in "0123456789abcdefABCDEF" for ch in c) else INK


boxes, segs = [], []
f_lab0, LINE0, PAD0 = f_lab, LINE, PAD
for t in S.get("titles", []):
    tw_, th_ = text_box([t["text"]], f_tit)
    cx, cy = to_px(t["x"], t["y"])
    x0, y0 = cx - tw_ / 2, cy - th_ / 2
    l, tp, r, b = d.textbbox((0, 0), t["text"], font=f_tit)
    d.text((x0 - l, y0 + (th_ - (b - tp)) / 2 - tp), t["text"], font=f_tit, fill=INK)
    boxes.append(("標題 " + t["text"], (x0, y0, x0 + tw_, y0 + th_)))

for lb in S.get("labels", []):
    lines = [lb["zh"]] + ([f"({lb['en']})"] if lb.get("en") else [])
    name = lines[0]
    pt_, bold_ = float(lb.get("pt", lab_pt)), bool(lb.get("bold"))
    if pt_ < 24:
        problems.append(f"「{name}」字級 {pt_}pt 低於 24pt")
    if pt_ != lab_pt or bold_ or lb.get("color"):             # 這個標籤自己的字級、粗體、顏色
        f_lab = ImageFont.truetype(FB if bold_ else FR, max(8, round(pt_ * px_per_pt)))
    else:
        f_lab = f_lab0
    LINE, PAD, ink = round(f_lab.size * 1.18), round(f_lab.size * 0.35), hexcolor(lb.get("color"))
    tw_, th_ = text_box(lines, f_lab, LINE)
    if "at" in lb:                                            # 指定位置、不畫引線；預設墊白色圓角底（壓在組織上），"box": false 不墊
        cx, cy = to_px(*lb["at"])
        x0, y0 = cx - tw_ / 2, cy - th_ / 2
        if lb.get("box", True):
            d.rounded_rectangle((x0 - PAD, y0 - PAD / 2, x0 + tw_ + PAD, y0 + th_ + PAD / 2), radius=PAD, fill="white")
            boxes.append((name, (x0 - PAD, y0 - PAD / 2, x0 + tw_ + PAD, y0 + th_ + PAD / 2)))
        else:
            boxes.append((name, (x0, y0, x0 + tw_, y0 + th_)))
        draw_lines(x0, y0, lines, f_lab, "center", tw_, LINE, ink)
        if "point" in lb:                                     # 從文字框的邊拉直線到 point
            px, py = to_px(*lb["point"])
            hw, hh = tw_ / 2 + PAD, th_ / 2 + PAD / 2
            ddx, ddy = px - cx, py - cy
            if abs(ddx) > hw or abs(ddy) > hh:
                tt = min(hw / abs(ddx) if ddx else 1e9, hh / abs(ddy) if ddy else 1e9)
                a = (cx + ddx * tt, cy + ddy * tt)
                if HALO:
                    d.line([a, (px, py)], fill="white", width=LW + 2 * HALO)
                    d.ellipse((px - DOT - HALO, py - DOT - HALO, px + DOT + HALO, py + DOT + HALO), fill="white")
                d.line([a, (px, py)], fill=INK, width=LW)
                d.ellipse((px - DOT, py - DOT, px + DOT, py + DOT), fill=INK)
                segs.append((name, a, (px, py)))
        continue
    side = lb.get("side", "left")
    px, py = to_px(*lb["point"])
    if side in ("left", "right"):
        cy = to_px(0, lb.get("y", lb["point"][1]))[1]
        y0 = cy - th_ / 2
        if side == "left":
            x0 = PAD; align = "right"; ax, ay = x0 + max(tw_, L - 3 * PAD), cy
            x0 = ax - tw_
            start = (ax + PAD, cy)
        else:
            x0 = W - PAD - max(tw_, R - 3 * PAD); align = "left"
            start = (x0 - PAD, cy)
        draw_lines(x0, y0, lines, f_lab, align, tw_, LINE, ink)
        rect = (x0, y0, x0 + tw_, y0 + th_)
    else:
        cx = to_px(lb.get("x", lb["point"][0]), 0)[0]
        x0 = cx - tw_ / 2
        y0 = PAD if side == "top" else H - PAD - th_
        draw_lines(x0, y0, lines, f_lab, "center", tw_, LINE, ink)
        rect = (x0, y0, x0 + tw_, y0 + th_)
        start = (cx, y0 + th_ + PAD) if side == "top" else (cx, y0 - PAD)
    boxes.append((name, rect))
    pts = [start]
    if lb.get("elbow", True) and side in ("left", "right"):
        # 先水平拉到圖邊附近，再斜向構造
        ex = L - PAD if side == "left" else L + w0 + PAD
        if (side == "left" and ex > start[0]) or (side == "right" and ex < start[0]):
            pts.append((ex, start[1]))
    pts.append((px, py))
    if HALO:
        d.line(pts, fill="white", width=LW + 2 * HALO, joint="curve")
        d.ellipse((px - DOT - HALO, py - DOT - HALO, px + DOT + HALO, py + DOT + HALO), fill="white")
    d.line(pts, fill=INK, width=LW, joint="curve")
    d.ellipse((px - DOT, py - DOT, px + DOT, py + DOT), fill=INK)
    for a, b in zip(pts, pts[1:]):
        segs.append((name, a, b))


for bk in S.get("brackets", []):                              # 括線：豎線、兩端小橫指向圖，字在另一側
    lines = ([bk["zh"]] + ([f"({bk['en']})"] if bk.get("en") else [])) if bk.get("zh") else [str(bk.get("text", ""))]
    name = "括線 " + lines[0]
    pt_ = float(bk.get("pt", lab_pt))
    f_b = ImageFont.truetype(FB if bk.get("bold", True) else FR, max(8, round(pt_ * px_per_pt)))
    LINE_b, PAD_b, ink = round(f_b.size * 1.18), round(f_b.size * 0.25), hexcolor(bk.get("color"))
    lx, ya = to_px(bk["x"], bk["y0"])
    yb = to_px(bk["x"], bk["y1"])[1]
    side = bk.get("side", "left")
    tick = float(bk.get("tick", 0.14)) * px_per_pt * 72.0
    sg = 1 if side == "left" else -1
    lwb = max(2, round(f_b.size * 0.07))
    d.line([(lx, ya), (lx, yb)], fill=ink, width=lwb)
    d.line([(lx, ya), (lx + sg * tick, ya)], fill=ink, width=lwb)
    d.line([(lx, yb), (lx + sg * tick, yb)], fill=ink, width=lwb)
    tw_, th_ = text_box(lines, f_b, LINE_b)
    cy = (ya + yb) / 2 + float(bk.get("dy", 0)) * (yb - ya)
    x0, align = (lx - PAD_b - tw_, "right") if side == "left" else (lx + PAD_b, "left")
    draw_lines(x0, cy - th_ / 2, lines, f_b, align, tw_, LINE_b, ink)
    boxes.append((name, (x0, cy - th_ / 2, x0 + tw_, cy + th_ / 2)))

def overlap(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def cross(p1, p2, p3, p4):
    def o(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return (v > 1e-9) - (v < -1e-9)
    return o(p1, p2, p3) * o(p1, p2, p4) < 0 and o(p3, p4, p1) * o(p3, p4, p2) < 0


for i in range(len(boxes)):
    n, r = boxes[i]
    if r[0] < 0 or r[1] < 0 or r[2] > W or r[3] > H:
        problems.append(f"「{n}」超出畫布（加大 margins 或移位置）")
    for j in range(i + 1, len(boxes)):
        if overlap(r, boxes[j][1]):
            problems.append(f"「{n}」和「{boxes[j][0]}」重疊")
for i in range(len(segs)):
    for j in range(i + 1, len(segs)):
        if segs[i][0] != segs[j][0] and cross(segs[i][1], segs[i][2], segs[j][1], segs[j][2]):
            problems.append(f"「{segs[i][0]}」和「{segs[j][0]}」的引線交叉")

out = P(S["out"])
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
im.save(out, optimize=True)
if A.preview:
    pv = im.copy(); pv.thumbnail((1600, 1600)); pv.save(A.preview)
print(f"-> {out} {im.size}；放進 {slot_w} 吋寬版位：標籤 {f_lab0.size / px_per_pt:.1f}pt、標題 {f_tit.size / px_per_pt:.1f}pt；"
      f"標籤 {len(S.get('labels', []))} 個", "OK" if not problems else "要改：" + "；".join(sorted(set(problems))))
sys.exit(1 if problems else 0)

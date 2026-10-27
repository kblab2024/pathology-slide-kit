# -*- coding: utf-8 -*-
"""實驗講義截圖加註記：照教師在 QuPath 上的畫法（紅圈、紅箭頭、深色底白字的小標籤），字級以投影片版位換算、至少 24pt。

教師 2026 自製的實驗講義（〈病理學實驗_A1_發炎〉）截圖上是 QuPath 的註記：紅色圓圈或箭頭指出構造，旁邊一個深灰底白字的標籤
「黏膜(Mucosa)」。這支程式畫同樣的東西，但字用微軟正黑體、以投影片上的大小換算（教師 2026-10-14：專有名詞「中文(English)」，
圖上標籤至少 24pt）。只標教學重點或文獻寫到的構造（教師 2026-10-19：「不要雞婆」）。

規格（JSON）：
{"image": "<截圖.png>", "out": "<輸出.png>", "slot_w": 6.14, "label_pt": 24,
 "marks": [
   {"type": "circle", "c": [0.42, 0.55], "r": [0.10, 0.08]},       橢圓圈：中心、半徑（圖寬、圖高的比例）
   {"type": "arrow", "from": [0.80, 0.20], "to": [0.62, 0.38]},     箭頭：箭頭尖在 to
   {"type": "span", "from": [0.30, 0.20], "to": [0.30, 0.65]},      雙頭箭頭：標一段範圍（例：上皮全層）
   {"type": "line", "from": [0.50, 0.00], "to": [0.50, 1.00], "dash": true},   線（dash：虛線；例：正常與病灶的交界）
   {"type": "label", "zh": "角化珠", "en": "keratin pearl", "at": [0.75, 0.15]},  標籤：框的中心；兩行「中文」「(English)」
   {"type": "label", "text": "正常上皮(normal epithelium)", "at": [0.2, 0.1]}      text：一行寫完（短的才用）
   {"type": "label", "lines": ["核大 核黑", "核不規則"], "at": [0.2, 0.1]}       lines：自己分行（不是專有名詞的描述句）
 ]}
  座標一律是圖寬、圖高的比例 0–1。color 可寫在各 mark（預設紅 #E8241A；標籤底色預設深灰 #2B2B2B、白字）。
  標籤框超出圖時自動移進圖內（箭頭不跟著動，移完要看一次）；壓在重要構造上時移到旁邊、用箭頭指過去。
成品（2026-10-27 起）：教師要能改註記，所以講義放沒加註記的原始截圖，這份規格由 merge_annot.py 帶進 deck.json，
gen_lab_pptx.py 畫成 PowerPoint 原生圖形、html_lab_deck.py 畫成 SVG；這支輸出的燒好的圖只給寫的人自查位置用。
檢查：字級 < 24pt、標籤超出圖、標籤彼此重疊，印「要改」並以結束碼 1 結束（圖仍會輸出，方便看哪裡要調）。
用法：python annotate_shot.py <規格.json> [--preview <縮圖.png>]
      規格可以是 {"shots": [規格, …]}：一個檔放一整例的截圖，一次做完（image、out 相對規格檔所在的資料夾）。
"""
import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FD = "/Applications/Microsoft PowerPoint.app/Contents/Resources/DFonts/"
WF = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
FONT = next((p for p in [os.path.join(WF, "msjh.ttc"), FD + "MSJH.ttf", "/System/Library/Fonts/PingFang.ttc",
                         "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"] if os.path.exists(p)), None)
RED = "#E8241A"
BOX = (43, 43, 43, 225)


def hex_rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def annotate(S, base, preview=None):
    P = lambda p: p if os.path.isabs(p) else os.path.join(base, p)

    im = Image.open(P(S["image"])).convert("RGB")
    W, H = im.size
    slot_w = float(S.get("slot_w", 6.14))
    px_per_pt = W / slot_w / 72.0
    lab_pt = float(S.get("label_pt", 24))
    problems = []
    if lab_pt < 24:
        problems.append(f"標籤字級 {lab_pt}pt 低於 24pt")
    font = ImageFont.truetype(FONT, max(8, round(lab_pt * px_per_pt))) if FONT else ImageFont.load_default()
    LW = max(3, round(0.035 * 72 * px_per_pt))          # 線寬約 0.035 吋
    HALO = max(1, LW // 2)
    over = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    to_px = lambda p: (p[0] * W, p[1] * H)

    def seg(p1, p2, color, width, dash=False):
        if not dash:
            d.line([p1, p2], fill=color, width=width)
            return
        L = math.dist(p1, p2)
        n = max(1, int(L / (width * 6)))
        for i in range(0, n, 2):
            t0, t1 = i / n, min(1, (i + 1) / n)
            d.line([(p1[0] + (p2[0] - p1[0]) * t0, p1[1] + (p2[1] - p1[1]) * t0),
                    (p1[0] + (p2[0] - p1[0]) * t1, p1[1] + (p2[1] - p1[1]) * t1)], fill=color, width=width)

    def head(tip, frm, color, size):
        ang = math.atan2(tip[1] - frm[1], tip[0] - frm[0])
        pts = [tip]
        for s in (+1, -1):
            a2 = ang + math.pi - s * math.radians(26)
            pts.append((tip[0] + size * math.cos(a2), tip[1] + size * math.sin(a2)))
        d.polygon(pts, fill=color)

    boxes = []
    for m in S.get("marks", []):
        t = m.get("type")
        col = hex_rgb(m.get("color", RED)) + (255,)
        white = (255, 255, 255, 230)
        if t == "circle":
            cx, cy = to_px(m["c"])
            rx, ry = m["r"][0] * W, m["r"][1] * H
            e = (cx - rx, cy - ry, cx + rx, cy + ry)
            d.ellipse((e[0] - HALO, e[1] - HALO, e[2] + HALO, e[3] + HALO), outline=white, width=LW + 2 * HALO)
            d.ellipse(e, outline=col, width=LW)
        elif t in ("arrow", "span", "line"):
            p1, p2 = to_px(m["from"]), to_px(m["to"])
            hs = LW * 4.2
            dash = bool(m.get("dash"))
            # 線段縮短到箭頭底，不讓線頭戳出箭頭尖
            def shorten(a_, b_, k):
                L = math.dist(a_, b_) or 1
                return (b_[0] - (b_[0] - a_[0]) * k / L, b_[1] - (b_[1] - a_[1]) * k / L)
            q2 = shorten(p1, p2, hs * 0.8) if t in ("arrow", "span") else p2
            q1 = shorten(p2, p1, hs * 0.8) if t == "span" else p1
            seg(q1, q2, white, LW + 2 * HALO, dash)
            seg(q1, q2, col, LW, dash)
            if t in ("arrow", "span"):
                head(p2, p1, white, hs + 2 * HALO)
                head(p2, p1, col, hs)
            if t == "span":
                head(p1, p2, white, hs + 2 * HALO)
                head(p1, p2, col, hs)
        elif t == "label":
            lines = m["lines"] if m.get("lines") else ([m["text"]] if m.get("text") else [m["zh"], f"({m['en']})"])
            ws = [d.textbbox((0, 0), s, font=font) for s in lines]
            tw = max(b[2] - b[0] for b in ws)
            lh = round(font.size * 1.2)
            pad = round(font.size * 0.32)
            bw, bh = tw + 2 * pad, lh * len(lines) + 2 * pad - round(font.size * 0.12)
            cx, cy = to_px(m["at"])
            x0, y0 = cx - bw / 2, cy - bh / 2
            # 超出圖的標籤自動移進圖內（留 1% 邊）；圖比標籤還窄才報錯
            mx, my = W * 0.01, H * 0.01
            x0 = min(max(x0, mx), W - mx - bw) if bw + 2 * mx <= W else x0
            y0 = min(max(y0, my), H - my - bh) if bh + 2 * my <= H else y0
            r = (x0, y0, x0 + bw, y0 + bh)
            fill = hex_rgb(m["bg"]) + (225,) if m.get("bg") else BOX
            d.rounded_rectangle(r, radius=round(font.size * 0.18), fill=fill)
            for i, s in enumerate(lines):
                l, tp, rr, b = d.textbbox((0, 0), s, font=font)
                d.text((x0 + pad + (tw - (rr - l)) / 2 - l, y0 + pad + i * lh - tp + (lh - (b - tp)) / 2 - round(font.size * 0.06)),
                       s, font=font, fill=(255, 255, 255, 255))
            name = m.get("text") or m.get("zh") or " ".join(m.get("lines", []))
            if r[0] < 0 or r[1] < 0 or r[2] > W or r[3] > H:
                problems.append(f"標籤「{name}」超出圖")
            for (n2, r2) in boxes:
                if not (r[2] <= r2[0] or r2[2] <= r[0] or r[3] <= r2[1] or r2[3] <= r[1]):
                    problems.append(f"標籤「{name}」和「{n2}」重疊")
            boxes.append((name, r))
        else:
            problems.append(f"不認得的 mark type：{t}")

    out = Image.alpha_composite(im.convert("RGBA"), over).convert("RGB")
    out_path = P(S["out"])
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    if out_path.lower().endswith((".jpg", ".jpeg")):
        out.save(out_path, quality=90)
    else:
        out.save(out_path)
    if preview:
        pv = out.copy()
        pv.thumbnail((1000, 1000))
        pv.save(preview)
    print(f"輸出：{out_path}（標籤 {lab_pt:g}pt＝{font.size}px，版位寬 {slot_w} 吋）")
    for p in problems:
        print("要改：" + p)
    return problems


def main():
    ap = argparse.ArgumentParser(description="實驗講義截圖加註記（紅圈、箭頭、深色底白字標籤）")
    ap.add_argument("spec", help="一張的規格，或 {\"shots\": [規格, …]}（一次做一整例）")
    ap.add_argument("--preview", help="另存一張長邊 1000 px 的縮圖（只用在單張規格）")
    a = ap.parse_args()
    S = json.load(open(a.spec, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(a.spec))
    probs = []
    for one in (S["shots"] if "shots" in S else [S]):
        probs += annotate(one, base, a.preview if "shots" not in S else None)
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())

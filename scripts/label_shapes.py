# -*- coding: utf-8 -*-
"""示意圖的標籤畫成 PowerPoint 原生的文字方塊、指線與圓點（文字方塊版），和 label_image.py（圖版）讀同一份規格。

教師 2026-11-12（docs/教師偏好與決策.md 第 4 節）：加標籤的圖「作一個圖版一個文字方塊版」；同日另一條：我們寫的字不燒進圖。
所以一份標籤規格（JSON，格式見 label_image.py 的 docstring）出兩版：
  - 圖版：python label_image.py <規格.json> → 規格的 "out"（標籤疊進圖；HTML 版用，也可以整張貼到別處）
  - 文字方塊版：素材池那一張寫
        <!-- IMG: <規格的 out，相對課程資料夾> ｜ 出處：… ｜ 內容：… -->
        <!-- labels: <規格.json，相對課程資料夾> -->
    gen_pptx 在 PPTX 上就不放圖版，改放規格的 "image"（沒有字的母圖，或程式畫的圖），標籤畫成文字方塊、指線、圓點，
    教師在 PowerPoint 裡可以直接改字、拖、刪。規格另可寫 "brackets"（括線：豎線加兩端小橫、旁邊一個字，例：Reid 指數的 a、b；格式見 label_image.py）。一張投影片可以寫好幾行 labels（例：pair 的兩張圖各一份）；
    哪一份規格對哪一張圖，看規格的 "out" 和 IMG 的路徑是不是同一個檔。html_deck.py 不認 labels，照舊用 IMG 的圖版。

排法和 label_image.py 相同：母圖四周依 margins 留白邊，side＝left／right／top／bottom 的標籤放白邊，指線從文字框拉到 point
（母圖寬高的比例 0–1），終點是圓點；at 的標籤放在指定位置（預設墊白色圓角底，"box": false 不墊），
同時寫了 point 就從文字框的邊拉一條直線過去。
字級是真的字級（label_pt 預設取課程 sizes.label，title_pt 預設 28；每個標籤可以另寫 "pt"、"bold"、"color"），不隨圖縮放：
規格的 slot_w 要寫這張圖在投影片上實際的寬（吋）。實際放得比 slot_w 窄、或標籤互壓、超出投影片，都記進 _layout.json，
check_deck 會報。每個圖形都有名字（「標籤 基底細胞」「標籤 基底細胞 指線1」「標籤 基底細胞 圓點」），回灌時看得出是哪一個。
"""
import json
import os
import re

from PIL import Image
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from flow_shapes import _line_shape, _plain

INK = "1E2A35"


def load_spec(path):
    """讀一份標籤規格；image、out 換成絕對路徑。讀不到回 None。"""
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception:
        return None
    base = os.path.dirname(os.path.abspath(path))
    for k in ("image", "out"):
        if d.get(k):
            d[k] = d[k] if os.path.isabs(d[k]) else os.path.normpath(os.path.join(base, d[k]))
    return d


def parse_refs(body, course_dir):
    """素材池一張裡所有的 <!-- labels: 規格.json --> → [{"spec", "abspath", "data"}]。"""
    out = []
    for m in re.finditer(r"<!--\s*labels:\s*(.*?)-->", body, re.S):
        ref = re.split(r"[｜|\n]", m.group(1))[0].strip()
        absp = ref if os.path.isabs(ref) else os.path.join(course_dir, ref)
        out.append({"spec": ref, "abspath": absp, "data": load_spec(absp) if os.path.exists(absp) else None})
    return out


def attach(imgs, specs):
    """把規格掛到 "out" 和 IMG 路徑相同的那張圖（img["labels"]）；回傳沒有對到任何 IMG 的規格。"""
    left = []
    for sp in specs:
        d = sp.get("data") or {}
        hit = False
        for im in imgs:
            if d.get("out") and os.path.normpath(os.path.abspath(im["abspath"])) == os.path.normpath(os.path.abspath(d["out"])):
                im["labels"] = sp
                hit = True
        if not hit:
            left.append(sp["spec"])
    return left


def _lines(lb):
    return [lb["zh"]] + ([f"({lb['en']})"] if lb.get("en") else [])


def label_text(data):
    """這份規格的全部文字（一個標籤一行「中文(English)」），給 style_check 查中英對照與用語。"""
    d = data or {}
    out = [t.get("text", "") for t in d.get("titles", [])]
    out += ["".join(_lines(lb)) for lb in d.get("labels", [])]
    out += ["".join(_lines(bk)) for bk in d.get("brackets", []) if bk.get("zh")]
    return [t for t in out if t]


def _lh(size):
    return size * 1.2 / 72.0


def _tw(g, text, size, bold):
    return g._w(g.strip_markup(text), bold) * size / 72.0 * 1.04 + 0.05


def _color(g, key):
    """顏色：六碼色碼，或課程 emphasis 的名字（藍、橘、紅…）；沒寫就是墨色。"""
    if not key:
        return INK
    return g.G.EMPH.get(key, key if re.fullmatch(r"[0-9A-Fa-f]{6}", str(key)) else INK)


def _text(g, slide, x, y, w, h, lines, size, color, bold, align, name):
    tb, tf = g.textbox(slide, x, y, w, h, anchor=MSO_ANCHOR.MIDDLE)
    tf.word_wrap = False
    for i, t in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p._p.get_or_add_pPr().set("hangingPunct", "0")
        p.space_after = Pt(0)
        p.line_spacing = 1.0
        r = p.add_run()
        r.text = t
        g._font(r, size, color, bold)
    tb.name = name
    return tb


def _leader(g, slide, pts, pt, name, halo):
    """指線（一段或兩段直線）與終點的圓點。"""
    px, py = pts[-1]
    lw = max(1.25, pt * 0.06)
    dot = 0.16 * pt / 72.0
    for q, (a, b) in enumerate(zip(pts, pts[1:]), 1):
        if halo:
            hl = _line_shape(slide, a[0], a[1], b[0], b[1])
            hl.line.color.rgb = g.C("FFFFFF")
            hl.line.width = Pt(lw + 2.5)
            hl.name = f"標籤 {name} 指線{q} 白邊"
        ln = _line_shape(slide, a[0], a[1], b[0], b[1])
        ln.line.color.rgb = g.C(INK)
        ln.line.width = Pt(lw)
        ln.name = f"標籤 {name} 指線{q}"
    if halo:
        hd = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(px - dot - 0.03), Inches(py - dot - 0.03),
                                    Inches(2 * dot + 0.06), Inches(2 * dot + 0.06))
        _plain(hd)
        hd.fill.solid()
        hd.fill.fore_color.rgb = g.C("FFFFFF")
        hd.line.fill.background()
        hd.name = f"標籤 {name} 圓點 白邊"
    dt = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(px - dot), Inches(py - dot), Inches(2 * dot), Inches(2 * dot))
    _plain(dt)
    dt.fill.solid()
    dt.fill.fore_color.rgb = g.C(INK)
    dt.line.fill.background()
    dt.name = f"標籤 {name} 圓點"


def place(g, slide, s, img, x, y, w, h):
    """在 (x, y, w, h) 放母圖與原生標籤。g＝gen_pptx 模組。回傳值和 gen_pptx.place_image 相同。"""
    G = g.G
    d = img["labels"]["data"]
    try:
        iw, ih = Image.open(d["image"]).size
    except Exception:
        return None
    M = {k: float((d.get("margins") or {}).get(k, 0)) for k in ("left", "right", "top", "bottom")}
    L, R, T, B = iw * M["left"], iw * M["right"], ih * M["top"], ih * M["bottom"]
    W, H = iw + L + R, ih + T + B
    cred = img.get("src") or ""
    ctext = cred if cred.startswith(("圖", "資料來源")) else "圖：" + cred
    cw_of = lambda dw: max(dw, min(w, 4.5))
    ch = 0.0
    for _ in range(4):                       # 和 place_image 同一個算法：圖下留出處行，不壓到左下「資料來源」
        hh = h - ch
        floor = G.SH - getattr(G, "src_h", 0.0) - 0.10 - ch
        if y + hh > floor:
            hh = max(0.8, floor - y)
        far, iar = w / hh, W / H
        dw, dh = (w, w / iar) if iar > far else (hh * iar, hh)
        need = (g.n_lines(ctext, G.S["credit"], cw_of(dw)) * 0.25 + 0.06) if cred else 0.0
        if abs(need - ch) < 1e-6:
            break
        ch = need
    dx, dy = x + (w - dw) / 2, y
    k = dw / W                               # 吋／母圖像素
    bx, by, bw, bh = dx + L * k, dy + T * k, iw * k, ih * k
    pic = slide.shapes.add_picture(g.prep_image(d["image"]), Inches(bx), Inches(by), Inches(bw), Inches(bh))
    pic.name = "標籤圖 母圖"
    to_in = lambda fx, fy: (bx + fx * bw, by + fy * bh)
    lab_pt = float(d.get("label_pt", G.S.get("label", 24)))
    tit_pt = float(d.get("title_pt", 28))
    slot_w = float(d.get("slot_w", dw))
    if dw < slot_w - 0.05:
        g.note_fit(s, slot_w, dw, "標籤圖的寬（規格 slot_w；放得比它窄，標籤會互壓）")
    halo = bool(d.get("halo"))
    boxes, texts = [], []                    # 文字最後畫，蓋在指線上面

    for t in d.get("titles", []):
        pt = float(t.get("pt", tit_pt))
        tw, th = _tw(g, t["text"], pt, True), _lh(pt)
        cx, cy = to_in(t["x"], t["y"])
        texts.append((cx - tw / 2, cy - th / 2, tw, th, [t["text"]], pt, _color(g, t.get("color")), True,
                      PP_ALIGN.CENTER, "標籤 標題 " + t["text"]))
        boxes.append(("標題 " + t["text"], (cx - tw / 2, cy - th / 2, cx + tw / 2, cy + th / 2)))

    for lb in d.get("labels", []):
        pt = float(lb.get("pt", lab_pt))
        bold = bool(lb.get("bold", False))
        col = _color(g, lb.get("color"))
        lines = _lines(lb)
        name = lines[0]
        pad = 0.35 * pt / 72.0
        tw, th = max(_tw(g, t, pt, bold) for t in lines), _lh(pt) * len(lines)
        if "at" in lb:
            cx, cy = to_in(*lb["at"])
            x0, y0 = cx - tw / 2, cy - th / 2
            rect = (x0 - pad, y0 - pad / 2, x0 + tw + pad, y0 + th + pad / 2)
            if lb.get("box", True):
                bg = g.rect(slide, rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1], hexc="FFFFFF", rounded=True,
                            radius=0.3)
                _plain(bg)
                bg.name = f"標籤 {name} 底"
            else:
                rect = (x0, y0, x0 + tw, y0 + th)
            texts.append((x0, y0, tw, th, lines, pt, col, bold, PP_ALIGN.CENTER, f"標籤 {name}"))
            boxes.append((name, rect))
            if "point" in lb:                # 從文字框的邊拉直線到 point
                px, py = to_in(*lb["point"])
                hw, hh = tw / 2 + pad, th / 2 + pad / 2
                ddx, ddy = px - cx, py - cy
                if abs(ddx) > hw or abs(ddy) > hh:
                    tt = min(hw / abs(ddx) if ddx else 1e9, hh / abs(ddy) if ddy else 1e9)
                    _leader(g, slide, [(cx + ddx * tt, cy + ddy * tt), (px, py)], pt, name, halo)
            continue
        side = lb.get("side", "left")
        px, py = to_in(*lb["point"])
        if side in ("left", "right"):
            cy = to_in(0, lb.get("y", lb["point"][1]))[1]
            y0 = cy - th / 2
            if side == "left":
                ax = dx + pad + max(tw, L * k - 3 * pad)
                x0, align, start, ex = ax - tw, PP_ALIGN.RIGHT, (ax + pad, cy), dx + L * k - pad
                elbow = ex > start[0] + 1e-6
            else:
                x0 = dx + dw - pad - max(tw, R * k - 3 * pad)
                align, start, ex = PP_ALIGN.LEFT, (x0 - pad, cy), dx + L * k + bw + pad
                elbow = ex < start[0] - 1e-6
        else:
            cx = to_in(lb.get("x", lb["point"][0]), 0)[0]
            x0 = cx - tw / 2
            y0 = dy + pad if side == "top" else dy + dh - pad - th
            align = PP_ALIGN.CENTER
            start = (cx, y0 + th + pad) if side == "top" else (cx, y0 - pad)
            elbow = False
        pts = [start]
        if lb.get("elbow", True) and side in ("left", "right") and elbow:
            pts.append((ex, start[1]))
        pts.append((px, py))
        _leader(g, slide, pts, pt, name, halo)
        texts.append((x0, y0, tw, th, lines, pt, col, bold, align, f"標籤 {name}"))
        boxes.append((name, (x0, y0, x0 + tw, y0 + th)))

    for bk in d.get("brackets", []):        # 括線：一條豎線、兩端各一小橫（指向圖），字在另一側（例：Reid 指數的 a、b）
        pt = float(bk.get("pt", lab_pt))
        bold = bool(bk.get("bold", True))
        col = _color(g, bk.get("color"))
        lines = _lines(bk) if bk.get("zh") else [str(bk.get("text", ""))]
        name = "括線 " + lines[0]
        lx, ya = to_in(bk["x"], bk["y0"])
        yb = to_in(bk["x"], bk["y1"])[1]
        side = bk.get("side", "left")        # 字在豎線的哪一側；小橫指向另一側（圖）
        tick = float(bk.get("tick", 0.14))
        sg = 1 if side == "left" else -1
        lw = max(1.5, pt * 0.07)
        for q, (a, b) in enumerate([((lx, ya), (lx, yb)), ((lx, ya), (lx + sg * tick, ya)), ((lx, yb), (lx + sg * tick, yb))], 1):
            ln = _line_shape(slide, a[0], a[1], b[0], b[1])
            ln.line.color.rgb = g.C(col)
            ln.line.width = Pt(lw)
            ln.name = f"標籤 {name} 線{q}"
        tw, th = max(_tw(g, t, pt, bold) for t in lines), _lh(pt) * len(lines)
        pad = 0.25 * pt / 72.0
        cy = (ya + yb) / 2 + float(bk.get("dy", 0)) * (yb - ya)
        x0, align = (lx - pad - tw, PP_ALIGN.RIGHT) if side == "left" else (lx + pad, PP_ALIGN.LEFT)
        texts.append((x0, cy - th / 2, tw, th, lines, pt, col, bold, align, f"標籤 {name}"))
        boxes.append((name, (x0, cy - th / 2, x0 + tw, cy + th / 2)))

    for a in texts:
        _text(g, slide, *a)

    # 檢查：標籤超出投影片、互壓（記進 _layout.json，check_deck 會報）
    bad = []
    for i, (n, r) in enumerate(boxes):
        if r[0] < -0.01 or r[1] < -0.01 or r[2] > G.SW + 0.01 or r[3] > G.SH + 0.01:
            bad.append(f"「{n}」超出投影片")
        for m, q in boxes[i + 1:]:
            if not (r[2] <= q[0] or q[2] <= r[0] or r[3] <= q[1] or q[3] <= r[1]):
                bad.append(f"「{n}」和「{m}」互壓")
    if bad:
        g.note_fit(s, 1.0, 0.0, "標籤：" + "；".join(bad))
    if cred:
        cw = cw_of(dw)
        g.credit(slide, cred, x + (w - cw) / 2 if cw > dw else dx, cw, dy + dh + 0.04)
    return pic, dx, dy, dw, dh, (ch if cred else 0.0)

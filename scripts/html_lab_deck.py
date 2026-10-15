# -*- coding: utf-8 -*-
"""實驗講義的 HTML 版：讀 gen_lab_pptx.py 用的 deck.json，產「一個 HTML 檔」（圖片內嵌、手機或任何瀏覽器直接開）。

教師 2026-10-14：「成品要有 html 版，去哪裡都好做事」。html_deck.py 只吃大堂課的素材池（pool.md），實驗講義的來源是
deck.json，所以另寫這支：版面照 gen_lab_pptx.py 的幾何（13.33×7.5 吋 → 1920×1080 畫布，1 吋＝144px、1pt＝2px），
CSS、鍵盤換張與圖片縮圖沿用 html_deck.py。截圖位、示意圖待換位、圖待補位畫成淡灰框（和 PPTX 一樣不寫字）。

用法：
  python html_lab_deck.py <deck.json> --out <檔案.html> [--max-side 760] [--quality 60] [--title 名稱]
  img.path 相對 deck.json 所在的資料夾；放 OneDrive 的版本要壓到 4 MB 以下（工作區 AGENTS 第 9 節）。

注意：PPTX 是主檔；網頁版只給看內容、帶著走，改內容一樣改 deck.json 再重產。教師在 PPTX 換上的截圖不會出現在這裡。
"""
import argparse
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import bullet_level  # noqa: E402
from gen_lab_pptx import (BG_H, BG_IND, BG_LINE, BG_SPACE, BG_W, BG_X, BG_Y, BLUE, DIV_W, DIV_X, IMG_H, IMG_W,  # noqa: E402
                          IMG_X, IMG_Y, SH, SPACE_AFTER, SW, SZ, TITLE_W, TITLE_Y, TXT_W, TXT_X, kind_of, plan_bg,
                          TBL_GAP, Report, bullets_need, n_lines, side_text, slot_side)
from html_deck import CSS, JS, data_uri  # noqa: E402
from PIL import Image  # noqa: E402

PX = 1920 / SW            # 每吋幾 px
PT = PX / 72.0            # 每 pt 幾 px（=2）
FONT = "'Microsoft JhengHei','微軟正黑體','PingFang TC','Noto Sans TC','Heiti TC',sans-serif"

LAB_CSS = """
.lab{position:absolute;inset:0;background:#fff;color:#000;font-family:%s}
.lab .bx{position:absolute;box-sizing:border-box;overflow:visible}
.lab .div{background:#%s;color:#fff}
.lab .ph{background:#e6e6e6}
.lab .mid{display:flex;flex-direction:column;justify-content:center}
.lab p{margin:0}
.lab ul{list-style:none;margin:0;padding:0}
.lab table{border-collapse:collapse;table-layout:fixed}
.lab td{border:1px solid #c9d3e0;padding:4px 12px;vertical-align:middle;overflow-wrap:anywhere}
""" % (FONT, BLUE)


def esc(t):
    return html.escape(str(t or ""))


def box(x, y, w, h, inner="", cls="bx", style=""):
    return (f'<div class="{cls}" style="left:{x * PX:.0f}px;top:{y * PX:.0f}px;width:{w * PX:.0f}px;'
            f'height:{h * PX:.0f}px;{style}">{inner}</div>')


def ptxt(t, size, extra=""):
    return f'<p style="font-size:{size * PT:.1f}px;line-height:1.12;{extra}">{esc(t)}</p>'


def title_html(t):
    return box((SW - TITLE_W) / 2, TITLE_Y, TITLE_W, 0.93, ptxt(t, SZ["title"], "text-align:center"))


def image_html(c, base, side, max_side, quality):
    img = c.get("img") or {}
    p = img.get("path")
    ap = os.path.normpath(os.path.join(base, p)) if p else None
    x = IMG_X[side]
    if kind_of(c) in ("gx", "sc") and ap and os.path.exists(ap):
        uri = data_uri(ap, max_side, quality)
        iw, ih = Image.open(ap).size
        cred = img.get("credit") or ""
        t = (cred if cred.startswith(("圖", "資料來源", "示意圖")) else "圖：" + cred) if cred else ""
        hh = min(IMG_H, SH - 0.08 - 0.25 * n_lines(t, SZ["credit"], IMG_W) - 0.04 - IMG_Y) if t else IMG_H
        dw, dh = (IMG_W, IMG_W * ih / iw) if iw / ih > IMG_W / hh else (hh * iw / ih, hh)
        dx, dy = x + (IMG_W - dw) / 2, IMG_Y + (hh - dh) / 2      # 和 gen_lab_pptx 一樣：等比、置中、出處行不壓圖
        out = box(dx, dy, dw, dh, f'<img src="{uri}" style="width:100%;height:100%">')
        if t:
            out += box(x, dy + dh + 0.04, IMG_W, 0.5, ptxt(t, SZ["credit"], "color:#595959"))
        return out
    return box(x, IMG_Y, IMG_W, IMG_H, cls="bx ph")


def side_html(c, side):
    text = side_text(c)
    tside = "left" if side == "right" else "right"
    inner = "".join(ptxt(t, SZ["body"], f"margin-bottom:{SPACE_AFTER * PT if i < len(text) - 1 else 0:.0f}px")
                    for i, t in enumerate(text))
    return box(TXT_X[tside], IMG_Y, TXT_W, IMG_H, inner, cls="bx mid")


def bg_html(c, bg_pt):
    pages, layout = plan_bg(c, bg_pt, Report(), c.get("id", ""))
    out = []
    for page in pages:
        parts = [title_html(c.get("title", ""))]
        y = BG_Y
        if page["bullets"]:
            lis = []
            for b in page["bullets"]:
                lvl, t = bullet_level(b)
                ind = (BG_IND + 0.40 * lvl) * PX
                mark, col = ("• ", f"#{BLUE}") if lvl == 0 else ("– ", "#595959")
                lis.append(f'<li style="font-size:{bg_pt * PT:.1f}px;line-height:{BG_LINE * 1.12:.2f};'
                           f'margin-bottom:{BG_SPACE * PT:.0f}px;padding-left:{ind:.0f}px;text-indent:{-0.32 * PX:.0f}px">'
                           f'<b style="color:{col}">{mark}</b>{esc(t)}</li>')
            parts.append(box(BG_X, BG_Y, BG_W, BG_H, "<ul>" + "".join(lis) + "</ul>"))
            y = BG_Y + bullets_need(page["bullets"], bg_pt) + TBL_GAP
        if page["rows"] and layout:
            rows, widths, _ = layout
            cols = "".join(f'<col style="width:{w * PX:.0f}px">' for w in widths)
            trs = []
            for k, i in enumerate([0] + page["rows"]):
                bgc = f"#{BLUE}" if i == 0 else ("#fff" if k % 2 else "#EEF2FA")
                tds = "".join(f'<td style="background:{bgc};color:{"#fff" if i == 0 else "#000"};'
                              f'font-weight:{"bold" if (i == 0 or j == 0) else "normal"};font-size:{bg_pt * PT:.1f}px;'
                              f'line-height:1.2">{esc(v)}</td>' for j, v in enumerate(rows[i]))
                trs.append(f"<tr>{tds}</tr>")
            parts.append(box(BG_X, y, BG_W, BG_Y + BG_H - y,
                             f'<table style="width:{BG_W * PX:.0f}px"><colgroup>{cols}</colgroup>{"".join(trs)}</table>'))
        out.append("".join(parts))
    return out


def build(deck, base, max_side, quality, bg_pt):
    frames = []   # (html, 標籤)
    frames.append((box(0.5, 3.04, SW - 1.0, 0.9, ptxt(deck.get("cover", ""), SZ["cover"], "text-align:center"),
                       cls="bx mid"), "封面"))
    for sec in deck.get("sections", []):
        d = sec.get("divider", {})
        inner = box(DIV_X, 2.52, DIV_W, 0.3, ptxt(d.get("label", ""), SZ["label"]))
        y = 2.91
        for line in d.get("title_lines", []):
            inner += box(DIV_X, y, DIV_W, 0.7, ptxt(line, SZ["theme"]))
            y += 0.75
        inner += box(DIV_X, y - 0.07, DIV_W, 0.8, ptxt(d.get("slides_line", ""), SZ["glass"]))
        frames.append((box(0, 0, SW, SH, inner, cls="bx div"), d.get("label", "")))
        for c in sec.get("slides", []):
            if kind_of(c) == "bg":
                for h in bg_html(c, bg_pt):
                    frames.append((h, c.get("id", "")))
                continue
            side = slot_side(c)
            frames.append((title_html(c.get("title", "")) + image_html(c, base, side, max_side, quality)
                           + side_html(c, side), c.get("id", "")))
    return frames


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("deck")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-side", type=int, default=760)
    ap.add_argument("--quality", type=int, default=60)
    ap.add_argument("--bg-pt", type=float, default=24)
    ap.add_argument("--title", default=None)
    a = ap.parse_args()
    deck = json.load(open(a.deck, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(a.deck))
    frames = build(deck, base, a.max_side, a.quality, a.bg_pt)
    title = a.title or deck.get("cover", "實驗講義")
    secs = []
    body = []
    for i, (h, lab) in enumerate(frames, 1):
        if lab.startswith("Section"):
            secs.append((lab, i))
        body.append(f'<div class="frame" id="s{i}"><span class="num">{i} {esc(lab)}</span>'
                    f'<div class="slide"><section><div class="lab">{h}</div></section></div></div>')
    toc = "".join(f'<a href="#s{n}">{esc(t)}（{n}）</a>' for t, n in secs)
    doc = (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>'
           f'<style>{CSS}{LAB_CSS}</style></head><body><header><b>{esc(title)}</b>'
           f'<span>{len(frames)} 張（←／→ 換張）</span><span>{toc}</span></header>'
           f'<div class="wrap">{"".join(body)}</div><script>{JS}</script></body></html>')
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "w", encoding="utf-8", newline="\n").write(doc)
    print(f"{len(frames)} 張 -> {a.out}（{os.path.getsize(a.out) / 1e6:.2f} MB）")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

# -*- coding: utf-8 -*-
"""把課程素材池產成「一個 HTML 檔」的投影片：圖片內嵌、不需上傳、手機或任何瀏覽器直接開。

教師 2026-10-14：「所以其實就是成品要有 html 版，去哪裡都好做事」。to_claude_slides.py 要先在 claude.ai 上傳圖片
才能用；這支沿用同一個版面渲染（16:9、1920×1080 畫布、1pt＝2px），改成把圖縮小後以 data URI 內嵌，所有張串成一頁，
依視窗寬度縮放；鍵盤 ←／→、PageUp／PageDown 跳張。字型優先用微軟正黑體，沒有就用系統的繁中字型。

用法：
  cd <kit>/scripts && SLIDEKIT_MATERIALS=<materials> PYTHONIOENCODING=utf-8 python html_deck.py --course <課程> [--deck <deck>]
      [--out <檔案.html>] [--max-side 1200] [--quality 75] [--title 名稱]
預設輸出：<課程>/成品/<PPTX 檔名把 (PPTX) 換成 (HTML)>.html

注意：
- 這是「看內容、帶著走」的版本，版面是 16:9 的網頁排法，和 4:3 的 PPTX 不會逐點一樣；PPTX 仍是主檔。
- 網頁上改不了也不會回素材池；要改內容一樣改素材池再重產。
- 檔案大小主要是圖：--max-side、--quality 調小可以再縮（OneDrive 大檔傳不上時有用）。
"""
import argparse
import base64
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image  # noqa: E402

import to_claude_slides as tcs  # noqa: E402
from common import build_deck, deck_filename, load_course, notes_map, parse_script  # noqa: E402

CSS = """
html,body{margin:0;background:#2b2f36}
body{font-family:'Microsoft JhengHei','微軟正黑體','PingFang TC','Noto Sans TC','Heiti TC',sans-serif}
header{position:sticky;top:0;z-index:5;background:#16233a;color:#fff;padding:8px 14px;font:15px/1.4 inherit;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header a{color:#cfe0f5;text-decoration:none;margin-right:10px}
.wrap{display:flex;flex-direction:column;align-items:center;gap:18px;padding:18px 0 60px}
.frame{position:relative;width:min(96vw,1600px);aspect-ratio:16/9;background:#fff;box-shadow:0 2px 10px rgba(0,0,0,.4);overflow:hidden}
.frame>.num{position:absolute;right:10px;top:6px;z-index:3;font:14px sans-serif;color:#9aa4b2}
.slide{position:absolute;left:0;top:0;width:1920px;height:1080px;transform-origin:0 0}
.slide>section{position:relative;box-sizing:border-box;width:1920px;height:1080px;overflow:hidden;font-family:inherit!important}
.slide section *{font-family:inherit}
.slide aside{display:none}
.slide table{border-collapse:collapse;width:100%}
.slide th,.slide td{border:1px solid #c9d3e0;padding:8px 14px;text-align:left;vertical-align:middle}
.slide th{color:#fff;background:#1F4E8C}
.slide ul{margin:0;padding-left:1.1em}.slide p,.slide h1,.slide h2{margin:0}
"""

JS = """
function fit(){document.querySelectorAll('.frame').forEach(function(f){
 var w=f.clientWidth||1600;f.querySelector('.slide').style.transform='scale('+(w/1920)+')';});}
fit();window.addEventListener('DOMContentLoaded',fit);window.addEventListener('load',fit);window.addEventListener('resize',fit);
document.addEventListener('keydown',function(e){var fs=[].slice.call(document.querySelectorAll('.frame'));
 var y=window.scrollY+70,i=fs.findIndex(function(f){return f.offsetTop+f.offsetHeight>y;});if(i<0)i=0;
 if(e.key==='ArrowRight'||e.key==='PageDown'){i=Math.min(fs.length-1,i+1);}else if(e.key==='ArrowLeft'||e.key==='PageUp'){i=Math.max(0,i-1);}else return;
 e.preventDefault();window.scrollTo(0,fs[i].offsetTop-60);});
"""


def data_uri(path, max_side, quality):
    im = Image.open(path)
    im.load()
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    if has_alpha:
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    if max(im.size) > max_side:
        r = max_side / max(im.size)
        im = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
    # 程式圖、標籤圖（字多、色塊平）用 PNG 比較清楚；照片用 JPEG
    is_drawing = ("程式圖" in path) or path.endswith(("_zh.png", "_zh2.png", "_zh3.png", "_zh4.png")) or "legend" in path
    buf = io.BytesIO()
    if is_drawing:
        im.quantize(colors=128).save(buf, "PNG", optimize=True)
        mime = "image/png"
    else:
        im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
        mime = "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--course", required=True)
    ap.add_argument("--deck", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-side", type=int, default=1200)
    ap.add_argument("--quality", type=int, default=75)
    ap.add_argument("--title", default=None)
    a = ap.parse_args()
    c = load_course(a.course)
    deck = a.deck or c["deck_order"][0]
    built = build_deck(c, deck)
    slides = built["slides"]
    paths = sorted({os.path.abspath(i["abspath"]) for s in slides for i in s["imgs"] if i.get("exists")})
    assets = {os.path.normcase(p): data_uri(p, a.max_side, a.quality) for p in paths}
    r = tcs.R(c, assets)
    notes = notes_map(built, parse_script(c))
    title = a.title or f"{c['topic']}（{built['name']}）"
    secs, frames, cur = [], [], None
    for s in slides:
        sid = re.sub(r"[^A-Za-z0-9_-]", "-", s["id"])[:64]
        if s["section_title"] != cur:
            cur = s["section_title"]
            secs.append((cur.split("｜", 1)[-1], s["num"]))
        html = r.render(dict(s, id=sid), built["questions"], "")
        frames.append(f'<div class="frame" id="s{s["num"]}"><span class="num">{s["num"]}</span>'
                      f'<div class="slide">{html}</div></div>')
    toc = "".join(f'<a href="#s{n}">{tcs.esc(t)}（{n}）</a>' for t, n in secs)
    out = a.out or os.path.join(c.path("out_dir"), deck_filename(c, deck, None).replace("(PPTX)", "(HTML)") + ".html")
    doc = (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{tcs.esc(title)}</title>'
           f'<style>{CSS}</style></head><body><header><b>{tcs.esc(title)}</b><span>{len(slides)} 張（←／→ 換張）</span>'
           f'<span>{toc}</span></header><div class="wrap">{"".join(frames)}</div><script>{JS}</script></body></html>')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8", newline="\n").write(doc)
    print(f"{len(slides)} 張、{len(paths)} 張圖 -> {out}（{os.path.getsize(out) / 1e6:.1f} MB）")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

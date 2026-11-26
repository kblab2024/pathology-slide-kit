# -*- coding: utf-8 -*-
"""把課程素材池產成「一個 HTML 檔」的投影片：圖片內嵌、不需上傳、手機或任何瀏覽器直接開。

教師 2026-10-14：「所以其實就是成品要有 html 版，去哪裡都好做事」。to_claude_slides.py 要先在 claude.ai 上傳圖片
才能用；這支沿用同一個版面渲染（16:9、1920×1080 畫布、1pt＝2px），改成把圖縮小後以 data URI 內嵌，所有張串成一頁，
依視窗寬度縮放；鍵盤 ←／→、PageUp／PageDown 跳張。字型優先用微軟正黑體，沒有就用系統的繁中字型。

用法：
  cd <kit>/scripts && SLIDEKIT_MATERIALS=<materials> PYTHONIOENCODING=utf-8 python html_deck.py --course <課程> [--deck <deck>]
      [--out <檔案.html>] [--max-side 1200] [--quality 75] [--title 名稱]
      [--flow-dir <資料夾>]   流程圖 PNG（assets/images/程式圖/ 的檔）改從這個資料夾讀同名檔（試畫、比較用；不寫進課程資料夾）
預設輸出：<課程>/成品/<PPTX 檔名把 (PPTX) 換成 (HTML)>.html

注意：
- 這是「看內容、帶著走」的版本，版面是 16:9 的網頁排法，和 4:3 的 PPTX 不會逐點一樣；PPTX 仍是主檔。
- 網頁上改不了也不會回素材池；要改內容一樣改素材池再重產。
- 檔案大小主要是圖：--max-side、--quality 調小可以再縮（OneDrive 大檔傳不上時有用）。
- 顏色與開關照這一講實際用的設定：course.yaml 的值再蓋上 decks.<deck> 的 design、emphasis、background（合併法和 gen_pptx.build_pptx 相同）。
- slate 設計（2026-11-26；docs/設計系統.md）：這一講開了 layout.table_style: slate、flow_look: slate 或 lead_bar 時，標題用 design.title 的字色、
  title_bar 的直條、title_rule 的細線，說明句用 design.lead 的字色（lead_bar 開了左邊再加一條藍色直條），條列符號用 design.bullet；
  table_style: slate 的表格是深色表頭白色粗字、隔列淡底、沒有直線、首欄粗體（和 gen_pptx 同一組顏色）。沒開的講照舊，輸出逐位元不變。
- 流程圖的 PNG 由 draw_flow.py 畫（HTML 版只放圖）：開了 flow_look: slate 的講，PNG 也要是 slate 樣子
  （draw_flow.py 給 --course 時會照用到那張圖的講自動判斷；PNG 還是舊樣子時這支會印出來）。
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
from common import build_deck, deck_filename, load_course  # noqa: E402

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


# ---- slate 設計（2026-11-26；docs/設計系統.md）。1pt＝2px。只在這一講開了 slate 的開關時加上去 ----
SLATE_CSS = """
.slide li::marker{{color:#{bullet}}}
"""
# 表格（layout.table_style: slate）：顏色和 gen_pptx.L_table3 的 slate 同一組。表頭下 2pt 深線、列間 1pt 淡線、表底 1.5pt 灰線、沒有直線；
# 第一列資料白底、第二列淡底，依序隔列（和 PPTX 一樣）；首欄粗體。
SLATE_TABLE_CSS = """
.slide th,.slide td{{border:none;border-bottom:2px solid #{thin};padding:10px 16px}}
.slide th{{background:#{head};color:#FFFFFF;font-weight:700;border-bottom:4px solid #{rule}}}
.slide tr:nth-child(odd) td{{background:#{zebra}}}
.slide tr:nth-child(even) td{{background:#FFFFFF}}
.slide tr:last-child td{{border-bottom:3px solid #{foot}}}
.slide td:first-child{{font-weight:700;color:#{first}}}
"""


def deck_course(c, deck):
    """(這一講用的課程設定, 這一講的 layout)：course.yaml 再蓋上 decks.<deck> 的 design、emphasis、background、layout
    （合併法和 gen_pptx.build_pptx 相同）。沒有蓋的講，值和原來的一樣，輸出逐位元不變。"""
    dk = (c.get("decks") or {}).get(deck) or {}
    c2 = type(c)(c)
    if isinstance(dk.get("design"), dict):
        c2["design"] = {**c["design"], **dk["design"]}
    if isinstance(dk.get("emphasis"), dict):
        c2["emphasis"] = {**c["emphasis"], **dk["emphasis"]}
    if dk.get("background"):
        c2["slide"] = {**c["slide"], "background": str(dk["background"])}
    L = {**(c.get("layout") or {}), **(dk["layout"] if isinstance(dk.get("layout"), dict) else {})}
    return c2, L


def is_slate(L):
    return L.get("table_style") == "slate" or L.get("flow_look") == "slate" or bool(L.get("lead_bar"))


def slate_css(D, L):
    css = SLATE_CSS.format(bullet=D.get("bullet", D.get("title_bar", D["cobalt"])))
    if L.get("table_style") == "slate":
        css += SLATE_TABLE_CSS.format(thin=D.get("tbl_line", "E2E8F0"), head=D.get("tbl_head_dark", D.get("cover_block", "1E293B")),
                                      rule=D.get("title", D["deep"]), zebra=D.get("tbl_zebra", "F1F5F9"), foot=D.get("tbl_foot", "94A3B8"),
                                      first=D.get("tbl_first", D["ink"]))
    return css


class SlateR(tcs.R):
    """slate 設計的標題、說明句與國考題題下那一行（其他照 to_claude_slides.R）。版面照 gen_pptx 的 content_title、_lead_bar、L_quiz。"""

    def __init__(self, course, assets, layout):
        super().__init__(course, assets)
        self.L = layout

    def title(self, s):
        D = self.D
        h2 = (f'<h2 style="font-size:{self.pt("title")}px; font-weight:700; line-height:1.15; color:#{D.get("title", D["deep"])}; '
              f'border-left:12px solid #{D.get("title_bar", D["cobalt"])}; padding:0px 0px 0px 28px">{tcs.rich(s["title"], self.E)}</h2>')
        if not D.get("title_rule"):
            return h2
        w = max(1, round(float(D.get("title_rule_w", 0.75)) * tcs.PX))          # 標題下一條淡色細線
        return f'<div style="border-bottom:{w}px solid #{D["title_rule"]}; padding-bottom:14px">{h2}</div>'

    def lead(self, bl):
        col = self.D.get("lead", self.D["cobaltd"])
        ps = "".join(f'<p style="font-size:{self.pt("lead")}px; line-height:1.35; color:#{col}">'
                     f'{tcs.rich(tcs.bullet_level(b)[1], self.E)}</p>' for b in bl)
        lb = self.L.get("lead_bar")
        if not ps or not lb:
            return ps
        bar = lb if isinstance(lb, str) else self.D.get("title_bar", self.D["cobalt"])     # layout.lead_bar: true 或色碼
        return f'<div style="border-left:8px solid #{bar}; padding-left:24px">{ps}</div>'

    def render(self, s, qs, note):
        html = super().render(s, qs, note)
        band = self.L.get("quiz_note_band")
        if s["type"] == "quiz" and s.get("quiz_note") and isinstance(band, dict):
            # 題下那一行：淡冰藍底、左邊一條藍色細直線的橫條（gen_pptx.L_quiz 的 quiz_note_band）
            old = f'<p style="font-size:{self.pt("label")}px; color:#{self.D["cobaltd"]}">{tcs.esc(s["quiz_note"])}</p>'
            new = (f'<p style="font-size:{self.pt("label")}px; line-height:1.3; color:#{self.D.get("lead", self.D["cobaltd"])}; '
                   f'background:#{band.get("fill", "EAF1F8")}; border-left:9px solid #{band.get("bar", self.D["cobalt"])}; '
                   f'padding:16px 30px">{tcs.esc(s["quiz_note"])}</p>')
            html = html.replace(old, new)
        return html


def data_uri(path, max_side, quality, kind_path=None):
    """kind_path：用哪個路徑判斷是不是程式圖（--flow-dir 換了檔案來源時，照原來的路徑判斷）。"""
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
    kp = kind_path or path
    is_drawing = ("程式圖" in kp) or kp.endswith(("_zh.png", "_zh2.png", "_zh3.png", "_zh4.png")) or "legend" in kp
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
    ap.add_argument("--flow-dir", default=None, help="流程圖 PNG（assets/images/程式圖/ 的檔）改從這個資料夾讀同名檔（試畫、比較用）")
    a = ap.parse_args()
    c0 = load_course(a.course)
    deck = a.deck or c0["deck_order"][0]
    c, L = deck_course(c0, deck)                  # 這一講實際用的顏色與開關
    built = build_deck(c0, deck)
    slides = built["slides"]

    def src_of(p):
        if a.flow_dir and os.path.basename(os.path.dirname(p)) == "程式圖":
            alt = os.path.join(a.flow_dir, os.path.basename(p))
            if os.path.isfile(alt):
                return alt
        return p

    paths = sorted({os.path.abspath(i["abspath"]) for s in slides for i in s["imgs"] if i.get("exists")})
    assets = {os.path.normcase(p): data_uri(src_of(p), a.max_side, a.quality, kind_path=p) for p in paths}
    slate = is_slate(L)
    if L.get("flow_look") == "slate":
        # 流程圖 PNG 是 draw_flow.py 畫的；slate 的 PNG 帶著 flow_look 的標記，沒有就是還沒照這一講的設定重畫
        old = set()
        for s in slides:
            if not (s.get("flow") or {}).get("fig") or s["flow"]["fig"].get("kind") == "stages":
                continue
            for i in s["imgs"]:
                p = i.get("abspath") or ""
                if i.get("exists") and os.path.basename(os.path.dirname(p)) == "程式圖":
                    try:
                        look = getattr(Image.open(src_of(p)), "text", {}).get("flow_look")
                    except Exception:
                        look = None
                    if look != "slate":
                        old.add(os.path.basename(p))
        if old:
            print(f"[注意] 這一講開了 flow_look: slate，下面 {len(old)} 張流程圖 PNG 還是舊樣子；先跑 draw_flow.py <規格.json> <程式圖資料夾> "
                  f"--course {a.course} --deck {deck}：" + "、".join(sorted(old)), file=sys.stderr)
    r = SlateR(c, assets, L) if slate else tcs.R(c, assets)
    title = a.title or f"{c['topic']}（{built['name']}）"
    secs, frames, cur = [], [], None
    for s in slides:
        sid = re.sub(r"[^A-Za-z0-9_-]", "-", s["id"])[:64]
        if s["section_title"] != cur:
            cur = s["section_title"]
            secs.append((cur.split("｜", 1)[-1], s["num"]))
        html = r.render(dict(s, id=sid), built["questions"], "")      # 第三個參數是備忘稿：HTML 版一律不放（硬規則 18）
        frames.append(f'<div class="frame" id="s{s["num"]}"><span class="num">{s["num"]}</span>'
                      f'<div class="slide">{html}</div></div>')
    toc = "".join(f'<a href="#s{n}">{tcs.esc(t)}（{n}）</a>' for t, n in secs)
    out = a.out or os.path.join(c.path("out_dir"), deck_filename(c, deck, None).replace("(PPTX)", "(HTML)") + ".html")
    doc = (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{tcs.esc(title)}</title>'
           f'<style>{CSS + (slate_css(c["design"], L) if slate else "")}</style></head><body><header><b>{tcs.esc(title)}</b><span>{len(slides)} 張（←／→ 換張）</span>'
           f'<span>{toc}</span></header><div class="wrap">{"".join(frames)}</div><script>{JS}</script></body></html>')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8", newline="\n").write(doc)
    print(f"{len(slides)} 張、{len(paths)} 張圖 -> {out}（{os.path.getsize(out) / 1e6:.1f} MB）")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

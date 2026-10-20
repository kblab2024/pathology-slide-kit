# -*- coding: utf-8 -*-
"""把課程素材池轉成 Claude Slides（claude.ai 的投影片 Artifact）可讀的檔案，讓教師在網頁上手動改。

Claude Slides 是 16:9、1920×1080 px 畫布；字級換算 1pt = 2px（標題 36pt→72px、內文 28pt→56px、出處 14pt→28px）。
字型用 Google Fonts 的 Noto Sans TC（微軟正黑體無法在網頁載入）。
注意：網頁上改的內容不會自動回到 pool.md；要回灌就從網頁匯出 PPTX，再用 dump_pptx.py／diff_decks.py 比對。

兩段式用法：
  1) python to_claude_slides.py --course immune --from 1 --to 18 --list-images <out.json>
       列出這些張需要上傳的圖檔（絕對路徑），交給 Artifact 工具以 asset 上傳
  2) python to_claude_slides.py --course immune --from 1 --to 18 --assets <map.json> --out <資料夾> [--title 名稱]
       map.json = {"<圖檔絕對路徑>": "/_blob/<id>", …}；產出 <資料夾>/project/deck.json 與 project/slides/<id>.html
"""
import argparse
import datetime
import html
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SOFT_BREAK, build_deck, bullet_level, load_course, notes_map, parse_markup, parse_script  # noqa: E402

PX = 2  # 1pt → 2px
FONT = "'Noto Sans TC', Arial, sans-serif"
CN_NUM = {1: "一", 2: "二", 3: "三", 4: "四"}


def esc(t):
    return html.escape(unicodedata.normalize("NFC", t or ""), quote=False)


def brk(t):
    """esc＋素材池的段內換行「⏎」換成 <br>（2026-10-20 之前網頁版會把 ⏎ 原樣印出來）。"""
    return esc(t).replace(SOFT_BREAK, "<br>")


def rich(text, emph):
    out = []
    for t, col in parse_markup(text or "", emph):
        if not t:
            continue
        out.append(f'<span style="color:#{col}">{brk(t)}</span>' if col else brk(t))
    return "".join(out)


def lines(text, px, width):
    """估算行數：中文字寬 1em、西文 0.55em。"""
    from common import strip_markup
    em = sum(1.0 if ord(ch) > 0x2E7F else 0.55 for ch in strip_markup(text or ""))
    return max(1, int(-(-em * px // width)))


INNER_H = 1080 - 72 - 96   # section 上下 padding 之後的高度
INNER_W = 1920 - 96 * 2


class R:
    def __init__(self, course, assets):
        self.c = course
        self.S = course.sizes
        self.D = course["design"]
        self.E = course["emphasis"]
        self.assets = assets

    def pt(self, key):
        return int(self.S[key] * PX)

    def img(self, im, w, h):
        src = self.assets.get(os.path.normcase(os.path.abspath(im["abspath"])))
        if not src:
            return ""
        alt = esc(im.get("desc") or im.get("label") or os.path.basename(im["path"]))
        return (f'<img src="{src}" alt="{alt}" style="width:{w}px; height:{h}px; object-fit:contain">')

    def credit(self, text):
        t = text if text.startswith(("圖", "資料來源")) else "圖：" + text
        return f'<p style="font-size:{self.pt("credit")}px; color:#{self.D["grey"]}; line-height:1.25">{esc(t)}</p>'

    def figure(self, im, w, h, label=None):
        parts = []
        if label:
            parts.append(f'<p style="font-size:{self.pt("label")}px; font-weight:700; color:#{self.D["cobaltd"]}; '
                         f'text-align:center">{esc(label)}</p>')
        parts.append(self.img(im, w, h))
        if im.get("src"):
            parts.append(self.credit(im["src"]))
        return (f'<div style="display:flex; flex-direction:column; gap:8px; align-items:center; flex:1">'
                + "".join(parts) + "</div>")

    def title_h(self, s):
        return lines(s["title"], self.pt("title"), INNER_W - 40) * self.pt("title") * 1.15

    def lead_h(self, bl):
        return sum(lines(b, self.pt("lead"), INNER_W) * self.pt("lead") * 1.35 for b in bl)

    def title(self, s):
        return (f'<h2 style="font-size:{self.pt("title")}px; font-weight:700; line-height:1.15; color:#{self.D["deep"]}; '
                f'border-left:12px solid #{self.D["cobalt"]}; padding:0px 0px 0px 28px">{rich(s["title"], self.E)}</h2>')

    def bullets(self, bl, size_key="body"):
        lis = "".join(f"<li>{rich(bullet_level(b)[1], self.E)}</li>" for b in bl)
        return (f'<ul style="font-size:{self.pt(size_key)}px; line-height:1.35; color:#{self.D["ink"]}">{lis}</ul>')

    def lead(self, bl):
        return "".join(f'<p style="font-size:{self.pt("lead")}px; line-height:1.35; color:#{self.D["cobaltd"]}">'
                       f'{rich(bullet_level(b)[1], self.E)}</p>' for b in bl)

    def src_line(self, s):
        if not s.get("src"):
            return ""
        return (f'<p style="position:absolute; left:96px; bottom:36px; width:1728px; font-size:{self.pt("credit")}px; '
                f'color:#{self.D["grey"]}">{esc("資料來源：" + "；".join(s["src"]))}</p>')

    def section(self, s, body, dark=False, note=""):
        bg = self.D["deep"] if dark else self.c["slide"].get("background", self.D["snow"])
        col = "#FFFFFF" if dark else f"#{self.D['ink']}"
        aside = f"<aside>{esc(note)[:3900]}</aside>" if note else ""
        pb = 96
        if s.get("src"):                        # 出處行是絕對定位在底部；兩行時預留空間，內容才不會壓到它（2026-10-20）
            n = lines("資料來源：" + "；".join(s["src"]), self.pt("credit"), 1728)
            pb = max(96, int(36 + n * self.pt("credit") * 1.3 + 16))
        return (f'<section id="{s["id"]}" style="background:#{bg}; color:{col}; font-family:{FONT}; '
                f'padding:72px 96px {pb}px; display:flex; flex-direction:column; gap:32px">'
                f'{body}{self.src_line(s)}{aside}</section>')

    def diagram(self, s):
        """框架圖（course.yaml diagrams.<名>），版面照 gen_pptx.L_diagram：orient rows＝節點直排、屬性為欄（node_w、col_w 單位 in），
        預設 cols＝節點橫排、屬性為列。格子裡的換行字元分行；未點亮的畫淺灰。2026-10-20 補：之前網頁版的框架圖張只有標題。"""
        spec = (self.c.get("diagrams") or {}).get(s.get("diagram"))
        if not spec:
            return f'<p style="font-size:{self.pt("body")}px; color:#{self.D["terrad"]}">（course.yaml 沒有框架圖 {esc(s.get("diagram"))}）</p>'
        bright = set(s.get("diagram_bright") or ["全部"])
        allon = "全部" in bright
        nodes, rows, groups = spec["nodes"], spec.get("rows", []), spec.get("groups", {})
        lit = lambda nd: allon or nd["label"].replace("\n", "") in bright or nd["label"] in bright or nd.get("group") in bright
        gcol = lambda nd: groups.get(nd.get("group"), {"main": self.D["cobalt"], "light": "E3EDF8"})
        cs, lab, gap = self.pt("min"), self.pt("label"), 12
        sw, m = self.c["slide"]["width"], self.c["slide"].get("margin", 0.5)
        W = 1920 - 2 * 72                       # 框架圖左右各借 24px，寬度對到 PPTX 的 0.5 in 邊界（144 px／in）
        scale = W / (sw - 2 * m)

        def txt(x):                             # 換行字元先換成「⏎」再上色，標記內的換行也不會把 [[橘:…]] 拆壞
            return f'<div>{rich(str(x).replace(chr(10), SOFT_BREAK), self.E)}</div>'

        def box(x, size, on, g, head=False):
            fill = g["light"] if on else "FFFFFF"
            line = g["main"] if on else ("C3D3E0" if head else "E2EAF1")
            col = (self.D["deep"] if head else self.D["ink"]) if on else ("8AA0B5" if head else "BCCBD8")
            return (f'<div style="background:#{fill}; border:{4 if head else 2}px solid #{line}; '
                    f'border-radius:{20 if head else 14}px; padding:4px 10px; display:flex; align-items:center; '
                    f'justify-content:center; text-align:center; font-size:{size}px; line-height:1.12; color:#{col}; '
                    f'font-weight:{700 if head and on else 400}">{txt(x)}</div>')

        def name(x, align="center", on=True):
            return (f'<div style="display:flex; align-items:center; justify-content:{align}; text-align:{align}; '
                    f'font-size:{cs}px; font-weight:700; line-height:1.1; color:#{self.D["deep"] if on else "A8BACA"}">'
                    f'{txt(x)}</div>')

        if spec.get("orient") == "rows":
            nc = len(rows)
            w0 = spec.get("node_w", 3.0) * scale
            cw = spec.get("col_w") or [1.0] * nc
            rest = W - w0 - nc * gap
            cols = [w0] + [rest * x / sum(cw) for x in cw]
            cells = ['<div></div>'] + [name(r["name"]) for r in rows]
            for i, nd in enumerate(nodes):
                on = lit(nd)
                cells.append(box(nd["label"], lab, on, gcol(nd), head=True))
                cells += [box(r["cells"][i], cs, on and (allon or r["name"] in bright), gcol(nd)) for r in rows]
            tmpl_r = f"auto repeat({len(nodes)}, minmax(min-content, 1fr))"
        else:
            lw = spec.get("label_w", 0.95) * scale if rows else 0
            nw = (W - lw - (len(nodes) - 1) * gap - (gap if rows else 0)) / len(nodes)
            cols = ([lw] if rows else []) + [nw] * len(nodes)
            cells = (['<div></div>'] if rows else []) + [box(nd["label"], lab, lit(nd), gcol(nd), head=True) for nd in nodes]
            for r in rows:
                on_row = allon or r["name"] in bright
                cells.append(name(r["name"], align="flex-end", on=on_row))
                cells += [box(x, cs, on_row and lit(nodes[i]), gcol(nodes[i])) for i, x in enumerate(r["cells"])]
            tmpl_r = f"auto repeat({len(rows)}, minmax(min-content, 1fr))"
        return (f'<div style="display:grid; grid-template-columns:{" ".join(f"{x:.0f}px" for x in cols)}; '
                f'grid-template-rows:{tmpl_r}; gap:{gap}px; flex:1; min-height:0; margin:0 -24px">{"".join(cells)}</div>')

    def render(self, s, qs, note):
        t, imgs = s["type"], [i for i in s["imgs"] if i.get("exists")]
        if t == "title":
            sub = "".join(f'<p style="font-size:{self.pt("cover_sub") if i == 0 else self.pt("min")}px; color:#D8E6F4">'
                          f'{esc(bullet_level(b)[1])}</p>' for i, b in enumerate(s["bullets"][:4]))
            body = (f'<div style="flex:1"></div><div style="display:flex; flex-direction:column; gap:24px; '
                    f'border-left:14px solid #{self.D["terra"]}; padding:0px 0px 0px 40px">'
                    f'<h1 style="font-size:{self.pt("cover")}px; font-weight:700; color:#FFFFFF">{brk(s["title"])}</h1>'
                    f'{sub}</div><div style="flex:1"></div>')
            return self.section(s, body, dark=True, note=note)
        if t == "divider":
            sub = "".join(f'<p style="font-size:{self.pt("divider_sub")}px; color:#D8E6F4">{esc(bullet_level(b)[1])}</p>'
                          for b in s["bullets"][:2])
            body = (f'<div style="flex:1"></div><div style="display:flex; flex-direction:column; gap:24px; '
                    f'border-left:14px solid #{self.D["terra"]}; padding:0px 0px 0px 40px">'
                    f'<h1 style="font-size:{self.pt("divider")}px; font-weight:700; color:#FFFFFF">{brk(s["title"])}</h1>'
                    f'{sub}</div><div style="flex:1"></div>')
            return self.section(s, body, dark=True, note=note)
        if t == "quiz":
            q = qs.get(s["quiz"] or "")
            if not q:
                return self.section(s, self.title(s) + f'<p style="font-size:56px">（題庫查無 {esc(s["quiz"])}）</p>', note=note)
            tpl = self.c.deck(s["deck"]).get("quiz_label", "{年度}-{第幾次} 第{題號}題")
            label = tpl.format(年度=q["年度"], 第幾次=CN_NUM.get(int(q["第幾次"]), q["第幾次"]), 次=q["第幾次"], 題號=q["題號"])
            ans = [a.strip() for a in str(q["answer"]).split(",")]
            opts = "".join(
                f'<p style="font-size:{self.pt("quiz")}px; line-height:1.3; color:'
                f'{("#" + self.E.get("藍", "143F9C")) if k in ans else "#" + self.D["ink"]}">'
                f'({k}) {esc(v)}</p>' for k, v in q["options"].items())
            note_line = (f'<p style="font-size:{self.pt("label")}px; color:#{self.D["cobaltd"]}">{esc(s["quiz_note"])}</p>'
                         if s.get("quiz_note") else "")
            body = (self.title(dict(s, title=label))
                    + f'<p style="font-size:{self.pt("quiz")}px; line-height:1.3; color:#{self.D["deep"]}">'
                      f'{q["題號"]}. {esc(q["question"])}</p>'
                    + f'<div style="display:flex; flex-direction:column; gap:8px">{opts}</div>' + note_line)
            return self.section(s, body, note=note)
        if t == "stats":
            tiles = [b.split("｜", 1) for b in s["bullets"] if "｜" in b]
            cards = "".join(
                f'<div style="flex:1; display:flex; flex-direction:column; gap:16px; align-items:center; '
                f'justify-content:center; background:#{self.D["tint"]}; border:2px solid #{self.D["line"]}; '
                f'border-radius:24px; padding:40px">'
                f'<p style="font-size:{self.pt("stats_big")}px; font-weight:700; color:#{self.D["cobalt"]}">{esc(a)}</p>'
                f'<p style="font-size:{self.pt("label")}px; text-align:center">{esc(b)}</p></div>' for a, b in tiles)
            return self.section(s, self.title(s) + f'<div style="display:flex; gap:32px">{cards}</div>', note=note)
        if t in ("flash", "robbins", "big") or (t == "pair" and len(imgs) < 2):
            lead = (f'<p style="font-size:{self.pt("big")}px; line-height:1.25; color:#{self.D["deep"]}">'
                    + "<br>".join(rich(bullet_level(b)[1], self.E) for b in s["bullets"]) + "</p>"
                    if t == "big" and s["bullets"] else self.lead(s["bullets"]))
            used = self.title_h(s) + (sum(lines(b, self.pt("big"), INNER_W) * self.pt("big") * 1.25 for b in s["bullets"])
                                      if t == "big" else self.lead_h(s["bullets"])) + 32 * 3 + 45
            fig = self.figure(imgs[0], 1700, int(max(300, INNER_H - used))) if imgs else ""
            return self.section(s, self.title(s) + lead + fig, note=note)
        if t == "pair":
            used = self.title_h(s) + self.lead_h(s["bullets"]) + 32 * 3 + 45 + (70 if any(i.get("label") for i in imgs) else 0)
            figs = "".join(self.figure(im, 820, int(max(300, INNER_H - used)), label=im.get("label")) for im in imgs[:2])
            return self.section(s, self.title(s) + self.lead(s["bullets"])
                                + f'<div style="display:flex; gap:48px">{figs}</div>', note=note)
        if t == "diagram":
            return self.section(s, self.title(s) + self.diagram(s), note=note)
        if t == "table3" and s.get("table"):
            rows = s["table"]
            n = len(rows[0])
            head = "".join(f'<th style="width:{int(100 / n)}%">{rich(c, self.E)}</th>' for c in rows[0])
            trs = "".join("<tr>" + "".join(f"<td>{rich(c, self.E)}</td>" for c in r) + "</tr>" for r in rows[1:])
            table = (f'<table style="font-size:{self.pt("table")}px; color:#{self.D["ink"]}">'
                     f'<tr style="background:#{self.D["tint"]}">{head}</tr>{trs}</table>')
            return self.section(s, self.title(s) + self.lead(s["bullets"]) + table, note=note)
        # left（預設）：條列＋右圖
        if imgs:
            body = (self.title(s) + f'<div style="display:flex; gap:48px; flex:1">'
                    f'<div style="flex:1; display:flex; flex-direction:column">{self.bullets(s["bullets"])}</div>'
                    f'{self.figure(imgs[0], 820, int(max(300, min(640, INNER_H - self.title_h(s) - 32 - 50))))}</div>')
        else:
            body = self.title(s) + self.bullets(s["bullets"], "body_noimg")
        return self.section(s, body, note=note)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", required=True)
    ap.add_argument("--deck", default=None)
    ap.add_argument("--from", dest="lo", type=int, default=1)
    ap.add_argument("--to", dest="hi", type=int, default=10 ** 6)
    ap.add_argument("--list-images")
    ap.add_argument("--assets")
    ap.add_argument("--out")
    ap.add_argument("--title", default=None)
    a = ap.parse_args()
    c = load_course(a.course)
    deck = a.deck or c["deck_order"][0]
    built = build_deck(c, deck)
    slides = [s for s in built["slides"] if a.lo <= s["num"] <= a.hi]
    if a.list_images:
        paths = sorted({os.path.abspath(i["abspath"]) for s in slides for i in s["imgs"] if i.get("exists")})
        json.dump(paths, open(a.list_images, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
        print(len(paths), "images")
        return 0
    assets = {os.path.normcase(os.path.abspath(k)): v for k, v in json.load(open(a.assets, encoding="utf-8")).items()}
    r = R(c, assets)
    notes = notes_map(built, parse_script(c))
    os.makedirs(os.path.join(a.out, "project", "slides"), exist_ok=True)
    order, sections, cur = [], {}, None
    for s in slides:
        sid = re.sub(r"[^A-Za-z0-9_-]", "-", s["id"])[:64]
        s = dict(s, id=sid)
        order.append(sid)
        if s["section_title"] != cur:
            cur = s["section_title"]
            sections[f"sec{len(sections) + 1}"] = {"description": cur, "start": sid}
        open(os.path.join(a.out, "project", "slides", sid + ".html"), "w", encoding="utf-8", newline="\n").write(
            r.render(s, built["questions"], notes.get(s["id"], "")))
    idx = {"v": 4, "createdOnFiles": {"v": 1, "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
           "title": a.title or f"{c['topic']}（{built['name']}）", "order": order, "sections": sections,
           "faces": {"noto-sans-tc": {"family": "Noto Sans TC",
                                      "href": "https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&display=swap"}},
           "designSystems": []}
    json.dump(idx, open(os.path.join(a.out, "project", "deck.json"), "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=1)
    print(len(order), "slides ->", a.out)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

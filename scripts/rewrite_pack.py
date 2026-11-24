#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重寫包：把一講投影片上的字交給另一個模型（教師指定 Gemini）用它自己的話整張重寫，回來以後檢查、對照、套回來源檔。

這是每一講的必備步驟（教師 2026-11-21：「請把這個gemini後處理流程列為slidekit的必備流程」）。
規則在 AGENTS.md 硬規則 17，步驟在 docs/SOP_新教案流程.md 第 9b 步，緣由在 docs/教師偏好與決策.md 第 4 節。

為什麼是「重寫」不是「潤飾」：教師喜歡 Gemini 寫中文的方式（「我是喜歡gemini的語法的」「實質上是用gemini的話重寫」）。
先前試過的包寫的是「改成像他的句子、已經像的不要動、寧可少改、新句不可以比原句長」，並附他的舊句子當範本，
對方幾乎不動（「他這樣潤飾得很少 非常不行」）。所以這裡不放他的舊句子、不放句型規則，只鎖事實與版面的底線。
為什麼一定附研究資料：只給句子，對方不知道每一句在講什麼、原書講得多肯定（「你要給gemini一些研究資料 不然他純語句會很糟糕」）。

包裡有什麼：請它做的事 → 不能變的事（重點不增不減、數字與頁碼、專有名詞的中英文、肯定的程度、上色記號、照抄的行、
並陳句、講圖的方位、表格的形狀、標題、長度上限、文體）→ 輸出格式 → 研究資料（各段的事實）→ 每一張的原文（上面列圖的內容、
這一張引用的事實、移下投影片的細節）。不放：教科書的英文原句與引句、圖說原文、頁圖、PDF、圖檔、學生資料、任何私人語料。
不給 PPTX（對方改不回來源檔）。教師自己把包拿去跑、把回覆帶回來；本工具不連外。

用法（在 <kit>/scripts；SLIDEKIT_MATERIALS 指向教材庫）：
  python rewrite_pack.py make  --course <課程> --deck <deck> --out <雲端同步資料夾與 repo 以外的資料夾> [--only 12,13,20-25] [--per-pack 45]
      一節寫一份 .md（節太長就平分），另寫「怎麼用」一份；每張的原文與上限記在 <課程>/_archive/revoice/rewrite_manifest_<deck>.json。
      --only：只包這幾張（內容改過、要請對方再重寫時用）。
  python rewrite_pack.py apply --course <課程> --deck <deck> <回覆檔 …> [--tag gemini1] [--write] [--accept soft|9,13,20-25] [--keep-titles]
      不加 --write 只檢查：寫對照表 <課程>/_archive/revoice/rewrite_<tag>_<deck>_對照表.md（原來／改成／檢查／依據），
      有要對方自己修的張（超行、漏數字、漏英文、上色、沒有回、幾乎沒有改）另寫 …_退回給Gemini.md，請教師貼回同一個對話。
      --write 把檢查是 ok 的張寫回來源檔（--accept 另外指定要套的「看」的張；soft＝全部），紀錄存 rewrite_<tag>_<deck>.json。
回覆的格式（每一張都要回）：
  ### 第 9 張
  T｜標題
  B｜一條條列            （條數可以和原來不同）
  R0｜表頭｜表頭         R1｜格｜格 …（列數、欄數不能變）

機械檢查查得到數字、英文、上色、長度、表格形狀與照抄的行；意思有沒有跑掉查不到。套回以前，主 session 要拿對照表逐張對依據：
程度詞（often 寫成「多」、may 寫成「容易」、many 寫成「多數」）、時態、誰對誰；只把跑掉的那幾個字換回事實帳的說法，逐條記下來。
超長或漏東西的張請對方自己修，不由我們改句子（我們一改又變回我們的話）。套回以後照常重產、補英文、算圖、逐張看。
重寫包交出去以後、回覆套回來以前，不要改那一講的來源檔（改了 apply 會說那一張改過，要重出重寫包）。

course.yaml 選填的設定：
  rewrite:
    label: B2泌尿            # 重寫包檔名用的簡稱（預設：課程代碼＋deck 代號）
    src: [_archive/written/w_a.md, …]     # 句子所在的檔（預設：素材池）。素材池是從批檔組裝出來的課才要寫
    notes: [_archive/written/w_a_notes.md, …]   # 移下投影片的細節（「### 投影片 slug｜…」底下的條列）；預設讀講稿檔的【講義補充】
    digest_dir: _archive/written/digest   # 各段事實摘要 <段>.md（有就用，沒有就從 facts_R.json 列出那一段的事實）
    keep: ['^古文引句', '我覺得']          # 照抄的行（正規表示式，比對去掉上色記號後的字）：引句、教師自己的比喻與個人意見
對象讀 course.yaml 的 audience。數字卡片（stats 版型的「數字｜說明」）、封面、分隔張、國考題張一律不給重寫。
"""
import argparse
import datetime
import difflib
import hashlib
import json
import math
import os
import re
import sys

from common import SOFT_BREAK, build_deck, load_course, parse_pool, parse_script

HEAD = re.compile(r"^## 投影片 ([A-Za-z0-9_\-]+)｜(.*)$")
MARK = re.compile(r"\[\[(藍|紅|橘|青|灰)[:：](.+?)\]\]")
PAIRED = re.compile(r"Robbins|p\.\d{3}")       # 並陳句（教科書前後不一的兩種說法）與帶頁碼的句子
TYPE_ZH = {"left": "左字右圖", "flash": "上字下圖", "pair": "上字、下面左右兩張圖", "table3": "表格", "stats": "數字卡片＋條列",
           "big": "大字張", "robbins": "上字下圖", "diagram": "條列＋框架圖"}
TIGHT = ("flash", "pair", "big", "robbins")    # 說明句多一行、圖就矮一截的版型：上限＝現在的行數；其他版型的上限＝原來字數的 1.1 倍
SKIP = ("title", "divider")


def rd(p):
    return open(p, encoding="utf-8").read()


def visible(s):
    return MARK.sub(r"\2", s).replace(SOFT_BREAK, "")


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def show(text, cell=False):
    """給對方看的寫法：條列去掉我們手動排的換行（⏎），格子照留。"""
    return text if cell else text.replace(SOFT_BREAK, "")


# ---------- 來源檔 ----------
def parse_src(path):
    """回傳 (行, {slug: slide})；slide = {slug, title, tline, type, bullets:[(行號, 文字)], rows:[(行號, [格…])], facts, nested}"""
    lines = rd(path).split("\n")
    slides, cur = {}, None
    for i, ln in enumerate(lines):
        h = HEAD.match(ln)
        if h:
            cur = {"slug": h.group(1), "title": h.group(2).strip(), "tline": i, "type": "left", "bullets": [], "rows": [], "facts": [],
                   "nested": False}
            slides[cur["slug"]] = cur
            continue
        if cur is None:
            continue
        m = re.match(r"<!--\s*type:\s*([a-z0-9]+)\s*-->", ln)
        if m:
            cur["type"] = m.group(1)
            continue
        m = re.match(r"<!--\s*facts:\s*(.*?)-->", ln)
        if m:
            cur["facts"] += m.group(1).split()
            continue
        if ln.startswith("<!--"):
            continue
        b = re.match(r"^((?:  )*)- (.*)$", ln)
        if b:
            cur["nested"] = cur["nested"] or bool(b.group(1))
            cur["bullets"].append((i, b.group(2)))
            continue
        st = ln.strip()
        if st.startswith("|") and not re.match(r"^\|[\s\-:|]*$", st):
            cur["rows"].append((i, split_row(ln)))
    return lines, slides


def settings(course):
    c = dict(course.get("rewrite") or {})
    ab = lambda p: p if os.path.isabs(p) else os.path.join(course["dir"], p)
    c["src"] = [ab(p) for p in (c.get("src") or [])] or [course.path("pool")]
    c["notes"] = [ab(p) for p in (c.get("notes") or [])]
    c["digest_dir"] = ab(c["digest_dir"]) if c.get("digest_dir") else os.path.join(course["dir"], "_archive", "written", "digest")
    c["keep"] = [re.compile(x) for x in (c.get("keep") or [])]
    c["rv"] = os.path.join(course["dir"], "_archive", "revoice")
    return c


def load(course, deck):
    """照 deck 的張序回傳 (設定, 檔 {路徑: 行}, [entry])；entry = {slug, num, nums, section, s（來源檔那一張）, src, pool}。
    封面、分隔張、國考題張與沒有字的張不在裡面。"""
    cfg = settings(course)
    files, where = {}, {}
    for p in cfg["src"]:
        if not os.path.exists(p):               # 別的 deck 還沒寫出來的批檔
            continue
        lines, slides = parse_src(p)
        files[p] = lines
        for slug, s in slides.items():
            where.setdefault(slug, (p, s))
    pool = parse_pool(course)
    out, seen, missing, stale = [], {}, [], []
    for b in build_deck(course, deck)["slides"]:
        slug = b["id"].split("~")[0]
        if slug in seen:
            seen[slug]["nums"].append(b["num"])
            continue
        pe = pool.get(slug) or {}
        if slug not in where:
            if pe.get("type") not in SKIP and not pe.get("quiz"):
                missing.append(slug)
            continue
        p, s = where[slug]
        e = {"slug": slug, "num": b["num"], "nums": [b["num"]], "section": b.get("section_title") or "", "s": s, "src": p, "pool": pe}
        seen[slug] = e
        if s["type"] in SKIP or pe.get("quiz") or not (s["bullets"] or s["rows"]):
            continue
        if pe and (pe.get("title") != s["title"] or [x.strip() for x in pe.get("bullets", [])] != [t for _, t in s["bullets"]]):
            stale.append(slug)
        out.append(e)
    if missing:
        print(f"  [注意] deck 裡有 {len(missing)} 張不在 rewrite.src 的檔裡（沒有包進去）：{missing[:8]}")
    if stale:
        print(f"  [注意] 來源檔和素材池不一致 {len(stale)} 張（先重組素材池再出包或套回）：{stale[:8]}")
    return cfg, files, out


# ---------- 研究資料 ----------
def load_research(course):
    """事實帳與文獻的中文條目：id → (頁或出處, 中文, 種類)。只取改寫過的中文，不取英文原句與引句。"""
    out = {}
    p = os.path.join(course["dir"], "facts", "facts_R.json")
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        for f in (d["facts"] if isinstance(d, dict) and "facts" in d else d):
            out[f["id"]] = (f"p.{f.get('page')}", f.get("zh", ""), f.get("kind", ""))
    p = os.path.join(course["dir"], "facts", "facts_X.json")
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        for c in (d.get("claims", []) if isinstance(d, dict) else []):
            out[c["id"]] = ("文獻 " + str(c.get("slide_cite", "")).strip("()（）"), c.get("claim_zh", ""), "literature")
    return out


def load_notes(course, cfg):
    """移下投影片的細節：slug → [條]。course.yaml rewrite.notes 的檔優先，沒有就讀講稿檔的【講義補充】。"""
    out = {}
    for path in cfg["notes"]:
        cur = None
        if not os.path.exists(path):
            continue
        for ln in rd(path).split("\n"):
            m = re.match(r"^### 投影片 ([A-Za-z0-9_\-]+)｜", ln)
            if m:
                cur = m.group(1)
                out.setdefault(cur, [])
            elif cur and ln.startswith("- "):
                out[cur].append(ln[2:].strip())
    if not cfg["notes"]:
        try:
            for slug, e in parse_script(course).items():
                if e.get("bullets"):
                    out[slug] = [visible(x) for x in e["bullets"]]
        except Exception:
            pass
    return out


EN_QUOTE = re.compile(r"「([^」]*)」")


def en_quote_line(ln):
    """這一行引了英文原文（「」裡幾乎都是英文：中文字 ≤2、英文字母 ≥20）：教科書的英文原句與引句不放進包
    （2026-11-24 發現「前後不一」那一節整段是 Robbins 原句）。中文句子裡夾英文術語的引號不算。"""
    for q in EN_QUOTE.findall(ln):
        cjk = sum("\u4e00" <= ch <= "\u9fff" for ch in q)
        if cjk <= 2 and sum(ch.isascii() and ch.isalpha() for ch in q) >= 20:
            return True
    return False


def digest_text(cfg, seg, research):
    """一段的事實：有摘要檔就用（留事實條目；不留圖說原文、表格轉錄、檔案路徑與引英文原句的行，
    「前後不一」的說明若都是原句就整節不放），沒有就從事實帳列出。"""
    p = os.path.join(cfg["digest_dir"], f"{seg}.md")
    if os.path.exists(p):
        out, keep = [], True
        for ln in rd(p).split("\n"):
            if en_quote_line(ln):
                continue
            if ln.startswith("# "):
                out.append("### " + re.sub(r"；facts_R\.json 切出，(\d+) 條", r"；\1 條", ln[2:]))
                continue
            if ln.startswith("格式："):
                out.append("（每一條：編號｜頁｜種類｜圖表｜內容；英文術語在中文後的括號裡）")
                continue
            if ln.startswith("## "):
                keep = not (ln.startswith("## 本段頁上的圖") or ln.startswith("## 本段頁上的表"))
                if keep:
                    out.append("#### " + re.sub(r"（教師.*$", "", ln[3:]))
                continue
            if keep:
                out.append(ln)
        # 標題底下什麼都沒留（例：「前後不一」整節都是原句）就連標題一起拿掉
        tidy = []
        for i, ln in enumerate(out):
            if ln.startswith("#### "):
                nxt = next((x for x in out[i + 1:] if x.strip()), "")
                if not nxt or nxt.startswith("#"):
                    continue
            tidy.append(ln)
        return "\n".join(tidy).strip() + "\n"
    rows = [(k, v) for k, v in research.items() if k.startswith(seg + "-")]
    if not rows:
        return ""
    return f"### {seg}（{len(rows)} 條；每一條：編號｜頁｜種類｜內容）\n\n" + "".join(f"- {k}｜{v[0]}｜{v[2]}｜{v[1]}\n" for k, v in rows)


def clean_pic(x):
    """IMG 的「內容」是寫給我們自己看的（有檔案路徑、哪個檔是圖版）：只留這張圖畫了什麼。"""
    x = re.sub(r"（[^（）]*(?:_archive|assets/|\.py|\.json)[^（）]*）", "", x or "")
    for cut in ("這個檔是圖版", "原來的手繪圖", "原來放的", "PPTX 上", "；圖裡沒有字"):
        i = x.find(cut)
        if i > 0:
            x = x[:i]
    return x.strip(" ；。：")


# ---------- 一張的原文、照抄的行與上限 ----------
_GP = {}


def lead_metrics(text, typ):
    """說明句排出來幾行、把最後一行寫滿還放得下幾個全形字（用 gen_pptx 的量字函式，和產檔時的斷行估算一致）。"""
    gp = _GP["gp"]
    size = gp.G.S["big"] if typ == "big" else gp.G.S["lead"]
    w = gp.G.SW - 2 * gp.G.M - 0.26
    n = gp.n_lines(text, size, w)
    k = 0
    while k < 14 and gp.n_lines(text + "字" * (k + 1), size, w) == n:
        k += 1
    return n, k


def keep_why(cfg, typ, text):
    if typ == "stats" and "｜" in text:
        return "數字卡片"
    if any(rx.search(visible(text)) for rx in cfg["keep"]):
        return "教師自己的話"
    return ""


def record(cfg, e):
    """一張的原文與上限（寫進 manifest，也是 apply 比對的基準）。"""
    s = e["s"]
    bullets = [t for _, t in s["bullets"]]
    rows = [cs for _, cs in s["rows"]]
    n = sum(len(visible(t)) for t in bullets) + sum(len(visible(c)) for cs in rows for c in cs)
    rec = {"slug": s["slug"], "type": s["type"], "title": s["title"], "bullets": bullets, "rows": rows,
           "keep": [t for t in bullets if keep_why(cfg, s["type"], t)], "n": n, "limit": int(math.ceil(n * 1.1)), "lines": None}
    if s["type"] in TIGHT and bullets:
        ll = [lead_metrics(t, s["type"]) for t in bullets]
        rec["lines"] = sum(a for a, _ in ll)
        rec["limit"] = n + min(14, sum(max(0, b - 1) for _, b in ll))      # 把現在這幾行寫滿還放得下的字數
    return rec


RULES = """## 一、請你做的事

- 這是一位病理科教師大堂課投影片的草稿。對象是{AUDIENCE}。
- 內容以 {TEXTBOOK}為準：事實、數字、頁碼都逐條查核過，每一張要教哪幾件事也已經定了。
- 現在的句子是另一個 AI 起草的，教師不滿意它的文法與用字；他喜歡你寫中文的方式。
- 所以請你**用你自己的話，把每一張投影片上的字整個重寫**。這是重寫，不是校對，也不是潤飾：
  - 每一條條列、每一格表格都請你重新造句。只換幾個詞、只調語序，或把原句照抄回來，都不算重寫。
  - 不必保留原文的句型、語序、語氣與用詞，也不必模仿任何人的文風。照你自己認為最清楚、最自然的中文寫。
  - 同一張裡的條列可以重新安排：合併、拆開、調整先後都可以。
  - 原文的用處，只是告訴你這一張要教哪幾件事。請先讀懂研究資料，再用你的話把這幾件事講清楚。
  - 建議的做法：看完一張的原文與依據以後，先想「這一張要讓學生學到哪幾件事」，然後從頭寫，不要一句對一句地改。
- 順序：先讀第四節（研究資料），再照第五節一張一張重寫，照第三節的格式輸出。

## 二、不能變的事（只有這些；除此之外都交給你）

1. **內容**：每一張要教的重點不增加、不減少。研究資料裡有、原文沒有的事實不要加進來（這一班教多少，教師已經定了）；原文有的重點不要漏掉。你可以依照研究資料把一句話講得更清楚、更準確（例如把因果關係寫出來），但不要因此多放新的病名、機轉或數字。
2. **數字與頁碼**：原文的每一個數字（百分比、年齡、層數、分數、頁碼如 p.871）都要留著，寫法照原樣；不要加原文沒有的數字。
3. **專有名詞**：一律寫成「中文(English)」，括號用半形，括號裡的英文與縮寫照抄。中文名稱照原文，不換成別的譯名（例：分化不良(dysplasia)不要寫成異型增生；研究資料裡的譯名和原文不同時以原文為準）。同一個名詞在一張裡出現幾次，每一次都要帶著括號裡的英文。不要新增原文沒有的專有名詞。
4. **肯定的程度**：原文與研究資料寫「通常、大多、常、很少、有可能、目前認為」的地方，重寫後要一樣保留，不要寫成「一定、都會、不會」，也不要把「常」寫成「多數」、「可能」寫成「容易」；過去的事不要寫成現在還是這樣。
5. **上色的記號**：`[[橘:名詞]]`、`[[藍:重點]]` 這種雙中括號是上色（冒號前面是顏色）。原文包起來的名詞，重寫後這個名詞還要在，照樣用同一種顏色包起來。原文包起來的是一句重點的，重寫後也要有一處同色的重點，標在同一件事上（裡面的字跟著你的新句子寫）。每一種顏色的處數和原文一樣，原文沒有上色的地方不要自己加。
6. **標了「（照抄）」的行**：引句、教師自己的比喻與個人意見、數字卡片。一個字都不要改，原樣抄回來（放在這一張的第幾條可以調）。
7. **並陳句**：有些句子或格子寫「Robbins p.xxx 寫…，p.yyy 寫…」，是刻意把教科書前後不一的兩種說法並列給學生看（那一張會註明）。句型可以換，但是兩種說法與兩個頁碼都要留著，不要合併成一種，也不要替教科書下結論。
8. **講圖的句子**：圖沒有換。原文說「左圖、右圖、箭頭指的是…」的地方，方位與所指的東西照原文。
9. **表格**：列數、欄數不變，每一格還是講原來那一格的事；格子可以是短語。格子裡要換行的地方寫 `⏎`（一行大約不超過原來最長的那一行）；條列裡不要寫 `⏎`。
10. **標題**：只是病名或構造名的標題照留。寫成一句話的標題可以重寫，不要比原來長。註明「標題和上一張相同」的，要改就改成同一個。
11. **長度**：版面已經排好了。每一張都標了正文（條列與表格，不含標題）原來幾個字、上限幾個字，重寫後不要超過上限；表格的每一格不要比原來長（最多多兩三個字）。「上字下圖」的張另外標了說明句現在佔幾行：一行大約 {PER_LINE} 個全形字（英文兩個字母算一個字），多一行圖就矮一截，所以不要比現在多行。
12. **文體**：繁體中文（台灣用語）。這份投影片上課時投在螢幕上，也是學生的講義：每一條要是看得懂的完整句子。不稱呼學生、不寫開場白與打氣的話、不提考試、不用驚嘆號與表情符號、不用粗體星號。
13. 我們的檢查程式會擋下面這些字，請避開：連寫的全形破折號（——）、值得注意的是、讓我們、總而言之、綜上所述、簡而言之、換句話說、換言之、本質上、至關重要、扮演…角色、關鍵在於、不僅…更…。

以上是底線，不是要你保守。在這些底線之內，句子怎麼寫完全由你決定，請放手重寫。

## 三、輸出格式

照第五節的順序，**每一張都要輸出**（封面、分隔張與註明不用重寫的張除外），寫法和第五節每一張「原文」底下那幾行一樣。例：

```
### 第 4 張
T｜（標題）
B｜（一條條列）
B｜（另一條條列）
R0｜（表頭第 1 欄）｜（表頭第 2 欄）
R1｜（第 1 列第 1 欄）｜（第 1 列第 2 欄）
```

- 一行一個單位：`T` 是標題，`B` 是一條條列，`R0` 是表頭，`R1`、`R2`… 是表格的每一列；用全形直線「｜」分隔。沒有表格的張就沒有 `R` 行。
- 請把整份輸出放在程式碼區塊（```）裡，複製的時候才不會跑掉換行。
- 不要把「依據」「細節」這些研究資料抄回來，也不用解釋每一句為什麼這樣寫。
- 全部輸出完以後，在程式碼區塊外面另寫一段「備註」：只列你發現原文和研究資料不合、或看起來有錯的地方（張號加一句話）。這種地方重寫時意思仍照原文，不要自己改掉，由教師決定。沒有就寫「無」。
- 一次寫不完的話，請停在某一張的結尾；我說「繼續」，你再從下一張接著寫。
"""

HOWTO = """# 給 Gemini 的重寫包怎麼用（{LABEL}，{DATE}，草稿）

這幾份包請 Gemini「用它自己的話整張重寫」投影片上的字，不是潤飾。

1. 每一份包各開一個新對話，選最好的模型。
2. 把檔案上傳（或整份貼上），訊息寫一句：
   「請照這份檔案開頭的指示，用你自己的話重寫第五節的每一張投影片。」
3. 它寫到一半停下來，就回「繼續」。
4. 它回的內容整段複製（程式碼區塊右上角有複製鈕，最後的備註也要），直接貼給做投影片的 session；
   或存成文字檔放進這個資料夾，再說一聲。
5. 接下來由做投影片的 session 檢查（數字、頁碼、英文、上色、長度、照抄的行）、逐張對意思、套回來源檔、重產，交下一版。
   有超長或漏數字的張，會給一小段「退回給 Gemini」的文字，貼回同一個對話請它自己修。

不要請它直接改 PPTX（改不回來源檔）。回覆套回來以前，這一講的來源檔先不動。

{KEEP}
標題也開放它重寫（只是病名或構造名的標題不動）；不要它動標題的話，套回時可以不套。
"""


FUSE_TASK = """## 一、請你做的事（這一次是「融合」，不是整張重寫）

- 這是一位病理科教師大堂課投影片的草稿，對象是{AUDIENCE}。內容以 {TEXTBOOK}為準，句子已經是你上一次重寫的字，教師很滿意。
- 這一講的學生是中醫系。教師希望把**中醫的對照（方劑與組成、證型、對應的西醫病理）融合進原來的投影片**，讓學生看到自己學的中醫和這一張的病理怎麼接起來；**不是另外教中醫**，每一張的主角仍是病理。
- 所以這一次只改第五節列的幾張。每一張都附了「要融合的中醫對照」（已經查核過），請把它用你自己的話融合進這一張：通常是加一條，或把它併進原有的一條或一格；可以順手調整原來的句子讓整張讀起來順，但原來的重點、數字、頁碼、專有名詞、上色都要留著（見第二節）。標了「新加的融合張」的幾張是我們起草的對照表，請用你自己的話整張寫。
- 教師的話：「融合部分要少但精 不要耽誤到正課內容」。中醫的部分寫短、寫準，不要擴寫。
- **張數與上課時間不能增加**：不再新增投影片（融合張已經放好了）；每一張的字數上限已經含融合用的放寬（第五節每張第一行），不要超過；原來的張裡，中醫的部分一張最多一條，寫成一句完整、短的句子。
- 第五節每一張附的「建議的一行」是我們起草的，只是告訴你要放什麼，請用你自己的話寫。
- 第六節是國考題下面那一行說明（藍灰色小字），請改寫成「方劑（關鍵組成）→ 證型 → 西醫病理」的一句或兩句。
- 順序：先讀第四節（研究資料），再照第五、六節一張一張做，照第三節的格式輸出（第六節的格式寫在第六節）。

"""

FUSE_RW_ADD = """- 這一講的學生是中醫系。這一次除了整張重寫，還要把**中醫的對照（方劑與組成、證型、對應的西醫病理）融合進去**：第五節有些張附了「要融合的中醫對照」（已經查核過），請在重寫那一張的時候把它融合進去（通常是一條，或併進原有的一條或一格）；標了「新加的融合張」的幾張是我們起草的對照表，請用你自己的話整張寫。融合不是另外教中醫，每一張的主角仍是病理。
- 教師的話：「我要的是融合進原內容且符合張數跟時間限制 不是另外教中醫喔」「融合部分要少但精 不要耽誤到正課內容」「給gemini那個不只融合還要重寫喔」。中醫的部分寫短、寫準，不要擴寫；原來的張裡，中醫的部分一張最多一條。不新增投影片；每一張的字數上限已經含融合用的放寬（第五節每張第一行）。
- 這一份有國考題的話，最後有第六節「國考題下面那一行說明」：請改寫成「方劑（關鍵組成）→ 證型 → 西醫病理」的一句或兩句。
"""

FUSE_RW_HOWTO = """# 給 Gemini 的重寫融合包怎麼用（{LABEL}，{DATE}，草稿）

這幾份包請 Gemini「用它自己的話整張重寫」投影片上的字（不是潤飾），同時把中醫的對照（方劑與組成、證型、西醫病理）融合進附了素材的那幾張；有國考題的那一份，最後一節是國考題下面那一行說明。不新增投影片，張數與上課時間不變。

1. 每一份包各開一個新對話，選最好的模型。
2. 把檔案上傳（或整份貼上），訊息寫一句：
   「請照這份檔案開頭的指示，用你自己的話重寫第五節的每一張投影片，把附了中醫對照的那幾張融合進去，並改寫第六節的國考題說明（有的話）。」
3. 它寫到一半停下來，就回「繼續」。
4. 它回的內容整段複製（程式碼區塊與最後的備註），貼給做投影片的 session，或存成文字檔再說一聲。
5. 接下來由做投影片的 session 檢查（數字、頁碼、英文、上色、長度、照抄的行）、逐張對研究資料、套回來源檔、重產、算圖，交下一版。

不要請它直接改 PPTX。回覆套回來以前，這一講的來源檔先不動。

{KEEP}
標題也開放它重寫（只是病名或構造名的標題不動）；不要它動標題的話，套回時可以不套。
"""

FUSE_HOWTO = """# 給 Gemini 的融合包怎麼用（{LABEL}，{DATE}，草稿）

這份包請 Gemini 把中醫的對照（方劑與組成、證型、西醫病理）融合進原來的投影片：只改第五節列的幾張、每張最多加一條，不新增投影片，張數與上課時間不變；第六節是國考題下面那一行說明。

1. 開一個新對話，選最好的模型。
2. 把檔案上傳（或整份貼上），訊息寫一句：
   「請照這份檔案開頭的指示，把中醫的對照融合進第五節的每一張投影片，並改寫第六節的國考題說明。」
3. 它寫到一半停下來，就回「繼續」。
4. 它回的內容整段複製（程式碼區塊與最後的備註），貼給做投影片的 session，或存成文字檔再說一聲。
5. 接下來由做投影片的 session 檢查（數字、頁碼、英文、上色、長度）、逐張對研究資料、套回來源檔、重產、算圖，交下一版。

不要請它直接改 PPTX。回覆套回來以前，這一講的來源檔先不動。
"""


def fuse_allow(texts):
    """融合素材與建議句裡的數字與英文：套回時不算「多了原文沒有的」。"""
    t = " ".join(texts)
    return sorted(set(NUM.findall(t))), sorted({x.lower() for x in ENG.findall(t)})


def per_line():
    gp = _GP["gp"]
    return int((gp.G.SW - 2 * gp.G.M - 0.26) * 72.0 / gp.G.S["lead"])


def setup_gp(course):
    import gen_pptx
    gen_pptx.setup(course)
    _GP["gp"] = gen_pptx


def parse_only(s):
    out = set()
    for x in (s or "").split(","):
        x = x.strip()
        if not x:
            continue
        if "-" in x:
            a, b = x.split("-")
            out |= set(range(int(a), int(b) + 1))
        else:
            out.add(int(x))
    return out


def cmd_make(a):
    course = load_course(a.course)
    setup_gp(course)
    cfg, files, entries = load(course, a.deck)
    fuse = json.load(open(a.fuse, encoding="utf-8")) if getattr(a, "fuse", None) else None
    fuse_rw = bool(fuse) and bool(getattr(a, "rewrite", False))     # 重寫＋融合（教師 2026-11-22：「給gemini那個不只融合還要重寫喔」）
    fslides = {f["slug"]: f for f in (fuse or {}).get("slides", [])}
    for f in (fuse or {}).get("new_slides", []):          # 新加的融合張（已經寫進 rewrite.src 的檔）：整張請它寫
        fslides[f["slug"]] = dict(f, new=True, extra_chars=0, extra_lines=0)
    for f in (fuse or {}).get("inline", []):
        fslides.setdefault(f["slug"], f)
    only = parse_only(a.only)
    if fuse:
        miss = [x for x in fslides if x not in {e["slug"] for e in entries}]
        if miss:
            print(f"  [注意] 融合表裡有 {len(miss)} 張不在可以重寫的張裡（略過）：{miss}")
    if fuse and not fuse_rw:
        entries = [e for e in entries if e["slug"] in fslides]
    elif only:
        entries = [e for e in entries if e["num"] in only]
    if not entries:
        sys.exit("沒有可以重寫的張")
    os.makedirs(a.out, exist_ok=True)
    research = load_research(course)
    notes = load_notes(course, cfg)
    label = cfg.get("label") or f"{course.get('course_code', '')}{a.deck}"
    deck_name = course.deck(a.deck).get("name") or a.deck
    rules = (RULES.replace("{AUDIENCE}", str(course.get("audience") or "醫學相關科系的大學部學生"))
             .replace("{TEXTBOOK}", str(cfg.get("textbook") or "Robbins 病理學第 11 版")).replace("{PER_LINE}", str(per_line())))
    if fuse and not fuse_rw:
        task = (FUSE_TASK.replace("{AUDIENCE}", str(course.get("audience") or "醫學相關科系的大學部學生"))
                .replace("{TEXTBOOK}", str(cfg.get("textbook") or "Robbins 病理學第 11 版")))
        rules = task + rules[rules.index("## 二、"):]
    elif fuse_rw:
        rules = rules.replace("- 順序：先讀第四節（研究資料），再照第五節一張一張重寫，照第三節的格式輸出。",
                              FUSE_RW_ADD + "- 順序：先讀第四節（研究資料），再照第五節一張一張重寫，照第三節的格式輸出；有第六節的話，國考題的說明照第六節的格式輸出。", 1)
    if fuse:
        rules = rules.replace("1. **內容**：", "1. **內容**（這一次的例外：第五節每一張「要融合的中醫對照」可以加進那一張，只能用那裡列的內容，不要再加別的）：", 1)
        rules = rules.replace("2. **數字與頁碼**：", "2. **數字與頁碼**（「要融合的中醫對照」裡的數字可以用）：", 1)
        rules = rules.replace("不要新增原文沒有的專有名詞。", "不要新增原文沒有的專有名詞（「要融合的中醫對照」裡的方劑、藥材、證型與病名除外）。", 1)
        rules = rules.replace("11. **長度**：", "11. **長度**（第五節每一張標的上限已經含融合用的放寬）：", 1)
    for e in entries:
        if e["s"]["nested"]:
            print(f"  [注意] 第 {e['num']} 張有第二層條列：套回時會變成同一層")
    # 分包：一節一份；節太長就平分
    packs, cur = [], None
    for e in entries:
        if cur is None or cur["section"] != e["section"]:
            cur = {"section": e["section"], "items": []}
            packs.append(cur)
        cur["items"].append(e)
    split = []
    for p in packs:
        k = max(1, math.ceil(len(p["items"]) / max(1, a.per_pack)))
        size = math.ceil(len(p["items"]) / k)
        split += [{"section": p["section"], "items": p["items"][i:i + size]} for i in range(0, len(p["items"]), size)]
    if fuse and not fuse_rw:                   # 融合包張數少：整講一份，教師只要開一個對話
        split = [{"section": "全講", "items": entries}]
    mp = os.path.join(cfg["rv"], f"rewrite_manifest_{a.deck}.json")
    os.makedirs(cfg["rv"], exist_ok=True)
    manifest = json.load(open(mp, encoding="utf-8")) if (only and not fuse and os.path.exists(mp)) else {"deck": a.deck, "slides": {}}
    if fuse:
        manifest["mode"] = "rewrite_fuse" if fuse_rw else "fuse"
    qassign = {}                               # 國考題說明放在哪一份包（只融合：最後一份；重寫＋融合：張號落在哪一份就放哪一份）
    if fuse and fuse.get("quiz"):
        pool_q = parse_pool(course)
        nums_q = {b["id"].split("~")[0]: b["num"] for b in build_deck(course, a.deck)["slides"]}
        his = [max(e["num"] for e in p["items"]) for p in split]
        for q in fuse["quiz"]:
            qn = nums_q.get(q["slug"], q.get("num"))
            kk = next((i + 1 for i, h in enumerate(his) if qn is not None and qn <= h), len(split)) if fuse_rw else len(split)
            qassign.setdefault(kk, []).append((qn, q))
    all_titles = {}
    prev = None
    for e in load(course, a.deck)[2] if only else entries:        # 「標題和上一張相同」照整講的張序判斷
        all_titles[e["num"]] = (e["s"]["title"] == prev)
        prev = e["s"]["title"]
    keep_all = []
    for k, p in enumerate(split, 1):
        nums = [e["num"] for e in p["items"]]
        sec = re.sub(r"\([^)]*\)", "", p["section"]).split("｜")[-1].strip() or f"第{k}份"
        sec = re.sub(r"[\\/:*?\"<>|\s]+", "", sec)
        if fuse and not fuse_rw:
            title_line = f"# 請把中醫的對照融合進這幾張投影片：{deck_name}（{sec}，第 {min(nums)}–{max(nums)} 張）\n\n"
        elif fuse_rw:
            title_line = f"# 請用你自己的話重寫這份投影片，並把中醫的對照融合進去：{deck_name}（{sec}，第 {min(nums)}–{max(nums)} 張）\n\n"
        else:
            title_line = f"# 請用你自己的話重寫這份投影片：{deck_name}（{sec}，第 {min(nums)}–{max(nums)} 張）\n\n"
        out = [title_line, rules]
        segs = []
        for e in p["items"]:
            for fid in e["s"]["facts"]:
                m = re.match(r"([A-Za-z]+\d+)-", fid)
                if m and fid in research and m.group(1) not in segs and research[fid][2] != "literature":
                    segs.append(m.group(1))
        out.append("\n## 四、研究資料：這一段查核過的事實（教科書的內容，中文改寫，附頁碼）\n\n"
                   "讓你讀懂這一段在講什麼、每一句有多肯定；不是要搬上投影片的字。「種類」欄：number 數字、mechanism 機轉、morphology 形態、"
                   "clinical 臨床、key_concept 重點等。有「前後不一」說明的地方，是教科書自己有兩種說法。\n")
        for seg in sorted(segs):
            t = digest_text(cfg, seg, research)
            if t:
                out.append("\n" + t)
        out.append("\n## 五、要重寫的投影片\n\n每一張的第一行是張號、版型與字數上限；接著是圖的內容、「依據」（這一張引用的事實）與「沒有放上投影片的細節」，"
                   "這些只是讓你知道這一張在講什麼，不要抄回來、也不要搬上投影片。「原文：」底下的每一行才是要重寫的字（`T` 標題、`B` 條列、`R` 表格列）。\n")
        n_units = 0
        for e in p["items"]:
            s, pe = e["s"], e["pool"]
            rec = dict(record(cfg, e), b=os.path.relpath(e["src"], course["dir"]))
            fz = fslides.get(s["slug"]) if fuse else None
            if fz:
                rec["limit"] += int(fz.get("extra_chars", 30))
                if rec["lines"]:
                    rec["lines"] += int(fz.get("extra_lines", 1))
                texts = [m.get("fact", "") for m in fz.get("materials", [])] + [fz.get("suggest", "")]
                an, ae = fuse_allow(texts)
                rec["fuse"] = {"suggest": fz.get("suggest", ""), "materials": fz.get("materials", []), "allow_numbers": an, "allow_english": ae}
            manifest["slides"][str(e["num"])] = rec
            typ = TYPE_ZH.get(s["type"], s["type"])
            imgs = [clean_pic(im.get("desc")) for im in (pe.get("imgs") or [])]
            flow = pe.get("flow_text") or []
            if s["type"] == "left" and not imgs and not flow:
                typ = "只有字"
            head = f"\n### 第 {e['num']} 張〔{typ}｜正文原來 {rec['n']} 字，上限 {rec['limit']} 字"
            if rec["lines"]:
                head += f"，說明句現在共 {rec['lines']} 行、不要更多行"
            if all_titles.get(e["num"]):
                head += "；標題和上一張相同"
            out.append(head + "〕\n")
            if flow:
                out.append("圖：下面是流程圖（流程圖裡的字不用重寫）：" + " ".join(visible(x) for x in flow)[:400] + "\n")
            elif any(imgs):
                out.append("圖：" + "；".join(x for x in imgs if x)[:160] + "\n")
            units = [rec["title"]] + rec["bullets"] + [c for r in rec["rows"] for c in r]
            if any(PAIRED.search(visible(u)) for u in units if u not in rec["keep"]):
                out.append("注意：這一張帶頁碼的句子或格子，是把教科書前後不一的兩種說法並列（或註明出自哪一頁）：兩種說法與頁碼都要留著。\n")
            seen, fl = set(), []
            for fid in s["facts"]:
                if fid in research and fid not in seen:
                    seen.add(fid)
                    fl.append(f"  - {research[fid][0]}｜{research[fid][1]}（{fid}）\n")
            if fl:
                out.append("依據：\n" + "".join(fl))
            if notes.get(s["slug"]):
                out.append("沒有放上投影片的細節：\n" + "".join(f"  - {x}\n" for x in notes[s["slug"]]))
            if fz and fz.get("new"):
                out.append("這是新加的融合張（我們起草的，內容已查核）：請用你自己的話整張寫；表格的列數、欄數不變，每格不要比原來長。素材（只能用這裡的內容）：\n"
                           + "".join(f"  - {m.get('fact', '')}（{m.get('source', '')}）\n" for m in fz.get("materials", [])))
            elif fz:
                out.append("要融合的中醫對照（已查核；只能用這裡的內容）：\n"
                           + "".join(f"  - {m.get('fact', '')}（{m.get('source', '')}）\n" for m in fz.get("materials", []))
                           + (f"建議的一行（我們起草的，請用你自己的話寫，放在這一張最適合的位置）：{fz.get('suggest', '')}\n" if fz.get("suggest") else ""))
            out.append("原文：\n")
            out.append(f"T｜{show(rec['title'])}\n")
            for t in rec["bullets"]:
                out.append(("B（照抄）｜" if t in rec["keep"] else "B｜") + show(t) + "\n")
                n_units += 1
                if t in rec["keep"]:
                    keep_all.append((e["num"], t))
            for r, cs in enumerate(rec["rows"]):
                out.append(f"R{r}｜" + "｜".join(show(c, True) for c in cs) + "\n")
                n_units += len(cs)
        if qassign.get(k):
            out.append("\n## 六、國考題下面那一行說明\n\n國考題的題目與選項照考選部原文，不能改；題目下面有一行藍灰色的小字說明（我們寫的），"
                       "請把它改寫成「方劑（關鍵組成）→ 證型 → 西醫病理」的一句或兩句（最多約 70 個全形字，英文兩個字母算一個字），"
                       "只能用每一題列的素材。專有名詞寫「中文(English)」。輸出格式：一題一行，寫成 `Q 第 N 張｜新的說明`，放在同一個程式碼區塊的最後。\n")
            for qn, q in qassign[k]:
                cur_note = (pool_q.get(q["slug"]) or {}).get("quiz_note", "").replace(SOFT_BREAK, "")
                out.append(f"\n### 第 {qn} 張（國考題 {q.get('key', '')}）\n現在的說明：{cur_note}\n素材：\n"
                           + "".join(f"  - {m.get('fact', '')}（{m.get('source', '')}）\n" for m in q.get("materials", []))
                           + f"建議（我們起草的）：{q.get('note', '')}\n")
                manifest.setdefault("quiz", {})[str(qn)] = {"slug": q["slug"], "key": q.get("key", ""), "old": cur_note,
                                                             "allow": fuse_allow([m.get("fact", "") for m in q.get("materials", [])] + [q.get("note", "")])}
        text = "".join(out)
        kind = "重寫融合包" if fuse_rw else ("融合包" if fuse else "重寫包")
        fn = os.path.join(a.out, f"給Gemini_{kind}_{label}_{k}{sec}_第{min(nums)}-{max(nums)}張.md")
        open(fn, "w", encoding="utf-8", newline="\n").write(text)
        print(f"-> {fn}（{len(text)} 字；要重寫 {len(p['items'])} 張、{n_units} 個條列與格子）")
    manifest["hash"] = hashlib.sha1(json.dumps(manifest["slides"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]
    json.dump(manifest, open(mp, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print(f"-> {mp}（{len(manifest['slides'])} 張，版本 {manifest['hash']}；照抄的行 {len(keep_all)} 條）")
    for n, t in keep_all:
        print(f"   照抄 第 {n} 張｜{t[:60]}")
    today = datetime.date.today().strftime("%Y%m%d")
    keep_txt = ("照抄、不給它重寫的行（共 %d 行）：\n" % len(keep_all) + "".join(f"- 第 {n} 張：{visible(t)[:50]}\n" for n, t in keep_all)) if keep_all else "這一講沒有指定照抄的行。\n"
    if fuse and not fuse_rw:
        hp = os.path.join(a.out, f"0_怎麼用_融合包_{label}_{today}_草稿.md")
        open(hp, "w", encoding="utf-8", newline="\n").write(FUSE_HOWTO.replace("{LABEL}", label).replace("{DATE}", today))
    elif fuse_rw:
        hp = os.path.join(a.out, f"0_怎麼用_重寫融合包_{label}_{today}_草稿.md")
        open(hp, "w", encoding="utf-8", newline="\n").write(FUSE_RW_HOWTO.replace("{LABEL}", label).replace("{DATE}", today).replace("{KEEP}", keep_txt))
    else:
        hp = os.path.join(a.out, f"0_怎麼用_重寫包_{label}_{today}_草稿.md")
        open(hp, "w", encoding="utf-8", newline="\n").write(HOWTO.replace("{LABEL}", label).replace("{DATE}", today).replace("{KEEP}", keep_txt))
    print(f"-> {hp}")
    # 最後再掃一次：包裡不可以有教科書的英文原句（2026-11-24 發現摘要的「前後不一」整節是 Robbins 原句，之前的包都帶出去了）
    bad = []
    for fn in sorted(os.listdir(a.out)):
        if fn.endswith(".md"):
            for i, ln in enumerate(rd(os.path.join(a.out, fn)).split("\n"), 1):
                if re.search(r"([A-Za-z]+[ ,;]+){10,}", ln) or en_quote_line(ln):
                    bad.append((fn, i, ln))
    if bad:
        print(f"[RED] 包裡有 {len(bad)} 行像教科書的英文原句（不可以交出去；先找出來源、拿掉再重出）：")
        for fn, i, ln in bad[:8]:
            print(f"   {fn}:{i}｜{ln[:100]}")
    else:
        print("包裡沒有英文原句（連續 10 個以上英文字、或「」裡引英文的行）")


# ---------- 讀回覆 ----------
SL = re.compile(r"^[\s#>*\-]*第\s*(\d+)\s*張")
QLINE = re.compile(r"^[\s>*\-•`]*Q\s*第?\s*(\d+)\s*張?\s*[｜|]\s?(.*?)`*\s*$")
UNIT = re.compile(r"^[\s>*\-•]*(?:\d+[.、]\s*)?[`*]*(T|R\d+|B\d*)[`*]*\s*(?:[（(〔\[][^）)〕\]｜|]*[）)〕\]])?\s*[｜|]\s?(.*)$")
JOINED = re.compile(r"(?<=[^\s\-*•>#.\d`])[ \t]+(?=(?:T|R\d+|B\d*)(?:（[^）｜|]*）)?[｜|])")


def norm(t, cell=False):
    """對方寫回來的字整理成來源檔的寫法（上色記號、換行記號、半形括號、中文和括號之間不留空白）。"""
    t = re.sub(r"^`+|`+$", "", t.strip()).strip()
    t = t.replace("**", "")
    t = re.sub(r"\[\[\s*(橘|橙|藍|蓝|紅|红|青|灰)\s*[:：]\s*", lambda m: "[[" + {"橙": "橘", "蓝": "藍", "红": "紅"}.get(m.group(1), m.group(1)) + ":", t)
    t = re.sub(r"\s+\]\]", "]]", t)
    t = re.sub(r"<br\s*/?>", SOFT_BREAK, t, flags=re.I)
    t = re.sub(r"[ \t]*⏎[ \t]*", SOFT_BREAK, t)
    t = t.replace("（", "(").replace("）", ")")
    t = re.sub(r"(?<=[一-鿿])[ \t]+\(", "(", t)
    return t if cell else t.replace(SOFT_BREAK, "")


def parse_reply(text):
    """回傳 ({張號: {title, bullets, rows:{列號: [格]}}}, [備註行], [認不得的行])。同一張回兩次以後面的為準。"""
    lines = [x for ln in text.replace("\r", "").split("\n") for x in JOINED.sub("\n", ln).split("\n")]
    out, notes, odd = {}, [], []
    cur, in_notes = None, False

    def has_unit_after(i):
        for x in lines[i + 1:i + 6]:
            if x.strip() and not x.strip().startswith("```"):
                return bool(UNIT.match(x))
        return False
    for i, ln in enumerate(lines):
        st = ln.strip()
        if not st or st.startswith("```"):
            continue
        m = SL.match(ln)
        if m and has_unit_after(i):
            cur = {"n": int(m.group(1)), "title": None, "bullets": [], "rows": {}}
            out[cur["n"]] = cur
            in_notes = False
            continue
        if re.match(r"^[\s#>*\-]*備註", st):
            in_notes, cur = True, None
        if in_notes:
            notes.append(st)
            continue
        if QLINE.match(ln):                     # 融合包的國考題說明（Q 行），apply 另外讀
            continue
        u = UNIT.match(ln)
        if u and cur is not None:
            lab, body = u.group(1), u.group(2)
            if lab == "T":
                cur["title"] = norm(body)
            elif lab.startswith("B"):
                if norm(body):
                    cur["bullets"].append(norm(body))
            else:
                cur["rows"][int(lab[1:])] = [norm(c, True) for c in re.split(r"[｜|]", body.strip().strip("｜|"))]
        elif cur is not None:
            odd.append((cur["n"], st))
    return out, notes, odd


# ---------- 檢查 ----------
NUM = re.compile(r"\d+(?:[.,:]\d+)*%?")
ENG = re.compile(r"[A-Za-zα-ωΑ-Ωé][A-Za-z0-9α-ωΑ-Ωé&\-]*")
BAN = ["——", "值得注意", "讓我們", "總而言之", "綜上所述", "簡而言之", "換句話說", "換言之", "本質上", "至關重要", "關鍵在於", "不難發現",
       "深入探討", "堪稱", "旨在", "雙面刃", "同學", "各位", "你們", "考試", "必考", "常考", "！", "!", "【"]
BAN_RX = [(re.compile(r"扮演.{0,8}角色"), "扮演…角色"), (re.compile(r"不僅.{0,20}更"), "不僅…更")]
HEDGE = ["通常", "大多", "多半", "多數", "常常", "經常", "往往", "很少", "少數", "少見", "偶爾", "有時", "可能", "目前認為", "幾乎", "約", "主要",
         "一定", "都會", "所有", "容易", "極"]


def setdiff(rx, old, new, lower=False):
    """新舊兩邊的記號（數字或英文）比對：整個不見的、次數變少的、次數變多的、新出現的。"""
    f = (lambda x: x.lower()) if lower else (lambda x: x)
    o = [f(x) for u in old for x in rx.findall(visible(u))]
    n = [f(x) for u in new for x in rx.findall(visible(u))]
    gone = sorted(set(o) - set(n))
    fewer = sorted(x for x in set(o) & set(n) if o.count(x) > n.count(x))
    more = sorted(x for x in set(o) & set(n) if n.count(x) > o.count(x))
    added = sorted(set(n) - set(o))
    return gone, fewer, more, added


def restore_keep(rec, bullets):
    """照抄的行被改了就換回原句；不見了就放回原來的位置。回傳 (新條列, [說明])。"""
    notes, bullets = [], list(bullets)
    kept = [show(x) for x in rec["keep"]]
    for t in rec["keep"]:
        if any(b == show(t) or b == t for b in bullets):
            continue
        best, bi = 0.0, -1
        for i, b in enumerate(bullets):
            if b in kept or b in rec["keep"]:
                continue
            r = difflib.SequenceMatcher(None, visible(t), visible(b)).ratio()
            if r > best:
                best, bi = r, i
        if best >= 0.6:
            notes.append(f"照抄的行被改了，已換回原句（它寫：{visible(bullets[bi])[:40]}）")
            bullets[bi] = t
        else:
            pos = min(rec["bullets"].index(t), len(bullets))
            bullets.insert(pos, t)
            notes.append(f"照抄的行不見了，已放回第 {pos + 1} 條（看有沒有和別條重複：{visible(t)[:24]}）")
    return bullets, notes


def check_slide(rec, new, same_title_as_prev_old, prev_new_title):
    """回傳 dict：lvl（ok／看／不套）、hard（不能套的問題）、soft（要人決定的）、hint（對意思時的提示）、ask（請對方自己修的話）、sim（新舊正文的相似度）。
    new＝{title, bullets, rows:[[格]]}（已整理、已放回照抄的行）。"""
    hard, soft, hint, ask = [], [], [], []
    old_rows, new_rows = rec["rows"], new["rows"]
    if [len(r) for r in old_rows] != [len(r) for r in new_rows]:
        hard.append(f"表格的形狀不同（原來每列 {[len(r) for r in old_rows]} 格，回來 {[len(r) for r in new_rows]}）")
        ask.append(f"表格要和原文一樣：{len(old_rows)} 列（含表頭 R0），每列 {len(old_rows[0]) if old_rows else 0} 格" if old_rows else "這一張原文沒有表格，不要輸出 R 行")
    if rec["bullets"] and not new["bullets"]:
        hard.append("條列沒有回")
        ask.append("條列（B 行）沒有輸出，請補上")
    if not rec["bullets"] and new["bullets"]:
        hard.append("原來沒有條列，回來卻有")
        ask.append("這一張原文只有表格、沒有條列，不要加 B 行")
    old_u = [rec["title"]] + rec["bullets"] + [c for r in old_rows for c in r]
    new_u = [new["title"]] + new["bullets"] + [c for r in new_rows for c in r]
    if any(u.count("[[") != u.count("]]") or re.search(r"\[\[(?!(?:藍|紅|橘|青|灰):)", u) for u in new_u):
        hard.append("上色記號寫壞了")
        ask.append("上色記號的寫法是 [[橘:名詞]] 與 [[藍:重點]]，請照這個寫法")
    fz = rec.get("fuse") or {}
    gone, fewer, more, added = setdiff(NUM, old_u, new_u)
    added = [x for x in added if x not in set(fz.get("allow_numbers", []))]
    if gone:
        hard.append("數字不見了：" + "、".join(gone))
        ask.append("原文的數字不見了，請放回去（寫法照原文）：" + "、".join(gone))
    if added:
        hard.append("多了原文沒有的數字：" + "、".join(added))
        ask.append("多了原文沒有的數字，請拿掉或照原文的寫法：" + "、".join(added))
    if fewer:
        soft.append("數字出現的次數變少：" + "、".join(fewer))
    gone, fewer, more, added = setdiff(ENG, old_u, new_u, lower=True)
    added = [x for x in added if x.lower() not in set(fz.get("allow_english", []))]
    if gone:
        hard.append("英文不見了：" + "、".join(gone))
        ask.append("原文的英文不見了（專有名詞要帶括號裡的英文，原文的名詞不要漏）：" + "、".join(gone))
    if added:
        soft.append("多了原文沒有的英文：" + "、".join(added))
        ask.append("多了原文沒有的英文（不要新增專有名詞，括號裡的英文照原文）：" + "、".join(added))
    if more:
        hint.append("英文多寫了幾次（同一個名詞再出現）：" + "、".join(more))
    if fewer:
        hint.append("英文少寫了幾次：" + "、".join(fewer))
    exact = setdiff(ENG, old_u, new_u)
    if not gone and not added and (exact[0] or exact[3]):
        soft.append("英文的大小寫不同：" + "、".join(exact[0]) + " → " + "、".join(exact[3]))
        ask.append("英文的大小寫照原文：" + "、".join(exact[0]))
    marks = lambda us, c: [visible(m.group(2)) for u in us for m in MARK.finditer(u) if m.group(1) == c]
    for c in ("橘", "藍", "紅", "青", "灰"):
        om, nm = marks(old_u, c), marks(new_u, c)
        if not om and not nm:
            continue
        terms = [x for x in om if "(" in x]                       # 包起來的是名詞（帶英文）：要原樣留著
        lost = [x for x in terms if x not in nm]
        if lost:
            soft.append(f"{c}色的名詞不見或換了字：" + "、".join(lost))
            ask.append(f"原文用 [[{c}:…]] 標的名詞還要在、照樣標起來：" + "、".join(lost))
        if len(om) != len(nm):
            soft.append(f"{c}色 {len(om)} 處 → {len(nm)} 處")
            ask.append(f"[[{c}:…]] 這一張原文有 {len(om)} 處，重寫後也要 {len(om)} 處，標在同樣的名詞或重點上" if om else f"這一張原文沒有 [[{c}:…]]，不要加")
        elif [x for x in om if x not in terms] != [x for x in nm if x not in terms]:
            hint.append(f"{c}色標的字：" + "、".join(x for x in om if x not in terms) + " → " + "、".join(x for x in nm if x not in om))
    n_new = sum(len(visible(u)) for u in new_u[1:])
    if rec.get("lines"):
        nl = sum(lead_metrics(b, rec["type"])[0] for b in new["bullets"])
        if nl > rec["lines"]:
            soft.append(f"說明句 {rec['lines']} 行 → {nl} 行（圖會被擠小）；正文 {rec['n']} → {n_new} 字")
            ask.append(f"說明句現在排出來 {nl} 行，上限 {rec['lines']} 行（一行約 {per_line()} 個全形字，英文兩個字母算一個字）：請縮短")
    elif n_new > rec["limit"]:
        soft.append(f"正文 {n_new} 字，超過上限 {rec['limit']}（原來 {rec['n']}）")
        ask.append(f"正文現在 {n_new} 字，上限 {rec['limit']} 字：請縮短")
    if len(old_rows) == len(new_rows):
        long = [f"R{r}C{c + 1}(+{len(visible(y)) - len(visible(x))})" for r, (a, b) in enumerate(zip(old_rows, new_rows)) if len(a) == len(b)
                for c, (x, y) in enumerate(zip(a, b)) if len(visible(y)) - len(visible(x)) > max(3, round(0.15 * len(visible(x))))]
        if long:
            soft.append("格子變長：" + "、".join(long))
            ask.append("這幾格比原文長（R 列 C 欄，括號裡是多了幾個字），請縮短到不比原文長：" + "、".join(long))
    if len(new["bullets"]) > len(rec["bullets"]) + 1:
        soft.append(f"條列 {len(rec['bullets'])} 條 → {len(new['bullets'])} 條")
        ask.append(f"條列最多 {len(rec['bullets']) + 1} 條")
    if new["title"] != rec["title"]:
        hint.append("標題改了")
        d = len(visible(new["title"])) - len(visible(rec["title"]))
        if d > 0:
            soft.append(f"標題變長 {d} 個字")
            ask.append("標題不要比原來長")
    if same_title_as_prev_old and prev_new_title is not None and new["title"] != prev_new_title:
        soft.append("原來和上一張同一個標題，現在不一樣")
        ask.append("這一張和上一張原來是同一個標題：要改就兩張改成一樣的")
    old_all, new_all = "".join(visible(u) for u in old_u), "".join(visible(u) for u in new_u)
    keep_all = "".join(visible(t) for t in rec["keep"])
    bad = [w for w in BAN if new_all.count(w) > old_all.count(w) and w not in keep_all]
    bad += [name for rx, name in BAN_RX if rx.search(new_all) and not rx.search(old_all)]
    if bad:
        soft.append("多了「" + "」「".join(bad) + "」")
        ask.append("請不要用：「" + "」「".join(bad) + "」")
    hd = [f"{w} {old_all.count(w)}→{new_all.count(w)}" for w in HEDGE if old_all.count(w) != new_all.count(w)]
    if hd:
        hint.append("頻率與肯定的字（對依據看有沒有寫重或寫輕）：" + "、".join(hd))
    olds, keeps = [show(x) for x in rec["bullets"]], [show(x) for x in rec["keep"]]
    same = [b for b in new["bullets"] if show(b) in olds and show(b) not in keeps]
    if same:
        hint.append(f"照抄原句 {len(same)} 條")
    zh = lambda us: re.sub(r"[^一-鿿]", "", "".join(visible(u) for u in us))
    sim = difflib.SequenceMatcher(None, zh(old_u[1:]), zh(new_u[1:])).ratio()        # 只比中文字：英文、數字、括號本來就不能變
    return {"lvl": "不套" if hard else ("看" if soft else "ok"), "hard": hard, "soft": soft, "hint": hint, "ask": ask, "sim": sim, "copied": len(same)}


def parse_accept(s):
    out = parse_only(s.replace("soft", "")) if s else set()
    if s and "soft" in s:
        out.add("soft")
    return out


def cmd_apply(a):
    course = load_course(a.course)
    setup_gp(course)
    cfg, files, entries = load(course, a.deck)
    rv = cfg["rv"]
    man = json.load(open(os.path.join(rv, f"rewrite_manifest_{a.deck}.json"), encoding="utf-8"))["slides"]
    research = load_research(course)
    cur = {e["num"]: e for e in entries}
    reply, notes, odd = {}, [], []
    for fn in a.replies:
        r, n, o = parse_reply(rd(fn))
        reply.update(r)
        notes += n
        odd += o
    accept = parse_accept(a.accept)
    res, ops, applied = [], {}, []
    rec_p = os.path.join(rv, f"rewrite_{a.tag}_{a.deck}.json")
    prior = {r["n"]: r for r in json.load(open(rec_p, encoding="utf-8"))} if os.path.exists(rec_p) else {}      # 先前已經套進來源檔的張
    flat = lambda d: json.dumps([d["title"], d["bullets"], d["rows"]], ensure_ascii=False).replace(SOFT_BREAK, "")    # 不算手動換行
    prev_old_title = prev_new_title = None
    for num in sorted(int(x) for x in man):
        rec = man[str(num)]
        base = {"title": rec["title"], "bullets": rec["bullets"], "rows": rec["rows"]}
        same_prev = rec["title"] == prev_old_title
        prev_old_title = rec["title"]
        e = cur.get(num)
        if e is None or e["slug"] != rec["slug"]:
            res.append({"n": num, "rec": rec, "s": None, "lvl": "不套", "hard": ["重寫包做好以後張序變了（這個張號現在不是這一張），重出重寫包"], "soft": [], "hint": [],
                        "ask": [], "sim": None, "copied": 0, "new": None, "take": False})
            continue
        s = e["s"]
        now = {"title": s["title"], "bullets": [t for _, t in s["bullets"]], "rows": [cs for _, cs in s["rows"]]}
        if num not in reply:
            res.append({"n": num, "rec": rec, "s": s, "lvl": "已套" if num in prior else "沒有回", "hard": [], "soft": [], "hint": [], "ask": [], "sim": None,
                        "copied": 0, "new": None, "take": False})
            prev_new_title = now["title"]
            continue
        rp = reply[num]
        bullets, kn = restore_keep(rec, rp["bullets"])
        back = {show(t): t for t in rec["bullets"]}            # 和原句（去掉手動換行）一樣的條列用原來的寫法，手動換行才留得住
        bullets = [back.get(b, b) for b in bullets]
        rows = [rp["rows"].get(i, []) for i in range(max(len(rec["rows"]), (max(rp["rows"]) + 1) if rp["rows"] else 0))]
        title = rec["title"] if (a.keep_titles or not rp["title"] or rp["title"] == show(rec["title"])) else rp["title"]
        new = {"title": title, "bullets": bullets, "rows": rows}
        c = check_slide(rec, new, same_prev, prev_new_title)
        c["soft"] = kn + c["soft"]
        if kn and c["lvl"] == "ok":
            c["lvl"] = "看"
        prev_new_title = new["title"]
        state = ""
        if now != base:
            if flat(now) == flat(new):
                state = "已套"
            elif num in prior and flat(prior[num]["new"]) == flat(new):
                state = "已套後手改"                 # 套的是同一版回覆，之後主 session 手動調過（換行、事實用字）
            elif num in prior:
                c["hint"].append("這一張先前套過另一版回覆，這次是新的版本：套用會蓋掉先前那一版與之後的手改")
            else:
                c["lvl"] = "不套"
                c["hard"].append("重寫包做好以後，來源檔的這一張改過了（重出重寫包，或先把來源檔改回去）")
        take = (not state) and (c["lvl"] == "ok" or (c["lvl"] == "看" and ("soft" in accept or num in accept)))
        r = dict(c, n=num, rec=rec, s=s, new=new, take=take)
        if state:
            r["lvl"] = state
        res.append(r)
        if take and new != now:
            mine, ok = [], True
            if new["bullets"] != now["bullets"]:
                bl = [i for i, _ in s["bullets"]]
                if bl == list(range(bl[0], bl[-1] + 1)):
                    mine.append((bl[0], bl[-1] + 1, ["- " + b for b in new["bullets"]]))
                elif len(bl) == len(new["bullets"]):
                    mine += [(i, i + 1, ["- " + b]) for i, b in zip(bl, new["bullets"])]
                else:
                    ok = False
            if not ok:
                r.update(take=False, lvl="不套")
                r["hard"].append("這一張的條列在來源檔裡不連續，條數不能變")
                continue
            if new["title"] != now["title"]:
                mine.append((s["tline"], s["tline"] + 1, [f"## 投影片 {rec['slug']}｜{new['title']}"]))
            for (i, old_cells), new_cells in zip(s["rows"], new["rows"]):
                if new_cells != old_cells:
                    mine.append((i, i + 1, ["| " + " | ".join(new_cells) + " |"]))
            ops.setdefault(e["src"], []).extend(mine)
            applied.append({"n": num, "b": os.path.relpath(e["src"], course["dir"]), "slug": rec["slug"], "old": base, "new": new})
    # ---------- 對照表 ----------
    tag = a.tag
    rep = os.path.join(rv, f"rewrite_{tag}_{a.deck}_對照表.md")
    cnt = {}
    for r in res:
        cnt[r["lvl"]] = cnt.get(r["lvl"], 0) + 1
    sims = [r["sim"] for r in res if r["sim"] is not None]
    man_mode = json.load(open(os.path.join(rv, f"rewrite_manifest_{a.deck}.json"), encoding="utf-8")).get("mode")
    fuse_mode = man_mode == "fuse"
    barely = [] if fuse_mode else [r["n"] for r in res if r["sim"] is not None and (r["sim"] >= 0.9 or r["copied"]) and r["lvl"] not in ("已套", "已套後手改")]
    with open(rep, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# 重寫對照表（{tag}，{a.deck}）\n\n"
                "> 檢查：ok＝機械檢查沒有問題；看＝要人決定（上色、長度、多了英文、照抄的行）；不套＝數字或英文不見、多了數字、表格形狀不同。\n"
                "> 機械檢查查不到意思有沒有跑掉：每一張都要拿「改成」對「依據」看頻率詞、時態、因果、誰對誰，對完才套。"
                "相似度＝新舊正文的中文字有多像（1＝沒有改；名詞不能換，所以表格張天生偏高）。\n\n"
                f"合計：{'、'.join(f'{k} {v} 張' for k, v in cnt.items())}"
                + (f"；相似度中位數 {sorted(sims)[len(sims) // 2]:.2f}；幾乎沒有改（相似度 ≥0.9 或有照抄的句子）的 {len(barely)} 張：{barely}" if sims else "") + "\n")
        for r in res:
            rec, s = r["rec"], r["s"]
            f.write(f"\n## 第 {r['n']} 張 {rec['slug']}〔{rec['type']}〕檢查：{r['lvl']}"
                    + (f"｜相似度 {r['sim']:.2f}" if r["sim"] is not None else "") + (f"｜套用：{'是' if r['take'] else '否'}" if r["new"] else "") + "\n")
            for name, xs in (("不套", r["hard"]), ("要看", r["soft"]), ("提示", r["hint"])):
                for x in xs:
                    f.write(f"- 〔{name}〕{x}\n")
            if not r["new"]:
                continue
            seen = set()
            fl = [f"  - {research[x][0]}｜{research[x][1]}（{x}）\n" for x in s["facts"] if x in research and not (x in seen or seen.add(x))]
            if fl:
                f.write("\n依據：\n" + "".join(fl))
            for name, d in (("原來", {"title": rec["title"], "bullets": rec["bullets"], "rows": rec["rows"]}), ("改成", r["new"])):
                f.write(f"\n{name}：\n\n    T｜{d['title']}\n" + "".join(f"    B｜{b}\n" for b in d["bullets"])
                        + "".join(f"    R{i}｜" + "｜".join(cs) + "\n" for i, cs in enumerate(d["rows"])))
        if notes:
            f.write("\n## 它的備註\n\n" + "\n".join(notes) + "\n")
        if odd:
            f.write("\n## 回覆裡認不得的行（可能是斷行的句子，對一下有沒有漏字）\n\n" + "".join(f"- 第 {n} 張｜{x}\n" for n, x in odd))
    print(f"回覆 {len(reply)} 張（重寫包 {len(man)} 張）：" + "、".join(f"{k} {v}" for k, v in cnt.items()) + f"；對照表 → {rep}")
    if sims:
        print(f"相似度中位數 {sorted(sims)[len(sims) // 2]:.2f}；幾乎沒有改的 {len(barely)} 張")
    if odd:
        print(f"  [注意] 認不得的行 {len(odd)} 行（見對照表最後）")
    extra = sorted(set(reply) - {int(x) for x in man})
    if extra:
        print(f"  [注意] 回覆裡有重寫包沒有的張號：{extra}")
    # ---------- 退回包：請對方自己修（超長、漏數字、漏英文、上色、沒有回的張、幾乎沒有改的張），不由我們改句子 ----------
    got = {r["rec"].get("b") for r in res if r["new"]}
    lo, hi = (min(reply), max(reply)) if reply else (0, -1)
    missing = [r["n"] for r in res if r["lvl"] == "沒有回" and r["rec"].get("b") in got and lo <= r["n"] <= hi]
    fix = [r for r in res if r["ask"] and r["lvl"] in ("看", "不套")]
    lazy = [n for n in barely if n not in {r["n"] for r in fix}]
    bk = os.path.join(rv, f"rewrite_{tag}_{a.deck}_退回給Gemini.md")
    if fix or missing or lazy:
        with open(bk, "w", encoding="utf-8", newline="\n") as f:
            f.write("下面幾張還有地方要修。規則和前面一樣（用你自己的話寫）；請只輸出這裡列到的張，照同樣的格式放在程式碼區塊裡，其他張不用再輸出。\n")
            if fix:
                f.write("\n## 要修的張\n")
                for r in fix:
                    f.write(f"\n### 第 {r['n']} 張\n" + "".join(f"- {x}\n" for x in r["ask"]))
            if missing:
                f.write("\n## 上一次沒有輸出的張，請補上\n\n第 " + "、".join(str(n) for n in missing) + " 張\n")
            if lazy:
                f.write("\n## 和原文幾乎一樣的張\n\n整張都是名詞、沒有句子可以重寫的就不用動；否則請用你自己的話重寫：第 " + "、".join(str(n) for n in lazy) + " 張\n")
        print(f"退回包（要修 {len(fix)} 張、沒有回 {len(missing)} 張、幾乎沒有改 {len(lazy)} 張）→ {bk}")
    elif os.path.exists(bk):
        os.remove(bk)
    if man_mode in ("fuse", "rewrite_fuse"):
        mq = json.load(open(os.path.join(rv, f"rewrite_manifest_{a.deck}.json"), encoding="utf-8")).get("quiz", {})
        qs = {}
        for fn in a.replies:
            for ln in rd(fn).replace("\r", "").split("\n"):
                m = QLINE.match(ln)
                if m:
                    qs[m.group(1)] = norm(m.group(2))
        qout = []
        for n, q in sorted(mq.items(), key=lambda x: int(x[0])):
            new_q = qs.get(n)
            prob = []
            if new_q is None:
                prob.append("沒有回")
            else:
                an, ae = q.get("allow", [[], []])
                gone, _, _, added = setdiff(NUM, [q["old"]], [new_q])
                added = [x for x in added if x not in set(an)]
                if added:
                    prob.append("多了素材沒有的數字：" + "、".join(added))
                gone, _, _, added = setdiff(ENG, [q["old"]], [new_q], lower=True)
                added = [x for x in added if x.lower() not in set(ae)]
                if added:
                    prob.append("多了素材沒有的英文：" + "、".join(added))
                if len(visible(new_q)) > 80:
                    prob.append(f"太長（{len(visible(new_q))} 字）")
            qout.append({"num": int(n), "slug": q["slug"], "key": q["key"], "old": q["old"], "new": new_q, "problems": prob})
        qp = os.path.join(rv, f"rewrite_{a.tag}_{a.deck}_quiz.json")
        json.dump(qout, open(qp, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
        with open(rep, "a", encoding="utf-8", newline="\n") as f:
            f.write("\n## 國考題下面那一行說明（Q 行；不寫進來源檔，由課程自己的程式套）\n")
            for q in qout:
                f.write(f"\n### 第 {q['num']} 張（{q['key']}）" + (f"〔{'；'.join(q['problems'])}〕" if q["problems"] else "") + f"\n- 原來：{q['old']}\n- 改成：{q['new']}\n")
        print(f"國考題說明 {sum(1 for q in qout if q['new'])}/{len(qout)} 題 → {qp}")
    if not a.write:
        print("（只檢查，沒有寫檔；逐張對過意思以後加 --write 才套用）")
        return
    for path, o in ops.items():
        lines = files[path]
        for i, j, rep_lines in sorted(o, key=lambda x: -x[0]):
            lines[i:j] = rep_lines
        open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    prior.update({r["n"]: r for r in applied})
    json.dump([prior[k] for k in sorted(prior)], open(rec_p, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print(f"套用 {len(applied)} 張 → 來源檔；紀錄 {rec_p}。接著重產（來源檔是批檔就先重組素材池）、style_check 補英文、算圖、逐張看。")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make", help="出重寫包")
    m.add_argument("--course", required=True)
    m.add_argument("--deck", required=True)
    m.add_argument("--out", required=True, help="輸出資料夾（雲端同步資料夾與 repo 以外；做好再一次複製過去）")
    m.add_argument("--only", default="", help="只包這幾張，例 12,13,20-25")
    m.add_argument("--per-pack", type=int, default=45, help="一份包最多幾張（一節超過就平分）")
    m.add_argument("--fuse", help="融合包：JSON（slides：[{slug, materials:[{fact, source}], suggest, extra_chars, extra_lines}]、quiz：[{slug, key, note, materials}]）；"
                                  "只包表上的張，請 Gemini 把素材融合進原來的投影片（不新增張、不整張重寫），上限照 extra_chars 放寬")
    m.add_argument("--rewrite", action="store_true", help="和 --fuse 一起用：整講照一般重寫包分節、每張整張重寫，附了素材的張同時融合，"
                                                         "國考題說明放在張號所在的那一份（教師 2026-11-22：「給gemini那個不只融合還要重寫喔」）")
    p = sub.add_parser("apply", help="檢查回覆、寫對照表；--write 才套回來源檔")
    p.add_argument("--course", required=True)
    p.add_argument("--deck", required=True)
    p.add_argument("replies", nargs="+")
    p.add_argument("--write", action="store_true")
    p.add_argument("--accept", default="", help="soft（全部「看」的張）或張號清單，例 9,13,20-25")
    p.add_argument("--keep-titles", action="store_true", help="不套標題的改動")
    p.add_argument("--tag", default="gemini1")
    a = ap.parse_args()
    (cmd_make if a.cmd == "make" else cmd_apply)(a)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

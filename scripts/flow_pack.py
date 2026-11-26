#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""流程圖改善包：把一講的流程圖交給另一個模型（教師指定 Gemini）重新設計成比較好懂的樣子，回來以後檢查。

教師 2026-11-25 晚（看了腎臟一的毛胚）：「我覺得流程圖還是很難理解 這次給gemini的時候除了寫作包以外 另外給一個流程圖改善包」。
kit 的重寫包（scripts/rewrite_pack.py）只送標題、條列與表格；流程圖的字在流程圖規格（flows.json）裡，沒有送過。
這一支把每一張流程圖現在的畫法（排法、說明句、每一格與箭頭上的字）、這一張引用的事實（事實帳的中文改寫，附頁碼）、
移下投影片的細節、前後張的標題，連同版面放得下的限制寫成一份 .md，請對方：先說原來哪裡不好懂，再重新設計
（可以改每一格的字、箭頭上的說明、格數與切法、排法、拆成兩頁，或建議改成表格或條列），照固定的格式回覆。
不放：教科書的英文原句、圖檔、PPTX、PDF、學生資料、任何私人語料（和重寫包同一條底線；make 最後會掃一次）。
中醫的辨證路徑（flow kind: stages）不送：那是教師自己定的格式。

用法（python 用有 PyYAML 的那一個；加 --course <課程> 就從哪裡跑都可以，沒加要在課程資料夾裡跑）：
  python flow_pack.py make <deck> --course <課程> --out <雲端同步資料夾與 repo 以外的資料夾> [--label B2腎臟一]
      寫 給Gemini_流程圖改善包_<label>.md 與 0_怎麼用_流程圖改善包_<label>_<日期>_草稿.md；
      每張圖送出去時的規格記在 _archive/revoice/flowpack_manifest_<deck>.json。
  python flow_pack.py check <deck> --course <課程> <回覆檔 …>
      讀回覆（格式見包的第三節），逐張列出：排法、格數、每行字數有沒有超過、有沒有編號、專有名詞的英文有沒有少，
      寫對照表 _archive/revoice/flowpack_<deck>_對照表.md（原來／改成／判斷與理由）。不改任何來源檔：
      套回由主 session 逐張對事實帳以後改 _archive/written/flows_<批>.json（意思有沒有跑掉程式查不到）。
流程圖改善包交出去以後、回覆處理完以前，不要改那一講流程圖的規格（和重寫包同一個規則）。
2026-11-26 從 uro-kidney-b2 收進 kit（和 rewrite_pack.py 放一起）；排法的清單加了 cycle、diamond、sieve（docs/設計系統.md 第 4 節）。
"""
import datetime
import hashlib
import json
import os
import re
import sys

import yaml

def _course_dir():
    """課程資料夾：--course <課程>（從 common.find_materials() 找）；沒給就用目前的資料夾（要有 course.yaml）。"""
    a = sys.argv
    if "--course" in a:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import common
        c = a[a.index("--course") + 1]
        return c if os.path.isdir(c) else os.path.join(common.find_materials(), "courses", c)
    return os.getcwd()


CD = os.path.normpath(_course_dir())
SB = "⏎"
STYLE_ZH = {"timeline": "時間軸（一條直線，由上往下，每一格是線上的一個點）", "stack": "直式卡片（由上往下的幾張卡片）",
            "spine": "中軸式（置中的幾個框，由上往下）", "steps": "橫向兩格（左邊一格 → 右邊一格）",
            "merge": "匯流（左邊並排的幾格 → 右邊一格共同的結果）", "fork": "分流（左邊一格 → 右邊並排的幾個結果）",
            "cycle": "循環回饋（直式卡片，左邊一條從最後一格接回第一格的回頭箭頭）",
            "diamond": "菱形分合（上面一格 → 左右兩支 → 下面一格）", "sieve": "雙關卡（來源 → 兩道關卡 → 結果，被擋住的東西回到來源）",
            "axis": "雙軸式", None: "直式卡片"}
EN_RUN = re.compile(r"([A-Za-z]+[ ,;]+){10,}")
HEAD = re.compile(r"^## 投影片 ([A-Za-z0-9_\-]+)｜(.*)$")
MARK = re.compile(r"\[\[(藍|紅|橘|青|灰)[:：](.+?)\]\]")


def rd(p):
    return open(p, encoding="utf-8").read()


def width(t):
    """全形字算 1、半形字算 0.5（和投影片的量法相同的近似）。"""
    return sum(1 if ord(ch) > 0x2E7F else 0.5 for ch in t)


def load(deck):
    cfg = yaml.safe_load(rd(os.path.join(CD, "course.yaml")))
    pool = rd(os.path.join(CD, cfg["paths"]["pool"]))
    order = [ln[2:].strip() for ln in rd(os.path.join(CD, cfg["paths"]["decks_dir"], deck + ".md")).split("\n") if ln.startswith("- ")]
    sections, cur = {}, None
    for ln in rd(os.path.join(CD, cfg["paths"]["decks_dir"], deck + ".md")).split("\n"):
        if ln.startswith("## "):
            cur = ln[3:].replace(SB, "").strip()
        elif ln.startswith("- "):
            sections[ln[2:].strip()] = cur
    slides, s = {}, None
    for ln in pool.split("\n"):
        h = HEAD.match(ln)
        if h:
            s = {"slug": h.group(1), "title": h.group(2).strip().replace(SB, ""), "type": "", "flow": None, "facts": [], "bullets": [], "quiz": False}
            slides[s["slug"]] = s
            continue
        if s is None:
            continue
        m = re.match(r"<!--\s*type:\s*(\w+)", ln)
        if m:
            s["type"] = m.group(1)
        m = re.match(r"<!--\s*flow:\s*\S+#(\S+)", ln)
        if m:
            s["flow"] = m.group(1)
        m = re.match(r"<!--\s*facts:\s*(.*?)\s*-->", ln)
        if m:
            s["facts"] = m.group(1).split()
        if ln.startswith("<!-- quiz:"):
            s["quiz"] = True
        if ln.startswith("- "):
            s["bullets"].append(MARK.sub(r"\2", ln[2:]).replace(SB, ""))
    flows = json.loads(rd(os.path.join(CD, cfg["paths"]["pool"].replace("-pool.md", "-flows.json"))))["figures"]
    facts = {f["id"]: f for f in json.loads(rd(os.path.join(CD, cfg["paths"]["facts_R"])))["facts"]}
    notes, cur = {}, None
    npath = os.path.join(CD, cfg["paths"]["pool"].replace("-pool.md", "-notes.md"))
    if os.path.exists(npath):
        for ln in rd(npath).split("\n"):
            m = re.match(r"^### 投影片 ([A-Za-z0-9_\-]+)｜", ln)
            if m:
                cur = m.group(1)
                notes[cur] = []
            elif cur and ln.strip():
                notes[cur].append(re.sub(r"^【講義補充】", "", ln.strip()))
    lay = json.loads(rd(os.path.join(CD, cfg["paths"]["out_dir"], cfg["decks"][deck]["filename"] + "_layout.json")))["slides"]
    num = {k: v["num"] for k, v in lay.items()}
    return cfg, order, sections, slides, flows, facts, notes, num


def slug_to_num(text, num, slides):
    """講義補充裡提到別張時寫的是代號（kid1-glom-presentations）：換成「第 N 張〈標題〉」，對方才看得懂。"""
    def f(m):
        s_ = m.group(0)
        return f"第 {num[s_]} 張〈{slides[s_]['title']}〉" if s_ in num and s_ in slides else s_
    return re.sub(r"[a-z0-9]+(?:-[a-z0-9]+)+", f, text)


def chart_text(fig):
    """現在的流程圖 → 文字（和回覆的格式相同：格｜、箭｜）。merge／fork 並排的格用「／」分開。"""
    st = fig.get("style")
    items = fig.get("items", [])
    nodes = [it["node"] for it in items if "node" in it]
    out = []
    ni = 0
    for it in items:
        if "node" in it:
            lines = [str(x).replace(SB, "") for x in it["node"]]
            side = (st == "merge" and ni == 0) or (st == "fork" and ni == len(nodes) - 1)
            out.append("格｜" + (" ／ " if side else " " + SB + " ").join(lines))
            ni += 1
        else:
            ls = []
            for ln in it.get("arrow", []):
                if isinstance(ln, dict):
                    ln = ln.get("inhibit", [])
                if isinstance(ln, str):
                    ln = [ln]
                ls.append("".join(r if isinstance(r, str) else r.get("t", "") for r in ln).replace(SB, ""))
            out.append("箭｜" + (" ".join(x for x in ls if x) or "無"))
    return out


PROMPT = """# 請重新設計這份投影片的流程圖：{NAME}

## 一、請你做的事

- 這是一位病理科教師大堂課投影片的草稿。對象是{AUD}。
- 內容以 Robbins 病理學第 11 版為準：事實、數字、頁碼都逐條查核過。
- 這一講有 {N} 張流程圖（講致病機轉、病程、診斷與處置的順序）。現在的流程圖是另一個 AI 畫的，教師看了說：**「流程圖還是很難理解」**。
- 請你把每一張流程圖**重新設計成學生第一次看就看得懂的樣子**。你可以：
  - 改寫每一格的字與箭頭上的說明（用你自己的話，寫成看得懂的短句，不必保留原來的寫法）；
  - 重新決定要分成幾格、每一格放哪一件事、先後怎麼切；
  - 換一種排法（第二節列的九種），**照這件事的形狀挑**：單線的先後用直的排法；兩個原因造成一個結果、一個原因造成兩個結果、一個原因經兩條路造成同一個結果、會回頭的惡性循環、兩道關卡擋住同一個東西，各有對應的排法。該並列的不要畫成一直線，該回頭的要有回頭的箭頭；
  - 一頁放不下或太擠時拆成兩頁；
  - 如果這件事根本不適合畫成流程圖（不是一個先後或因果的順序），請直說，並改成表格或條列。
- 每一張請先用一兩句話說**原來的圖哪裡不好懂**（例：一格塞了兩件事、箭頭上的字看不出為什麼會到下一步、前後兩格之間跳了一步、名詞沒有交代、順序和學生想的相反），再給你的設計。
- 建議的做法：先讀「這一張的事實」弄懂這件事的來龍去脈，想好要讓學生記住的是哪一條因果，再從頭畫；不要一格對一格地改字。
- 全部做完以後，請另外寫一段「總評」：這份講義的流程圖共同的毛病是什麼、你建議以後照什麼原則畫。

## 二、不能變的事

1. **事實**：每一步的先後、因果、誰造成誰，以每一張附的「這一張的事實」為準。不要加事實裡沒有的病名、機轉或數字；現在的圖上有的重點（尤其是有英文的名詞與數字）不要漏掉。你可以把圖上原來省略的中間一步補出來，但那一步要在「這一張的事實」或「移下投影片的細節」裡找得到。
2. **肯定的程度**：事實寫「通常、大多、常、很少、有可能、目前認為」的地方照樣保留，不要寫成「一定、都會、不會」。
3. **數字**：現在的圖與說明句上的數字照留、寫法照原樣；不要加原來沒有的數字。
4. **專有名詞**：一律寫成「中文(English)」，括號用半形；中文名稱與括號裡的英文照現在圖上的寫法，不換成別的譯名。「這一張的事實」裡的譯名和現在圖上不同時（例：事實寫腎小球、圖上寫腎絲球），以現在圖上的寫法為準。同一個名詞在同一張出現幾次，每一次都帶著英文。圖上沒有、你從事實補進來的名詞，照事實括號裡的英文寫。
5. **不要編號**：格子與說明上不要放 1、2、3、①②③、「第一步」「步驟一」。教師說過：「無論你用哪一種 都不要號碼」。
6. **不寫的東西**：不用比喻與擬人、不寫中醫、不稱呼學生、不提考試、不用驚嘆號與表情符號。
7. **版面放得下才畫得出來**（字級固定 24–30pt，不能縮字；全形字算 1 個字，英文兩個字母算 1 個字）：
   - 流程圖上方的**說明句**最多一行、30 個字以內（四格的圖上方不要放第二行）。
   - **一格**最多兩行，每行最多 22 個字（「橫向兩格」「匯流」「分流」的格子只有半寬：每行最多 12 個字、每格最多三行）。
   - **箭頭上的說明**是一個小膠囊：一行、12 個字以內（中軸式可以兩行）；沒有要說的就寫「無」。
   - 可以用的排法與每頁的格數：

     | 排法（回覆時寫英文代號） | 樣子 | 一頁最多 |
     |---|---|---|
     | timeline | 時間軸：由上往下，一條直線上的幾個點 | 4 格（每格一行），或 3 格（每格兩行） |
     | stack | 直式卡片：由上往下的幾張卡片 | 3 格（每格一到兩行） |
     | spine | 中軸式：置中的幾個框，由上往下 | 3 格（每格一行） |
     | steps | 橫向兩格：左一格 → 右一格 | 剛好 2 格 |
     | merge | 匯流：左邊並排的兩三格 → 右邊一格共同的結果 | 左邊 2–3 格、右邊 1 格 |
     | fork | 分流：左邊一格 → 右邊並排的兩三個結果 | 左邊 1 格、右邊 2–3 格 |
     | diamond | 菱形分合：上面一格 → 左右兩支 → 下面一格（一個原因經兩條路造成或加重同一個結果） | 上 1 格、中間 2 格（半寬，每格最多三行）、下 1 格 |
     | cycle | 循環回饋：直式卡片，左邊一條從最後一格接回第一格的回頭箭頭（惡性循環） | 3 格（每格一到兩行）＋回頭箭頭上的字（兩行、每行 5 個字以內） |
     | sieve | 雙關卡：來源 → 兩道並列的關卡 → 結果；被擋住的東西回到來源 | 來源 1 塊、關卡 2 格（每格四行、每行 8 個字以內）、結果 1 格 |

   - 最後一格會畫成深色的實心格，代表這個流程的終點：請讓最後一格是學生要記住的結果。
   - **超過一頁的格數就拆成兩頁**：第二頁的第一格要重複第一頁的最後一格（教師：「當你拆兩張的時候項目應該要有重疊 不然學生沒辦法記得之前發生什麼事」）。同一個流程的兩頁用同一種排法。
   - 相鄰兩張不同的流程圖最好不要用同一種排法（教師：「各種方式交替使用」）。
   - 箭頭上的說明只寫「為什麼會走到下一步」，不要重複格子裡的狀態；最後一格要直接呼應這一張的標題。
   - 九種排法都不合適時，可以在「版面建議」那一行描述你想要的畫法，我們再看做不做得出來；但還是請先用九種裡最接近的一種給一個版本。

## 三、輸出格式

照第四節的順序，**每一張都要輸出**，一張一段。例：

```
### 第 26 張
判斷｜（原來的圖哪裡不好懂，一兩句）
排法｜timeline
說明句｜（流程圖上方那一句；不要就寫「無」）
格｜（第一格的字；一格兩行時用「⏎」分開兩行）
箭｜（這一格到下一格的說明；沒有就寫「無」）
格｜（下一格）
箭｜（…）
格｜（最後一格：學生要記住的結果）
理由｜（改了什麼、為什麼這樣比較好懂，一兩句，給教師看）
```

- 一行一個單位，用全形直線「｜」分隔；「格」和「箭」照由上往下（或由左到右）的順序交替寫，第一行與最後一行都是「格」。
- merge 與 fork 並排的幾格寫在同一行，用「／」分開。例（匯流）：`格｜原因甲 ／ 原因乙`、`箭｜…`、`格｜共同的結果`。
- diamond：`格｜上面那一格`、`箭｜左支的說明 ／ 右支的說明`、`格｜左格 ／ 右格`、`格｜下面的結果`。
- cycle：和 stack 一樣寫，最後多一行 `回頭箭｜回頭箭頭上的字`（兩行用「⏎」分開）。
- sieve：先寫 `來源｜來源那一塊的字`，再 `格｜第一道關卡 ／ 第二道關卡`、`箭｜被擋回的東西`、`格｜結果`。
- 拆成兩頁時，寫完第一頁的格與箭以後，另起一行寫 `--- 第二頁`，再從 `排法｜`、`說明句｜` 寫起；第二頁的第一格重複第一頁的最後一格。「判斷」與「理由」一張只寫一次。
- 建議改成表格時：`排法｜改成表格`，接著用 `R0｜表頭｜表頭`、`R1｜格｜格` 寫（最多 4 列、每格兩行以內）。建議改成條列時：`排法｜改成條列`，接著用 `B｜一條條列` 寫（最多 4 條）。
- 想提九種以外的畫法時多寫一行 `版面建議｜…`。
- 請把整份輸出放在程式碼區塊（```）裡，複製的時候才不會跑掉換行。
- 全部輸出完以後，在程式碼區塊外面寫「總評」（共同的毛病與建議的原則），以及「備註」：你發現現在的圖和「這一張的事實」不合、或看起來有錯的地方（張號加一句話）；沒有就寫「無」。
- 一次寫不完的話，請停在某一張的結尾；我說「繼續」，你再從下一張接著寫。

## 四、每一張流程圖

每一張有：現在的畫法（排法、說明句、格與箭頭上的字）、它在講義裡的位置（前後張的標題）、這一張的事實（教科書的內容，中文改寫，附頁碼；不是要搬上投影片的字）、移下投影片的細節（投影片上放不下、留在講義補充的）。
「這一張的事實」每一條：編號｜頁｜內容；英文術語在中文後的括號裡。

"""

HOWTO = """# 給 Gemini 的流程圖改善包怎麼用（{LABEL}，{DATE}，草稿）

教師 {DATE2}：「我覺得流程圖還是很難理解 這次給gemini的時候除了寫作包以外 另外給一個流程圖改善包」。

這一份包請 Gemini 把這一講的 {N} 張流程圖**重新設計**：先說每一張原來哪裡不好懂，再給新的畫法（每一格的字、箭頭上的說明、排法；可以拆成兩頁，或建議改成表格）。

1. 另開一個新對話（不要和重寫包同一個對話），選最好的模型。
2. 上傳 `給Gemini_流程圖改善包_{LABEL}.md`（或整份貼上），訊息寫一句：
   「請照這份檔案開頭的指示，重新設計第四節的每一張流程圖。」
3. 它寫到一半停下來，就回「繼續」。
4. 它回的內容整段複製（程式碼區塊、後面的總評與備註都要），直接貼給做投影片的 session；或存成文字檔放進這個資料夾，再說一聲。
5. 接下來由做投影片的 session 逐張對事實、量版面放不放得下，照它的設計改流程圖、重產，連同它的「判斷」「理由」與「總評」列給您看。

包裡的 {N} 張（張號是這一版的張號）：
{LIST}
沒有送的：中醫的辨證路徑 {NP} 張（那是您定的格式）。要一起送請說。

不要請它直接改 PPTX。回覆處理完以前，這一講流程圖的規格先不動。
想看它畫出來的樣子，可以在它回完以後再請它「把第 N 張畫成網頁給我看」；那是給您看的參考，套回投影片照它文字格式的那一份。
它若在「版面建議」提了九種排法以外的畫法，我們會列出來，做得出來的再加進工具（cycle、diamond、sieve 三種就是這樣來的）。
"""


def make(deck, out, label):
    cfg, order, sections, slides, flows, facts, notes, num = load(deck)
    name = cfg["decks"][deck].get("name", deck)
    picks = [s for s in order if slides.get(s, {}).get("flow") and flows.get(slides[s]["flow"], {}).get("kind") != "stages"]
    n_path = sum(1 for s in order if slides.get(s, {}).get("flow") and flows.get(slides[s]["flow"], {}).get("kind") == "stages")
    content = [s for s in order if not slides[s]["quiz"] and "-fuse-" not in s and slides[s]["type"] not in ("divider",)]
    L = [PROMPT.replace("{NAME}", name).replace("{AUD}", cfg.get("audience", "")).replace("{N}", str(len(picks)))]
    man, lst = {}, []
    for slug in picks:
        s, fig = slides[slug], flows[slides[slug]["flow"]]
        i = content.index(slug)
        prev = [f"第 {num[x]} 張「{slides[x]['title']}」" for x in content[max(0, i - 2):i]]
        nxt = [f"第 {num[x]} 張「{slides[x]['title']}」" for x in content[i + 1:i + 2]]
        st = fig.get("style")
        L.append(f"### 第 {num[slug]} 張｜{s['title']}\n")
        L.append(f"- 位置：{sections.get(slug, '')}。前面是{'、'.join(prev) or '（這一節的開頭）'}；後面是{'、'.join(nxt) or '（這一節的結尾）'}。")
        L.append(f"- 現在的排法：{st or 'stack'}（{STYLE_ZH.get(st, st)}）")
        L.append("- 現在的畫法：\n\n```")
        L.append("說明句｜" + ("　／　".join(s["bullets"]) if s["bullets"] else "無"))
        L += chart_text(fig)
        L.append("```\n")
        fs = [facts[f] for f in s["facts"] if f in facts]
        if fs:
            L.append("- 這一張的事實：")
            L += [f"  - {f['id']}｜p.{f['page']}｜{f['zh']}" for f in fs]
        if notes.get(slug):
            L.append("- 移下投影片的細節：")
            L += [f"  - {slug_to_num(x, num, slides)}" for x in notes[slug]]
        L.append("")
        man[slug] = {"num": num[slug], "fig": s["flow"], "title": s["title"], "lead": s["bullets"],
                     "spec_sha": hashlib.sha1(json.dumps(fig, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12],
                     "chart": chart_text(fig), "style": st}
        lst.append(f"- 第 {num[slug]} 張：{s['title']}（{st or 'stack'}）")
    os.makedirs(out, exist_ok=True)
    today = datetime.date.today()
    pk = os.path.join(out, f"給Gemini_流程圖改善包_{label}.md")
    text = "\n".join(L).rstrip() + "\n"
    open(pk, "w", encoding="utf-8", newline="\n").write(text)
    hp = os.path.join(out, f"0_怎麼用_流程圖改善包_{label}_{today:%Y%m%d}_草稿.md")
    open(hp, "w", encoding="utf-8", newline="\n").write(
        HOWTO.replace("{LABEL}", label).replace("{DATE2}", "2026-11-25").replace("{DATE}", f"{today:%Y%m%d}").replace("{N}", str(len(picks)))
        .replace("{NP}", str(n_path)).replace("{LIST}", "\n".join(lst) + "\n"))
    mp = os.path.join(CD, "_archive", "revoice", f"flowpack_manifest_{deck}.json")
    json.dump({"deck": deck, "label": label, "made": f"{today:%Y-%m-%d}", "slides": man}, open(mp, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print(f"-> {pk}（{len(text)} 字；流程圖 {len(picks)} 張；辨證路徑 {n_path} 張沒有送）")
    print(f"-> {hp}")
    print(f"-> {mp}")
    bad = [(i, ln) for i, ln in enumerate(text.split("\n"), 1) if EN_RUN.search(ln) and not ln.lstrip().startswith("#")]
    bad += [(i, ln) for i, ln in enumerate(text.split("\n"), 1) if re.search(r"「[^」]*[A-Za-z][^」]{40,}」", ln) and sum("一" <= c <= "鿿" for c in ln) < 10]
    if bad:
        print(f"[RED] 包裡有 {len(bad)} 行像教科書的英文原句（不可以交出去）：")
        for i, ln in bad[:8]:
            print(f"   {i}｜{ln[:110]}")
        return 1
    print("包裡沒有英文原句（連續 10 個以上英文字的行）")
    return 0


UNIT = re.compile(r"^[\s>*\-•`]*(判斷|排法|說明句|格|箭|回頭箭|來源|理由|版面建議|R\d+|B)\s*[｜|]\s?(.*?)`*\s*$")
SL = re.compile(r"^[\s#>*\-]*第\s*(\d+)\s*張")
LIMIT = {"timeline": (4, 22, 2), "stack": (4, 22, 2), "spine": (3, 22, 1), "steps": (2, 12, 3), "merge": (2, 12, 3), "fork": (2, 12, 3)}


def parse_reply(text):
    out, cur, page = {}, None, None
    for ln in text.split("\n"):
        m = SL.match(ln)
        if m:
            cur = {"判斷": "", "理由": "", "版面建議": "", "pages": []}
            out[int(m.group(1))] = cur
            page = None
            continue
        if cur is None:
            continue
        if re.match(r"^[\s`]*-{2,}\s*第二頁", ln):
            page = None
            cur["_split"] = True
            continue
        u = UNIT.match(ln)
        if not u:
            continue
        k, v = u.group(1), u.group(2).strip()
        if k in ("判斷", "理由", "版面建議"):
            cur[k] = (cur[k] + " " + v).strip()
            continue
        if k == "排法" or page is None:
            page = {"排法": v if k == "排法" else "", "說明句": "", "units": []}
            cur["pages"].append(page)
            if k == "排法":
                continue
        if k == "說明句":
            page["說明句"] = "" if v in ("無", "") else v
        else:
            page["units"].append((k, v))
    return out


def check(deck, files):
    mp = os.path.join(CD, "_archive", "revoice", f"flowpack_manifest_{deck}.json")
    man = json.loads(rd(mp))["slides"]
    by_num = {v["num"]: (k, v) for k, v in man.items()}
    rep = {}
    for f in files:
        rep.update(parse_reply(rd(f)))
    L = [f"# 流程圖改善包的回覆對照表（{deck}；{datetime.date.today():%Y-%m-%d}）", "",
         "機械檢查只查格數、每行字數、編號與英文有沒有少；先後與因果有沒有跑掉要逐張對事實帳。", ""]
    n_issue = 0
    for n, (slug, m) in sorted(by_num.items()):
        r = rep.get(n)
        L.append(f"## 第 {n} 張 `{slug}`｜{m['title']}\n")
        L.append("**原來**（" + (m["style"] or "stack") + "）\n\n```\n說明句｜" + ("　／　".join(m["lead"]) or "無") + "\n" + "\n".join(m["chart"]) + "\n```\n")
        if not r:
            L.append("**沒有回這一張。**\n")
            n_issue += 1
            continue
        issues = []
        old_en = set(re.findall(r"\(([A-Za-z][^()]*)\)", " ".join(m["chart"] + m["lead"])))
        new_txt = " ".join(v for p in r["pages"] for _, v in p["units"]) + " " + " ".join(p["說明句"] for p in r["pages"])
        miss = sorted(e for e in old_en if e not in new_txt)
        if miss:
            issues.append("少了原來的英文：" + "、".join(miss))
        if re.search(r"[①-⑩]|第[一二三四五六]步|步驟[一二三四1-6]|(?:^|｜|／)\s*[1-6][.、)]", new_txt):
            issues.append("有編號")
        for p in r["pages"]:
            st = p["排法"].split("＋")[0].strip()
            L.append(f"**改成**（{p['排法']}）\n\n```\n說明句｜{p['說明句'] or '無'}\n" + "\n".join(f"{k}｜{v}" for k, v in p["units"]) + "\n```\n")
            if width(p["說明句"]) > 30:
                issues.append(f"說明句 {width(p['說明句']):g} 字（上限 30）")
            if st in LIMIT:
                mx, per, lines = LIMIT[st]
                nodes = [v for k, v in p["units"] if k == "格"]
                side = st in ("merge", "fork")
                boxes = [b.strip() for v in nodes for b in (v.split("／") if side else [v])]
                if not side and len(nodes) > mx:
                    issues.append(f"{st} {len(nodes)} 格（一頁最多 {mx}）")
                for b in boxes:
                    for ln_ in b.split(SB):
                        if width(ln_.strip()) > per:
                            issues.append(f"格的一行 {width(ln_.strip()):g} 字（上限 {per}）：{ln_.strip()[:16]}…")
                    if len(b.split(SB)) > lines:
                        issues.append(f"一格 {len(b.split(SB))} 行（上限 {lines}）")
                for k, v in p["units"]:
                    if k == "箭" and v != "無" and width(v) > (24 if st == "spine" else 12):
                        issues.append(f"箭頭說明 {width(v):g} 字：{v[:14]}…")
        L.append(f"- 判斷：{r['判斷'] or '（沒有寫）'}\n- 理由：{r['理由'] or '（沒有寫）'}" + (f"\n- 版面建議：{r['版面建議']}" if r["版面建議"] else ""))
        L.append("- 機械檢查：" + ("；".join(issues) if issues else "沒有問題") + "\n")
        n_issue += bool(issues)
    op = os.path.join(CD, "_archive", "revoice", f"flowpack_{deck}_對照表.md")
    open(op, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    print(f"回覆 {len(rep)} 張／送出 {len(man)} 張；有機械問題或沒有回的 {n_issue} 張 → {op}")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "make":
        out = a[a.index("--out") + 1]
        lab = a[a.index("--label") + 1] if "--label" in a else (yaml.safe_load(rd(os.path.join(CD, "course.yaml"))).get("rewrite") or {}).get("label", a[1])
        sys.exit(make(a[1], out, lab))
    if len(a) >= 3 and a[0] == "check":
        sys.exit(check(a[1], a[2:]))
    print(__doc__)
    sys.exit(2)

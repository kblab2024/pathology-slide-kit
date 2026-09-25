# -*- coding: utf-8 -*-
"""共用模組：找教材庫、讀課程設定（course.yaml）、解析素材池／講稿／選單、組出一套投影片。

所有工具都用 `--course <名稱或路徑>` 指定課程。搜尋順序（load_course）：
  1. 既有的路徑：course.yaml 本身，或含 course.yaml 的資料夾
  2. <教材庫>/courses/<名稱>/course.yaml（教材庫見 find_materials()）
  3. <工具包>/examples/<名稱>/course.yaml
  都找不到就列出每個試過的路徑。
教材庫（find_materials）：環境變數 SLIDEKIT_MATERIALS → 同層的 pathology-slide-materials
  → 工具包的上一層（若含 courses/）→ None。
語料（corpus_dir）：SLIDEKIT_CORPUS → <教材庫>/corpus → <工具包>/style/corpus。
國考題庫：<工具包>/question_banks/<題庫>/*.json（醫師題庫只收題號 76–100）。
來源檔格式（路徑在 course.yaml 的 paths，相對於課程資料夾）：
  pool.md    素材池：「## 投影片 {slug}｜標題」＋ HTML 註解（type／IMG／quiz／diagram／src／aud／img_wanted／build）＋「- 」條列＋「|」表格
  script.md  講稿：「### 投影片 {slug}｜標題」＋【講稿】／【講稿:系別】／【講義補充】
  decks/*.md 選單：「## 節｜標題」→「### 段落」→「- slug」，渲染時依序編號
行內強調標記：[[藍:文字]]、[[紅:文字]]、[[橘:文字]]、[[青:文字]]、[[灰:文字]]，色票在 course.yaml 的 emphasis。
"""
import glob
import json
import os
import re
import sys

import yaml

# 工具包根目錄（含 scripts/ 的資料夾）；KIT 與 ROOT 同義，ROOT 保留給既有程式
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = ROOT
MATERIALS_REPO = "pathology-slide-materials"

# 教師接受過的藍×赤陶設計系統（ENT、lung 沿用）；course.yaml 的 design 可覆寫
DESIGN = {
    "deep": "14263B", "cobalt": "2563A8", "cobaltd": "1B4A80", "terra": "BF5B3C", "terrad": "8F4129",
    "snow": "F4F8FB", "tint": "E9F1F7", "tint2": "DCE9F2", "line": "CFE0EC", "ink": "1E2A35", "grey": "5B6B78",
}
DARK_TEXT = {"hi": "FFFFFF", "mid": "D8E6F4", "low": "9FC1E8", "dim": "6E8CAD"}
FONT = "Microsoft JhengHei"   # PPTX 內寫入的字型名稱；雲端量字改用 Noto Sans CJK TC，但檔案內仍寫這個名字


# ---------------- 教材庫與語料 ----------------
_WARNED = set()


def _warn(msg):
    if msg not in _WARNED:
        _WARNED.add(msg)
        print("[warn] " + msg, file=sys.stderr)


def find_materials():
    """回傳教材庫（私有 repo）的絕對路徑；找不到回傳 None。
    順序：SLIDEKIT_MATERIALS → <KIT>/../pathology-slide-materials → <KIT>/..（若含 courses/）。"""
    env = os.environ.get("SLIDEKIT_MATERIALS", "").strip()
    if env:
        p = os.path.abspath(os.path.expanduser(env))
        if os.path.isdir(p):
            return p
        _warn(f"SLIDEKIT_MATERIALS={env} 不是資料夾，改用預設搜尋")
    parent = os.path.dirname(KIT)
    sib = os.path.join(parent, MATERIALS_REPO)
    if os.path.isdir(sib):
        return sib
    if os.path.isdir(os.path.join(parent, "courses")):
        return parent
    return None


def corpus_dir():
    """教師投影片語料（decks/*.json|txt、edits/、index.md）所在資料夾。
    順序：SLIDEKIT_CORPUS → <教材庫>/corpus → <KIT>/style/corpus（最後一個不保證存在）。"""
    env = os.environ.get("SLIDEKIT_CORPUS", "").strip()
    if env:
        p = os.path.abspath(os.path.expanduser(env))
        if os.path.isdir(p):
            return p
        _warn(f"SLIDEKIT_CORPUS={env} 不是資料夾，改用預設搜尋")
    m = find_materials()
    if m and os.path.isdir(os.path.join(m, "corpus")):
        return os.path.join(m, "corpus")
    return os.path.join(KIT, "style", "corpus")


def question_bank_dir(bank):
    """國考題庫資料夾：<KIT>/question_banks/<bank>。"""
    return os.path.join(KIT, "question_banks", bank)


# ---------------- 課程設定 ----------------
class Course(dict):
    """course.yaml 的內容＋解析過的絕對路徑。用 c.path('pool') 取絕對路徑。"""

    def path(self, key):
        return os.path.join(self["dir"], self["paths"][key])

    def textbook_path(self, key="pages_dir"):
        """course.yaml textbook.<key>（相對於課程資料夾）的絕對路徑；沒設定回傳 None。
        key：pages_dir（pNN_PPP.jpg|png＋.txt＋.tsv）或 pdf。"""
        tb = self.get("textbook") or {}
        v = tb.get(key) or (tb.get("pages_png") if key == "pages_dir" else None)  # pages_png＝舊鍵名
        if not v:
            return None
        return os.path.normpath(v if os.path.isabs(v) else os.path.join(self["dir"], v))

    @property
    def sizes(self):
        return self["sizes"]

    def deck(self, d):
        return self["decks"][d]


def course_candidates(name_or_path):
    """load_course 依序嘗試的 course.yaml 路徑。"""
    p = os.path.expanduser(str(name_or_path))
    tried = []
    if p.endswith((".yaml", ".yml")):
        tried.append(os.path.abspath(p))
    else:
        tried.append(os.path.abspath(os.path.join(p, "course.yaml")))
    m = find_materials()
    name = os.path.basename(os.path.normpath(p))
    if name.endswith((".yaml", ".yml")):
        name = os.path.basename(os.path.dirname(os.path.abspath(p)))
    if m:
        tried.append(os.path.join(m, "courses", name, "course.yaml"))
    tried.append(os.path.join(KIT, "examples", name, "course.yaml"))
    out = []
    for t in tried:
        if t not in out:
            out.append(t)
    return out


def load_course(name_or_path):
    tried = course_candidates(name_or_path)
    p = next((t for t in tried if os.path.isfile(t)), None)
    if p is None:
        m = find_materials()
        where = m or "（未找到；設 SLIDEKIT_MATERIALS，或把 pathology-slide-materials 放在工具包同層）"
        raise FileNotFoundError(
            f"找不到課程 {name_or_path!r} 的 course.yaml。試過：\n  " + "\n  ".join(tried)
            + f"\n教材庫：{where}")
    cfg = yaml.safe_load(open(p, encoding="utf-8"))
    c = Course(cfg)
    c["dir"] = os.path.dirname(p)
    c["materials"] = find_materials()
    c["design"] = {**DESIGN, **(cfg.get("design") or {})}
    c.setdefault("emphasis", {})
    c.setdefault("diagrams", {})
    return c


# ---------------- 行內強調標記 ----------------
_MARK = re.compile(r"\[\[(藍|紅|橘|青|灰)[:：](.+?)\]\]")


def parse_markup(text, emphasis):
    """回傳 [(文字, 色碼或 None)]。"""
    out, pos = [], 0
    for m in _MARK.finditer(text or ""):
        if m.start() > pos:
            out.append((text[pos:m.start()], None))
        out.append((m.group(2), emphasis.get(m.group(1))))
        pos = m.end()
    if pos < len(text or ""):
        out.append((text[pos:], None))
    return out or [("", None)]


def strip_markup(text):
    return _MARK.sub(lambda m: m.group(2), text or "")


# ---------------- 國考題庫 ----------------
def load_questions(course, deck):
    """<KIT>/question_banks/<bank>/*.json 合併；key='{年度}-{第幾次}#{題號}'。
    醫師題庫只收病理段（題號 76–100）。"""
    bank = course.deck(deck).get("question_bank")
    if not bank:
        return {}
    d = question_bank_dir(bank)
    files = sorted(glob.glob(os.path.join(d, "*.json")))
    if not files:
        _warn(f"題庫 {bank} 沒有任何 JSON：{d}")
    qs = {}
    for f in files:
        if os.path.basename(f) == "manifest.json":
            continue
        data = json.load(open(f, encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("questions", [])
        for q in data:
            if bank == "醫師" and not (76 <= int(q["題號"]) <= 100):
                continue
            q = dict(q)
            q["bank"] = bank
            qs[f"{q['年度']}-{q['第幾次']}#{q['題號']}"] = q
    return qs


# ---------------- 素材池 ----------------
_HDR = re.compile(r'\s*([A-Za-z0-9_\-]+)\s*[｜|]\s*(.*)')
_SEP_ROW = re.compile(r'^\|[\s\-:｜|]*$')


def _table_rows(lines):
    rows = []
    for ln in lines:
        st = ln.strip()
        if not st.startswith("|") or _SEP_ROW.match(st):
            continue
        cells = [c.strip() for c in st.strip("|").split("|")]
        if any(cells):
            rows.append(cells)
    return rows


def _split_list(s, seps=r'[,，、\s]+'):
    return [x for x in re.split(seps, s.strip()) if x]


def _field(body, name):
    m = re.search(r'<!--\s*' + name + r':\s*(.*?)\s*-->', body, re.S)
    return m.group(1).strip() if m else ""


def parse_pool(course):
    path = course.path("pool")
    raw = open(path, encoding="utf-8").read()
    blocks = re.split(r'(?m)^##\s*投影片\s*', raw)[1:]
    pool = {}
    for b in blocks:
        lines = b.splitlines()
        m = _HDR.match(lines[0]) if lines else None
        if not m:
            raise ValueError("素材池標頭格式錯誤：" + (lines[0][:80] if lines else "(空)"))
        sid, title = m.group(1), m.group(2).strip()
        if sid in pool:
            raise ValueError(f"素材池 slug 重複：{sid}")
        body = "\n".join(lines[1:])
        stype = _field(body, "type") or "left"
        quiz = re.search(r'<!--\s*quiz:\s*([\d\-#]+)\s*(?:[｜|]\s*([^>]*?))?\s*-->', body)
        dia_raw = _field(body, "diagram")
        dia_name, dia_bright = "", []
        if dia_raw:
            parts = re.split(r'亮[:：]', dia_raw, maxsplit=1)
            dia_name = parts[0].strip(" ｜|")
            if len(parts) > 1:
                dia_bright = [t.strip() for t in re.split(r'[,，]', parts[1]) if t.strip()]
        auds = _split_list(_field(body, "aud")) if _field(body, "aud") else list(course["deck_order"])
        bad = [a for a in auds if a not in course["decks"]]
        if bad:
            raise ValueError(f"{sid}: aud 含未知 deck {bad}")
        imgs = []
        for im in re.finditer(r'<!--\s*IMG:\s*(.*?)-->', body, re.S):
            inner = im.group(1)
            p = re.split(r'[｜|\n]', inner)[0].strip()
            get = lambda k: (re.search(k + r'：\s*([^｜|\n]+)', inner).group(1).strip()
                             if re.search(k + r'：\s*([^｜|\n]+)', inner) else "")
            img = {"path": p, "desc": get("內容"), "src": get("出處"), "label": get("標籤")}
            absp = p if os.path.isabs(p) else os.path.join(course["dir"], p)
            img["abspath"], img["exists"] = absp, os.path.exists(absp)
            imgs.append(img)
        src = _field(body, "src")
        pool[sid] = {
            "id": sid, "title": title, "type": stype,
            "quiz": quiz.group(1) if quiz else None,
            "quiz_note": (quiz.group(2).strip() if quiz and quiz.group(2) else ""),
            "diagram": dia_name, "diagram_bright": dia_bright,
            "aud": auds, "build": _field(body, "build"),
            "src": [x.strip() for x in re.split(r'[｜|]', src) if x.strip()] if src else [],
            "img_wanted": _field(body, "img_wanted"),
            "robbins": _field(body, "robbins"),
            "title_ov": {m.group(1): m.group(2).strip()
                         for m in re.finditer(r'<!--\s*title:([a-z]+):\s*([^>]*?)\s*-->', body)},
            "imgs": imgs,
            "bullets": [ln.rstrip()[2:] if not ln.startswith("  ") else ln.rstrip()
                        for ln in lines[1:] if re.match(r'^(  )*- ', ln)],
            "table": _table_rows(lines[1:]),
        }
    return pool


def bullet_level(b):
    """條列縮排：兩個空白一層（「  - 子層」）。回傳 (層級, 文字)。"""
    m = re.match(r'^((?:  )*)- (.*)$', b)
    if m:
        return len(m.group(1)) // 2, m.group(2)
    return 0, b


# ---------------- 選單 ----------------
def parse_deck_manifest(course, deck):
    path = os.path.join(course.path("decks_dir"), f"{deck}.md")
    sections, cur_sec, cur_seg = [], None, None
    for ln in open(path, encoding="utf-8").read().splitlines():
        st = ln.strip()
        if st.startswith("## "):
            title = st[3:].strip()
            cur_sec = {"title": title, "label": title.split("｜", 1)[0].strip(), "segments": []}
            sections.append(cur_sec)
            cur_seg = None
        elif st.startswith("### "):
            cur_seg = {"title": st[4:].strip(), "ids": []}
            cur_sec["segments"].append(cur_seg)
        elif st.startswith("- "):
            if cur_seg is None:
                cur_seg = {"title": cur_sec["title"], "ids": []}
                cur_sec["segments"].append(cur_seg)
            cur_seg["ids"].append(st[2:].strip().split()[0])
    if not sections:
        raise ValueError(f"{path} 沒有任何節")
    return sections


def _expand(s, course, deck, qs):
    """表格超過 table_max_rows 列就拆成同標題連張（重複表頭）；其他張原樣回傳。"""
    sz = course.sizes
    if s["type"] == "table3" and len(s["table"]) - 1 > sz["table_max_rows"]:
        head, rows = s["table"][0], s["table"][1:]
        k = sz["table_max_rows"]
        out = []
        for i in range(0, len(rows), k):
            t = dict(s)
            t["table"] = [head] + rows[i:i + k]
            t["id"] = s["id"] if i == 0 else f"{s['id']}~{i // k + 1}"
            t["bullets"] = s["bullets"] if i == 0 else []
            out.append(t)
        return out
    return [s]


def build_deck(course, deck, pool=None):
    pool = pool if pool is not None else parse_pool(course)
    qs = load_questions(course, deck)
    man = parse_deck_manifest(course, deck)
    slides, sections, segments, seen, n = [], [], [], set(), 0
    for sec in man:
        lo = n + 1
        for seg in sec["segments"]:
            seg_start = n + 1
            for sid in seg["ids"]:
                if sid not in pool:
                    raise KeyError(f"選單 {deck} 引用不存在的 slug：{sid}")
                if sid in seen:
                    raise ValueError(f"選單 {deck} 重複列出 slug：{sid}")
                seen.add(sid)
                base = dict(pool[sid])
                if deck not in base["aud"]:
                    raise ValueError(f"slug {sid} 未開放給 {deck}")
                base["title"] = base["title_ov"].get(deck, base["title"])
                for s in _expand(base, course, deck, qs):
                    n += 1
                    s.update({"num": n, "deck": deck, "section": sec["label"], "section_title": sec["title"],
                              "segment": seg["title"], "section_first": n == lo})
                    slides.append(s)
            if n >= seg_start:
                segments.append((seg_start, seg["title"]))
        if n >= lo:
            sections.append((lo, n, sec["title"]))
    return {"deck": deck, "name": course.deck(deck)["name"], "exam": course.deck(deck).get("exam", False),
            "slides": slides, "sections": sections, "segments": segments, "questions": qs}


# ---------------- 講稿 ----------------
_TAG = re.compile(r'(?m)^【(講稿(?::[a-z]+)?|講義補充|附表)】[ \t]*')


def parse_script(course):
    path = course.path("script")
    if not os.path.exists(path):
        return {}
    raw = open(path, encoding="utf-8").read()
    out = {}
    for b in re.split(r'(?m)^###\s*投影片\s*', raw)[1:]:
        lines = b.splitlines()
        m = _HDR.match(lines[0]) if lines else None
        if not m:
            continue
        body = re.sub(r'\n?---\s*$', '', "\n".join(lines[1:]))
        parts = _TAG.split(body)
        jiang, bul = {}, []
        for tag, content in zip(parts[1::2], parts[2::2]):
            content = content.strip()
            if tag.startswith("講稿"):
                jiang[tag.split(":", 1)[1] if ":" in tag else ""] = "" if content in ("", "（待補）") else content
            elif tag == "講義補充":
                bul = [x.strip() for x in re.split(r'(?m)^-\s+', content) if x.strip()]
        out[m.group(1)] = {"id": m.group(1), "title": m.group(2).strip(), "jiang": jiang, "bullets": bul}
    return out


def notes_map(built, script):
    """{slug: 備註全文}：講稿（系別覆寫優先）＋講義補充（多為文獻完整書目）。"""
    notes = {}
    for s in built["slides"]:
        e = script.get(s["id"].split("~")[0])
        if not e:
            continue
        jt = e["jiang"].get(built["deck"]) or e["jiang"].get("") or ""
        parts = [jt] if jt else []
        if e["bullets"]:
            parts += [""] + ["- " + strip_markup(b) for b in e["bullets"]]
        if parts:
            notes[s["id"]] = "\n".join(parts).strip()
    return notes


def deck_filename(course, deck, date=None, pdf=False):
    d = course.deck(deck)
    tpl = d.get("pdf_filename" if pdf else "filename")
    return tpl.format(date=date or course.get("lecture_date", "YYYYMMDD"))


def visible_text(s):
    """一張投影片的可見文字（標題＋條列＋表格），標記已剝除。"""
    parts = [s["title"]] + [bullet_level(b)[1] for b in s["bullets"]]
    for r in s.get("table") or []:
        parts += r
    return strip_markup("\n".join(parts))

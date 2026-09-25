#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_moex_exam.py — 考選部（MOEX）考畢試題 PDF 解析器（PyMuPDF 文字層）

把考選部「考畢試題查詢平臺」下載的三種 PDF 轉成題庫 JSON：

    {年度}-{次}_Q.pdf   試題（題幹「1.」「2.」…；選項「A.」「B.」「C.」「D.」）
    {年度}-{次}_A.pdf   測驗式試題標準答案（表格：題號列 01..N ／ 答案列 Ａ..Ｄ）
    {年度}-{次}_M.pdf   測驗題標準答案更正（同表格，更正題以「＃」標示，備註寫更正內容）

輸出 JSON 為 list，每題 key 固定為：
    題號 (int)、年度 (int)、第幾次 (int)、科目 (str)、question (str)、
    options ({"A":..,"B":..,"C":..,"D":..})、answer (str, 已套用更正)、src (試題 PDF URL)

answer 規則：
    單一正解        -> "C"
    一律給分／送分  -> "#"
    複選給分        -> "A,C"（「答Ａ、Ｃ給分」「答Ａ或Ｃ或AC者均給分」皆轉成逗號串）
    更正為單一答案  -> 該字母（「答案更正為Ｄ」）

用法
----
整個資料夾（檔名須為 {年度}-{次}_Q.pdf / _A.pdf / _M.pdf）：

    python parse_moex_exam.py --raw "immune/牙醫師國考/raw" \\
        --out "question_banks/牙醫師/questions-dent-{first}-{last}.json" \\
        --manifest "question_banks/牙醫師/manifest.json"

    * 若 raw 資料夾內有 sources.json（由 fetch_moex_dent_exam.py 產生），會用它填入
      src（試題 PDF URL）與 manifest 的考試代號／類科代號／科目代號。
    * --out 檔名的 {first}/{last} 會以實際最小／最大年度取代。
    * --full-subject 讓「科目」欄保留 PDF 標頭的完整科目名稱（預設只留「（包括」前的短名，
      例如 牙醫學(二)）。--subject 可強制指定科目字串。

單一場次：

    python parse_moex_exam.py --q 115-2_Q.pdf --a 115-2_A.pdf [--m 115-2_M.pdf] \\
        --year 115 --session 2 --src "https://wwwq.moex.gov.tw/exam/wHandExamQandA_File.ashx?t=Q&code=115090&c=303&s=0302&q=1" \\
        --out out.json

作為模組：

    from parse_moex_exam import parse_question_pdf, parse_answer_pdf, build_bank
    meta, qs = parse_question_pdf("115-2_Q.pdf")
    std = parse_answer_pdf("115-2_A.pdf")          # AnswerSheet(n, answers, corrections, ...)
    fix = parse_answer_pdf("115-2_M.pdf")
    rows, warns = build_bank(qs, std, fix, year=115, session=2, subject="牙醫學(二)", src=url)

解析細節（依 104–115 年牙醫師(一) 牙醫學(二) 24 場次實測）
--------------------------------------------------------------
試題 PDF
  * 題號採「循序期待」：只有當某行以「{下一題號}.」開頭、且上一題四個選項都已出現時才切新題，
    所以「26.26歲的男病患…」這種題幹以數字開頭的情況不會誤切。
  * 換行接合：中英文直接相接；英文/數字對英文/數字之間補一個空格（PDF 在英文字間換行）；
    單獨成行的 1–3 位數字（含 +/-）視為上標（N/m + 2 -> N/m²、mm + 3 -> mm³）。
  * 文字層瑕疵修正（parse 時自動處理，並在 stderr 印出警告）：
      - 康熙部首區（U+2F00–U+2FD5，如「⽣」）逐字 NFKC 還原；部首補充區（U+2E80–U+2EF3，如「⻑」）
        NFKC 無對應，用內建對照表還原（RADICAL_SUPP）。〔108-1 試題〕
      - Big5／倚天延伸碼位衝突：圈號 ①–⑩ 被讀成西里爾字母 U+045B–U+0464（ћќѝў…），還原為 ①–⑩。
        〔113-1 試題〕（--keep-cyrillic 可關閉）
      - Apple 轉碼提示私用字元 U+F870–U+F8FF（不可見）移除。〔104-2 試題〕
      - 有些頁面每一行被存成左右兩段、交接字重印一次（PyMuPDF 預設順序會先吐所有左段再吐右段，
        sort=True 則交接字重複）。偵測到同一列有水平重疊的文字行時，該頁改用字元座標重組：
        依 y 群成行、依 x 排序、同位置同字去重。〔112-1 p9、113-1 p10、115-1 p2〕
      - 第 1 頁標頭的重影行（同一片段重複 3–4 次）以片段去重後再抓考試名稱／代號／類科／科目。
        〔104-1、104-2、105-1、105-2、106-1、113-1〕
  * 圖片說明列「圖一  圖二」與「※」開頭的註記列會被略過；圖片本身不輸出。選項本身是圖片
    （文字層只有「A.」）者，該選項填 "[圖]"。
答案／更正 PDF
  * 答案表以字詞座標配對（題號格與答案格右緣 x 對齊、答案列在題號列正下方），並以文字流順序
    解析做交叉驗證；兩者不一致時印出警告，以座標法為準。
  * 更正檔（M）：表格內「＃」的題目以備註句解析；表格內非「＃」但與標準答案不同者，以更正檔為準
    並印出警告。

驗證：每份試題須解析出與答案檔「題數」相同的題目數、每題恰有 A–D 四個選項、每題都有答案，
否則以非零狀態碼結束（--lenient 可改為只警告）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    sys.exit("需要 PyMuPDF：pip install pymupdf")

# ---------------------------------------------------------------------------
# 字元修正
# ---------------------------------------------------------------------------
FW2HW = {"Ａ": "A", "Ｂ": "B", "Ｃ": "C", "Ｄ": "D", "Ｅ": "E", "＃": "#"}
LETTER_TOKEN_RE = re.compile(r"^(?:答案)?([ＡＢＣＤＥ＃ABCDE#])$")
FW_DIGITS = str.maketrans("０１２３４５６７８９．", "0123456789.")
SUPERSCRIPT = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")

# CJK 部首補充區（NFKC 無分解）-> 一般字
RADICAL_SUPP = {
    "⺠": "民", "⺟": "母", "⻄": "西", "⻑": "長", "⻘": "青", "⻝": "食", "⻣": "骨", "⻤": "鬼",
    "⻭": "齒", "⻯": "竜", "⻰": "龍", "⻳": "龜", "⻫": "斉", "⻮": "歯", "⻱": "亀", "⺫": "罒",
    "⻍": "辶", "⻎": "辶", "⻌": "辶", "⺼": "月", "⻖": "阝", "⻏": "阝", "⺧": "牛", "⺩": "王",
    "⻊": "足", "⻋": "车", "⻢": "马", "⻥": "鱼", "⻦": "鸟", "⻩": "黄", "⻬": "齐", "⻲": "龟",
    "⻅": "见", "⻉": "贝", "⻔": "门", "⻜": "飞", "⻛": "风", "⻚": "页", "⻙": "韦", "⻐": "钅",
    "⺮": "竹", "⺶": "羊", "⺷": "羊", "⺻": "聿", "⺹": "老", "⻂": "衤", "⺤": "爫", "⺥": "爫",
}
# Big5／倚天延伸：圈號 ①–⑩ 被讀成 U+045B–U+0464
BIG5_CIRCLED = {chr(0x045B + i): chr(0x2460 + i) for i in range(10)}

KEEP_CYRILLIC = False  # 由 --keep-cyrillic 設定


def fix_glyphs(s: str) -> str:
    """修正字型 cmap 造成的假字：康熙部首、部首補充、Big5 圈號、Apple 私用提示字元。"""
    if s.isascii():
        return s
    out = []
    for c in s:
        o = ord(c)
        if 0x2F00 <= o <= 0x2FDF:
            out.append(unicodedata.normalize("NFKC", c))
        elif 0x2E80 <= o <= 0x2EFF:
            out.append(RADICAL_SUPP.get(c, c))
        elif 0x045B <= o <= 0x0464 and not KEEP_CYRILLIC:
            out.append(BIG5_CIRCLED[c])
        elif 0xF870 <= o <= 0xF8FF:
            continue
        else:
            out.append(c)
    return "".join(out)


ODD_GLYPH_RE = re.compile(r"[⺀-⿟Ѐ-ӿ-]")


def norm_letter(ch: str) -> str:
    return FW2HW.get(ch, ch)


def collapse_ws(s: str) -> str:
    return re.sub(r"[ \t\r\f\v]+", " ", s).strip()


# ---------------------------------------------------------------------------
# 行接合
# ---------------------------------------------------------------------------
SUPERSCRIPT_LINE_RE = re.compile(r"^\d{1,3}[+\-]?$")


def join_lines(parts: List[str]) -> str:
    """把 PDF 的多行接成一段：中英直接相接、英文字間補空格、獨立數字列視為上標。"""
    parts = [p for p in (collapse_ws(p) for p in parts) if p]
    if not parts:
        return ""
    out = parts[0]
    for p in parts[1:]:
        if SUPERSCRIPT_LINE_RE.match(p) and re.search(r"[A-Za-z0-9)）]$", out):
            out += p.translate(SUPERSCRIPT)
        elif re.search(r"[A-Za-z0-9,.;:%\]]$", out) and re.match(r"^[A-Za-z0-9(\[]", p):
            out += " " + p
        else:
            out += p
    return collapse_ws(out)


# ---------------------------------------------------------------------------
# 頁面文字擷取（預設文字流；偵測到重疊行時改用字元座標重組）
# ---------------------------------------------------------------------------
def _has_overlapping_lines(page: "fitz.Page") -> bool:
    boxes = []
    for b in page.get_text("dict")["blocks"]:
        if b.get("type", 0) != 0:
            continue
        for l in b["lines"]:
            if len("".join(s["text"] for s in l["spans"]).strip()) >= 3:
                boxes.append(l["bbox"])
    for i in range(len(boxes)):
        a = boxes[i]
        for j in range(i + 1, len(boxes)):
            b = boxes[j]
            yov = min(a[3], b[3]) - max(a[1], b[1])
            xov = min(a[2], b[2]) - max(a[0], b[0])
            if yov > 0.5 * min(a[3] - a[1], b[3] - b[1]) and xov >= 3:
                return True
    return False


def _char_lines(page: "fitz.Page") -> List[str]:
    """字元座標重組：依垂直重疊群成行、依 x 排序、同位置同字（重印）去重。"""
    chars = []
    for b in page.get_text("rawdict")["blocks"]:
        if b.get("type", 0) != 0:
            continue
        for l in b["lines"]:
            for s in l["spans"]:
                for ch in s["chars"]:
                    x0, y0, x1, y1 = ch["bbox"]
                    chars.append([x0, y0, x1, y1, ch["c"]])
    chars.sort(key=lambda c: ((c[1] + c[3]) / 2, c[0]))
    lines: List[dict] = []
    for c in chars:
        h = c[3] - c[1]
        for L in lines[-4:]:
            ov = min(L["y1"], c[3]) - max(L["y0"], c[1])
            if ov > 0.5 * min(h, L["y1"] - L["y0"]):
                L["chars"].append(c)
                L["y0"] = min(L["y0"], c[1])
                L["y1"] = max(L["y1"], c[3])
                break
        else:
            lines.append({"y0": c[1], "y1": c[3], "chars": [c]})
    out = []
    for L in lines:
        s, prev = "", None
        for c in sorted(L["chars"], key=lambda c: c[0]):
            if prev and c[4] == prev[4] and abs(c[0] - prev[0]) < 0.5 * max(1.0, prev[2] - prev[0]):
                continue
            s += c[4]
            prev = c
        out.append(s)
    return out


def pdf_lines(path: str) -> Tuple[List[str], List[int]]:
    """回傳 (全部行, 使用字元重組的頁碼(1-based))。"""
    doc = fitz.open(path)
    lines: List[str] = []
    flagged: List[int] = []
    for pno, page in enumerate(doc, 1):
        if _has_overlapping_lines(page):
            flagged.append(pno)
            raw = _char_lines(page)
        else:
            raw = page.get_text().split("\n")
        lines.extend(fix_glyphs(l).strip() for l in raw)
    doc.close()
    return lines, flagged


# ---------------------------------------------------------------------------
# 試題 PDF
# ---------------------------------------------------------------------------
STEM_RE = re.compile(r"^(\d{1,3})\.(.*)$")
OPTION_RE = re.compile(r"^([A-EＡ-Ｅ])[\.．](.*)$")
CAPTION_RE = re.compile(r"^(?:圖\s*[一二三四五六七八九十\d]+)(?:\s+圖\s*[一二三四五六七八九十\d]+)*$")
STRIP_LINE_RE = re.compile(r"^(?:※|代\s*號[:：]|頁\s*次|第\s*\d+\s*頁\s*$|[（(]?請接|請翻)")
IMAGE_OPTION = "[圖]"


@dataclass
class QuestionMeta:
    exam_title: str = ""
    paper_code: str = ""      # 代號（試題代號，如 2303）
    category: str = ""        # 類科名稱（如 牙醫師(一)）
    subject_full: str = ""    # 科目名稱全文
    subject_short: str = ""   # 「（包括」之前的短名
    flagged_pages: List[int] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def dedupe_ghost_lines(lines: List[str]) -> str:
    """標頭重影：片段 f1 f1 f1 f1+f2 f2 f2 f2+f3 … -> f1+f2+f3…"""
    acc, frag = "", ""
    for L in lines:
        L = L.strip()
        if not L:
            continue
        if acc.endswith(L):
            frag = L
            continue
        if frag and L.startswith(frag) and len(L) > len(frag):
            acc += L[len(frag):]
        else:
            acc += L
        frag = L
    return acc


def _parse_q_header(lines: List[str], start: int) -> QuestionMeta:
    head = dedupe_ghost_lines(lines[:start])
    meta = QuestionMeta()
    m = re.search(r"代\s*號[:：]\s*(\d+)", head)
    if m:
        meta.paper_code = m.group(1)
    m = re.search(r"類科名稱[:：]\s*(.+?)\s*(?:科目名稱|考試時間|$)", head)
    if m:
        meta.category = collapse_ws(m.group(1))
    m = re.search(r"科目名稱[:：]\s*(.+?)\s*(?:考試時間|座號|※|$)", head)
    if m:
        meta.subject_full = re.sub(r"\s+", "", m.group(1))
        meta.subject_short = re.split(r"[（(]包括", meta.subject_full)[0]
    m = re.match(r"(.*?)代\s*號[:：]", head)
    meta.exam_title = re.sub(r"\s+", "", m.group(1)) if m else ""
    return meta


def parse_question_pdf(path: str) -> Tuple[QuestionMeta, List[dict]]:
    """回傳 (meta, [{'題號':int,'question':str,'options':{'A':..}} ...])。"""
    lines, flagged = pdf_lines(path)
    start = None
    for i, l in enumerate(lines):
        if re.match(r"^[1１][\.．]", l):
            start = i
            break
    if start is None:
        raise ValueError(f"{path}: 找不到第 1 題")
    meta = _parse_q_header(lines, start)
    meta.flagged_pages = flagged
    if flagged:
        meta.warnings.append(f"頁 {flagged} 偵測到重疊文字行，改用字元座標重組")

    questions: List[dict] = []
    cur: Optional[dict] = None
    expect_q = 1
    expect_opt: Optional[str] = None  # None=題幹中, 'A'..'D'=等下一個選項, 'END'=四選項齊
    last_key = "stem"

    for raw in lines[start:]:
        l = raw
        if not l or CAPTION_RE.match(l) or STRIP_LINE_RE.match(l):
            continue
        l = l[:4].translate(FW_DIGITS) + l[4:]  # 行首全形數字正規化

        m = STEM_RE.match(l)
        if m and int(m.group(1)) == expect_q and (cur is None or expect_opt == "END"):
            cur = {"題號": expect_q, "stem": [m.group(2)], "opts": {}}
            questions.append(cur)
            expect_q += 1
            expect_opt = "A"
            last_key = "stem"
            continue

        mo = OPTION_RE.match(l)
        if mo and cur is not None and expect_opt not in (None, "END") and norm_letter(mo.group(1)) == expect_opt:
            cur["opts"][expect_opt] = [mo.group(2)]
            last_key = expect_opt
            expect_opt = "END" if expect_opt == "D" else chr(ord(expect_opt) + 1)
            continue

        if cur is None:
            continue
        target = cur["stem"] if last_key == "stem" else cur["opts"][last_key]
        target.append(l)

    out = []
    for q in questions:
        opts = {k: join_lines(v) for k, v in q["opts"].items()}
        for k, v in opts.items():
            if not v:
                opts[k] = IMAGE_OPTION
        out.append({"題號": q["題號"], "question": join_lines(q["stem"]), "options": opts})
    odd = sorted({c for q in out for c in ODD_GLYPH_RE.findall(q["question"] + "".join(q["options"].values()))})
    if odd:
        meta.warnings.append("殘留異常字元：" + " ".join(f"{c}(U+{ord(c):04X})" for c in odd))
    return meta, out


# ---------------------------------------------------------------------------
# 答案／更正 PDF
# ---------------------------------------------------------------------------
@dataclass
class AnswerSheet:
    path: str
    n: int
    answers: Dict[int, str]                 # 題號 -> 'A'..'D' 或 '#'
    corrections: Dict[int, str] = field(default_factory=dict)  # 備註解析：題號 -> 'A,C' / '#' / 'D'
    is_correction_sheet: bool = False
    note: str = ""
    warnings: List[str] = field(default_factory=list)
    paper_code: str = ""


CLAUSE_RE = re.compile(r"第\s*(\d{1,3})\s*題\s*([^第。；;]*)")


def parse_correction_note(note: str) -> Dict[int, str]:
    """把備註句轉成 {題號: answer}。"""
    out: Dict[int, str] = {}
    note = re.sub(r"\s+", "", note)
    for m in CLAUSE_RE.finditer(note):
        q = int(m.group(1))
        body = m.group(2)
        m2 = re.search(r"(?:更正為|改為|應為|修正為|正確答案為)\s*([ＡＢＣＤＥABCDE])", body)
        if m2:
            out[q] = norm_letter(m2.group(1))
            continue
        if re.search(r"一律給分|送分|刪題|全部給分", body) and not re.search(r"[ＡＢＣＤＥABCDE]", body):
            out[q] = "#"
            continue
        letters: List[str] = []
        for c in re.findall(r"[ＡＢＣＤＥABCDE]", body):
            c = norm_letter(c)
            if c not in letters:
                letters.append(c)
        out[q] = ",".join(letters) if letters else "#"
    return out


def _positional_answers(doc: "fitz.Document", n: int) -> Tuple[Dict[int, str], List[str]]:
    warns: List[str] = []
    nums, letters = [], []
    for pno, page in enumerate(doc):
        for x0, y0, x1, y1, t, *_ in page.get_text("words"):
            t = t.strip()
            if re.fullmatch(r"\d{1,3}", t) and 1 <= int(t) <= n:
                nums.append((pno, x0, y0, x1, y1, int(t)))
            else:
                m = LETTER_TOKEN_RE.match(t)
                if m:
                    letters.append((pno, x0, y0, x1, y1, norm_letter(m.group(1))))
    ans: Dict[int, str] = {}
    for pno, x0, y0, x1, y1, letter in letters:
        cands = [N for N in nums if N[0] == pno and abs(N[3] - x1) <= 5 and -2 <= y0 - N[4] <= 30]
        if not cands:
            continue
        cands.sort(key=lambda N: y0 - N[4])
        q = cands[0][5]
        if q in ans:
            warns.append(f"座標法：題 {q} 重複配對（{ans[q]} / {letter}）")
        ans[q] = letter
    return ans, warns


def _sequential_answers(lines: List[str], n: int) -> Dict[int, str]:
    toks: List[str] = []
    started = False
    for l in lines:
        if "標準答案" in l:
            started = True
            continue
        if not started:
            continue
        if re.match(r"^備[\s　]*註", l):
            break
        m = LETTER_TOKEN_RE.match(l)
        if m:
            toks.append(norm_letter(m.group(1)))
    if len(toks) != n:
        return {}
    return {i + 1: t for i, t in enumerate(toks)}


def parse_answer_pdf(path: str) -> AnswerSheet:
    doc = fitz.open(path)
    text = "\n".join(p.get_text() for p in doc)
    lines = [l.strip() for l in text.split("\n")]
    m = re.search(r"題\s*數[:：]\s*(\d+)\s*題", text)
    if not m:
        raise ValueError(f"{path}: 找不到「題數」")
    n = int(m.group(1))
    is_corr = "標準答案更正" in text or "更正答案" in text[:600]
    pc = re.search(r"試題代號[:：]\s*(\d+)", text)

    pos, warns = _positional_answers(doc, n)
    seq = _sequential_answers(lines, n)
    doc.close()

    if len(pos) == n:
        answers = pos
        if seq and any(seq[q] != pos[q] for q in range(1, n + 1)):
            diff = [q for q in range(1, n + 1) if seq[q] != pos[q]]
            warns.append(f"座標法與文字流順序不一致（題 {diff}），採座標法")
    elif seq:
        answers = seq
        warns.append(f"座標法只配到 {len(pos)}/{n} 題，改用文字流順序")
    else:
        raise ValueError(f"{path}: 答案表解析失敗（座標法 {len(pos)}/{n}，文字流 {len(seq)}/{n}）")

    # 備註：最後一個「備　　註：」之後、去掉表格殘留（題號／答案／數字）
    note = ""
    idx = [mm.start() for mm in re.finditer(r"備[\s　]*註[:：]", text)]
    if idx:
        tail = re.sub(r"備[\s　]*註[:：]", "", text[idx[-1]:], count=1)
        keep = [l.strip() for l in tail.split("\n") if l.strip() and not re.fullmatch(r"題[號序]|答案|\d{1,3}", l.strip())]
        note = "".join(keep)
    corrections = parse_correction_note(note) if note else {}

    return AnswerSheet(path=path, n=n, answers=answers, corrections=corrections,
                       is_correction_sheet=is_corr, note=note, warnings=warns,
                       paper_code=pc.group(1) if pc else "")


def merge_answers(std: AnswerSheet, fix: Optional[AnswerSheet]) -> Tuple[Dict[int, str], List[str]]:
    """標準答案 + 更正檔 -> 最終答案；回傳 (answers, warnings)。"""
    warns: List[str] = []
    final = dict(std.answers)
    for q, a in std.corrections.items():   # 標準答案檔本身帶備註（少見）
        final[q] = a
    if fix is None:
        for q, a in final.items():
            if a == "#":
                warns.append(f"題 {q} 標準答案為 # 但無更正檔")
        return final, warns
    if fix.n != std.n:
        warns.append(f"更正檔題數 {fix.n} 與標準答案 {std.n} 不同")
    for q, a in fix.answers.items():
        if a == "#":
            if q in fix.corrections:
                final[q] = fix.corrections[q]
            else:
                warns.append(f"題 {q} 更正檔標 # 但備註未解析到更正內容，answer 設為 #")
                final[q] = "#"
        else:
            if std.answers.get(q) != a:
                warns.append(f"題 {q} 更正檔答案 {a} 與標準答案 {std.answers.get(q)} 不同，採更正檔")
            final[q] = a
    for q, a in fix.corrections.items():
        if fix.answers.get(q) != "#":
            warns.append(f"題 {q} 備註有更正（{a}）但表格未標 #，仍套用")
            final[q] = a
    return final, warns


# ---------------------------------------------------------------------------
# 組裝
# ---------------------------------------------------------------------------
def build_bank(questions: List[dict], std: AnswerSheet, fix: Optional[AnswerSheet], *,
               year: int, session: int, subject: str, src: str,
               lenient: bool = False, label: str = "") -> Tuple[List[dict], List[str]]:
    answers, warns = merge_answers(std, fix)
    errors: List[str] = []
    if len(questions) != std.n:
        errors.append(f"題目數 {len(questions)} != 答案檔題數 {std.n}")
    for q in questions:
        if sorted(q["options"]) != ["A", "B", "C", "D"]:
            errors.append(f"題 {q['題號']} 選項不完整：{sorted(q['options'])}")
        if not q["question"]:
            errors.append(f"題 {q['題號']} 題幹為空")
        if q["題號"] not in answers:
            errors.append(f"題 {q['題號']} 沒有答案")
    if errors and not lenient:
        raise ValueError(f"{label}: " + "；".join(errors))
    warns.extend(errors)
    rows = []
    for q in questions:
        rows.append({
            "題號": q["題號"],
            "年度": year,
            "第幾次": session,
            "科目": subject,
            "question": q["question"],
            "options": {k: q["options"].get(k, "") for k in "ABCD"},
            "answer": answers.get(q["題號"], "#"),
            "src": src,
        })
    return rows, warns


SESSION_FILE_RE = re.compile(r"^(\d{3})-(\d)_Q\.pdf$")


def discover_sessions(raw_dir: str) -> List[Tuple[int, int]]:
    out = []
    for f in os.listdir(raw_dir):
        m = SESSION_FILE_RE.match(f)
        if m:
            out.append((int(m.group(1)), int(m.group(2))))
    return sorted(out)


def load_sources(raw_dir: str) -> Dict[str, dict]:
    p = os.path.join(raw_dir, "sources.json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        return {d["session"]: d for d in json.load(fh)}


def _rel(path: str, anchor: Optional[str]) -> str:
    p = os.path.relpath(path, os.path.dirname(os.path.abspath(anchor))) if anchor else path
    return p.replace(os.sep, "/")


def main(argv: Optional[List[str]] = None) -> int:
    global KEEP_CYRILLIC
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", help="資料夾：含 {年度}-{次}_Q.pdf / _A.pdf / _M.pdf（與選用的 sources.json）")
    ap.add_argument("--q"); ap.add_argument("--a"); ap.add_argument("--m")
    ap.add_argument("--year", type=int); ap.add_argument("--session", type=int)
    ap.add_argument("--src", default="", help="單一場次模式：試題 PDF URL")
    ap.add_argument("--out", required=True, help="輸出 JSON（可含 {first}/{last} 佔位）")
    ap.add_argument("--manifest", help="另外輸出 manifest.json（列出每個 PDF 的 url/檔名/bytes/代號/解析題數）")
    ap.add_argument("--subject", help="強制指定「科目」欄字串")
    ap.add_argument("--full-subject", action="store_true", help="「科目」欄用 PDF 標頭完整科目名稱")
    ap.add_argument("--keep-cyrillic", action="store_true", help="不要把 U+045B–U+0464 轉成圈號 ①–⑩")
    ap.add_argument("--lenient", action="store_true", help="驗證失敗只警告不中止")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    KEEP_CYRILLIC = args.keep_cyrillic

    def log(*a):
        if not args.quiet:
            print(*a, file=sys.stderr)

    jobs: List[dict] = []
    if args.raw:
        sources = load_sources(args.raw)
        for year, ses in discover_sessions(args.raw):
            key = f"{year}-{ses}"
            info = sources.get(key, {})
            mpath = os.path.join(args.raw, f"{key}_M.pdf")
            jobs.append({
                "year": year, "session": ses, "key": key,
                "q": os.path.join(args.raw, f"{key}_Q.pdf"),
                "a": os.path.join(args.raw, f"{key}_A.pdf"),
                "m": mpath if os.path.exists(mpath) else None,
                "src": info.get("files", {}).get("Q", {}).get("url", ""),
                "info": info,
            })
    elif args.q and args.a and args.year and args.session:
        jobs.append({"year": args.year, "session": args.session, "key": f"{args.year}-{args.session}",
                     "q": args.q, "a": args.a, "m": args.m, "src": args.src, "info": {}})
    else:
        ap.error("請給 --raw，或 --q/--a/--year/--session")

    bank: List[dict] = []
    manifest_files: List[dict] = []
    summary: List[dict] = []
    failed = 0
    for job in jobs:
        try:
            meta, qs = parse_question_pdf(job["q"])
            std = parse_answer_pdf(job["a"])
            fix = parse_answer_pdf(job["m"]) if job["m"] else None
            subject = args.subject or (meta.subject_full if args.full_subject else meta.subject_short) or "?"
            rows, warns = build_bank(qs, std, fix, year=job["year"], session=job["session"],
                                     subject=subject, src=job["src"], lenient=args.lenient, label=job["key"])
        except Exception as e:  # noqa: BLE001
            failed += 1
            log(f"[FAIL] {job['key']}: {e}")
            continue
        bank.extend(rows)
        n_multi = sum(1 for r in rows if r["answer"] not in ("A", "B", "C", "D"))
        n_img = sum(1 for r in rows if IMAGE_OPTION in r["options"].values())
        log(f"[OK] {job['key']} 題數 {len(rows)}/{std.n} 更正 {len(fix.corrections) if fix else 0} "
            f"非單一答案 {n_multi} 圖片選項題 {n_img} 代號 {meta.paper_code} 科目 {subject}")
        for w in meta.warnings + warns + std.warnings + (fix.warnings if fix else []):
            log(f"      [warn] {job['key']}: {w}")
        summary.append({"session": job["key"], "questions": len(rows), "paper_code": meta.paper_code,
                        "category": meta.category, "subject": meta.subject_full,
                        "char_reconstructed_pages": meta.flagged_pages,
                        "corrections": (fix.corrections if fix else {}), "correction_note": (fix.note if fix else "")})
        info = job["info"]
        for t, path, cnt in (("Q", job["q"], len(qs)), ("A", job["a"], len(std.answers)),
                             ("M", job["m"], len(fix.answers) if fix else 0)):
            if not path:
                continue
            finfo = info.get("files", {}).get(t, {})
            manifest_files.append({
                "session": job["key"], "type": t,
                "url": finfo.get("url", job["src"] if t == "Q" else ""),
                "file": os.path.basename(path),  # 只留檔名：原始 PDF 不進 repo，相對路徑沒有意義
                "bytes": os.path.getsize(path),
                "exam_code": info.get("exam_code", ""),
                "exam_title": info.get("exam_title", ""),
                "category_code": info.get("category_code", ""),
                "category": meta.category,
                "subject_code": info.get("subject_code", ""),
                "subject": meta.subject_full,
                "paper_code": meta.paper_code,
                "count_parsed": cnt,
                "correction_note": (fix.note if (t == "M" and fix) else ""),
            })

    if not bank:
        log("沒有任何題目被解析")
        return 1
    years = sorted({r["年度"] for r in bank})
    out_path = args.out.replace("{first}", str(years[0])).replace("{last}", str(years[-1]))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(bank, fh, ensure_ascii=False, indent=1)
    log(f"寫出 {out_path}：{len(bank)} 題，{len(summary)} 場次，失敗 {failed}")

    if args.manifest:
        os.makedirs(os.path.dirname(os.path.abspath(args.manifest)), exist_ok=True)
        man = {
            "generated_by": "scripts/parse_moex_exam.py",
            "source": "考選部考畢試題查詢平臺 https://wwwq.moex.gov.tw/exam/wFrmExamQandASearch.aspx",
            "questions_json": _rel(out_path, args.manifest),
            "total_questions": len(bank),
            "sessions": summary,
            "files": manifest_files,
        }
        with open(args.manifest, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(man, fh, ensure_ascii=False, indent=1)
        log(f"寫出 {args.manifest}：{len(manifest_files)} 個檔案")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

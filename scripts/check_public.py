# -*- coding: utf-8 -*-
"""公開 kit 推上 GitHub 前的檢查：換行、本機路徑、電子郵件、第三人真名、他人投影片引句、圖檔與大檔。

用法：python check_public.py [--kit <kit 根目錄>] [--quiet]
檢查（FAIL 的結束碼為 1）：
  1. 文字檔含 CR（\\r）：Workflow 工具會拒絕含 CR 的腳本；kit 一律 LF
  2. 本機絕對路徑：Windows 與 macOS 的使用者資料夾、雲端硬碟組織資料夾、/home/<帳號>（/home/user 除外）、.claude/plans 等；
     文件裡示範用的 D:/localcode/…、C:/Program Files/…、/usr/share/… 不算
  3. 電子郵件
  4. 舊模型名（工作流一律 model: 'opus'；字串拆開寫，本檔才不會自己命中）
  5. 第三人真名：讀私人 repo 的 <語料>/pseudonyms.tsv（每行「真名<TAB>代稱」）；沒有這個檔就略過並提醒
  6. 他人投影片引句：「原文」（other_* #n）；另讀 <語料>/other_segments.tsv（每行「代號<TAB>起-迄張號」，
     整份他人的檔寫 1-999）列出的他人段落
  7. 圖檔、PDF、PPTX、Office 檔（kit 不放任何課程內容），以及超過 50 MB 的檔
.gitignore 排除的資料夾（_build/、__pycache__/、style/corpus/、examples/*/成品/）不檢查。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import KIT, corpus_dir  # noqa: E402

TEXT_EXT = {".md", ".py", ".js", ".json", ".yaml", ".yml", ".sh", ".txt", ".tsv", ".gitignore", ".gitattributes"}
BIN_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".emf", ".wmf", ".svg",
           ".pdf", ".pptx", ".ppt", ".docx", ".doc", ".xlsx", ".xls", ".zip", ".7z"}
SKIP_DIRS = {".git", "_build", "__pycache__", "node_modules"}


def ignored(rel):
    """kit 的 .gitignore 排除、不會進 repo 的位置。"""
    return rel.startswith("style/corpus/") or "/成品/" in rel or "/_archive/render/" in rel
PATH_BAD = [
    (re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+(?!<)[^\\/\s`'\"]+", re.I), "Windows 使用者資料夾路徑"),
    (re.compile("One" + "Drive" + r"\s*-", re.I), "雲端硬碟組織資料夾"),
    (re.compile(r"/home/(?!user\b)[a-z_][a-z0-9_-]*/"), "Linux 使用者資料夾路徑"),
    (re.compile(r"\.claude[\\/]+plans"), "本機計畫檔路徑"),
    (re.compile(r"/Users/[A-Za-z]"), "macOS 使用者資料夾路徑"),
]
OLD_MODEL = re.compile("fab" + "le", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
EMAIL_OK = ()  # 允許出現的電子郵件（目前沒有）
QUOTE = re.compile(r"「([^」]{2,300})」\s*[（(]\s*([0-9A-Za-z_一-鿿\-]+)\s*#\s*(\d+)\s*[）)]")


def load_tsv(name):
    p = os.path.join(corpus_dir(), name)
    if not os.path.exists(p):
        return None
    rows = []
    for ln in open(p, encoding="utf-8"):
        ln = ln.rstrip("\r\n")
        if ln.strip() and not ln.startswith("#") and "\t" in ln:
            rows.append(tuple(x.strip() for x in ln.split("\t", 1)))
    return rows


def walk(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            p = os.path.join(d, f)
            rel = os.path.relpath(p, root).replace("\\", "/")
            yield p, rel


def main():
    ap = argparse.ArgumentParser(description="公開 kit 推上 GitHub 前的隱私與格式檢查")
    ap.add_argument("--kit", default=KIT)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    names = load_tsv("pseudonyms.tsv")
    others = load_tsv("other_segments.tsv") or []
    ranges = {}
    for code, rg in others:
        lo, _, hi = rg.partition("-")
        ranges[code] = (int(lo or 1), int(hi or 999))
    fails, notes = [], []
    if names is None:
        notes.append(f"找不到 {os.path.join(corpus_dir(), 'pseudonyms.tsv')}：第三人真名未檢查（需要私人 repo）")
    nfiles = 0
    for p, rel in walk(a.kit):
        ext = os.path.splitext(p)[1].lower() or os.path.basename(p)
        size = os.path.getsize(p)
        if size > 50 * 1024 * 1024:
            fails.append(f"{rel}：{size / 1e6:.0f} MB（GitHub 50 MB 警告、100 MB 上限）")
        if ignored(rel):
            continue
        if ext in BIN_EXT:
            fails.append(f"{rel}：kit 不放圖檔、PDF 或 Office 檔")
            continue
        if ext not in TEXT_EXT:
            continue
        nfiles += 1
        raw = open(p, "rb").read()
        ncr = raw.count(b"\r")
        if ncr:
            fails.append(f"{rel}：含 CR 字元 {ncr} 個，要轉成 LF")
        try:
            txt = raw.decode("utf-8")
        except UnicodeDecodeError:
            fails.append(f"{rel}：不是 UTF-8")
            continue
        if rel == "scripts/check_public.py":
            continue
        for i, line in enumerate(txt.split("\n"), 1):
            for rx, what in PATH_BAD:
                m = rx.search(line)
                if m:
                    fails.append(f"{rel}:{i}：{what}「{m.group(0)[:60]}」")
            for m in EMAIL.finditer(line):
                if m.group(0).lower() not in EMAIL_OK:
                    fails.append(f"{rel}:{i}：電子郵件「{m.group(0)}」")
            if OLD_MODEL.search(line):
                fails.append(f"{rel}:{i}：舊模型名（{OLD_MODEL.pattern}）")
            for real, alias in names or []:
                if real in line:
                    fails.append(f"{rel}:{i}：第三人真名「{real}」→ 改成「{alias}」")
            for m in QUOTE.finditer(line):
                code, n = m.group(2), int(m.group(3))
                lohi = ranges.get(code)
                if code.startswith("other_") or (lohi and lohi[0] <= n <= lohi[1]):
                    fails.append(f"{rel}:{i}：他人投影片引句（{code} #{n}）→ 換成〔他人投影片引句，公開版省略；完整版在私人素材庫 style_evidence〕")
    if not a.quiet:
        for n in notes:
            print("[note]", n)
    for f in fails:
        print("[FAIL]", f)
    print(f"===== check_public：{nfiles} 個文字檔，FAIL {len(fails)} =====")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

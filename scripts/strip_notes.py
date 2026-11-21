# -*- coding: utf-8 -*-
"""查 PPTX 有沒有備忘稿（PowerPoint 的講者備註欄），或把備忘稿全部清掉另存新檔。

教師 2026-11-21：「備忘稿全清掉 我不用那個東西 也不要讓學生看到」。交件的 PPTX 不放備忘稿（AGENTS.md 硬規則 18）；
gen_pptx.py、gen_lab_pptx.py 預設已經不寫。這支給三種檔用：舊版工具產的檔、課程自己的程式產的檔、教師自己改過要發給學生的檔。

用法：
  python strip_notes.py --check <檔.pptx> [<檔.pptx> …]
      只看、不寫：每份印出張數、有字的備忘稿張數與字數。任何一份有字就結束碼 1。
  python strip_notes.py <來源.pptx> --out <新檔.pptx>
      清掉全部備忘稿頁，寫成新檔；來源檔不動。新檔已經存在就停（不覆寫）。

做法：直接改 zip，不經 python-pptx 重存，所以投影片、版型、圖片、字型每個零件都和來源檔逐位元相同；只有三種東西不一樣：
  1. ppt/notesSlides/ 底下的備忘稿頁整個拿掉（連同只有它們引用的零件，例如貼在備忘稿頁裡的圖）；
  2. 每張投影片的關聯檔（ppt/slides/_rels/slideN.xml.rels）拿掉指向備忘稿頁的那一條；
  3. [Content_Types].xml 拿掉備忘稿頁的登記。
備忘稿母片（ppt/notesMasters/）留著：它是空白的版型，沒有內容；之後教師要自己加備忘稿也還能加。
寫完自己驗一次：零件逐個比對 CRC、zip 完整、用 python-pptx 開得起來、張數相同、沒有任何備忘稿頁。

輸出不要直接寫進雲端同步資料夾（OneDrive、Dropbox）：在外面做好、驗完，再用最終檔名一次複製進去。
"""
import argparse
import html
import os
import posixpath
import re
import sys
import zipfile

SLIDE = re.compile(r"ppt/slides/slide\d+\.xml$")
SLIDE_RELS = re.compile(r"ppt/slides/_rels/slide\d+\.xml\.rels$")
NOTE = re.compile(r"ppt/notesSlides/notesSlide\d+\.xml$")
NOTES_DIR = "ppt/notesSlides/"
CLOUD = ("/CloudStorage/", "OneDrive", "Dropbox")


def note_text(xml):
    """一頁備忘稿裡的字（頁碼欄位不算）。"""
    x = re.sub(r"<a:fld\b.*?</a:fld>", "", xml, flags=re.S)
    return "".join(html.unescape(t) for t in re.findall(r"<a:t>([^<]*)</a:t>", x)).strip()


def stats(path):
    """{slides, parts（備忘稿頁數）, with_text（有字的頁數）, chars, first（第一頁有字的備忘稿的開頭）}"""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        out = {"slides": sum(1 for n in names if SLIDE.match(n)), "parts": 0, "with_text": 0, "chars": 0, "first": ""}
        for n in names:
            if not NOTE.match(n):
                continue
            out["parts"] += 1
            t = note_text(z.read(n).decode("utf-8", "replace"))
            if t:
                out["with_text"] += 1
                out["chars"] += len(t)
                out["first"] = out["first"] or t[:40].replace("\n", " ")
    return out


def _targets(z, rels_name):
    """這個關聯檔指到的零件（package 內的路徑；外部連結不算）。"""
    base = posixpath.dirname(posixpath.dirname(rels_name))
    out = set()
    for m in re.finditer(rb"<Relationship\b[^>]*>", z.read(rels_name)):
        el = m.group(0)
        if b'TargetMode="External"' in el:
            continue
        t = re.search(rb'Target="([^"]*)"', el)
        if not t:
            continue
        t = t.group(1).decode("utf-8")
        out.add(t.lstrip("/") if t.startswith("/") else posixpath.normpath(posixpath.join(base, t)))
    return out


def strip(src, dst):
    """把 src 的備忘稿全部拿掉寫到 dst；回傳 (拿掉的備忘稿頁數, 一起拿掉的其他零件, 改過的零件)。"""
    with zipfile.ZipFile(src) as zin:
        names = zin.namelist()
        drop = {n for n in names if n.startswith(NOTES_DIR)}
        from_notes, from_rest = set(), set()
        for n in names:
            if n.endswith(".rels"):
                (from_notes if n in drop else from_rest).update(_targets(zin, n))
        extra = {t for t in from_notes - from_rest if t in names and not t.startswith(NOTES_DIR)}
        extra |= {r for r in (posixpath.join(posixpath.dirname(t), "_rels", posixpath.basename(t) + ".rels") for t in extra)
                  if r in names}
        drop |= extra
        changed = []
        with zipfile.ZipFile(dst, "x") as zout:
            for info in zin.infolist():
                n = info.filename
                if n in drop:
                    continue
                data = zin.read(n)
                new = data
                if n == "[Content_Types].xml":
                    for d in drop:
                        new = re.sub(rb"<Override\b[^>]*PartName=\"/" + re.escape(d.encode("utf-8")) + rb"\"[^>]*/>", b"", new)
                elif SLIDE_RELS.match(n):
                    new = re.sub(rb"<Relationship\b[^>]*Type=\"[^\"]*/notesSlide\"[^>]*/>", b"", new)
                if new != data:
                    changed.append(n)
                zi = zipfile.ZipInfo(n, date_time=info.date_time)
                zi.compress_type = info.compress_type
                zi.external_attr = info.external_attr
                zi.create_system = info.create_system
                zout.writestr(zi, new)
    return sum(1 for n in drop if NOTE.match(n)), sorted(extra), changed


def verify(src, dst, changed):
    """清完的檔：zip 完整、沒有備忘稿頁、其他零件和來源檔相同、python-pptx 開得起來且張數相同。回傳問題清單。"""
    bad = []
    with zipfile.ZipFile(src) as a, zipfile.ZipFile(dst) as b:
        if b.testzip():
            bad.append(f"zip 壞了：{b.testzip()}")
        crc_a = {i.filename: i.CRC for i in a.infolist()}
        crc_b = {i.filename: i.CRC for i in b.infolist()}
        if any(n.startswith(NOTES_DIR) for n in crc_b):
            bad.append("還有備忘稿頁")
        for n, c in crc_b.items():
            if n not in changed and crc_a.get(n) != c:
                bad.append(f"零件和來源檔不同：{n}")
        na, nb = sum(1 for n in crc_a if SLIDE.match(n)), sum(1 for n in crc_b if SLIDE.match(n))
        if na != nb:
            bad.append(f"張數 {na} → {nb}")
    try:
        from pptx import Presentation
        prs = Presentation(dst)
        if len(prs.slides) != nb:
            bad.append(f"python-pptx 讀到 {len(prs.slides)} 張，zip 裡 {nb} 張")
        if any(s.has_notes_slide for s in prs.slides):
            bad.append("python-pptx 還讀得到備忘稿頁")
    except Exception as e:  # 開不起來就是壞檔
        bad.append(f"python-pptx 開不起來：{e!r}")
    return bad


def main():
    ap = argparse.ArgumentParser(description="查 PPTX 的備忘稿，或清掉另存新檔")
    ap.add_argument("pptx", nargs="+")
    ap.add_argument("--check", action="store_true", help="只看、不寫；有字就結束碼 1")
    ap.add_argument("--out", help="清掉備忘稿後的新檔（只能給一份來源檔）")
    a = ap.parse_args()
    if a.check or not a.out:
        if not a.check:
            ap.error("要清掉就給 --out <新檔.pptx>；只看就加 --check")
        hit = 0
        for p in a.pptx:
            st = stats(p)
            hit += bool(st["with_text"])
            tail = f"｜開頭：{st['first']}" if st["first"] else ""
            print(f"{'[有]' if st['with_text'] else '[無]'} {os.path.basename(p)}｜{st['slides']} 張｜"
                  f"備忘稿有字 {st['with_text']} 張、{st['chars']} 字{tail}")
        print(f"===== {len(a.pptx)} 份，有備忘稿的 {hit} 份 =====")
        return 1 if hit else 0
    if len(a.pptx) != 1:
        ap.error("--out 一次只能清一份")
    src, dst = a.pptx[0], a.out
    if os.path.exists(dst):
        print(f"[停] 新檔已經存在，不覆寫：{dst}")
        return 2
    if any(k in os.path.abspath(dst) for k in CLOUD):
        print(f"[停] 不直接寫進雲端同步資料夾：{dst}\n     在外面做好、驗完，再用最終檔名一次複製進去。")
        return 2
    before = stats(src)
    k, extra, changed = strip(src, dst)
    bad = verify(src, dst, changed)
    after = stats(dst)
    print(f"{os.path.basename(src)}：{before['slides']} 張，備忘稿有字 {before['with_text']} 張、{before['chars']} 字")
    print(f"  拿掉備忘稿頁 {k} 頁" + (f"、只被它們引用的零件 {len(extra)} 個（{', '.join(extra[:5])}）" if extra else "")
          + f"；改了 {len(changed)} 個關聯與登記檔，其他零件和來源檔逐位元相同")
    print(f"  -> {dst}（{os.path.getsize(dst) / 1e6:.1f} MB；備忘稿有字 {after['with_text']} 張）")
    for m in bad:
        print("  [RED] " + m)
    if bad:
        print("  驗證沒過：這份新檔不要交。")
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

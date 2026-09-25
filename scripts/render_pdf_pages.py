# -*- coding: utf-8 -*-
"""把教科書掃描 PDF 逐頁轉成圖檔（整頁；要的話加上下半頁）並用 Tesseract 做 OCR。

用途：Robbins 掃描檔沒有可用文字層（immune 的只有浮水印；lung 的是 PUA 編碼），
代理讀頁時需要「清楚的圖」＋「OCR 文字」兩者對照。

輸出（每頁；副檔名依 --format，預設 jpg）：
  p{PDF頁:02d}_{印刷頁}.jpg     整頁（robbins_crop.py 以 200dpi 的整頁找圖說）
  p{PDF頁:02d}_{印刷頁}_a.jpg   上半頁（含 4% 重疊；只有加 --halves 才輸出）
  p{PDF頁:02d}_{印刷頁}_b.jpg   下半頁
  p{PDF頁:02d}_{印刷頁}.txt     OCR 文字（eng）
  p{PDF頁:02d}_{印刷頁}.tsv     OCR 字詞座標（切圖用：找 "Fig." 圖說位置）

用法：
  python render_pdf_pages.py <pdf> <out_dir> --offset 166 [--dpi 200] [--pages 1-69] [--format png] [--halves] [--no-ocr]
  python render_pdf_pages.py --course immune [--pages 1-5]
    --offset   印刷頁 = PDF 頁 + offset（immune ch.6 為 166）
    --course   從 course.yaml 的 textbook.pdf／textbook.pages_dir／textbook.page_offset 補齊沒給的參數
    --format   jpg（預設；教材庫存頁一律用 jpg）或 png（約 3 倍大）；--quality 為 jpg 品質（預設 90）
    --halves   另出上下半頁 _a／_b（預設不出；工作流沒有半頁時會用 .tsv 字詞座標裁切放大）。--no-halves 為舊參數，等同預設
Tesseract 位置：環境變數 TESSERACT → PATH 上的 tesseract → C:\\Program Files\\Tesseract-OCR\\tesseract.exe。
找不到就報錯；只要圖不要 OCR 時加 --no-ocr。
"""
import argparse
import os
import shutil
import subprocess
import sys

import fitz  # PyMuPDF

WIN_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def find_tesseract():
    env = os.environ.get("TESSERACT", "").strip()
    if env and os.path.isfile(env):
        return env
    exe = shutil.which("tesseract")
    if exe:
        return exe
    if os.path.isfile(WIN_TESSERACT):
        return WIN_TESSERACT
    return None


def parse_range(s, n):
    if not s:
        return list(range(1, n + 1))
    out = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return [p for p in out if 1 <= p <= n]


def ocr(tess, img_path, out_base):
    for fmt in ("txt", "tsv"):
        args = [tess, img_path, out_base, "--psm", "3", "-l", "eng"]
        if fmt == "tsv":
            args.append("tsv")
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def save_pix(pix, path, fmt, quality):
    if fmt == "jpg":
        pix.save(path, jpg_quality=quality)
    else:
        pix.save(path)


def from_course(a):
    """--course：沒給的 pdf／out_dir／offset 從 course.yaml 的 textbook 補。"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from common import load_course
    c = load_course(a.course)
    tb = c.get("textbook") or {}
    a.pdf = a.pdf or c.textbook_path("pdf")
    a.out_dir = a.out_dir or c.textbook_path("pages_dir")
    if a.offset is None and tb.get("page_offset") is not None:
        a.offset = int(tb["page_offset"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", nargs="?")
    ap.add_argument("out_dir", nargs="?")
    ap.add_argument("--course", default=None)
    ap.add_argument("--offset", type=int, default=None)
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--pages")
    ap.add_argument("--format", choices=["png", "jpg"], default="jpg")
    ap.add_argument("--quality", type=int, default=90)
    ap.add_argument("--halves", action="store_true", help="另出上下半頁 _a／_b")
    ap.add_argument("--no-halves", action="store_true", help="舊參數，等同預設（不出半頁）")
    ap.add_argument("--no-ocr", action="store_true")
    a = ap.parse_args()
    if a.course:
        from_course(a)
    miss = [k for k in ("pdf", "out_dir", "offset") if getattr(a, k) is None]
    if miss:
        ap.error("缺少 " + "、".join(miss) + "（直接給，或用 --course 從 course.yaml 的 textbook 讀）")
    if not os.path.isfile(a.pdf):
        ap.error(f"找不到 PDF：{a.pdf}")
    tess = None
    if not a.no_ocr:
        tess = find_tesseract()
        if not tess:
            sys.exit("找不到 Tesseract。Ubuntu：apt-get install -y tesseract-ocr；"
                     "Windows：安裝 UB Mannheim 版到 C:\\Program Files\\Tesseract-OCR，"
                     "或設環境變數 TESSERACT=<tesseract 執行檔>；只要圖不要 OCR 就加 --no-ocr。")

    os.makedirs(a.out_dir, exist_ok=True)
    ext = "." + a.format
    doc = fitz.open(a.pdf)
    for pno in parse_range(a.pages, doc.page_count):
        page = doc[pno - 1]
        stem = f"p{pno:02d}_{pno + a.offset}"
        full = os.path.join(a.out_dir, stem + ext)
        save_pix(page.get_pixmap(dpi=a.dpi), full, a.format, a.quality)
        if a.halves and not a.no_halves:
            r = page.rect
            ov = r.height * 0.04
            for tag, clip in (("a", fitz.Rect(0, 0, r.width, r.height / 2 + ov)),
                              ("b", fitz.Rect(0, r.height / 2 - ov, r.width, r.height))):
                save_pix(page.get_pixmap(dpi=a.dpi, clip=clip), os.path.join(a.out_dir, f"{stem}_{tag}{ext}"),
                         a.format, a.quality)
        if tess:
            ocr(tess, full, os.path.join(a.out_dir, stem))
        print(stem, flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

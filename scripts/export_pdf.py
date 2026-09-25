# -*- coding: utf-8 -*-
r"""把 pptx 轉成 PDF（Windows：PowerPoint COM；否則 LibreOffice），再用 PyMuPDF 出縮圖拼板與逐張 PNG，供目視檢查。

用法：python export_pdf.py <in.pptx> [--pdf <out.pdf>] [--sheets <資料夾>] [--pngs <資料夾>] [--dpi 60]
                          [--engine auto|powerpoint|libreoffice] [--timeout 900]
  --pdf     PDF 輸出路徑（預設同檔名 .pdf）
  --sheets  每 12 張拼一張（4×3）的縮圖拼板，檔名 sheet_01.png…（附張號）
  --pngs    逐張 PNG（slide_001.png…），給審查代理看版面
  --engine  auto（預設；也可用環境變數 SLIDEKIT_PDF_ENGINE）：Windows 先試 PowerPoint，失敗或非 Windows 改用 LibreOffice
            powerpoint：只用 PowerPoint；libreoffice：只用 LibreOffice（在 Windows 上模擬雲端環境）
引擎：
  PowerPoint  用 PowerShell 的 COM 驅動（不需 pywin32）。能開檔且匯出成功＝PowerPoint 沒有跳修復提示（修復提示會讓 COM 呼叫失敗）。
  LibreOffice soffice --headless --convert-to pdf；執行檔找法：環境變數 SOFFICE → PATH 上的 soffice／libreoffice
              → C:\Program Files\LibreOffice\program\soffice.exe。每次用獨立的暫存設定檔，不會卡在已開啟的 LibreOffice。
              LibreOffice 沒有微軟正黑體，會用替代字型（雲端是 Noto Sans CJK TC），換行與 PowerPoint 略有差異，只供目視檢查。
兩種都不可用時，錯誤訊息列出每個引擎失敗的原因，結束碼 2。
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import fitz

ENGINES = ("auto", "powerpoint", "libreoffice")
SOFFICE_PATHS = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice", "/usr/lib/libreoffice/program/soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


def find_soffice():
    env = os.environ.get("SOFFICE", "").strip()
    if env and os.path.isfile(env):
        return env
    for name in ("soffice", "libreoffice"):
        exe = shutil.which(name)
        if exe:
            return exe
    return next((p for p in SOFFICE_PATHS if os.path.isfile(p)), None)


def pdf_powerpoint(pptx, pdf, timeout=900):
    """用 PowerShell 的 COM 驅動 PowerPoint（不需安裝 pywin32）。"""
    if os.name != "nt":
        raise RuntimeError("不是 Windows，沒有 PowerPoint")
    src = os.path.abspath(pptx).replace("'", "''")
    dst = os.path.abspath(pdf).replace("'", "''")
    ps = ("$ErrorActionPreference='Stop';"
          "$app = New-Object -ComObject PowerPoint.Application;"
          f"$p = $app.Presentations.Open('{src}', $true, $false, $false);"
          f"$p.SaveAs('{dst}', 32); $p.Close(); $app.Quit()")
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if r.returncode != 0 or not os.path.exists(pdf):
        raise RuntimeError("PowerPoint 匯出失敗：" + ((r.stderr or r.stdout).strip()[-800:] or f"結束碼 {r.returncode}"))


def pdf_libreoffice(pptx, pdf, timeout=900):
    """soffice --headless --convert-to pdf；輸出先寫到暫存資料夾再搬到 pdf。"""
    exe = find_soffice()
    if not exe:
        raise RuntimeError("找不到 LibreOffice（soffice）。Ubuntu：apt-get install -y libreoffice-impress；"
                           "Windows：安裝 LibreOffice，或設環境變數 SOFFICE=<soffice 執行檔>")
    outdir = tempfile.mkdtemp(prefix="slidekit_lo_out_")
    profile = tempfile.mkdtemp(prefix="slidekit_lo_profile_")
    try:
        cmd = [exe, "-env:UserInstallation=" + pathlib.Path(profile).as_uri(), "--headless", "--norestore",
               "--nolockcheck", "--convert-to", "pdf", "--outdir", outdir, os.path.abspath(pptx)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"LibreOffice 超過 {timeout} 秒沒有完成（大檔可加 --timeout）")
        made = os.path.join(outdir, os.path.splitext(os.path.basename(pptx))[0] + ".pdf")
        if not os.path.exists(made):
            raise RuntimeError(f"LibreOffice 匯出失敗（{exe}，結束碼 {r.returncode}）："
                               + ((r.stderr or r.stdout).strip()[-800:] or "沒有輸出檔"))
        dst = os.path.abspath(pdf)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(made, dst)
    finally:
        shutil.rmtree(outdir, ignore_errors=True)
        shutil.rmtree(profile, ignore_errors=True)


def to_pdf(pptx, pdf, engine=None, timeout=900):
    """回傳實際使用的引擎名稱；都失敗就 raise RuntimeError（訊息列出每個引擎的原因）。"""
    engine = (engine or os.environ.get("SLIDEKIT_PDF_ENGINE") or "auto").strip().lower()
    if engine not in ENGINES:
        raise RuntimeError(f"未知的引擎 {engine!r}（可用：{', '.join(ENGINES)}）")
    if not os.path.isfile(pptx):
        raise RuntimeError(f"找不到 pptx：{pptx}")
    order = {"auto": ["powerpoint", "libreoffice"] if os.name == "nt" else ["libreoffice"],
             "powerpoint": ["powerpoint"], "libreoffice": ["libreoffice"]}[engine]
    errs = []
    for eng in order:
        try:
            (pdf_powerpoint if eng == "powerpoint" else pdf_libreoffice)(pptx, pdf, timeout)
            return eng
        except (RuntimeError, OSError, subprocess.SubprocessError) as e:
            errs.append(f"{eng}：{e}")
    raise RuntimeError("PDF 匯出失敗（engine=" + engine + "）：\n  " + "\n  ".join(errs))


def sheets(pdf, outdir, dpi=60, cols=4, rows=3):
    os.makedirs(outdir, exist_ok=True)
    d = fitz.open(pdf)
    per = cols * rows
    for k in range(0, d.page_count, per):
        pix0 = d[0].get_pixmap(dpi=dpi)
        W, H = pix0.width, pix0.height
        lab = 26
        sheet = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, cols * W, rows * (H + lab)), 0)
        sheet.clear_with(255)
        for i in range(per):
            n = k + i
            if n >= d.page_count:
                break
            pix = d[n].get_pixmap(dpi=dpi)
            x, y = (i % cols) * W, (i // cols) * (H + lab) + lab
            pix.set_origin(x, y)
            sheet.copy(pix, pix.irect)
        out = os.path.join(outdir, f"sheet_{k // per + 1:02d}.png")
        sheet.save(out)
        # 張號標籤
        doc = fitz.open()
        img = fitz.open(out)
        page = doc.new_page(width=sheet.width, height=sheet.height)
        page.insert_image(page.rect, filename=out)
        for i in range(per):
            n = k + i
            if n >= d.page_count:
                break
            x, y = (i % cols) * W, (i // cols) * (H + lab)
            page.insert_text((x + 6, y + 19), f"#{n + 1}", fontsize=18, color=(0.8, 0.1, 0.1))
        page.get_pixmap().save(out)
        img.close()
    return d.page_count


def pngs(pdf, outdir, dpi=100):
    os.makedirs(outdir, exist_ok=True)
    d = fitz.open(pdf)
    for i, p in enumerate(d, 1):
        p.get_pixmap(dpi=dpi).save(os.path.join(outdir, f"slide_{i:03d}.png"))
    return d.page_count


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx")
    ap.add_argument("--pdf")
    ap.add_argument("--sheets")
    ap.add_argument("--pngs")
    ap.add_argument("--dpi", type=int, default=60)
    ap.add_argument("--engine", choices=ENGINES, default=None)
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    pdf = a.pdf or os.path.splitext(a.pptx)[0] + ".pdf"
    try:
        used = to_pdf(a.pptx, pdf, a.engine, a.timeout)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(2)
    try:  # LibreOffice 的 tagged PDF 會讓 MuPDF 每頁印「No common ancestor in structure tree」，不影響出圖
        fitz.TOOLS.mupdf_display_errors(False)
    except Exception:
        pass
    print(f"PDF（{used}）:", pdf)
    if used == "libreoffice":
        print("  註：LibreOffice 以替代字型排版，換行與 PowerPoint 略有差異；版面定稿以 PowerPoint 為準")
    if a.sheets:
        print("sheets:", sheets(pdf, a.sheets, a.dpi), "pages")
    if a.pngs:
        print("pngs:", pngs(pdf, a.pngs), "pages")

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
  LibreOffice soffice --headless：pptx → odp → pdf。中間把 ODF 的 text-autospace 改成 none：LibreOffice 預設在中文與
              英文、數字之間自動加空隙，PowerPoint 沒有，不改會多斷行、看起來像溢出。執行檔找法：環境變數 SOFFICE
              → PATH 上的 soffice／libreoffice → 常見安裝位置（含 /Applications/LibreOffice.app）。每次用獨立的暫存設定檔，
              不會卡在已開啟的 LibreOffice。
              字型：有微軟正黑體時（Mac 跑一次 lo_fonts_mac.sh，把 PowerPoint 內建的字型放進 LibreOffice）斷行與 PowerPoint
              相同，表格列高比 PowerPoint 略高（偏保守）；沒有時用替代字型（雲端是 Noto Sans CJK TC），換行略有差異。
              2026-10-20 在教師的 Mac 對照 PowerPoint 算過的 lab-bj-a1（103 張）、uro-a3（118 張）、headneck-dent 框架圖。
兩種都不可用時，錯誤訊息列出每個引擎失敗的原因，結束碼 2。
"""
import argparse
import os
import pathlib
import re
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


def _no_autospace(odp):
    """LibreOffice 預設在中文與英文、數字之間自動加空隙（ODF style:text-autospace="ideograph-alpha"），
    PowerPoint 沒有這個行為，會讓 LibreOffice 多斷行、看起來像溢出。改成 none 後重新打包。"""
    import zipfile
    tmp = odp + ".tmp"
    n = 0
    with zipfile.ZipFile(odp) as zi, zipfile.ZipFile(tmp, "w") as zo:
        names = zi.namelist()
        order = (["mimetype"] if "mimetype" in names else []) + [x for x in names if x != "mimetype"]
        for name in order:
            data = zi.read(name)
            if name in ("styles.xml", "content.xml"):
                data, k = re.subn(rb'text-autospace="ideograph-alpha"', b'text-autospace="none"', data)
                n += k
            comp = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
            zo.writestr(zi.getinfo(name), data, compress_type=comp)
    os.replace(tmp, odp)
    return n


def _soffice_convert(exe, profile, fmt, src, outdir, timeout):
    cmd = [exe, "-env:UserInstallation=" + pathlib.Path(profile).as_uri(), "--headless", "--norestore",
           "--nolockcheck", "--convert-to", fmt, "--outdir", outdir, os.path.abspath(src)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"LibreOffice 超過 {timeout} 秒沒有完成（大檔可加 --timeout）")
    made = os.path.join(outdir, os.path.splitext(os.path.basename(src))[0] + "." + fmt)
    if not os.path.exists(made):
        raise RuntimeError(f"LibreOffice 匯出 {fmt} 失敗（{exe}，結束碼 {r.returncode}）："
                           + ((r.stderr or r.stdout).strip()[-800:] or "沒有輸出檔"))
    return made


def pdf_libreoffice(pptx, pdf, timeout=900):
    """soffice --headless：pptx → odp（關掉中英文之間自動加空隙）→ pdf；輸出先寫到暫存資料夾再搬到 pdf。"""
    exe = find_soffice()
    if not exe:
        raise RuntimeError("找不到 LibreOffice（soffice）。Ubuntu：apt-get install -y libreoffice-impress；"
                           "Mac：brew install --cask libreoffice；"
                           "Windows：安裝 LibreOffice，或設環境變數 SOFFICE=<soffice 執行檔>")
    outdir = tempfile.mkdtemp(prefix="slidekit_lo_out_")
    profile = tempfile.mkdtemp(prefix="slidekit_lo_profile_")
    try:
        work = os.path.join(outdir, "deck" + os.path.splitext(pptx)[1])
        shutil.copyfile(pptx, work)  # 檔名改成 ASCII，避免路徑與中文檔名的問題
        odp = _soffice_convert(exe, profile, "odp", work, outdir, timeout)
        _no_autospace(odp)
        made = _soffice_convert(exe, profile, "pdf", odp, outdir, timeout)
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
        names = {f[3].split("+")[-1] for p in fitz.open(pdf) for f in p.get_fonts()}
        if any("JhengHei" in n for n in names):
            print("  註：LibreOffice 用微軟正黑體排版，斷行與 PowerPoint 相同；表格列高比 PowerPoint 略高（偏保守），"
                  "表格剛好壓到出處行時以 PowerPoint 為準")
        else:
            print("  註：LibreOffice 沒有微軟正黑體，用替代字型排版，換行與 PowerPoint 略有差異；版面定稿以 PowerPoint 為準"
                  + ("（Mac：先跑 bash lo_fonts_mac.sh）" if sys.platform == "darwin" else ""))
    if a.sheets:
        print("sheets:", sheets(pdf, a.sheets, a.dpi), "pages")
    if a.pngs:
        print("pngs:", pngs(pdf, a.pngs), "pages")

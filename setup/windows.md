# Windows 本機安裝

工具包在 Windows 10／11 上開發與測試。雲端（Claude Code 雲端 session，Ubuntu）見 `cloud-setup.sh`。

## 需要的軟體

| 軟體 | 必要性 | 用途 |
|---|---|---|
| Python 3.10 以上（在 3.11 測過；python.org 安裝版或 Microsoft Store 版） | 必要 | 所有工具 |
| Git | 必要 | 取得兩個 repo |
| Microsoft PowerPoint | 建議 | `export_pdf.py` 用 PowerPoint 轉 PDF（版面最準）；gen_pptx 量字用系統的微軟正黑體 |
| Tesseract OCR | 做新章節時必要 | `render_pdf_pages.py` 做教科書掃描頁 OCR；Robbins 章節 PDF 是掃描檔，沒有 OCR 就沒有 `.txt`／`.tsv`，`robbins_crop.py` 找不到圖說、蒐集代理也少了頁面文字。只重產既有課程時用不到 |
| LibreOffice | 選用 | 沒有 PowerPoint 時 `export_pdf.py` 的替代引擎 |

微軟正黑體（`C:\Windows\Fonts\msjh.ttc`、`msjhbd.ttc`）是 Windows 內建字型，不必另外安裝。

## 資料夾擺法

兩個 repo 放在同一層，工具包會自動找到教材庫（不必設環境變數）：

```
D:\localcode\
  pathology-slide-kit\          公開工具包（scripts、workflows、style、question_banks…）
  pathology-slide-materials\    私有教材庫（courses、textbook、corpus…）
```

建議不要放在雲端硬碟的同步資料夾內：同步時的檔案鎖會讓 PowerPoint 匯出與 git 出錯。

## 取得 repo（保留 LF 換行）

Workflow 工具會拒絕含 `\r` 的腳本，所以 clone 時關掉換行轉換：

```powershell
cd D:\localcode
git clone -c core.autocrlf=false https://github.com/kblab2024/pathology-slide-kit.git
git clone -c core.autocrlf=false https://github.com/kblab2024/pathology-slide-materials.git
```

已經用預設設定 clone 過、檔案變成 CRLF 的話：先提交或備份自己的修改，再用上面的指令重新 clone（最單純）。

## 安裝 Python 套件

```powershell
cd D:\localcode\pathology-slide-kit
py -3 -m pip install -r requirements.txt
```

Microsoft Store 版沒有 `py` 啟動器時，改用 `python -m pip install -r requirements.txt`。

## Tesseract（做新章節時必要）

安裝 UB Mannheim 版（GitHub `UB-Mannheim/tesseract` 的 Windows 安裝檔），預設裝到 `C:\Program Files\Tesseract-OCR\`，
`render_pdf_pages.py` 會自動找到。裝在別處就設環境變數 `TESSERACT` 指到 `tesseract.exe`。

## LibreOffice（選用）

裝在預設位置（`C:\Program Files\LibreOffice\`）即可被 `export_pdf.py` 找到；其他位置設 `SOFFICE` 指到 `soffice.exe`。
在 Windows 上模擬雲端（不用 PowerPoint）：`--engine libreoffice` 或 `$env:SLIDEKIT_PDF_ENGINE = "libreoffice"`。

## 執行時的編碼

Windows 主控台預設是 cp950，中文輸出會亂碼或報錯，執行前先設：

```powershell
$env:PYTHONIOENCODING = "utf-8"          # PowerShell
```

```bash
PYTHONIOENCODING=utf-8 python style_check.py --course immune   # Git Bash
```

## 環境變數（都可不設）

| 變數 | 作用 |
|---|---|
| `SLIDEKIT_MATERIALS` | 教材庫位置；不設就找工具包同層的 `pathology-slide-materials`，再找工具包的上一層（若含 `courses\`） |
| `SLIDEKIT_CORPUS` | 教師投影片語料位置；不設就用 `<教材庫>\corpus`，再退到 `<工具包>\style\corpus` |
| `SLIDEKIT_PDF_ENGINE` | `auto`（預設）／`powerpoint`／`libreoffice` |
| `TESSERACT`、`SOFFICE` | Tesseract、LibreOffice 執行檔路徑 |
| `SLIDEKIT_MEASURE_FONT` | 量字字型檔路徑；`em` 表示不用字型、改用粗估（測試雲端行為用） |

長期設定用「系統內容 → 環境變數」，或 PowerShell 的 `[Environment]::SetEnvironmentVariable("SLIDEKIT_MATERIALS", "D:\localcode\pathology-slide-materials", "User")`。

## 裝好之後的檢查

```powershell
cd D:\localcode\pathology-slide-kit\scripts
$env:PYTHONIOENCODING = "utf-8"
python -c "import common; print(common.find_materials())"   # 應印出教材庫路徑
python gen_pptx.py --course immune --name _smoketest       # 產到 成品\_smoketest.pptx（不蓋交件檔，看完可刪）；最後一行應為 ===== ALL GREEN =====
python style_check.py --course immune                       # RED 0
python verify_quotes.py                                     # fail 0
python check_public.py                                      # FAIL 0（推 kit 之前）
```

# Mac 本機安裝

教師目前在 Mac 上做課、算圖、交件（PowerPoint for Mac）。Windows 見 `windows.md`，雲端（Linux）見 `cloud-setup.sh`。

## 需要的軟體

| 軟體 | 必要性 | 用途 |
|---|---|---|
| Python 3.10 以上（例：Anaconda 的 `python`；找不到 `python` 就用 `python3`） | 必要 | 所有工具 |
| Git | 必要 | 取得 repo |
| Microsoft PowerPoint for Mac | 建議 | `scripts/ppt_pdf_mac.sh` 存 PDF 與逐張 PNG；gen_pptx 量字用它內建的微軟正黑體（自動找，不必設 `SLIDEKIT_MEASURE_FONT`） |
| Tesseract（例：Homebrew 的 `brew install tesseract`） | 做新章節時必要 | `render_pdf_pages.py` 的 OCR；不在 PATH 上就設 `TESSERACT=<執行檔路徑>` |
| node | 選用 | 沒有時用 `osascript -l JavaScript workflows/tools/wf_check_mac.js <腳本> <args.json>` 代替 `check_workflows.js`（macOS 內建的 JavaScriptCore） |

## 安裝

維護者另有 kit 的私人工作版：有權限時做課用工作版，下面第一行 clone 與 `cd` 換成工作版（repo 名與 clone 指令在私人 repo 的 `AGENTS.md` 第 2 節；兩份 kit 的差別見 `../AGENTS.md` 第 2 段）。沒有權限就照下面用公開版。

```bash
git clone -c core.autocrlf=false https://github.com/kblab2024/pathology-slide-kit
git clone -c core.autocrlf=false https://github.com/kblab2024/pathology-slide-materials   # 私人 repo，需要權限
cd pathology-slide-kit
python -m pip install -r requirements.txt
cd scripts
export PYTHONIOENCODING=utf-8
python -c "import common; print(common.find_materials())"   # 應印出私人 repo 的路徑
```

## 在 Mac 上要知道的事（2026-10 的實測）

- `export_pdf.py` 在 Mac 存不了 PDF；改用 `bash scripts/ppt_pdf_mac.sh <課>/成品/<檔>.pptx`。第一次跑會跳 macOS 自動化授權，教師要在電腦前按允許；PowerPoint 開著別的簡報就停（結束碼 3），不動他的檔。
- 從圖形介面或背景程式啟動的工具不一定讀 `~/.zprofile`，Homebrew 與 Anaconda 可能不在 PATH 上；這時把 `/opt/homebrew/bin` 與 Anaconda 的 `bin` 加進 PATH。
- 把檔案放進 OneDrive 等雲端同步資料夾之前，照 `docs/教師偏好與決策.md` 第 8 節。

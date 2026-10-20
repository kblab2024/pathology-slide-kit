#!/bin/bash
# Mac：把 PowerPoint for Mac 內建的微軟正黑體（與 Arial、Calibri、Times New Roman）放進 LibreOffice 自己的字型資料夾，
# 讓 export_pdf.py --engine libreoffice 用和 PowerPoint 相同的字型排版（不用開 PowerPoint、不跳 macOS 授權）。
# 用法：bash lo_fonts_mac.sh        （LibreOffice 裝好或更新後跑一次；brew upgrade 會換掉整個 app，要再跑）
#
# 為什麼放進 app 裡：Mac 版 LibreOffice 只另外讀 app 內的 Resources/fonts/truetype；放這裡只影響 LibreOffice，
# 不裝進系統或使用者字型（~/Library/Fonts），其他 app 看不到。字型檔不進任何 repo。
# 放進去後 codesign --verify 會說 sealed resource 不符；從命令列跑 soffice 不受影響（2026-10-20 在教師的 Mac 試過）。
# 安裝 LibreOffice：brew install --cask libreoffice（app 被刪、brew 還記得時加 --force）。
set -euo pipefail
LO="${LIBREOFFICE_APP:-/Applications/LibreOffice.app}"
PPT="${POWERPOINT_APP:-/Applications/Microsoft PowerPoint.app}"
DST="$LO/Contents/Resources/fonts/truetype"
SRC="$PPT/Contents/Resources/DFonts"
[ -d "$DST" ] || { echo "找不到 LibreOffice 的字型資料夾：$DST（先 brew install --cask libreoffice）" >&2; exit 2; }
[ -d "$SRC" ] || { echo "找不到 PowerPoint 內建字型：$SRC" >&2; exit 2; }
n=0
for f in MSJH.ttf MSJHBD.ttf arial.ttf arialbd.ttf arialbi.ttf ariali.ttf \
         Calibri.ttf Calibrib.ttf Calibrii.ttf Calibriz.ttf times.ttf timesbd.ttf timesbi.ttf timesi.ttf; do
  [ -f "$SRC/$f" ] || { echo "（PowerPoint 裡沒有 $f，略過）"; continue; }
  if [ -f "$DST/$f" ] && cmp -s "$SRC/$f" "$DST/$f"; then continue; fi
  cp "$SRC/$f" "$DST/$f"
  n=$((n + 1))
done
echo "放進 $n 個字型到 $DST"
ls "$DST" | grep -q -i '^MSJH.ttf$' && echo "微軟正黑體：有" || { echo "微軟正黑體：沒有" >&2; exit 1; }

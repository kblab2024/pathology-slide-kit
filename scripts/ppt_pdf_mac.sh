#!/bin/bash
# 用 PowerPoint for Mac 把課程成品 PPTX 存成 PDF，再出縮圖拼板（sheet_NN.png）與逐張 PNG（slide_NNN.png）。
# Mac 本機沒有 Windows 的 PowerPoint COM，也不一定裝 LibreOffice，export_pdf.py 存不了 PDF，所以用這支（拼板與逐張 PNG 仍用 export_pdf.py 的函式）。
# 用法：bash ppt_pdf_mac.sh <課程>/成品/<in.pptx> [out.pdf] [png資料夾] [縮圖資料夾]
# 預設：PDF 與 PPTX 同資料夾、檔名把 (PPTX) 換成 (PDF)；PNG／縮圖放 <課程>/_archive/render/{png,sheets}。
# 第一次跑時 macOS 會問要不要允許控制 Microsoft PowerPoint，請教師在 Mac 上按允許。
#
# 安全規則（2026-10-14；舊版用 active presentation 取簡報、最後 close p saving no，
# 教師若開著別的簡報，會存錯檔，還會把他的簡報關掉而且不存檔）：
#   1. 只接受課程 成品/ 底下的 .pptx；路徑含 OneDrive／CloudStorage 一律拒絕。
#   2. 開檔前檢查 PowerPoint：開著任何簡報就停下來（結束碼 3），請教師自己存檔關掉，不替他關。
#   3. 暫存檔用獨一無二的檔名，開檔後用 name 找出剛開的那一份，只存、只關那一份。
#   4. 匯出前清掉舊的 slide_*.png 與 sheet_*.png（張數變少時，舊 PNG 不會留給審查代理看）。
#   5. 用 trap 清暫存檔；逾時就報錯，不 mv 不存在的檔。
set -euo pipefail
[ $# -ge 1 ] || { echo "用法：bash ppt_pdf_mac.sh <課程>/成品/<in.pptx> [out.pdf] [png資料夾] [縮圖資料夾]" >&2; exit 2; }
IN="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
case "$IN" in
  *CloudStorage*|*OneDrive*) echo "拒絕：不對 OneDrive 裡的檔跑（$IN）" >&2; exit 2 ;;
esac
case "$IN" in
  */成品/*.pptx) ;;
  *) echo "拒絕：只對課程 成品/ 底下的 .pptx 跑（$IN）" >&2; exit 2 ;;
esac
[ -s "$IN" ] || { echo "找不到檔案：$IN" >&2; exit 2; }
OUT="${2:-$(dirname "$IN")/$(basename "$IN" .pptx | sed 's/(PPTX)/(PDF)/').pdf}"
CDIR="$(cd "$(dirname "$IN")/.." && pwd)"
PNG="${3:-$CDIR/_archive/render/png}"
SHEETS="${4:-$CDIR/_archive/render/sheets}"
KIT="${SLIDEKIT_KIT:-$(cd "$(dirname "$0")/.." && pwd)}"   # 預設＝本腳本所在的 kit

# 2. PowerPoint 若在跑，而且開著任何簡報，就停
if pgrep -xq "Microsoft PowerPoint"; then
  OPENED="$(osascript -e 'tell application "Microsoft PowerPoint" to get name of every presentation' 2>/dev/null || true)"
  if [ -n "$OPENED" ]; then
    echo "PowerPoint 現在開著這些簡報：$OPENED" >&2
    echo "為了不動到您的檔案，先停下來。請自己存檔並關掉這些簡報（可以不關 PowerPoint），再重跑。" >&2
    exit 3
  fi
fi

# 3. 獨一無二的暫存檔名（放在 PowerPoint 沙盒容器內，免授權對話框）
BOX="$HOME/Library/Containers/com.microsoft.Powerpoint/Data/slidekit_export"
mkdir -p "$BOX"
TAG="slidekit_$$_$(date +%s)"
TMPIN="$BOX/$TAG.pptx"; TMPOUT="$BOX/$TAG.pdf"
trap 'rm -f "$TMPIN" "$TMPOUT"' EXIT
cp "$IN" "$TMPIN"

osascript <<EOF
with timeout of 1200 seconds
tell application "Microsoft PowerPoint"
  open POSIX file "$TMPIN"
  set target to missing value
  repeat 120 times
    repeat with p in presentations
      if (name of p) is "$TAG.pptx" then set target to contents of p
    end repeat
    if target is not missing value then exit repeat
    delay 1
  end repeat
  if target is missing value then error "找不到剛開的 $TAG.pptx，不存也不關任何簡報"
  save target in POSIX file "$TMPOUT" as save as PDF
  close target saving no
end tell
end timeout
EOF

for i in $(seq 1 120); do [ -s "$TMPOUT" ] && break; sleep 1; done
[ -s "$TMPOUT" ] || { echo "逾時：PowerPoint 沒有產出 PDF" >&2; exit 4; }
mv "$TMPOUT" "$OUT"
echo "PDF -> $OUT"

# 4. 清掉舊的 PNG 與拼板，再出新的
mkdir -p "$PNG" "$SHEETS"
rm -f "$PNG"/slide_*.png "$SHEETS"/sheet_*.png
cd "$KIT/scripts"
PYTHONIOENCODING=utf-8 python - "$OUT" "$SHEETS" "$PNG" <<'PY'
import sys, export_pdf as e
pdf, sh, png = sys.argv[1:4]
n1 = e.sheets(pdf, sh)
n2 = e.pngs(pdf, png)
print("sheets ->", sh, "| png ->", png, "| 張數", n2)
PY

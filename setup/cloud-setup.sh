#!/usr/bin/env bash
# 病理投影片工具包：Claude Code 雲端環境（Ubuntu）設定腳本
#
# 用法（擇一）：
#   1. 把整份內容貼進雲端環境設定的「Setup script」欄位（建議；不依賴 repo 放在哪裡）
#   2. 在 repo 內執行：bash setup/cloud-setup.sh
# 特性：
#   - 可重複執行：已安裝的套件、已存在的 repo 都會略過
#   - 目標 5 分鐘內完成（主要時間花在 apt 安裝 LibreOffice 與中文字型）
#   - 任何一步失敗只印警告，不中斷 session（最後一定 exit 0）
# 可用的環境變數（在雲端環境設定的環境變數欄位設定）：
#   SLIDEKIT_SKIP_APT=1        不裝系統套件（只裝 Python 套件，最快）
#   SLIDEKIT_NO_CLONE=1        只有教材庫時，不要自動 git clone 公開工具包
#   SLIDEKIT_KIT_URL=<網址>    工具包 repo 網址（預設 https://github.com/kblab2024/pathology-slide-kit.git）
#   SLIDEKIT_MATERIALS=<路徑>  教材庫位置（通常不必設：工具包會自動找同層的 pathology-slide-materials）

set -u
export PYTHONIOENCODING=utf-8
log() { echo "[slidekit-setup] $*"; }
T0=$(date +%s)

# 系統層的步驟（apt、字型對應、連結）只在 Linux 執行；在 Windows Git Bash 跑只會做找 repo、pip 與摘要
IS_LINUX=0
[ "$(uname -s 2>/dev/null)" = "Linux" ] && IS_LINUX=1
SUDO=""
if [ "$IS_LINUX" = "1" ] && [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
fi

# ---------- 1. 系統套件 ----------
# fonts-noto-cjk：Noto Sans CJK TC，gen_pptx 量字寬、LibreOffice 排版中文用（雲端沒有微軟正黑體）
# tesseract-ocr：render_pdf_pages.py 的 OCR
# libreoffice-impress：export_pdf.py 在沒有 PowerPoint 時把 PPTX 轉 PDF
PKGS="fonts-noto-cjk tesseract-ocr libreoffice-impress"
if [ "${SLIDEKIT_SKIP_APT:-0}" = "1" ]; then
  log "SLIDEKIT_SKIP_APT=1，略過系統套件"
elif [ "$IS_LINUX" != "1" ]; then
  log "不是 Linux，略過系統套件"
elif ! command -v apt-get >/dev/null 2>&1; then
  log "沒有 apt-get（不是 Debian／Ubuntu），略過系統套件"
else
  NEED=""
  for p in $PKGS; do
    dpkg -s "$p" >/dev/null 2>&1 || NEED="$NEED $p"
  done
  if [ -n "$NEED" ]; then
    log "安裝系統套件：$NEED"
    export DEBIAN_FRONTEND=noninteractive
    # shellcheck disable=SC2086
    { $SUDO apt-get update -qq && $SUDO apt-get install -y -qq --no-install-recommends $NEED; } \
      || log "警告：apt 安裝失敗（沒有網路或權限？），略過"
  else
    log "系統套件都已安裝，略過"
  fi
fi

# ---------- 2. 字型對應 ----------
# PPTX 內寫的字型是「Microsoft JhengHei」；讓 LibreOffice 轉 PDF 時改用 Noto Sans CJK TC（繁中字形），
# 否則 fontconfig 可能挑到簡中或日文字形。
if [ "$IS_LINUX" = "1" ] && command -v fc-cache >/dev/null 2>&1; then
  if [ -w /etc/fonts/conf.d ] || [ -n "$SUDO" ]; then
    FC_DIR=/etc/fonts/conf.d
  else
    FC_DIR="$HOME/.config/fontconfig/conf.d"
  fi
  FC_FILE="$FC_DIR/99-slidekit-jhenghei.conf"
  if [ ! -f "$FC_FILE" ]; then
    log "寫入字型對應：$FC_FILE"
    $SUDO mkdir -p "$FC_DIR" 2>/dev/null || mkdir -p "$FC_DIR"
    $SUDO tee "$FC_FILE" >/dev/null <<'XML' || log "警告：無法寫入字型對應"
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <alias binding="same">
    <family>Microsoft JhengHei</family>
    <prefer><family>Noto Sans CJK TC</family></prefer>
  </alias>
  <alias binding="same">
    <family>微軟正黑體</family>
    <prefer><family>Noto Sans CJK TC</family></prefer>
  </alias>
</fontconfig>
XML
    fc-cache -f >/dev/null 2>&1 || true
  fi
fi

# ---------- 3. 找兩個 repo ----------
# 工具包＝含 scripts/common.py 與 style/rules.yaml 的資料夾；教材庫＝含 courses/<課程>/course.yaml 的資料夾
KIT=""
MAT=""
SELF_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
# 依序搜尋：本腳本所在 repo 與其上一層、目前目錄與其上一層、常見的雲端工作目錄
ROOTS="${SELF_DIR:+$SELF_DIR/.. $SELF_DIR/../..} $PWD $PWD/.. $HOME /home/user /workspace /workspaces /repo /code /src"
if [ -n "${SLIDEKIT_MATERIALS:-}" ] && [ -d "${SLIDEKIT_MATERIALS}/courses" ]; then
  MAT="$(cd "$SLIDEKIT_MATERIALS" && pwd)"
fi
for r in $ROOTS; do
  [ -d "$r" ] || continue
  if [ -z "$KIT" ]; then
    while IFS= read -r f; do
      d="$(dirname "$(dirname "$f")")"
      if [ -f "$d/style/rules.yaml" ]; then
        KIT="$(cd "$d" && pwd)"
        break
      fi
    done < <(find "$r" -maxdepth 3 -type f -path '*/scripts/common.py' 2>/dev/null)
  fi
  if [ -z "$MAT" ]; then
    f=$(find "$r" -maxdepth 4 -type f -path '*/courses/*/course.yaml' 2>/dev/null | head -n 1)
    [ -n "$f" ] && MAT="$(cd "$(dirname "$f")/../.." && pwd)"
  fi
done
log "工具包：${KIT:-（未找到）}"
log "教材庫：${MAT:-（未找到）}"

# ---------- 4. 只有教材庫時，clone 公開工具包到教材庫旁邊 ----------
# 最好的做法是開 session 時把兩個 repo 都加進去。雲端的 GitHub proxy 可能只放行加進 session 的 repo，
# 這一步 clone 失敗時只印警告；那就回到 repository selector 把 pathology-slide-kit 加進來。
if [ -z "$KIT" ] && [ -n "$MAT" ] && [ "${SLIDEKIT_NO_CLONE:-0}" != "1" ]; then
  URL="${SLIDEKIT_KIT_URL:-https://github.com/kblab2024/pathology-slide-kit.git}"
  DEST="$(dirname "$MAT")/pathology-slide-kit"
  if [ -e "$DEST" ]; then
    log "警告：$DEST 已存在但不是完整的工具包，不覆蓋"
  elif command -v git >/dev/null 2>&1; then
    log "clone 工具包：$URL -> $DEST"
    if git clone -q --depth 1 -c core.autocrlf=false "$URL" "$DEST"; then
      KIT="$DEST"
    else
      log "警告：clone 失敗"
    fi
  fi
fi

# ---------- 5. 讓工具包找得到教材庫 ----------
# 工具包預設找「同層的 pathology-slide-materials」；教材庫資料夾名稱不同時，在工具包旁建一個同名連結
if [ "$IS_LINUX" = "1" ] && [ -n "$KIT" ] && [ -n "$MAT" ]; then
  SIB="$(dirname "$KIT")/pathology-slide-materials"
  if [ ! -e "$SIB" ] && [ "$(cd "$MAT" && pwd)" != "$(cd "$(dirname "$KIT")" && pwd)" ]; then
    ln -s "$MAT" "$SIB" 2>/dev/null && log "建立連結：$SIB -> $MAT" \
      || log "警告：無法建立連結；請在環境變數設 SLIDEKIT_MATERIALS=$MAT"
  fi
fi

# ---------- 6. Python 套件 ----------
PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  log "警告：找不到 python3"
else
  if [ -n "$KIT" ] && [ -f "$KIT/requirements.txt" ]; then
    REQ=(-r "$KIT/requirements.txt")
  else
    REQ=("python-pptx>=0.6.21" "PyMuPDF>=1.23.0" "Pillow>=10.0" "PyYAML>=6.0" "lxml>=4.9")
  fi
  log "安裝 Python 套件"
  "$PY" -m pip install -q --disable-pip-version-check "${REQ[@]}" 2>/dev/null \
    || "$PY" -m pip install -q --disable-pip-version-check --break-system-packages "${REQ[@]}" 2>/dev/null \
    || "$PY" -m pip install -q --disable-pip-version-check --user "${REQ[@]}" \
    || log "警告：pip 安裝失敗"
fi

# ---------- 6b. 讓「python」指令可用 ----------
# 文件與工作流的固定寫法都是 python；Ubuntu 映像常只有 python3。建一個指向同一個直譯器的 python
# （就是上面裝好套件的那一個），避免 python 指到另一個沒裝套件的直譯器。
if [ "$IS_LINUX" = "1" ] && [ -n "$PY" ] && ! command -v python >/dev/null 2>&1; then
  if [ -w /usr/local/bin ] || [ -n "$SUDO" ]; then
    $SUDO ln -sf "$PY" /usr/local/bin/python 2>/dev/null && log "建立連結：/usr/local/bin/python -> $PY"
  else
    mkdir -p "$HOME/.local/bin" && ln -sf "$PY" "$HOME/.local/bin/python" \
      && log "建立連結：$HOME/.local/bin/python -> $PY（需在 PATH 上）"
  fi
  command -v python >/dev/null 2>&1 || log "警告：還是沒有 python 指令；請改用 python3 執行工具"
fi

# ---------- 7. 摘要 ----------
if [ -n "$PY" ]; then
  "$PY" -c "import pptx, fitz, PIL, yaml, lxml; print('[slidekit-setup] Python 套件 OK：python-pptx', pptx.__version__, '／PyMuPDF', fitz.VersionBind, '／Pillow', PIL.__version__)" \
    || log "警告：Python 套件不完整"
  if [ -n "$KIT" ]; then
    (cd "$KIT/scripts" && "$PY" -c "import common; print('[slidekit-setup] find_materials() =', common.find_materials())") || true
  fi
fi
command -v tesseract >/dev/null 2>&1 && log "tesseract：$(tesseract --version 2>&1 | head -n 1)" || log "tesseract：無"
command -v soffice >/dev/null 2>&1 && log "LibreOffice：$(soffice --version 2>/dev/null | head -n 1)" || log "LibreOffice：無"
command -v fc-match >/dev/null 2>&1 && log "Microsoft JhengHei 對應到：$(fc-match 'Microsoft JhengHei' 2>/dev/null)"
log "完成，用時 $(( $(date +%s) - T0 )) 秒"
exit 0

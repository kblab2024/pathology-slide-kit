# pathology-slide-kit：病理學教案投影片工具組

**English summary.** A kit for building pathology lecture decks (PowerPoint, Traditional Chinese with English terms) in the style of one teacher at a Taiwanese medical school. It contains Python tools (python-pptx based generator, checkers, PDF/PNG export, textbook page rendering and figure cropping, exam-bank parsing, deck dumping and diffing), multi-agent Claude Code Workflow scripts (gather facts, blueprint, write, review, style mining, style guide), a 28-file style guide of the teacher's slide style with a machine-readable `style/rules.yaml`, and public Taiwanese licensing-exam question banks. Course materials (textbook pages, figure crops, fact ledgers, other people's slides, the teacher's original deck files and their full per-slide dumps) are **not** here; they live in a separate private repository (`pathology-slide-materials`) that the tools find automatically when it is cloned next to this one. The style guide does quote excerpts from the teacher's own slides and speaker notes to document his style; colleagues appear only under pseudonyms. License: code MIT (`LICENSE`), docs and style guide CC BY-NC 4.0 (`LICENSE-docs.md`). Works on Windows (PowerPoint) and in Claude Code cloud sessions (Ubuntu, LibreOffice, Noto CJK). Start with `CLAUDE.md` (Claude) or `AGENTS.md` (other agents).

---

## 這是什麼

這是一套「照授課教師的投影片風格做病理學大堂課投影片」的工具組，給 Claude（或其他程式代理）與老師本人使用。流程是：

1. 從教科書（Robbins 11e 的某一章）抽出可查核的事實帳；
2. 排出每一張投影片的藍圖（張型、圖、事實、國考題）；
3. 分批撰寫文字，並由查核代理核對事實、老師的語氣、中英術語與字數；
4. 用 `gen_pptx.py` 把來源檔（素材池 pool.md、講稿 script.md、選單 decks/*.md）算成 PPTX，自動檢查；
5. 渲染成 PDF 與逐張 PNG，人眼看過，再跑一到兩輪審查；
6. 交給老師，老師親手改過之後，把他的改動回灌來源檔，並更新風格指南。

**永遠只改來源檔，不手改產出的 PPTX。**

## 給誰用

- **Claude Code**（本機桌面 app 或雲端 session）：讀 `CLAUDE.md`。
- **其他程式代理**（GPT／Codex 等，沒有 Workflow 工具）：讀 `AGENTS.md`，依序手動跑各階段。
- **老師本人**：看 `docs/cloud_session_教學.md`（雲端 session 入門）與 `docs/SOP_新教案流程.md`（整條流程與要您決定的地方）。

## 兩個 repo

| repo | 公開性 | 放什麼 |
|---|---|---|
| `pathology-slide-kit`（本 repo） | 公開 | 程式、工作流、範本、風格指南、國考題庫、文件 |
| `pathology-slide-materials` | 私人 | 各課程資料夾（courses/）、教科書頁圖與 OCR（textbook/）、老師投影片語料（corpus/）、風格研究證據（style_evidence/）、成品 |

兩個 repo 放在同一個上層資料夾下（兄弟資料夾），工具會自動找到私人 repo。找法（`scripts/common.py` 的 `find_materials()`）：

1. 環境變數 `SLIDEKIT_MATERIALS`；
2. 否則找 `<kit>/../pathology-slide-materials`；
3. 否則 `<kit>/..` 底下有 `courses/` 就用它；
4. 都找不到就回傳 None（只能跑不需要課程資料的工具）。

課程設定 `--course <名稱>` 的找法：先看是不是 course.yaml 或其資料夾的路徑，再找 `<materials>/courses/<名稱>/course.yaml`，最後找 `<kit>/examples/<名稱>/course.yaml`；都沒有就報錯並列出試過的路徑。

## 資料夾地圖

```
pathology-slide-kit/
├─ README.md            本檔
├─ CLAUDE.md            Claude session 的操作守則（先讀）
├─ AGENTS.md            其他代理（GPT／Codex）的操作守則，無 Workflow 工具時的循序做法
├─ requirements.txt     Python 套件
├─ setup/               cloud-setup.sh（雲端環境的 Setup script）、windows.md（本機安裝）
├─ scripts/             Python 工具；README.md 有每支的用法與來源檔格式；check_public.py 是推上 GitHub 前的隱私檢查
├─ workflows/           Claude Code 多代理工作流（*.js）與 README.md；reference/ 是免疫課當時的原版腳本
├─ templates/           course.template.yaml、brief.template.md、gather.template.json、course.CLAUDE.template.md、
│                       blueprint.schema.json、written.schema.json
├─ style/
│  ├─ guide/            老師投影片風格指南 28 檔（入口 00_README.md）
│  └─ rules.yaml        機器可讀規則（style_check.py、check_written.py 讀）
├─ question_banks/      醫師、牙醫師國考題庫 JSON（說明見該資料夾 README.md）
├─ examples/immune/     範例課程設定（course.yaml、brief.md）
└─ docs/
   ├─ SOP_新教案流程.md       新教案從頭到交付的步驟與指令
   ├─ cloud_session_教學.md   給老師的雲端 session 入門（含費用）
   ├─ 教師偏好與決策.md       老師的教學理念、課程代碼、開工前要問的事、交付慣例
   └─ lessons_learned.md      管線踩過的坑
```

## 快速開始

### A. Windows 本機（Claude 桌面 app 的 Local，或終端機）

需要：Python 3.10 以上（在 3.11 測過）、Git for Windows（含 Git Bash）、PowerPoint（匯出 PDF 用；沒有就裝 LibreOffice）、Tesseract（教科書章節轉頁圖時做 OCR；Robbins 章節 PDF 是掃描檔，新章節一定要裝）。詳細見 `setup/windows.md`。

```bash
# 在 Git Bash；上層資料夾自選，例如 D:/work
cd /d/work
git clone -c core.autocrlf=false https://github.com/kblab2024/pathology-slide-kit
git clone -c core.autocrlf=false https://github.com/kblab2024/pathology-slide-materials   # 私人 repo，需要權限
cd pathology-slide-kit
python -m pip install -r requirements.txt
cd scripts
export PYTHONIOENCODING=utf-8
python -c "import common; print(common.find_materials())"   # 應印出私人 repo 的路徑
python gen_pptx.py --course immune --name _smoketest        # 重產範例課程到 成品/_smoketest.pptx，應該 ALL GREEN（不會蓋掉交件檔；看完可刪）
```

`core.autocrlf=false` 很重要：Workflow 工具拒絕含 `\r` 的腳本，Windows 的 Git 預設會把換行轉成 CRLF。PowerShell 裡設編碼用 `$env:PYTHONIOENCODING="utf-8"`。

### B. Claude Code 雲端 session（兩個 repo 一起加）

1. 一次性設定：在 GitHub 安裝 Claude GitHub App（私人 repo 一定要）；在 claude.ai/code 建一個 cloud environment，Network access 選 Trusted，把 `setup/cloud-setup.sh` 的內容貼進 Setup script 欄。
2. 開 session：桌面 app 選 **Cloud**（或開 claude.ai/code），repository 選 `pathology-slide-materials`，再按 **+** 加 `pathology-slide-kit`，分支選 main。
3. 第一句話請 Claude 先讀兩個 repo 的 CLAUDE.md，再照 `docs/SOP_新教案流程.md` 做。
4. 成品由 session 推到一個新分支；到 GitHub 網頁切到該分支下載 PPTX，或按 **Create PR**。

逐步圖解、可直接複製的第一句話、費用控制與常見陷阱，見 `docs/cloud_session_教學.md`。Workflow 工具在雲端 session 能不能用還沒有實測；不能用時照 `AGENTS.md` 循序做，產出的檔案相同。

**費用**：多代理工作流是主要花費。以 API 牌價換算，一門約 180 張的新課從蒐集到兩輪審查約 $950–1,200，只做一輪審查約 $830–990；各階段的單價、省錢設定，以及這些金額和方案用量、usage credits 的關係，見 `docs/cloud_session_教學.md` 第 9 節。

## 新教案流程總覽

詳細指令、預期產出與要老師決定的檢查點見 `docs/SOP_新教案流程.md`。

| 步驟 | 做什麼 | 工具或工作流 | 主要產出（在私人 repo 的 `courses/<課程>/`） |
|---|---|---|---|
| 0 | 開工前問老師、建課程資料夾 | `style/guide/50_檢查/51_撰寫前檢查清單.md`、`templates/` | course.yaml、brief.md、gather.json |
| 1 | 教科書轉頁圖＋OCR | `scripts/render_pdf_pages.py` | `textbook/<章>/pages/pNN_PPP.jpg`＋.txt＋.tsv |
| 2 | 切教科書圖表、抽舊投影片的圖 | `scripts/robbins_crop.py`、`scripts/extract_deck_images.py` | `assets/images/` |
| 3 | 蒐集事實、國考題、文獻 | `workflows/lecture-gather.js` → `scripts/merge_facts.py` | `facts/facts_R.json`、`facts_X.json`、`_archive/gather/` |
| 4 | 藍圖 | `workflows/lecture-blueprint.js` → `scripts/validate_blueprint.py` | `_archive/blueprint/blueprint.json`、glossary.md |
| 5 | 撰寫與組裝 | `scripts/make_batches.py` → `workflows/lecture-write.js` → `scripts/merge_written.py` → `scripts/assemble.py` | `sources/*-pool.md`、`*-script.md`、`sources/decks/*.md` |
| 6 | 產 PPTX 與檢查 | `scripts/gen_pptx.py`（自動 check_deck）→ `style_check.py` → `export_pdf.py` → 逐張看 PNG | `成品/*.pptx`、PDF |
| 7 | 審查一到兩輪 | `workflows/lecture-review.js` → 重產 | `_archive/review/round<N>/fix_report.md` |
| 8 | 交付 | `scripts/img_todo.py`、待教師裁決清單 | `成品/` |
| 9 | 老師改稿後回灌 | `scripts/dump_pptx.py`＋`scripts/diff_decks.py` | 更新 pool.md、語料、風格指南 |

風格研究（很少需要重跑）：`workflows/style-mining.js`（22 面向挖掘）與 `workflows/style-guide.js`（重寫指南）。現有指南已完成，老師有新改稿時照 `style/guide/00_README.md`「版本與更新規則」局部更新即可。

## 風格指南從哪裡開始

- 入口：`style/guide/00_README.md`（依任務的讀法、最重要的十條、檔案地圖）。
- 衝突怎麼判：`style/guide/01_權威順序.md`（他親手改我們的稿 ＞ 他自製 2026 ＞ 2025 ＞ 2024 ＞ 某課的明令只管該課 ＞ 我們的毛胚 ＞ 他人）。
- 交付前：`style/guide/50_檢查/52_交付前檢查清單.md`。
- 指南引用的語料（他的投影片逐張傾印）在私人 repo 的 `corpus/`；指南內寫的 `style/corpus/`、`style/_work/`、`immune/` 等舊路徑怎麼對到現在的位置，見 `CLAUDE.md`「路徑對照」。

## 授權與著作權

- **教科書與他人資料不在本 repo。** Robbins & Cotran *Pathologic Basis of Disease* 的頁圖、切圖、OCR 文字與逐條事實帳，老師以外其他人的投影片（例如同事的舊講義），老師本人的投影片原檔與傾印，都只放在私人 repo。不要把這些檔案加進本 repo，也不要在本 repo 的 issue、PR 或文件貼上長段教科書原文。
- **國考題庫**：`question_banks/` 的題目取自考選部「考畢試題查詢平臺」公開的試題與答案。依著作權法第 9 條第 1 項第 5 款，依法令舉行之各類考試試題不得為著作權之標的，所以可以公開收錄；答案已套用考選部公告的更正。
- **風格指南的引句**是老師本人投影片與備註裡的句子，用來說明他的寫法（部分檔案收錄的比例不低，例如 `40_範例/` 三檔）；他人投影片的引句在公開版已經拿掉，留下「〔他人投影片引句，公開版省略…〕」的標記；同事只用代稱（同事甲、同事乙）。未遮蔽的完整版在私人 repo 的 `style_evidence/`。
- **推上 GitHub 之前**：`cd scripts && python check_public.py`，檢查換行、本機路徑、電子郵件、第三人真名、他人引句與圖檔，FAIL 要是 0（需要私人 repo 在旁邊，才讀得到代稱表）。
- **授權**：程式（`scripts/`、`workflows/`、`templates/`、`setup/`）採 MIT，見 `LICENSE`；說明文件與風格指南（`README.md`、`CLAUDE.md`、`AGENTS.md`、`docs/`、`style/`、`examples/`）採 CC BY-NC 4.0，見 `LICENSE-docs.md`。
- **不掛名**：公開版的授課教師與服務單位一律寫成「授課教師」；真名對照只在私人 repo 的 `corpus/pseudonyms.tsv`，`check_public.py` 會用它擋下殘留的真名。

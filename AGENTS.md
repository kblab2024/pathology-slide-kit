# AGENTS.md：給 GPT／Codex 等程式代理的操作守則

本檔與 `CLAUDE.md` 的規則相同，差別在於：你可能沒有 Claude Code 的 Workflow 工具（多代理腳本執行器），所以本檔說明怎麼把 `workflows/*.js` 的每個階段改成**依序、自己一步一步做**，而且輸出同名檔，之後換 Claude session 接手時可以直接沿用。

本 repo（公開）是工具；課程內容在兄弟 repo `pathology-slide-materials`（私人）。使用者是授課教師。

## 1. 環境

| | Windows | Linux（含雲端容器） |
|---|---|---|
| 安裝 | `python -m pip install -r requirements.txt`；PowerPoint 匯出 PDF | `bash setup/cloud-setup.sh`（apt 裝 fonts-noto-cjk、tesseract-ocr、libreoffice-impress，再 pip 裝套件；需要 root 或 sudo） |
| PDF 匯出 | `export_pdf.py` 走 PowerPoint | 走 LibreOffice（`soffice --headless`） |
| 換行量測字型 | 微軟正黑體 | Noto Sans CJK TC（PPTX 內仍指定微軟正黑體，所以最後在 Windows 的 PowerPoint 看一次） |

檢查兩個 repo 找得到彼此：

```bash
cd "<kit>/scripts" && PYTHONIOENCODING=utf-8 python -c "import common; print(common.ROOT); print(common.find_materials())"
```

`find_materials()` 的順序：環境變數 `SLIDEKIT_MATERIALS` → `<kit>/../pathology-slide-materials` → `<kit>/..`（若含 `courses/`）→ None。`--course <名稱>` 依序找：路徑本身 → `<materials>/courses/<名稱>/course.yaml` → `<kit>/examples/<名稱>/course.yaml`。語料：`SLIDEKIT_CORPUS` → `<materials>/corpus` → `<kit>/style/corpus`。

指令的固定寫法：

```bash
cd "<kit>/scripts" && SLIDEKIT_MATERIALS="<materials>" PYTHONIOENCODING=utf-8 python <script>.py --course <course> ...
```

`--course` 只給讀課程設定的工具（gen_pptx、check_deck、style_check、img_todo、assemble、merge_facts、merge_written、validate_blueprint、check_written、render_pdf_pages、robbins_crop、to_claude_slides）；make_batches、export_pdf、extract_deck_images、dump_pptx、diff_decks、verify_quotes、check_public、fetch_moex_dent_exam、parse_moex_exam 照各自用法（每支都有 `--help`）。Linux 找不到 `python` 就用 `python3`。

## 2. 先讀什麼

1. `docs/教師偏好與決策.md`（老師是誰、怎麼做決定、開工前要問什麼）
2. `style/guide/01_權威順序.md`（證據衝突時誰說了算）
3. 依任務：`style/guide/00_README.md` 的任務 A–F 讀法；新教案另讀 `docs/SOP_新教案流程.md`
4. 該課的 `<materials>/courses/<course>/CLAUDE.md`、`brief.md`、`course.yaml`（課程明令在這裡；檔名叫 CLAUDE.md 但內容對所有代理都適用）
5. 工具用法：`scripts/README.md`；工作流內容：`workflows/README.md` 與各 `.js` 檔

## 3. 硬規則（與 CLAUDE.md 相同）

1. 事實以 Robbins 11e 為唯一正典；文獻只補充、必附出處、不得蓋過 Robbins；衝突列進「待教師裁決清單」，不靜默改、不靜默沿用。
2. 不寫 LLM 語：全形雙破折號（U+2014 連寫兩個）、套語、舞台指示、打氣、戲劇化第二人稱、貫穿全套的比喻。清單見 `style/guide/20_文字/23_禁用語與LLM語.md`；老師自己的「其實」「不是 X，而是 Y」「因此」「=>」照用。
3. 字級、中英對照（course.yaml `bilingual`：per_slide／first_per_deck（預設）／off）、國考題版式（`decks.<deck>.quiz_style`）照該課明令（寫在該課 course.yaml、brief.md）；沒有明令照指南；不把某課的明令外推。
4. 一張講一件事、字少圖大；放不下拆同標題連張；不做大綱、總結、謝謝張；不產佔位張。
5. 只改來源檔（pool.md、script.md、decks/*.md、course.yaml、glossary.md），不手改 PPTX。
6. 不覆蓋老師親手改過的檔：先回灌再重產。
7. 檢查器全過之後還要渲染逐張 PNG 並實際看過。
8. 做過的步驟不重做：輸出檔已存在且完整就跳過（等同 Claude 工作流的 DONE 標籤）；做完的清單存在 `<課程資料夾>/_archive/journals/`，之後換 Claude session 可以用 `workflows/tools/done_from_journal.py --scan` 接手。
9. 額度或時間快用完時停在一個步驟的邊界，寫下完成清單與下一步，交回使用者；不要自行無限重試。
10. 文字檔 UTF-8、LF 換行；Windows 上 Python 寫檔要 `newline="\n"`。
11. Robbins 頁圖、切圖、事實帳、老師與他人的投影片、語料、成品只放私人 repo；本 repo 不放課程內容、個人資料與本機絕對路徑；同事一律用代稱（同事甲、同事乙）。commit 到本 repo 前跑 `python check_public.py`，FAIL 要是 0。
12. 修稿取捨：事實 ＞ 術語 ＞ 版面 ＞ 文風。
13. 繁體中文（台灣用語）；dysplasia 寫「分化不良」。

原本的工作流全部指定 Claude Opus；若你用其他模型，照樣遵守每個角色的品質要求與輸出格式，並在交付說明寫明用了什麼模型。

## 4. 沒有 Workflow 工具時：循序做各階段

每個 `workflows/*.js` 裡的 prompt 字串就是該角色的完整任務說明（要讀哪些檔、寫哪個檔、JSON 格式、驗收指令）。把 `<kit>`、`<materials>`、`<course>` 換成實際值，一個角色一個角色做。下表的檔名取自 immune 課程的實際產出，實際以 `.js` 內 prompt 寫的為準。

**要點**：查核與反駁角色要「換一雙眼睛」：重新從磁碟讀檔，不要憑剛才寫稿時的記憶判斷；反駁者的工作是試著推翻前一個角色的結論。兩個獨立反駁者就做兩次、分開寫檔。

### 4.1 蒐集（`lecture-gather.js`；設定在課程的 `gather.json`，格式見 `templates/gather.template.json`）

| 軌 | 每個單位依序做 | 輸出（課程資料夾內） |
|---|---|---|
| 教科書事實 | 每段：抽取 → 反駁 1 → 反駁 2 → 裁決 | `facts/seg/<段>.json`、`<段>_review1.json`、`<段>_review2.json`、`<段>_final.json` |
| 國考題 | 兩個獨立分類 → 核對並選題 | `_archive/gather/exam/classify_a.json`、`classify_b.json`、`exam_candidates.json` |
| 文獻 | 每題：搜尋 → 對 PubMed 摘要逐條查核 → 找開放授權圖 | `_archive/gather/lit/<題>.json`、`<題>_verified.json`、`<題>_images.json` |

然後：`python merge_facts.py --course <course>` → `facts/facts_R.json`、`facts_X.json`、`facts/facts.md`。

### 4.2 藍圖（`lecture-blueprint.js`）

glossary → 三個視角的草稿 → 三位評審 → 綜合 → 批評 → 修訂（老師看過 `blueprint_summary.md` 有意見時，把意見寫進 brief.md，再只做「修訂」這一步，把他的意見當最高優先）。輸出在 `_archive/blueprint/`：`draft_<視角>.json`、`judge_1..3.json`、綜合版、`critique.json`、`blueprint.json`、`diagrams.yaml`；glossary 寫在課程的 `glossary.md`。然後：

```bash
python validate_blueprint.py --course <course> "<課程資料夾>/_archive/blueprint/blueprint.json" --diagrams "<課程資料夾>/_archive/blueprint/diagrams.yaml"
```

RED 為 0 才往下；把 diagrams.yaml 的框架圖併進 course.yaml 的 `diagrams`。

### 4.3 撰寫（`lecture-write.js`）

```bash
python make_batches.py "<bp>" "<課程資料夾>/_archive/written/batches.json" --size 16
```

每一批（`batches.json` 的 `batches[k]`）依序：

1. 撰寫 → `_archive/written/batch_<k>_draft.json`，跑 `python check_written.py --course <course> --blueprint "<bp>" <檔>` 修到 RED 0；
2. 三個查核（事實、老師語氣與 LLM 語、中英術語與密度）→ `batch_<k>_check_facts.json`、`_check_voice.json`、`_check_terms.json`；
3. 修訂 → `batch_<k>.json`，再跑 check_written 到 RED 0。

全部批次做完：通讀全套做跨批連貫性修改 → `continuity_report.md`。然後：

```bash
python merge_written.py --course <course> --dir "<課程資料夾>/_archive/written" --blueprint "<bp>"
python assemble.py --course <course> "<bp>" "<課程資料夾>/_archive/written/written.json" --dry-run   # 先看 RED
python assemble.py --course <course> "<bp>" "<課程資料夾>/_archive/written/written.json"
```

### 4.4 產檔與檢查

```bash
python gen_pptx.py --course <course>                 # 產 PPTX 與 _layout.json，自動跑 check_deck
python style_check.py --course <course>              # RED 必須 0
python export_pdf.py "<成品>/<檔名>.pptx" --pdf "<成品>/<PDF 檔名>.pdf" --sheets "<課程資料夾>/_archive/render/sheets" --pngs "<課程資料夾>/_archive/render/png"
python img_todo.py --course <course>
```

逐張看 `_archive/render/png/` 的 PNG（或縮圖拼板 sheets）。

### 4.5 審查（`lecture-review.js`，一到兩輪）

六個面向：facts、voice、terms、layout、exam、images。每個面向：審查 → 兩個獨立反駁 → 最後一個修正者只套用至少一位反駁者確認的項目，改來源檔、重產、修到 check_deck 無 RED 且 style_check RED 0。輸出在 `_archive/review/round<N>/`：`review_<面向>.json`、`verify_<面向>_1.json`、`verify_<面向>_2.json`、`fix_report.md`。

### 4.6 交付與回灌

交付與老師改稿後的回灌步驟見 `docs/SOP_新教案流程.md` 第 10、11 步。

## 5. 產出與交回

- 中間檔在 `<materials>/courses/<course>/_archive/`；成品在 `<materials>/courses/<course>/成品/`（PPTX、PDF、待教師裁決清單.md、待補圖清單.md）。
- 檔名寫課程代碼：`病理學{碼}_{講題}(PPTX)_{YYYYMMDD}.pptx`。
- 用 git 交回時：課程檔 commit 在私人 repo；`成品/*.pptx` 被 .gitignore 排除，交件那個檔用 `git add -f`（同名 `_layout.json` 照常提交）；單檔小於 100 MB；同一門課只提交最後交件的 PPTX。每完成一個階段就 commit 一次。

## 6. 路徑對照

指南裡的舊路徑（`style/corpus/`、`style/_work/`、`immune/…`、`immune/_archive/robbins_png/`、`成品/工具腳本/`）與代稱（同事甲、同事乙）對到現在位置的表，見 `CLAUDE.md` 第 6 節。

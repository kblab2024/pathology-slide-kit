# CLAUDE.md：病理學教案投影片工具組的操作守則

本 repo（公開的 kit）是工具；課程內容在兄弟 repo `pathology-slide-materials`（私人）。使用者就是授課教師。他的本機記憶檔在雲端看不到，凡是需要長期記住的事都寫在本 repo 的 `docs/` 與 `style/guide/`，以及私人 repo 各課程的 `CLAUDE.md`、`brief.md`。

## 1. 開工第一件事：確認環境與兩個 repo

```bash
echo "remote=$CLAUDE_CODE_REMOTE os=$(uname -s 2>/dev/null)"   # 雲端 session 的 CLAUDE_CODE_REMOTE=true
cd "<kit>/scripts" && PYTHONIOENCODING=utf-8 python -c "import common; print(common.ROOT); print(common.find_materials())"
```

| | Windows 本機 | Claude Code 雲端 session |
|---|---|---|
| 判別 | `os.name == "nt"`；Git Bash 或 PowerShell | `CLAUDE_CODE_REMOTE=true`；Ubuntu |
| PDF 匯出 | `export_pdf.py` 用 PowerPoint | 沒有 PowerPoint，改用 LibreOffice（`soffice`）；`SLIDEKIT_PDF_ENGINE=auto｜powerpoint｜libreoffice` 可強制指定 |
| 換行量測字型 | 微軟正黑體（Microsoft JhengHei） | Noto Sans CJK TC；PPTX 內仍指定微軟正黑體 |
| 套件 | `pip install -r requirements.txt` | 由環境的 Setup script（`setup/cloud-setup.sh`）裝好；缺了就 `bash setup/cloud-setup.sh`（本次 session 有效） |
| `python` 指令 | python.org 或 Store 版的 `python` | cloud-setup.sh 會建 `python` 連結；還是找不到就用 `python3` |
| 編碼 | 一律 `PYTHONIOENCODING=utf-8`，否則 cp950 報錯 | 同左（無害） |

找不到私人 repo（`find_materials()` 回 None）時：本機就 `git clone` 到 kit 旁邊；雲端要請使用者在 repository selector 把 `pathology-slide-materials` 加進 session（雲端的 GitHub proxy 可能只放行加進 session 的 repo），或設 `SLIDEKIT_MATERIALS`。語料位置：`SLIDEKIT_CORPUS`，否則 `<materials>/corpus`，否則 `<kit>/style/corpus`。

**指令的固定寫法**（Workflow 的 prompt 裡也一樣）：

```bash
cd "<kit>/scripts" && SLIDEKIT_MATERIALS="<materials>" PYTHONIOENCODING=utf-8 python <script>.py --course <course> ...
```

`--course` 只給讀課程設定的工具：gen_pptx、check_deck、style_check、img_todo、assemble、merge_facts、merge_written、validate_blueprint、check_written、render_pdf_pages、robbins_crop、to_claude_slides。其他工具（make_batches、export_pdf、extract_deck_images、dump_pptx、diff_decks、verify_quotes、check_public、fetch_moex_dent_exam、parse_moex_exam）照各自的用法，不加 `--course`；每支都有 `--help`，用法總表在 `scripts/README.md`。

`<kit>`、`<materials>` 用絕對路徑（先 `pwd`、`ls` 確認；雲端的實際位置以 `ls` 為準）。課程資料夾 = `<materials>/courses/<course>`。

## 2. 依任務的讀法

每個任務都先讀 `docs/教師偏好與決策.md` 與 `style/guide/01_權威順序.md`，再照下表：

| 任務 | 讀 |
|---|---|
| 做新教案 | `docs/SOP_新教案流程.md` → `style/guide/00_README.md` 任務 A → 該課的 `CLAUDE.md`、`brief.md`、`course.yaml` |
| 在他的 deck 上改版、衍生給另一班 | `00_README.md` 任務 B → `30_結構/38_課別差異.md` |
| 回灌他親手改過的稿 | `00_README.md` 任務 C → `40_範例/42_改稿前後對照.md`（EDIT-42）→ SOP 第 11 步 |
| 交付前檢查 | `00_README.md` 任務 D → `50_檢查/52_交付前檢查清單.md` |
| 只改一張、一句或一個標題 | `00_README.md` 任務 E |
| 改工具、檢查器、rules.yaml | `scripts/README.md`、`00_README.md` 任務 F |
| 跑或續跑工作流 | `workflows/README.md`、`docs/lessons_learned.md` |
| 雲端 session、費用 | `docs/cloud_session_教學.md`（第 9 節是費用與額度） |

指南規則衝突照 `01_權威順序.md`；指南以外的舊說法（舊 ENT 專案的 CLAUDE.md「硬規則 v3」、舊記憶檔、v0 rules.yaml）一律以指南為準。指南裡寫的「CLAUDE.md」若指「硬規則 v3」「國考題節」，指的是那份舊 ENT 專案的 CLAUDE.md，不是本檔。

## 3. 硬規則

1. **事實以 Robbins 11e 為唯一正典。** 每一句都要對得到事實帳（facts_R.json）或已查核的文獻（facts_X.json）。文獻只補充、句內或標題括號附出處、不得蓋過 Robbins。Robbins、文獻、老師舊投影片三者衝突時，選一個做法做進成品，並列進「待教師裁決清單」；不靜默改，也不靜默沿用。他的錯字照 `24_術語與中英對照.md` TERM-18 處理。
2. **不寫 LLM 語。** 全形雙破折號（U+2014 連寫兩個）、套語（值得注意的是、讓我們、總而言之、扮演…角色、關鍵在於、不僅…更…）、舞台指示、打氣句、戲劇化第二人稱、貫穿全套的比喻一律不寫。他自己的「其實」「不是 X，而是 Y」「因此」「=>」照用（份量見指南 23、25）。清單以 `20_文字/23_禁用語與LLM語.md` 為準。
3. **字級、中英對照、國考題版式照該課的明令。** 課程有明令（例：immune 的標題 36、內文 28、學生要讀的字 ≥20、出處 14、每張專有名詞「中文(English)」）就照做，寫在該課 course.yaml（`sizes`、`bilingual: per_slide`、`decks.<deck>.quiz_style`）與 brief.md；沒有明令時照指南（`12_字級.md`；中英對照 `bilingual` 不寫＝`first_per_deck`，每套首見一次），不要把某一課的明令套到別的課。`templates/course.template.yaml` 的註解列了沒有明令時的預設字級。
4. **一張講一件事、字少、圖大。** 放不下就拆同標題連張，不縮字；不做學習目標、大綱、總結、謝謝張；不產「圖片待補」佔位張或佔位框，缺圖寫 `<!-- img_wanted: … -->` 進待補圖清單。
5. **只改來源檔，不手改 PPTX。** 來源檔：`sources/*-pool.md`、`*-script.md`、`sources/decks/*.md`、`course.yaml`、`glossary.md`。藍圖與撰寫 JSON 被審查修改超越後，不要再拿它們重跑 `assemble.py`（會蓋掉 pool.md）。
6. **不覆蓋老師親手改過的檔。** 他改過的 PPTX 要先用 `dump_pptx.py`＋`diff_decks.py` 回灌 pool.md，才能重產；產檔前看 `成品/` 有沒有同名檔（gen_pptx 覆寫既有檔時會印「[注意] 覆寫既有檔」），有就換日期或用 `--name`。只是確認環境時用 `--name _smoketest`。
7. **綠燈不算數。** `check_deck.py`、`style_check.py` 全過之後，還要 `export_pdf.py` 出逐張 PNG，一張一張看溢出、孤字、行首標點、被壓小的圖。估算「放得下」的改法要渲染過才算完成。
8. **工作流的代理一律 `model: 'opus'`**，每個 `agent()` 呼叫都寫死，不換其他模型。
9. **已完成的代理不重跑。** Workflow 工具的 `resumeFromRunId` 只在同一台機器、run 的紀錄還在時可用，而且只沿用「從頭算起沒有改動的那一段 agent() 呼叫」：腳本或 args 一改，從第一個不同的呼叫之後全部重跑。跨 session、本機與雲端互換、改過腳本或 args 時，一律用 DONE 標籤表（`args.done = {label: 輸出檔路徑}`）。
10. **額度保護。** 任何代理回傳 null（多半是額度用完）就停止派新代理；把完成清單寫成 DONE 表存檔，告訴使用者停在哪裡。沒有使用者同意不要自動續跑長工作流；每個工作流開跑前先報預計代理數與約略費用（`docs/cloud_session_教學.md` 第 9 節）。
11. **文字檔一律 UTF-8、LF 換行。** 兩個 repo 根目錄都有 `.gitattributes`（`eol=lf`）；Workflow 會拒絕含 `\r` 的腳本；Python 在 Windows 寫檔要 `newline="\n"`。長 heredoc（約 100 行以上）在 Windows 的 Bash 工具會被截斷，大檔用 Write 寫成檔再執行；heredoc 裡的反斜線也可能被改寫，含 `\n`、`\t` 的 Python 程式一樣用 Write。
12. **公開與私人的分界。** Robbins 頁圖、切圖、OCR、事實帳、老師與他人的投影片、語料、成品只放私人 repo；本 repo 不放任何課程內容、個人聯絡方式、教學評量資料或本機絕對路徑。第三人（同事）在公開文件一律用代稱（同事甲、同事乙；對照表只在私人 repo 的 `corpus/pseudonyms.tsv`），他人投影片的引句換成〔他人投影片引句，公開版省略；完整版在私人素材庫 style_evidence〕。**每次 commit 到本 repo 前跑 `python check_public.py`，FAIL 要是 0**（它讀私人 repo 的代稱表與他人段落表，所以要在兩個 repo 都在的環境跑）。
13. **修稿取捨順序**：事實 ＞ 術語 ＞ 版面 ＞ 文風；圖片與國考題的修正讓位（`01_權威順序.md` AUTH-07）。
14. **Traditional Chinese（台灣用語）**：投影片、講稿、文件都用繁體中文；dysplasia 寫「分化不良」。

## 4. 工作流怎麼叫

```text
Workflow({
  scriptPath: "<kit>/workflows/lecture-write.js",
  args: { kit: "<kit>", materials: "<materials>", course: "<course>", ...該工作流的其他參數..., done: {} }
})
```

各工作流的參數、代理數、費用與續跑方法見 `workflows/README.md`。從前一次 run 重建 DONE 表用 `workflows/tools/done_from_journal.py`（讀 journal，或 journal 不見時用 `--scan` 從輸出檔推回 label），不要手動拼。每跑完一個工作流，把 run 的 `journal.jsonl` 與當次 args 複製到 `<materials>/courses/<course>/_archive/journals/`（雲端 VM 回收後 journal 就不見了），重建的 DONE 表也存在那裡。沒有 Workflow 工具時照 `AGENTS.md` 循序做。

## 5. 產出放哪、怎麼交回

- 中間檔：`<materials>/courses/<course>/_archive/{gather,blueprint,written,review,render,journals}/`。
- 成品：`<materials>/courses/<course>/成品/`：PPTX、PDF、同名 `_layout.json`（每張的 slug 與張號，回灌用）、`待教師裁決清單.md`、`待補圖清單.md`。檔名寫課程代碼不寫系名：`病理學{碼}_{講題}(PPTX)_{YYYYMMDD}.pptx`，PDF 同名改 `(PDF)`（`course.yaml` 的 `decks.<deck>.filename`）。
- **雲端交件**：
  1. 在私人 repo 的 session 分支 commit（雲端只能 push 到 session 目前的工作分支）。
  2. `.gitignore` 排除 `成品/*.pptx`，交件那一個檔用 `git add -f` 加入（`_layout.json` 與 PDF 照常加）；先 `ls -l` 確認小於 100 MB（GitHub 上限；超過 50 MB 會警告）。太大就分節輸出（`gen_pptx.py --section N`，檔名自動加「_第N節」，不會蓋掉全套檔）或降低圖片解析度。同一門課只 commit 最後交件的 PPTX，不要每次重產都提交（每版約 60 MB，repo 歷史會一直變大）。
  3. 每跑完一個階段（蒐集、藍圖、撰寫、每一輪審查）就 commit＋push 一次 `_archive/`（含 `journals/`）與來源檔：雲端 VM 閒置會被回收，沒 push 的檔案與正在跑的工作流不會回來。
  4. 最後告訴使用者：分支名稱、成品路徑、張數、檢查結果、待他裁決的項目數。
- 本 repo 的工具若有修改，另外 commit 在本 repo 的 session 分支（先跑 `check_public.py`）；課程檔案絕不 commit 到本 repo。

## 6. 路徑對照（指南與舊文件裡的寫法 → 現在的位置）

| 指南或舊文件寫的 | 現在在哪 |
|---|---|
| `ENT草案/`、`<ROOT>/`（舊專案根目錄） | 本 repo 根目錄（`scripts/`、`style/`、`workflows/`、`question_banks/`、`templates/`） |
| `成品/工具腳本/`（ENT 舊工具：gen_handout.py、gen_teaching_plan.py 等） | 不在任何 repo；ENT 專用的講義與教案產生器沒有搬過來，現行工具只有 `scripts/` |
| `_archive/backup/…`（ENT 舊專案的備份，例 `style_evidence_20260907/`） | 不在任何 repo；需要的證據已整理進 `<materials>/corpus/edits/` 與 `<materials>/style_evidence/` |
| `immune/…`、`<課程>/…` | `<materials>/courses/immune/…`、`<materials>/courses/<課程>/…` |
| `immune/_archive/robbins_png/` | `<materials>/textbook/robbins11e_ch06_immune/pages/`（`pNN_PPP.jpg`＋`.txt`＋`.tsv`；印刷頁 = PDF 頁 + 166）；course.yaml 的 `textbook.pages_dir` |
| `style/corpus/`（decks/、edits/、index.md、corpus_list.tsv） | `<materials>/corpus/` |
| `style/_work/mining/`、`style/_work/writer_brief_immune.md`、`prior_findings_20260924.md`、`rhy_metrics.py` | `<materials>/style_evidence/`（mining/、writer_brief_immune.md、prior_findings_20260924.md、rhy_metrics.py） |
| `style/guide/_review/` | `<materials>/style_evidence/guide_review/` |
| 同事甲、同事乙（指南裡的代稱）；`other_同事甲_…` 代號 | 真名與語料檔名的對照在 `<materials>/corpus/pseudonyms.tsv`；未遮蔽的指南全文在 `<materials>/style_evidence/guide_full_20260925/` |
| `workflows/journals/`、`workflows/resume/` | `<materials>/courses/<課程>/_archive/journals/`（見第 4 節） |
| 舊專案 CLAUDE.md、本機記憶檔 | `docs/教師偏好與決策.md`、`docs/lessons_learned.md`、`style/guide/` |

## 7. 其他

- 不確定老師要什麼時，照 `style/guide/50_檢查/51_撰寫前檢查清單.md` A 段的預設做，並把問題列進待教師裁決清單；不要停下來等。
- 課程 immune（病理學C 免疫疾病，牙醫系三年級，2026-10-02）是第一套照整條管線做完的課，當範例看：`<materials>/courses/immune/`；公開的精簡範例在 `examples/immune/`。
- 開新課的課程指引範本：`templates/course.CLAUDE.template.md`。

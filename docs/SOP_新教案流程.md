# SOP：新教案從頭到交付

從「老師給一個主題和教科書章節」到「交出 PPTX＋PDF＋待教師裁決清單」，再到「老師改稿後回灌」的完整步驟。每一步寫明指令、用哪個工作流、預期產出，以及要老師決定的檢查點（標 **【老師決定】**）。範例課程是私人 repo 的 `courses/immune/`（病理學C 免疫疾病，184 張）。

## 總表

| 步 | 做什麼 | 工具或工作流 | 代理數（immune 實數，供估費用） | 老師決定 |
|---|---|---|---|---|
| 0 | 開工問答、建課程資料夾 | `templates/`、`51_撰寫前檢查清單.md` | 0 | 【老師決定】規格 |
| 1 | 教科書轉頁圖＋OCR | `render_pdf_pages.py` | 0 | |
| 2 | 切圖、抽舊投影片的圖 | `robbins_crop.py`、`extract_deck_images.py` | 0 | |
| 3 | 國考題庫（多半已有） | `fetch_moex_dent_exam.py`、`parse_moex_exam.py` | 0 | |
| 4 | 蒐集事實、選題、文獻 | `lecture-gather.js` → `merge_facts.py` | 97（更新題庫時 98） | 衝突清單（不擋進度） |
| 5 | 藍圖 | `lecture-blueprint.js` → `validate_blueprint.py` | 10 | 【老師決定】大綱（建議） |
| 6 | 撰寫與組裝 | `make_batches.py` → `lecture-write.js` → `merge_written.py` → `assemble.py` | 57（11 批 × 5＋連貫性 1＋讀檔 1） | |
| 7 | 產檔、檢查、看 PNG | `gen_pptx.py`、`style_check.py`、`export_pdf.py`、`img_todo.py` | 0 | |
| 8 | 審查 | `lecture-review.js`（每輪） | 19／輪（沒給 pngs 時 20） | |
| 9 | 交付前檢查、裁決清單 | `52_交付前檢查清單.md` | 0 | |
| 10 | 交付 | git 或直接給檔 | 0 | 【老師決定】回覆裁決清單 |
| 11 | 回灌老師改稿 | `dump_pptx.py`＋`diff_decks.py` | 0 | |

一門三節約 180 張的課，工作流合計約 200 個代理（兩輪審查）；以 API 牌價換算約 $950–1,200，只做一輪審查約 $830–990。各階段的單價與「這些金額和方案用量、usage credits 的關係」見 `docs/cloud_session_教學.md` 第 9 節，公式見 `workflows/README.md`。風格挖掘（`style-mining.js`，約 89 個）與重寫風格指南（`style-guide.js`，約 49 個）已經做完，新教案不必重跑（只有新課程的撰寫 brief 要跑 1 個代理，見第 6 步）。

## 指令寫法

先設定三個變數（每開一個新 shell 都要設）：

```bash
KIT="<kit 的絕對路徑>"            # 例：Windows Git Bash 的 /d/work/pathology-slide-kit
MAT="<materials 的絕對路徑>"      # 例：/d/work/pathology-slide-materials
C=<課程資料夾名>                  # 英文小寫，例：immune、lung、ent
CD="$MAT/courses/$C"
```

下文 `[py] xxx.py …` 一律代表（只有讀課程設定的工具才加 `--course`，清單見 `scripts/README.md`；Linux 沒有 `python` 時用 `python3`）：

```bash
cd "$KIT/scripts" && SLIDEKIT_MATERIALS="$MAT" PYTHONIOENCODING=utf-8 python xxx.py …
```

PowerShell 的寫法：`$env:SLIDEKIT_MATERIALS="<materials>"; $env:PYTHONIOENCODING="utf-8"; cd <kit>\scripts; python xxx.py …`。

工作流用 Claude Code 的 Workflow 工具執行，參數一律 `{kit, materials, course, …, done}`，`kit`、`materials` 用絕對路徑。各工作流的完整參數見 `workflows/README.md`。沒有 Workflow 工具時照 `AGENTS.md` 第 4 節循序做。

---

## 第 0 步：開工問答與課程資料夾

**老師要給的**：主題、課程代碼（A1–A4、B1、B2、C…）、對象、上課日期、節數與每節要講完的時間、教科書章節（通常是 Robbins 11e 某一章的 PDF）、他最近一版的同講題投影片（若有）。

**要問他的事**（`style/guide/50_檢查/51_撰寫前檢查清單.md` A 段；沒回覆就照預設做，並寫進待教師裁決清單）：

1. 張數與節數（預設一講 75–113 張、約一分鐘一張）；
2. 有沒有底稿可沿用；
3. 考哪一種國考、放幾題（A 班醫師國考 0–7 題；B 班不放醫師題；C 班先問）；
4. 國考題版式與正解顏色；
5. 畫幅（預設沿用該系列，新系列 4:3）；
6. 字級有沒有明令；
7. 中英對照的範圍（每套首見一次，或每張都要）；
8. 正典與文獻範圍；
9. 出處放哪裡；
10. 關鍵字色；
11. 古籍與中醫內容要不要；
12. 圖片來源與借同事的圖；
13. 開場的「國考重要性」判斷由誰下；
14. Robbins 表格貼截圖還是改原生表格。

**建資料夾**：

```bash
mkdir -p "$CD"/sources/decks "$CD"/facts/seg "$CD"/assets/images "$CD"/_archive "$CD"/成品
cp "$KIT/templates/course.template.yaml" "$CD/course.yaml"
cp "$KIT/templates/brief.template.md"    "$CD/brief.md"
cp "$KIT/templates/gather.template.json" "$CD/gather.json"
```

填 `course.yaml`（課程代碼、對象、日期、`textbook` 的 ref／page_offset／pages_dir（PDF 放 repo 外，`textbook.pdf` 寫絕對路徑）、`paths`、`decks`（節數、目標張數、每節範圍、國考題庫、國考題版式 `quiz_style`、檔名）、`sizes`（沒有字級明令就用範本註解裡「沒有明令時的預設」，不要照抄 immune 的明令值）、`bilingual`（沒有「每張中英」明令就刪掉或寫 `first_per_deck`）、`emphasis`、`cover`、`bilingual_whitelist`）；填 `brief.md` 的「教師已裁決」表（每列寫日期）；從 `templates/course.CLAUDE.template.md` 複製一份課程專屬的 `CLAUDE.md`（課程、裁決、單一事實來源、重產指令、待辦）：

```bash
cp "$KIT/templates/course.CLAUDE.template.md" "$CD/CLAUDE.md"
```

**【老師決定】** 規格表。明令只寫進這門課的 course.yaml、brief.md、glossary.md，不改風格指南的一般規則。

## 第 1 步：教科書轉頁圖＋OCR

教科書 PDF **不要 commit**（Robbins 單章掃描檔常超過 100 MB，GitHub 推不上去，也涉及著作權；私人 repo 的 `.gitignore` 已排除成品以外的所有 PDF）。PDF 放在 repo 以外的資料夾。在有 PDF 的電腦（通常是老師的 Windows）做這一步，把頁圖 commit 進私人 repo。這一步要裝 Tesseract（Robbins 章節是掃描檔，OCR 的 `.txt`／`.tsv` 是切圖與蒐集代理的依據）。

```bash
# page_offset = 印刷頁 − PDF 頁（immune：PDF 第 1 頁 = 印刷頁 167，offset 166）
[py] render_pdf_pages.py "<章節.pdf>" "$MAT/textbook/<書>_<章>/pages" --offset <K>
#   預設 jpg、不出上下半頁（教材庫的格式）；可加 --pages 1-5（試跑）；dpi 保持預設 200（切圖工具以 200 dpi 頁圖找圖說）
# course.yaml 已填 textbook.pdf、pages_dir、page_offset 時可簡寫：
[py] render_pdf_pages.py --course $C
```

- 資料夾名例：`robbins11e_ch06_immune`、`robbins11e_ch15_lung`。
- 產出：`pNN_PPP.jpg`（NN＝PDF 頁、PPP＝印刷頁）、`.txt`（OCR 文字）、`.tsv`（字詞座標）。`--format png`、`--halves`（另出上下半頁）只在特殊需要時用，檔案大約 3 倍，不要存進 repo。
- 在 course.yaml 設 `textbook.pages_dir: ../../textbook/<書>_<章>/pages`（相對於課程資料夾）。

## 第 2 步：切圖、抽舊投影片的圖

```bash
[py] robbins_crop.py --course $C --chapter <章號> --out "$CD/assets/images/Robbins抽圖" --expect <圖數> \
     [--ovr "$CD/assets/images/Robbins抽圖/ovr.json"]
# 或全部寫明：--pdf "<章節.pdf>" --pages-dir "$MAT/textbook/<書>_<章>/pages" --offset <K>
```

- 有 PDF 時以 300 dpi 從 PDF 重切（最清楚）；沒有 PDF（例如雲端只有頁圖）時直接從 200 dpi 頁圖裁切。
- 產出：`figN_M.png`、多面板另拆 `figN_M_1.png`…、`tableN_M.png`、`index.json`、`圖片清單.md`（檔案、圖號、頁碼、圖說開頭；藍圖代理靠它找圖；資料夾裡已有手寫的清單時改寫 `圖片清單_auto.md`）、`contact_*.png`（縮圖拼板）。`--out` 資料夾裡不在 index 內的 fig／table 舊檔會被刪除，不要指到別的用途的資料夾。
- 各圖片資料夾都齊了之後，在 `$CD/assets/images/圖片總表.md` 寫一段總覽（每個子資料夾放什麼、授權、哪些是他人的圖與致謝方式）；藍圖代理先讀它。
- 一定要看 contact 拼板。OCR 抓不到圖說（側邊圖說、反白圖說）或切錯的圖，在 `ovr.json` 手動給 200 dpi 的像素座標後重跑；其他鍵（塗白、面板座標、補圖說、丟碎片）見 `robbins_crop.py` 開頭說明。immune 46 圖＋17 表中，19 張圖與全部表格用了手動座標。

老師或同事的舊投影片：

```bash
[py] extract_deck_images.py "<舊.pptx>" "$CD/assets/images/舊講義抽圖" --code <代號> [--slides 1-47] [--author <作者>]
```

產出圖檔與 `圖片清單.md`。借用同事的圖，封面主標下加一行致謝即可，不必逐張標；舊講義的截圖常是 Robbins 舊版的圖，出處要寫 Robbins。

## 第 3 步：國考題庫

醫師（題號 76–100 病理段）與牙醫師（牙醫學(二)）題庫已在 `question_banks/`。要補新一年的題，見 `question_banks/README.md`。在 course.yaml 的 `decks.<deck>.question_bank` 指定 `醫師` 或 `牙醫師`；不放國考題的班設 `exam: false`。

## 第 4 步：蒐集（事實帳、選題、文獻）

先編輯 `$CD/gather.json`（格式與 immune 的範例值見 `templates/gather.template.json`）：教科書分段（每段約 4–7 頁、寫明起訖標題）、國考題分類設定、文獻題目。三部分都可以關掉不跑。

```text
Workflow({ scriptPath: "<kit>/workflows/lecture-gather.js",
           args: { kit: "<kit>", materials: "<materials>", course: "<course>", done: {} } })
```

可選參數（省額度或補跑一部分時用）：`parts: ["facts","exam","literature"]` 只跑其中幾部分、`segments: ["S01", …]` 只跑某幾段、`topics: ["<id>", …]` 只跑某幾個文獻題目、`refuters: 1`（預設 2）。

產出：`facts/seg/<段>_final.json`（每段經兩位反駁者與一位裁決者）、`_archive/gather/exam/exam_candidates.json`、`_archive/gather/lit/<題>_verified.json` 與 `_images.json`（開放授權圖放 `assets/images/文獻圖/`）。然後：

```bash
[py] merge_facts.py --course $C      # → facts/facts_R.json、facts_X.json、facts/facts.md
```

**檢查點**：Robbins 自相矛盾、Robbins 與文獻衝突的項目，先選一個做法（原則上照 Robbins），記進待教師裁決清單 A 組；不必等老師回覆。

雲端注意：文獻查核要連 PubMed／NCBI、找開放授權圖要連 Wikimedia Commons、CDC PHIL、PMC，題庫下載要連考選部，這些網站不在 Trusted 網路的預設名單；需要時把環境改成 Custom 並加網域（清單在 `docs/cloud_session_教學.md` §3.2），或在本機做這一部分。題庫已經有了就維持 gather.json 的 `exam.update_bank: false`（不下載）；`parts` 拿掉 `exam` 則是連選題都不做。

## 第 5 步：藍圖

```text
Workflow({ scriptPath: "<kit>/workflows/lecture-blueprint.js",
           args: { kit: "<kit>", materials: "<materials>", course: "<course>", done: {} } })
```

流程：glossary → 三個視角草稿 → 三位評審 → 綜合 → 批評 → 修訂。張數、節數、每節範圍、分鐘、國考題數、有圖率沒給時，代理從 course.yaml 與 brief.md 讀；也可以用 `total`、`sections`、`per_section`、`minutes`、`quiz`、`img_rate` 直接指定，`judges`（預設 3）、`lenses` 可調。產出 `_archive/blueprint/blueprint.json`（每張：slug、type、img、fact_ids、lit_ids、quiz、brief、build；格式見 `templates/blueprint.schema.json`）、`diagrams.yaml`，以及課程的 `glossary.md`。完整參數見 `workflows/README.md`。

```bash
[py] validate_blueprint.py --course $C "$CD/_archive/blueprint/blueprint.json" --diagrams "$CD/_archive/blueprint/diagrams.yaml"
```

RED 為 0 才往下（欄位、圖檔存在、國考 key 在題庫、框架圖、各節張數與分鐘、有圖率）。把 `diagrams.yaml` 的框架圖併進 course.yaml 的 `diagrams`。

**【老師決定】（建議）** 把藍圖摘要（各節張數、分鐘、有圖率、國考題清單、段落順序；工作流沒產 `blueprint_summary.md` 時，從 blueprint.json 整理一份）給老師看。這是改範圍最便宜的時間點：改藍圖只要重跑修訂（1 個代理），撰寫之後再改就要重寫。做法：他的決定寫進 brief.md，原話存成 `_archive/blueprint/teacher_notes_<日期>.md`，用 `done_from_journal.py --scan blueprint --drop revise` 重建 DONE 表、args 加 `teacher_notes`，再叫一次 lecture-blueprint（細節見 `workflows/README.md`「老師看過藍圖後修訂」）。

## 第 6 步：撰寫與組裝

```bash
mkdir -p "$CD/_archive/written"
[py] make_batches.py "$CD/_archive/blueprint/blueprint.json" "$CD/_archive/written/batches.json" --size 16
```

`batches.json` 的內容是 `{"batches":[{k, slugs, segments, prev, next}, …]}`；同標題連張不拆開，盡量在段落邊界切。放在 `_archive/written/batches.json` 時，工作流會自己讀，不必傳 `batches`。

```text
Workflow({ scriptPath: "<kit>/workflows/lecture-write.js",
           args: { kit: "<kit>", materials: "<materials>", course: "<course>", done: {} } })
```

藍圖不在預設位置時加 `blueprint`；要分次跑，就用 `batches` 只傳其中幾批（陣列，或 `{"batches":[…]}`），或用 `batches_file` 指到另一個檔。撰寫與審查的代理若找得到私人 repo 的 `style_evidence/writer_brief_<課程>.md` 就會讀（課程專用的風格 brief；immune 有一份可以參考），沒有也能跑，以風格指南為準。建議新課程在撰寫前花 1 個代理產一份：沿用 22 個面向的挖掘結果，只跑 `style-mining.js` 的 brief 代理（步驟見 `workflows/README.md`「新課程的撰寫 brief」）。

每批：撰寫 → 事實、老師語氣、中英術語與密度三位查核 → 修訂（`check_written.py` RED 0）；最後一位通讀全套做連貫性。產出 `_archive/written/batch_<k>.json`、`continuity_report.md`。

```bash
[py] merge_written.py --course $C --dir "$CD/_archive/written" --blueprint "$CD/_archive/blueprint/blueprint.json"
[py] assemble.py --course $C "$CD/_archive/blueprint/blueprint.json" "$CD/_archive/written/written.json" --dry-run
[py] assemble.py --course $C "$CD/_archive/blueprint/blueprint.json" "$CD/_archive/written/written.json"
```

產出來源檔：`sources/<主題>-pool.md`、`sources/<主題>-script.md`、`sources/decks/<deck>.md`；glossary 新詞併入 `glossary.md`，撰寫者提出的問題彙整成 `_archive/written/issues.md`。有 RED 時 assemble 不寫檔。

**從這一步起，來源檔是唯一的真相。** 審查會直接改 pool.md，之後不要再用藍圖或撰寫 JSON 重跑 assemble。

## 第 7 步：產檔、檢查、看 PNG

```bash
[py] gen_pptx.py --course $C                  # 可加 --date YYYYMMDD、--section N（檔名自動加 _第N節）、--name 檔名；自動跑 check_deck
[py] style_check.py --course $C               # RED 必須 0
[py] export_pdf.py "$CD/成品/<檔名>.pptx" --pdf "$CD/成品/<PDF 檔名>.pdf" \
     --sheets "$CD/_archive/render/sheets" --pngs "$CD/_archive/render/png"
[py] img_todo.py --course $C                  # → 成品/待補圖清單.md
```

- check_deck 要 ALL GREEN（字級、每張字元、有圖率、佔位字、靜態頁碼、國考 key、估算溢出）。
- **逐張看 PNG**：溢出、孤字、行首標點、英文字被斷行、圖太小、圖說壓到出處。檢查器全綠仍常有這些問題。
- Windows 用 PowerPoint 匯出；雲端用 LibreOffice，字型換成 Noto，斷行可能和 PowerPoint 略有不同，交件前最好在 Windows 的 PowerPoint 再看一次。
- 發現問題改來源檔，重跑本步。

## 第 8 步：審查（一到兩輪）

```text
Workflow({ scriptPath: "<kit>/workflows/lecture-review.js",
           args: { kit: "<kit>", materials: "<materials>", course: "<course>",
                   pptx: "<成品 PPTX 絕對路徑>", pngs: "<課程資料夾>/_archive/render/png",
                   round: 1, done: {} } })
```

沒給 `pngs` 時，工作流先派一個代理跑 `export_pdf.py` 產 PNG。可選：`lenses: ["facts","layout"]` 只審某幾個面向、`refuters: 1`（預設 2）、`sheets`（縮圖拼板資料夾）。

六個面向（事實、語氣與 LLM 語、中英術語、版面 PNG、國考題、圖）各一位審查＋兩位反駁，最後一位修正者只套用至少一位反駁者確認的項目，直接改來源檔並重產。報告在 `_archive/review/round1/fix_report.md`（確認幾條、套用幾條、未套用的理由、要老師決定的事）。

之後重跑第 7 步。immune 第一輪 206 條確認 192 套用 173，第二輪 129 條確認 126 套用 117；第二輪的邊際效益明顯較低，額度緊時做一輪即可，或第二輪只審問題多的面向（例：`lenses: ["layout","facts"]`）。

## 第 9 步：交付前檢查與待教師裁決清單

照 `style/guide/50_檢查/52_交付前檢查清單.md` 逐項過。再寫 `成品/待教師裁決清單.md`（格式照 `38_課別差異.md` AUD-36，範例 `courses/immune/成品/待教師裁決清單.md`）：

- 開頭：投影片檔名、張數與各節範圍、國考題數；張號以 slug 為準的說明。
- 「怎麼回覆」：每項後面寫「同意」「改成……」或「刪」，也可以直接改 PPTX。
- 「上課前最好先回」：列出會影響上課的少數幾項。
- 分組：A 事實與教科書衝突、B 國考題、C 圖片（授權、待補、暫代）、D 用字與譯名、E 版面與格式偏好、F 他舊投影片的錯誤、G 其他。每項寫張號與 slug、「目前」怎麼做（已做進成品）、回覆欄。

## 第 10 步：交付

成品在 `$CD/成品/`：`病理學{碼}_{講題}(PPTX)_{YYYYMMDD}.pptx`、同名 `(PDF)`、`待教師裁決清單.md`、`待補圖清單.md`。日期用上課日（course.yaml `lecture_date`）。

- **Windows 本機**：直接告訴老師檔案位置。
- **雲端 session**：在私人 repo 的 session 分支

  ```bash
  cd "$MAT"
  ls -l "courses/$C/成品/"                               # PPTX 必須 < 100 MB
  git add -f "courses/$C/成品/<檔名>.pptx"                 # .gitignore 排除 PPTX，交件檔要 -f（同名 _layout.json 與 PDF 照常加）
  git add "courses/$C/成品/" "courses/$C/sources/" "courses/$C/_archive/" "courses/$C/glossary.md" "courses/$C/course.yaml"
  git commit -m "<課程> 交付 <日期>：<張數> 張"
  git push
  ```

  回報分支名稱與檔案路徑；老師從 GitHub 網頁下載或 `git pull`（見 `docs/cloud_session_教學.md`）。

  同一門課只提交最後交件的那一版 PPTX（每版約 60 MB，每提交一次 repo 歷史就多 60 MB）；中途給老師看的版本用 PDF。要保留多個版本時，把 PPTX 放到 GitHub Release 的附件，不放進 git。

**【老師決定】** 他回覆裁決清單，或直接改 PPTX。

## 第 11 步：回灌老師的改動

### 11a. 他回覆了裁決清單

逐項改來源檔（pool.md、script.md、decks、course.yaml、glossary.md），重跑第 7 步，在清單上標「已處理」。事實類的改動先對 Robbins 頁碼。

### 11b. 他直接改了 PPTX

他改過的檔是最高權威（`01_權威順序.md`），而且**重產會蓋掉他的版本**，所以一定先回灌：

```bash
# 1. 傾印我交的版本與他改後的版本（代號規則：{年}_{課程碼}_{主題}_{MMDD}；我的加 mine_ 前綴）
[py] dump_pptx.py "<我交的.pptx>"  "$MAT/corpus/decks/mine_<主題>_<MMDD>"
[py] dump_pptx.py "<他改後.pptx>"  "$MAT/corpus/decks/<年>_<碼>_<主題>_<MMDD>"
# 2. 逐張比對（只比一部分時加 --range a-b）
[py] diff_decks.py "$MAT/corpus/decks/mine_<主題>_<MMDD>.json" "$MAT/corpus/decks/<年>_<碼>_<主題>_<MMDD>.json" \
     "$MAT/corpus/edits/<主題>_<我的張數>_to_教師<他的張數>.md" --layout "$CD/成品/<我交的檔名>_layout.json"
```

回灌規則（`42_改稿前後對照.md` EDIT-42）：

1. 新舊張配對以 slug 為準：`diff_decks.py` 以全文相似度配對新舊張，加 `--layout` 就會在每個「原#N」標出 slug，並列一張「新#→原#→slug」對照表（layout 檔隨交件一起 commit，新 clone 也有）；舊專案沒有 layout 檔時用備註表頭「投影片 N｜」。相似度低於約 0.6 的配對要人工確認。
2. 他改的標題、條列、表格寫回對應 slug；他新增的張給新 slug 並加進選單；他複製出的同標題連張，每張各自一個 slug、各存各的內容。
3. 他刪的張：從 `sources/decks/<deck>.md` 拿掉；若素材池由多個班別共用，只拿掉該班的 `aud`，不要刪 slug。
4. **不要把 PPTX 的備註寫回 script.md**（他不讀也不改備註，新增張的備註多半是複製殘留）。
5. 清掉他用圖蓋住但還留在檔內的佔位文字。
6. 他改的事實也要對 Robbins；有疑點列清單問他，不靜默採用或還原。
7. 回灌後重產，再 `diff_decks.py` 比一次「他的版本」與「重產版本」，除了刻意的修正外應該一致。

然後把新證據放進語料與風格指南（`style/guide/00_README.md`「版本與更新規則」；語料在私人 repo 的 `corpus/`）：

1. `corpus/corpus_list.tsv` 加一行「代號<TAB>pptx 路徑」；
2. 更新 `corpus/index.md` 的語料表與改稿對照表；
3. 依改動更新 `style/guide/` 對應主題檔的規則、正例、反例與證據強度，改 `last_verified`；被推翻的說法補進 `01_權威順序.md`；
4. 改到機械檢查的規則就同步 `style/rules.yaml`，新 regex 先對他自製的檔跑一次，會誤殺他的句子就降級；
5. `[py] verify_quotes.py` 核對全部引句，FAIL 修到 0；
6. 他沒動到的張不算「接受」（AUTH-03）；某課的明令只更新該課。

風格指南的更新 commit 在公開 kit（commit 前跑 `[py] check_public.py`，FAIL 0；新證據裡有同事的名字就用代稱，並把對照加進 `$MAT/corpus/pseudonyms.tsv`）；語料與 edits commit 在私人 repo。

---

## 常見錯誤

| 症狀 | 原因與處理 |
|---|---|
| `KeyError 選單引用不存在的 slug` | decks/<deck>.md 與 pool.md 不同步；重跑 assemble（只在第 6 步）或手改選單 |
| 中文亂碼、`UnicodeEncodeError: 'cp950'` | 沒設 `PYTHONIOENCODING=utf-8` |
| `find_materials()` 回 None | 私人 repo 不在 kit 旁邊；設 `SLIDEKIT_MATERIALS` |
| PowerPoint 匯出失敗 | 先關掉開著的同名 PPTX；沒有 PowerPoint 時改用 LibreOffice |
| Workflow 拒絕腳本 | 檔案含 `\r`（CRLF）；見 `docs/lessons_learned.md` |
| 素材池註解被截斷 | `<!-- … -->` 裡寫了 `>`（例如 `=>`），註解裡不要用 |
| 重產後老師的修改不見了 | 沒先做第 11b 步；從 git 歷史或老師的檔找回，回灌後再重產 |

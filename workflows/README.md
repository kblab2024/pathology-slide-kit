# workflows/：多代理工作流

用 Claude Code 的 Workflow 工具執行。六支通用工作流都吃同一組參數 `{kit, materials, course, ...}`，路徑全部由參數組出來，腳本裡沒有任何本機路徑，所以同一支腳本在 Windows 本機與雲端 session（Ubuntu）都能跑。

| 檔案 | 做什麼 | 主要產出（都在教材庫） |
|---|---|---|
| `lecture-gather.js` | 教科書逐段抽事實（抽取 → 2 反駁 → 裁決）、國考題分類與選題（2 分類 → 查核選題）、文獻搜尋 → PubMed 查核 → 開放授權圖；三部分各自可關，設定在課程的 `gather.json` | `courses/<課>/facts/seg/S??_final.json`、`_archive/gather/exam/exam_candidates.json`、`_archive/gather/lit/*_verified.json`、`assets/images/文獻圖/` |
| `lecture-blueprint.js` | 用語表＋3 個視角各寫一份完整藍圖 → 3 評審 → 綜合＋驗證 → 完整性批評 → 修訂 | `courses/<課>/glossary.md`、`_archive/blueprint/blueprint.json`、`diagrams.yaml`、`blueprint_summary.md` |
| `lecture-write.js` | 每批（約 16 張）撰寫 → 事實／教師聲音／術語與密度 3 查核 → 修訂；最後全套連貫性編修 | `courses/<課>/_archive/written/batch_<k>.json`、`continuity_report.md` |
| `lecture-review.js` | 成品 6 面向審查（事實、聲音、術語、版面 PNG、國考、圖）→ 每面向 2 反駁 → 1 位修正者改來源檔並重產 | `courses/<課>/_archive/review/round<N>/`、修改後的 pool.md 等來源檔 |
| `style-mining.js` | 從語料（他的 deck 傾印＋改稿對照）挖風格規則：每面向 1 挖掘 → 2 反駁 → 1 修訂（預設 22 面向）；給 course 時再寫該課撰寫 brief | `style_evidence/mining/<面向>_final.json/.md`、`style_evidence/writer_brief_<課>.md` |
| `style-guide.js` | 由挖掘結果寫公開的風格指南：每檔撰寫 → 一致性＋完整性批評 → 逐檔修訂 → 索引、檢查清單、`style/rules.yaml` | 工具包 `style/guide/`、`style/rules.yaml`；批評紀錄在 `style_evidence/guide_review/` |

其他檔案：
- `tools/done_from_journal.py`：從執行紀錄重建 DONE 表（見「續跑」）。
- `tools/check_workflows.js`：改完腳本後跑 `node workflows/tools/check_workflows.js`，檢查 CR 字元、禁用字、本機絕對路徑、meta 是否為純字面值、語法（照 Workflow 執行環境包起來編譯），並用假代理把每支工作流空跑一遍、核對代理數。
- `reference/`：2026-09 免疫課程的三支原版腳本（已去除本機路徑），只供對照；新課程用上面的通用版。
- 範本在 `../templates/`：`course.template.yaml`、`brief.template.md`、`gather.template.json`、`blueprint.schema.json`、`written.schema.json`。

## 共通規則
- **所有代理一律 `model: 'opus'`**，寫死在每支腳本的代理呼叫裡。
- **參數**：`kit`＝工具包根目錄（含 `scripts/`），`materials`＝教材庫根目錄（含 `courses/`、`textbook/`、`corpus/`、`style_evidence/`），`course`＝`materials/courses/` 下的資料夾名。三者缺一（style-mining、style-guide 的 course 可省）就只寫一行說明並結束，不派任何代理。路徑用正斜線（`D:/...`），反斜線也會被換掉，但 JSON 裡要寫成 `\\`，容易出錯。
- **代理呼叫腳本的固定寫法**：`cd "<kit>/scripts" && SLIDEKIT_MATERIALS="<materials>" PYTHONIOENCODING=utf-8 python <script>.py --course <course> ...`（代理用 Bash 工具；Windows 是 Git Bash；雲端找不到 `python` 時用 `python3`）。不收 `--course` 的工具（make_batches、export_pdf、verify_quotes 等）不加，清單見 `scripts/README.md`。
- **風格指南與國考題庫在工具包**（`style/guide/`、`question_banks/<題庫>/`）；**課程檔、教科書頁圖、語料、風格證據在教材庫**。
- 每個代理把成果**寫成檔案**，回傳 `{path, count, notes}`。
- **額度保護**：任何代理回傳 null（多半是額度用完或被略過）就停止派新代理，log 會出現 `ABORT`，之後用 DONE 表續跑。
- **共用選項**：`effort`（例 `"medium"`，傳給每個代理；省錢但品質未實測）、`done`（DONE 表）。gather、review、mining 另有 `refuters`（預設 2，可設 1–3）。

## 各工作流的參數

| 工作流 | 必填 | 選填（預設） |
|---|---|---|
| lecture-gather | kit, materials, course | `gather`（直接給設定物件；預設讀 `<課>/gather.json`）、`gather_file`、`parts`（`["facts","exam","literature"]` 的子集）、`segments`（例 `["S01","S02"]`）、`topics`（文獻主題 id）、`refuters`、`effort`、`done` |
| lecture-blueprint | kit, materials, course | `deck`、`total`、`sections`、`per_section`（`[lo,hi]`）、`minutes`（40）、`quiz`（文字，例 `"10-15 in total, 3-5 per section"`）、`img_rate`（0.65）、`slug_prefix`（課程名）、`lenses`（`[{id, d}]`，預設 audience／textbook／teacher 三視角）、`judges`（3）、`out`、`corpus`（預設 `<materials>/corpus`）、`pages`（教科書頁圖資料夾，預設讀 course.yaml）、`teacher_notes`（老師對藍圖摘要的意見：檔案路徑或文字，修訂代理最優先套用；見「老師看過藍圖後修訂」）、`effort`、`done`；張數沒給就用 course.yaml `decks.<deck>` 的 target／sections／per_section |
| lecture-write | kit, materials, course | `batches`（make_batches.py 的陣列）或 `batches_file`（預設 `<課>/_archive/written/batches.json`，由一個讀檔代理讀進來）、`blueprint`、`out`、`writer_brief`（預設 `style_evidence/writer_brief_<課>.md`，沒有就只用風格指南）、`pages`、`effort`、`done` |
| lecture-review | kit, materials, course, pptx | `round`（1）、`deck`、`pngs`／`sheets`（沒給就先派一個代理跑 export_pdf.py 產圖）、`lenses`（6 面向的子集）、`refuters`、`out`、`writer_brief`（預設 `style_evidence/writer_brief_<課>.md`）、`pages`（教科書頁圖資料夾，預設讀 course.yaml）、`effort`、`done` |
| style-mining | kit, materials | `course`（給了才寫撰寫 brief）、`dims`（面向 id、前綴或 `{id,p,f}` 物件；預設 22 面向）、`corpus`、`out`、`date`、`refuters`、`effort`、`done` |
| style-guide | kit, materials | `course`（把該課的教師明令與審查教訓併入）、`files`（只重寫這些檔，例 `["12_字級"]`）、`date`（frontmatter 的 last_verified）、`mining`、`corpus`、`effort`、`done` |

## 怎麼叫用（可直接複製）

在 Claude Code 對話裡說「用 Workflow 工具執行」並貼上呼叫。

**Windows 本機**（兩個 repo 並排 clone 在 `D:/localcode/`；位置不同就改路徑）：
```
Workflow({scriptPath: "D:/localcode/pathology-slide-kit/workflows/lecture-write.js",
          args: {kit: "D:/localcode/pathology-slide-kit",
                 materials: "D:/localcode/pathology-slide-materials",
                 course: "immune"}})
```

**雲端 session**（session 同時加入兩個 repo；先用 `ls ~` 或 `pwd` 確認 clone 位置，下面以 `/home/user/` 為例）：
```
Workflow({scriptPath: "/home/user/pathology-slide-kit/workflows/lecture-gather.js",
          args: {kit: "/home/user/pathology-slide-kit",
                 materials: "/home/user/pathology-slide-materials",
                 course: "immune", parts: ["facts"], segments: ["S01", "S02"]}})
```
雲端注意事項：
- 雲端讀得到 repo 裡的 CLAUDE.md，讀不到本機的記憶檔；要讓代理知道的事寫進 `brief.md`、`course.yaml` 或風格指南。
- 成果要 commit 並 push 到分支才會回到本機；工作流結束後請 Claude 在教材庫 commit（連同執行紀錄，見「續跑」）再 push。單檔上限 100 MB：逐張 PNG、PDF 草稿、下載的考題原始 PDF 視需要排除。
- 文獻查核、找開放授權圖與國考下載需要連外網；要加進 Custom 網路的網域清單見 `docs/cloud_session_教學.md` §3.2（PubMed／NCBI／PMC、Wikimedia Commons、CDC PHIL、doi.org、考選部）。環境的網路政策不允許時，把 `parts` 限成 `["facts"]`，文獻部分在本機做。
- 雲端沒有 PowerPoint 與微軟正黑體：export_pdf.py 改用 LibreOffice＋Noto CJK 算圖，換行位置和 PowerPoint 略有不同；版面審查以 `*_layout.json` 估算為主，交件前在 Windows 用 PowerPoint 再看一次。
- Workflow 工具在雲端 session 能不能用、能同時跑幾個代理（Workflow 工具的並行上限約是 min(16, CPU 數 − 2)，雲端 VM 的 CPU 數不確定，可能比本機慢），都還沒有實測。第一次在雲端跑時先用小範圍（例 lecture-gather 只給 `segments: ["S01"]`）試。沒有 Workflow 工具時，照 `AGENTS.md` 第 4 節循序做，或請 Claude 讀腳本、照同樣的提示逐一派子代理；DONE 表與代理數控管要自己盯。

## 代理數與費用（估算用）

代理數由設定決定（R＝refuters，預設 2）：

| 工作流 | 代理數公式 | 免疫課實例 |
|---|---|---|
| lecture-gather | 1（讀設定）＋ 段落數 ×(2＋R) ＋ 國考 3（更新題庫再＋1）＋ 文獻主題數 × 3（不找圖的主題 × 2） | 13 段、14 主題（1 個不找圖）：97（`exam.update_bank: true` 時 98） |
| lecture-blueprint | 1 用語表 ＋ 視角數 ＋ 評審數 ＋ 3 | 3 視角、3 評審：10 |
| lecture-write | 批數 × 5 ＋ 1（沒給 batches 陣列時再＋1 讀檔） | 11 批（藍圖 181 張，成品表格自動拆張後 184 張）：56，讀 batches.json 時 57 |
| lecture-review | 面向數 ×(1＋R) ＋ 1（沒給 pngs 時再＋1 算圖） | 6 面向：19–20 |
| style-mining | 面向數 ×(2＋R) ＋ 1（有 course 時的 brief） | 22 面向：88–89 |
| style-guide | 檔數 × 2 ＋ 3 | 23 檔：49 |

實測 token（2026-09 免疫課各次執行的代理紀錄），以 Opus 5.5 API 牌價換算（輸入 $4、快取寫入 $5、快取讀取 $0.20、輸出 $20／百萬 token；快取若以 1 小時計價，再多約 10–20%）：

| 工作流 | 每個代理 | 一次完整執行 |
|---|---|---|
| lecture-gather | 抽取、反駁、文獻約 $2–5，國考分類與選題約 $10–13 | 約 $300–420（該次由另一個模型執行、換算約 $156；Opus 代理在同類工作通常用 2–2.7 倍 token，故取此範圍） |
| lecture-blueprint | 草稿約 $30、評審約 $5、綜合／修訂約 $10 | 約 $150–190 |
| lecture-write | 每批約 $18（撰寫 $5.4、查核 $2–4 × 3、修訂 $3.7） | 184 張約 $230（每張約 $1.2） |
| lecture-review | 審查 $3–27、反駁 $2–16、修正 $17–21 | 第 1 輪 $149；第 2 輪 $377，其中「圖」面向開了兩千多次圖、單獨花 $235（現已在提示中限制每張圖只看一次） |
| style-mining | 挖掘約 $12、反駁約 $7、修訂約 $9 | 約 $750–850（一次性；有新改稿才重跑受影響的面向） |
| style-guide | 撰寫約 $10、修訂約 $6 | $408（一次性） |

一門新課從 gather 到兩輪 review，照預設約 $950–1,200（只做一輪 review 約 $830–990）。這些是「用 API 牌價把實測 token 換算的等值金額」，用來比較各階段的大小；雲端 session 實際怎麼扣（先扣雲端 session 額度，用完改吃方案用量；usage credits 只在使用者打開開關時才扣）與 $250 這類額度能做到哪裡，見 `docs/cloud_session_教學.md` 第 9 節。額度有限時的做法，依省下的多寡排列：
1. 風格兩支（mining、guide）不要重跑；只在教師親手改了新稿時，用 `dims`／`files` 只跑受影響的部分。
2. lecture-review 第 2 輪只跑有需要的面向，例 `lenses: ["facts", "terms", "layout"]`，並給 `refuters: 1`。
3. lecture-gather 用 `refuters: 1`；文獻主題只留真正要上投影片的，不需要圖的主題設 `"images": false`。
4. lecture-write 用 `make_batches.py --size 20` 減少批數（每批的代理都要重讀風格指南與事實帳，批數越少重讀越少；超過 20 張撰寫者一次要顧的太多，品質會掉）。
5. `effort: "medium"` 對所有代理生效；品質差多少尚未實測，建議先在一批或一個段落上比較。
6. 先跑小範圍（`segments`、`topics`、單一批）看實際花費再全跑；中途額度用完不會白費，用 DONE 表接著跑。

## 續跑（DONE 表）
- **同一台機器、run 的紀錄還在**：可以用 Workflow 的 `resumeFromRunId`。它沿用的是「從頭算起沒有改動的那一段 agent() 呼叫」：腳本或 args 一改，從第一個不同的呼叫之後全部重跑（提示裡嵌了 args，所以改 args 也算）；換到另一台機器（本機 ↔ 雲端）就沒有紀錄可以沿用。
- **跨 session、換環境（本機 ↔ 雲端）或改了腳本**：用 DONE 表。`args.done = {"<label>": "<輸出檔路徑>"}`，列在裡面的代理不重跑，直接把舊檔路徑交給下一步，log 出現 `reuse (not re-run): <label>`。

從執行紀錄重建 DONE 表：
1. 找到該次執行的 `journal.jsonl`：`~/.claude/projects/<專案代號>/<session id>/subagents/workflows/<runId>/journal.jsonl`（runId 在 Workflow 工具的回傳結果裡，例 `wf_fb57daa3-ed7`；Windows 的 `~` 是使用者資料夾 `%USERPROFILE%`）。雲端 session 結束後這個檔就不見了，所以每跑完一個工作流（雲端尤其要緊）就把 journal 複製到教材庫 `courses/<課>/_archive/journals/<工作流>_<runId>.jsonl`，連同當次 args 存成 `<工作流>-args.json`、重建出來的 DONE 表存成 `<工作流>-done_<日期>.json`，一起 commit。續跑紀錄只放這個資料夾。
2. 執行：
   ```
   python <kit>/workflows/tools/done_from_journal.py <journal 或 run 資料夾> [更多 journal] \
       --args <當次 args.json> --out <新 args.json> \
       [--map "/home/user/pathology-slide-materials=D:/localcode/pathology-slide-materials"] [--drop continuity]
   ```
   原始執行與每次續跑的 journal 都要給（續跑時被沿用的步驟不會再寫進新的 journal）。預設只收輸出檔真的存在的 label；`--map` 改寫雲端與本機不同的路徑前綴；`--drop` 讓某些步驟強迫重跑。
3. journal 已經不見（例如雲端 session 結束前沒複製）：改用輸出檔推回 label，`python <kit>/workflows/tools/done_from_journal.py --scan write --dir <materials>/courses/<課>/_archive/written --args ... --out ...`（種類：`gather` 給課程資料夾、`blueprint`（課程的 `glossary.md` 存在時也收 `glossary`）、`write`、`review` 給該輪資料夾、`mining` 給挖掘資料夾）。檔案存在不代表那一步當時做完了，先看過最後幾個檔，必要時用 `--drop` 讓它重跑。
4. 用新 args 再執行同一支工作流。

各工作流的 label：gather `robbins:extract:S01`、`robbins:review1:S01`、`robbins:adjudicate:S01`、`exam:download-parse`、`exam:classify-a`、`exam:classify-b`、`exam:verify-select`、`lit:search:<id>`、`lit:verify:<id>`、`lit:images:<id>`；blueprint `glossary`、`draft:<視角>`、`judge1`…、`synthesize`、`critic`、`revise`；write `write:<k>`、`facts:<k>`、`voice:<k>`、`terms:<k>`、`revise:<k>`、`continuity`；review `render`、`review:<面向>`、`verify1:<面向>`、`verify2:<面向>`、`fix`；mining `mine:<面向>`、`refute1:<面向>`、`refute2:<面向>`、`revise:<面向>`、`brief:writer`；guide `write:<檔>`、`critic:consistency`、`critic:completeness`、`revise:<檔>`、`index`。讀設定的 `load:*` 代理不進 DONE 表，每次都重跑（很便宜）。

## CR 字元（行尾）規則
- Workflow 工具拒絕含 `\r` 的腳本。所有 `.js` 一律 LF 行尾。
- 本資料夾有 `.gitattributes`（`eol=lf`），Windows 上即使 `core.autocrlf=true` 取出來也是 LF；在其他資料夾放新腳本時照做。
- 用 Python 在 Windows 寫檔一律 `open(..., "w", encoding="utf-8", newline="\n")`。
- 改完跑 `node workflows/tools/check_workflows.js`，第一項就是 CR 檢查。

## 新課程的建議順序
0. 在教材庫建 `courses/<課>/`：從 `templates/` 複製 `course.template.yaml` → `course.yaml`、`brief.template.md` → `brief.md`、`gather.template.json` → `gather.json`，逐項改寫。
1. 教科書頁圖與 OCR：`render_pdf_pages.py --course <課>`（預設 jpg、不出半頁，輸出到 course.yaml 的 `textbook.pages_dir`；頁圖有版權，只放教材庫）。切教科書圖表：`robbins_crop.py --course <課> ...`（同時寫 `圖片清單.md`）。抽他舊投影片的圖：`extract_deck_images.py`。
2. `lecture-gather` → `merge_facts.py --course <課>`（產 `facts_R.json`、`facts_X.json`、`facts.md`）。
3. `lecture-blueprint` → 看 `blueprint_summary.md` 的待裁決事項（建議給老師看，見下方「老師看過藍圖後修訂」）；把用到的框架圖從 `_archive/blueprint/diagrams.yaml` 貼進 course.yaml `diagrams`。
3b. （選做）新課程的撰寫 brief：見下方「新課程的撰寫 brief」。
4. `make_batches.py <blueprint.json> <課>/_archive/written/batches.json` → `lecture-write` → `merge_written.py --course <課> --dir <written> --blueprint <blueprint.json>` → `assemble.py --course <課> <blueprint.json> <written.json>`。
5. `gen_pptx.py --course <課>` → `style_check.py --course <課>` → `lecture-review`（1–2 輪；第 2 輪只跑需要的面向）→ `img_todo.py`。
6. 交件：成品 PPTX／PDF、待補圖清單、待教師裁決清單。
7. 教師親手改稿後：`dump_pptx.py` 傾印改稿、`diff_decks.py` 和我的毛胚比對，放進教材庫 `corpus/`；把改動回灌來源檔；再用 `style-mining`（`dims` 只選受影響的面向）與 `style-guide`（`files` 只選對應檔）更新風格指南。

以上 python 指令一律在 `<kit>/scripts` 以 `SLIDEKIT_MATERIALS="<materials>" PYTHONIOENCODING=utf-8 python ...` 執行，參數細節見 `scripts/README.md`。

## 老師看過藍圖後修訂

藍圖是改範圍最便宜的時間點。老師看完 `blueprint_summary.md` 有意見時：

1. 把他的決定連日期寫進課程的 `brief.md`「教師已裁決」表（之後的撰寫與審查也要知道）。
2. 把他的原話存成 `<課>/_archive/blueprint/teacher_notes_<日期>.md`。
3. 重建 DONE 表：`python <kit>/workflows/tools/done_from_journal.py --scan blueprint --dir <課>/_archive/blueprint --drop revise --args <當次 args.json> --out <新 args.json>`（其餘 9 個代理沿用舊檔）。
4. 在新 args 加 `teacher_notes: "<課>/_archive/blueprint/teacher_notes_<日期>.md"`，再叫一次 lecture-blueprint：只會跑「修訂」1 個代理，它把老師的意見放在批評之前套用，無法套用的列成待確認。
5. 範圍改動很大（例如整節換題目）時，改用 `--drop` 讓 `draft:*` 以後都重跑，並先報代理數。

## 新課程的撰寫 brief

`lecture-write` 與 `lecture-review` 會讀 `<materials>/style_evidence/writer_brief_<課>.md`（有就讀）：一份依這門課的對象、字級與國考題整理過的風格重點（25 條最重要的規則、他的原句、我常犯的錯）。沒有也能跑，代理直接讀風格指南，但 immune 的經驗是有 brief 時語氣修正少很多。產生方法，只花 1 個代理：

1. 先寫好課程的 `brief.md` 與 `course.yaml`（brief 代理讀它們）。
2. 重建 DONE 表，讓 22 個面向的挖掘全部沿用：`python <kit>/workflows/tools/done_from_journal.py --scan mining --dir <materials>/style_evidence/mining --out <args.json>`（得到 88 個 label，不含 `brief:writer`）。
3. 在 args.json 補上 `kit`、`materials`、`course: "<課>"`，叫 `style-mining.js`：只會跑 `brief:writer` 這 1 個代理，寫出 `style_evidence/writer_brief_<課>.md`。

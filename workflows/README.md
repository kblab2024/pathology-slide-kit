# workflows/：多代理工作流

用 Claude Code 的 Workflow 工具執行；沒有 Workflow 工具的工具照 `AGENTS.md` 第 4.0 節與 `docs/跨工具做法.md` 做同樣的角色。六支通用工作流都吃同一組參數 `{kit, materials, course, ...}`，路徑全部由參數組出來，腳本裡沒有任何本機路徑，所以同一支腳本在 Windows、Mac 本機與雲端 session（Ubuntu）都能跑。每個代理的模型與強度、反駁與複查的上限、開跑前的報價，照本檔「角色與強度」「反駁與複查的上限」「代理數與費用」與 `AGENTS.md` 硬規則 8、10、16。

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
- `tools/wf_check_mac.js`：沒有 node 的 Mac 用這支代替 check_workflows.js：`osascript -l JavaScript workflows/tools/wf_check_mac.js <腳本.js> <args.json> [load_mock.json]`。用 macOS 內建的 JavaScriptCore 查語法，再用假代理空跑，印出代理數、每個代理的 `label|model|effort|phase`、各強度的代理數 `effort_counts`（報價用），不是 opus 的列在 `not_opus`、沒寫 effort 的列在 `no_effort`（兩個都要是空的）。有讀設定代理（`load:*`）的工作流，第三個參數給它要回傳的內容。印出的 `agents` 就是報價用的代理數上限。`\r` 另外用 grep 查（2026-10-30 起印 effort；以前要用 grep 查 effort）。
- `tools/check_workflows.js`：改完腳本後跑 `node workflows/tools/check_workflows.js`，檢查 CR 字元、禁用字、本機絕對路徑、meta 是否為純字面值、語法（照 Workflow 執行環境包起來編譯），並用假代理把每支工作流空跑一遍、核對代理數。
- `reference/`：2026-09 免疫課程的三支原版腳本（已去除本機路徑），只供對照；新課程用上面的通用版。
- 範本在 `../templates/`：`course.template.yaml`、`brief.template.md`、`gather.template.json`、`course.CLAUDE.template.md`、`handoff.template.md`、`blueprint.schema.json`、`written.schema.json`。

## 共通規則
- **用 Claude 時所有代理一律 `model: 'opus'`**，寫死在每支腳本的代理呼叫裡；反駁與複查也一樣。其他公司的工具照 `AGENTS.md` 硬規則 8。
- **參數**：`kit`＝工具包根目錄（含 `scripts/`），`materials`＝教材庫根目錄（含 `courses/`、`textbook/`、`corpus/`、`style_evidence/`），`course`＝`materials/courses/` 下的資料夾名。三者缺一（style-mining、style-guide 的 course 可省）就只寫一行說明並結束，不派任何代理。路徑用正斜線（`D:/...`），反斜線也會被換掉，但 JSON 裡要寫成 `\\`，容易出錯。
- **代理呼叫腳本的固定寫法**：`cd "<kit>/scripts" && SLIDEKIT_MATERIALS="<materials>" PYTHONIOENCODING=utf-8 python <script>.py --course <course> ...`（代理在 shell 裡執行；Windows 是 Git Bash；Linux 找不到 `python` 時用 `python3`）。不收 `--course` 的工具（make_batches、export_pdf、verify_quotes 等）不加，清單見 `scripts/README.md`。
- **風格指南與國考題庫在工具包**（`style/guide/`、`question_banks/<題庫>/`）；**課程檔、教科書頁圖、語料、風格證據在教材庫**。
- 每個代理把成果**寫成檔案**，回傳 `{path, count, notes}`。
- **額度保護**：任何代理回傳 null（多半是額度用完或被略過）就停止派新代理，log 會出現 `ABORT`，之後用 DONE 表續跑。
- **共用選項**：`effort`（一個值套到這支工作流的每個代理；**一定要給**，例 `"xhigh"`：不給就繼承主 session 當時的強度，2026-10-14 實測繼承到 medium；lecture-gather 另收 `effort_hard`、`effort_light` 分角色，其他五支還不能分角色，見「角色與強度」）、`done`（DONE 表）。gather、review、mining 另有 `refuters`（預設 2，照 2 位用；只有審查的非事實面向可以另跑一次設 1，見「反駁與複查的上限」第 1 條）。

## 各工作流的參數

| 工作流 | 必填 | 選填（預設） |
|---|---|---|
| lecture-gather | kit, materials, course | `gather`（直接給設定物件；預設讀 `<課>/gather.json`）、`gather_file`、`parts`（`["facts","exam","literature"]` 的子集）、`segments`（例 `["S01","S02"]`）、`topics`（文獻主題 id）、`refuters`、`effort`（抽取、裁決、文獻搜尋、國考分類與選題）、`effort_hard`（事實反駁者、PubMed 查核；沒給＝`effort`）、`effort_light`（讀設定、下載題庫、找開放授權圖；沒給＝`effort`）、`done` |
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
- 雲端讀得到 repo 裡的 `AGENTS.md`（Claude Code 經 `CLAUDE.md` 匯入），讀不到本機的記憶檔；要讓代理知道的事寫進 `brief.md`、`course.yaml` 或風格指南。
- 成果要 commit 並 push 到分支才會回到本機；工作流結束後請代理在教材庫 commit（連同執行紀錄，見「續跑」）再 push。單檔上限 100 MB：逐張 PNG、PDF 草稿、下載的考題原始 PDF 視需要排除。
- 文獻查核、找開放授權圖與國考下載需要連外網；要加進 Custom 網路的網域清單見 `docs/cloud_session_教學.md` §3.2（PubMed／NCBI／PMC、Wikimedia Commons、CDC PHIL、doi.org、考選部）。環境的網路政策不允許時，把 `parts` 限成 `["facts"]`，文獻部分在本機做。
- 雲端沒有 PowerPoint 與微軟正黑體：export_pdf.py 改用 LibreOffice＋Noto CJK 算圖，換行位置和 PowerPoint 略有不同；版面審查以 `*_layout.json` 估算為主，交件前在 Windows 用 PowerPoint 再看一次。
- Workflow 工具在雲端 session 能不能用、能同時跑幾個代理（Workflow 工具的並行上限約是 min(16, CPU 數 − 2)，雲端 VM 的 CPU 數不確定，可能比本機慢），都還沒有實測。第一次在雲端跑時先用小範圍（例 lecture-gather 只給 `segments: ["S01"]`）試。沒有 Workflow 工具時，照 `AGENTS.md` 第 4.0 節的第 3 種做法一個角色一個角色做，或請代理讀腳本（`docs/跨工具做法.md`）、照同樣的提示逐一派子代理；DONE 表與代理數控管要自己盯。

## 角色與強度（2026-10-14 教師採用）

**規則**：每個 `agent()` 都明寫 `model: 'opus'` 與 effort（`AGENTS.md` 硬規則 8）。不寫 effort 的代理會繼承主 session 當時的強度，不是固定值：2026-10-14 uro-a3 撰寫第一次開跑時主 session 是 medium，代理就跟著 medium，停掉、腳本改成明寫 effort 後重開。

**分級原則**（流程結構不動，只調每個角色的強度）：
- **max**：做錯會一路傳下去的決定，以及查證：規劃或大綱、大綱批評、事實批評、事實反駁、第一輪事實複查、全套完整性檢查。
- **xhigh**：要長篇綜合判斷的：撰寫、修訂、口吻與連貫的批評、套用修正、跨批修正（充實的 form 批評例外，見表第 3 列）。
- **high**：有程式或規則撐著、比較機械的：版面（有 python 量字與 gen_pptx 量溢出）、中英對照與用字（有 glossary 與 style_check）、國考與指引的反駁、第二輪複查、用字審查、讀設定、找授權照片。
- 本專案的等級名稱最低是 high；對到其他公司的工具時依名次對，可能是該工具叫 medium 的那一級（`AGENTS.md` 第 4.0 節）。

| 階段 | max | xhigh | high |
|---|---|---|---|
| 0 腳本與工具 | 不開工作流（主 session 寫程式；能用程式算的不交給代理，例 `fit_capacity.py`；下一階段的腳本先空跑） | | |
| 1 研究 | 事實與文獻的反駁者；組織學正確性的反駁者 | 每段讀教科書建事實帳（抽取、裁決）；文獻查找與整理；示意圖說明的撰寫與修訂 | 讀設定；授權照片搜尋；授權與 Runway 可行性的反駁者 |
| 2 初稿 | 大綱；大綱批評；事實批評；事實反駁 ×2；第一輪事實複查；全套完整性批評 | 大綱修訂；撰寫；口吻批評；國考與指引批評；修訂；套用修正；跨批修正 | 用字與中英批評；版面批評；國考與指引反駁 ×2；版面與用字複查；第二輪事實複查；用字審查 |
| 3 充實 | 充實規劃；規劃的深度批評；事實批評；事實反駁 ×2；事實複查；全套檢查 | 規劃的連貫批評；規劃修訂；改寫；連貫與深度批評；修訂；套用修正；跨批修正 | 版面與口吻批評（充實腳本把版面、口吻、中英與試產量字合成一個 form 批評，以試產 PPTX 量字為主，所以用 high）；用字審查 |
| 審查（交草稿前） | 事實面向與它的反駁者；修正查核；完整性批評 | 國考、口吻、版面（要看 PNG）、圖片面向；修正 | 中英對照面向；非事實面向的反駁者 |

**依據**（uro-a3 初稿 57 個代理；2026-10-14 從 journal 與代理紀錄統計）：
- 實際強度：xhigh 30 個、max 27 個，沒有 high。教師原本以為那次是用 high 跑的；看了紀錄後選擇照實記（一般 xhigh、查證 max），再採用上表把機械性的角色降到 high。
- 花在哪裡（占 Workflow 工具回報的 subagent_tokens）：事實複查 11.7%、事實反駁 10.5%、版面與用字複查 8.4%、撰寫 8.3%、修訂 8.7%（含大綱修訂）、事實批評 6.7%、套用修正 7.7%（含跨批修正）。
- 事實反駁值得 max：三批事實批評共 50 條意見，13 條（26%）被至少一位反駁者推翻（膀胱 7/18、前列腺 5/20、臨床 1/12），其中 8 條兩位都推翻；沒擋下就會直接寫進投影片。
- 國考反駁可以降到 high：4 個代理（約 93 萬 subagent_tokens）只處理 6 條意見。兩位都推翻的有 3 條（膀胱 2、前列腺 1），比例不低，但都是用字、題目位置、題幹空白，不牽涉事實；降級的理由是每條花費高、出錯的代價低。
- 第二輪複查還找得到東西，但比第一輪少：事實＋版面用字複查合計，三批第一輪各 3、9、7 條，第二輪各 2、3、2 條；只看事實複查，第一輪 0、4、3 條，第二輪 0、1、0 條（所以第二輪事實複查降到 high）。
- 照上表調整、再加上「複查只看改過的張」，估計初稿約可省 15–25%；這是推估，下一門課跑過才知道。
- 研究（表第 1 列）的分配沒有實測：uro-a3 的研究是 kit 的標準結構，62 個代理全部 xhigh（腳本沒寫 effort，繼承 session），沒有 max、沒有複查；教師說的「research with ultracode」和實際跑的不同。第一次照表跑研究時，報價要和這 62 個代理、subagent_tokens 10,850,106 對照，寫出多出來的費用。

**程式現況**：
- lecture-gather（2026-10-30 起）分角色：`effort` 給抽取、裁決、文獻搜尋、國考分類與選題，`effort_hard` 給事實反駁者（`robbins:review*`）與 PubMed 查核（`lit:verify:*`），`effort_light` 給讀設定、下載題庫、找開放授權圖。照上表研究列給 `{"effort": "xhigh", "effort_hard": "max", "effort_light": "high"}`；只給 `effort` 時全部用同一級（舊寫法，和 uro-a3 研究一樣整支 xhigh）。第一次照表跑時，報價要和 uro-a3 研究（整支 xhigh）對照，寫出反駁與查核升到 max 多出來的費用。
- 其他五支通用工作流只吃一個 `args.effort` 套到全部代理（`const EFFORT = A0.effort || null`），還不能分角色；叫它們時一定要給 effort。分角色做好之前的過渡做法（2026-10-14 整理文件時定的預設，待教師確認）：
- lecture-review 用 `lenses` 分兩次：`["facts"]` 給 max，其他面向給 xhigh（兩次的 `out` 用不同資料夾，第二次用第一次修正後重算的 PNG）。
- 拆不開的（lecture-blueprint、lecture-write、style-mining、style-guide）整支給 `"xhigh"`。
- 報價時寫明哪些角色比上表高或低一級。

課程自寫的腳本照 uro-a3 的寫法：args 給 `effort`（一般）與 `effort_hard`（查證），每個 `agent()` 各自指定（範本：私人 repo `courses/uro-a3/_archive/journals/uro-write.js`）；之後寫的腳本，機械性的角色用第三個參數 `effort_light`（預設 high）。通用工作流加上這三個參數：lecture-gather 已做（2026-10-30），其他五支是待辦。

## 反駁與複查的上限（2026-10-14 教師採用）

教師 2026-10-14：之前費用失控最嚴重的那門課（lung），錢幾乎都花在用比 opus 更貴的型號跑的多輪反駁。主 session 當晚的分析：uro-a3 的反駁只跑一輪、每份批評檔 2 位、全部用 opus，沒有 lung 那種反駁循環；但 uro-a3 初稿的牌價換算下限約 $268（不含 output），不比 immune 省，10/15 凌晨也用完過一次方案額度。所以要管的是反駁的做法，不只是強度。下面四條上限是主 session 照這件事提的，教師 21:52 採用（`AGENTS.md` 硬規則 16）：

1. **反駁只做一輪。** 每份批評檔 2 位反駁者（不是每條意見各派一組）。兩位都推翻就丟；兩位都確認就套用；一推一留，由修訂者回原始資料（教科書頁圖、事實帳、glossary、PNG）查過再決定，並寫進報告。不做「反駁 → 再反駁」的循環，也不派人反駁反駁者。審查的非事實面向減成 1 位（`refuters: 1`）是 2026-10-14 以前就有的省錢選項，不屬於教師採用的上限：只有 1 位時沒有一推一留，那 1 位推翻就丟（`lecture-review.js` 的修正者就是這樣判），所以只用在非事實面向，要用先在報價寫明、教師說好。
2. **模型固定**（硬規則 8）：用 Claude 時一律 opus，反駁者與複查者也一樣，不換成比 opus 更貴的型號。用其他公司的工具時，整個階段固定用該家一個主力的推理模型（不用標價更高的頂級型號），反駁與複查也不換成更貴的模型。
3. **只有「找新問題」的複查可以重來，而且有上限。** 修訂後的複查最多 2 輪；第 2 輪只看第 1 輪改過的張；第 1 輪沒有找到事實問題就停，不跑第 2 輪。`lecture-review.js` 的第 2 輪也算第 2 輪：第 1 輪沒有事實問題就不跑；要跑只跑問題多的面向（它還不能只看改過的張，見待辦）。
4. **開跑前先算上限。** 先數出最多會派幾個代理（三種數法見「開跑前先空跑拿上限」；uro-a3：初稿最多 57、充實最多 34），報價照這個上限算（硬規則 10）。
5. **不重複審查**（2026-10-15 教師指出 uro-a3 的過度審查）：開任何審查或查核前，先列出前面各階段已經查過哪些面向、之後內容又改了什麼；只跑輸入有變、或需要新證據的面向（例：充實工作流已經做過事實、口吻、用字、國考的批評與反駁，算圖後只跑看 PNG 才有新證據的版面與圖片），其他面向不重跑；報價寫明哪些面向因為已查過而略過。

現有腳本（2026-10-14）：
- kit 的 `lecture-gather.js`、`lecture-review.js`、`style-mining.js`：每段或每個面向固定 `refuters` 位反駁者（預設 2），只做一輪；`lecture-review.js` 的修正者照第 1 條判定（一推一留回原始資料查）（腳本目前允許 `refuters` 設到 3，不要這樣設；上限改 2 是待辦）。
- 課程自寫的腳本（範本在私人 repo `courses/uro-a3/_archive/journals/`）：撰寫的複查最多 2 輪，但第 2 輪看整批（下次改成只看改過的張）；充實已照第 1 條寫；審查（還沒跑）是每個審查者 3 位反駁者、過半成立，國考面向與所有反駁者用 max，跑之前要改成本節與「角色與強度」的寫法。

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
2. lecture-review 第 2 輪只跑有需要的面向；facts 面向照舊 2 位反駁者，只有非事實面向（例 `lenses: ["terms", "layout"]`）可以另跑一次給 `refuters: 1`（舊有的省錢選項，報價寫明）。
3. lecture-gather 的文獻主題只留真正要上投影片的，不需要圖的主題設 `"images": false`；教科書事實帳的反駁者保留 2 位（事實反駁值得做，見「角色與強度」的依據）。
4. lecture-write 用 `make_batches.py --size 20` 減少批數（每批的代理都要重讀風格指南與事實帳，批數越少重讀越少；超過 20 張撰寫者一次要顧的太多，品質會掉）。
5. 照「角色與強度」把機械性的角色降到 high；不要整支降到 medium（本專案沒有用 medium 跑完的實測，教師採用的表最低用到 high）。
6. 先跑小範圍（`segments`、`topics`、單一批）看實際花費再全跑；中途額度用完不會白費，用 DONE 表接著跑。

**開跑前先空跑拿上限**（硬規則 10）：上面的公式是估算；報價以數出來的代理數上限為準。三種數法：(1) Mac：`osascript -l JavaScript workflows/tools/wf_check_mac.js <腳本> <args.json> [load_mock.json]` 印出的 `agents`；(2) 有 node（Windows、Linux）：`check_workflows.js` 只用內建參數空跑 kit 的腳本，不收這次的 args，所以照上表的公式代入這次的段數、批數、面向數；課程自寫的腳本照它的 phases 數；(3) 沒有 Workflow 工具：把要做的角色逐一列成表（角色、label、強度、輸出檔），列數就是上限，連表一起報價。報價時寫：代理數上限與怎麼數的、每個角色的強度、約略費用（照上限算）、約略時間。用其他公司的工具時怎麼報，見 `docs/跨工具做法.md` 第 7 節。

**四階段做法的實測（uro-a3，2026-10-14；從 journal 與代理紀錄統計）**：

| 階段 | 工作流 | 代理數 | 強度（實際） | Workflow 回報的 subagent_tokens | 時間 | 結果 |
|---|---|---|---|---|---|---|
| 1 研究 | 蒐集（`lecture-gather.js`）＋示意圖說明（課程自寫）＋文獻補充（`lecture-gather.js`） | 38＋21＋3＝62 | 全部 xhigh（腳本沒寫 effort，繼承 session） | 10,850,106 | 約 1 小時（前兩支同時跑） | 0 錯誤；Robbins 事實 732 條、文獻 62 條 |
| 2 初稿 | 撰寫（課程自寫，ultracode 結構） | 57 | xhigh 30、max 27 | 19,240,383 | 約 5.5 小時（12:52–18:25） | 0 錯誤；110 張，收尾後 check_deck ALL GREEN、style_check RED 0 |
| （2 的第一次開跑） | 同上的舊版（沒寫 effort） | 1 | medium（繼承） | — | 約 5 分鐘後停掉 | 沒有產出 |
| 3 充實 | 充實（課程自寫） | 空跑最多 34 | 腳本設定：一般 xhigh、查證 max | 還沒跑完 | 10/14 21:33 開跑；23:30 照教師新明令（臨床改成兩條 NCCN 決策樹）停掉、用 DONE 表續跑；10/15 00:29 方案額度用完中斷（完成 12 步）；03:30 再用 DONE 表續跑（剩約 18–21 個代理） | 跑完再補 |

- subagent_tokens 是 Workflow 工具回報的數字，等於每個代理最後一次 API 呼叫的 context 大小加總；不是計費 token，也不是總處理量。
- output token 從紀錄拿不到，所以只能算「API 牌價換算下限（不含 output）」：研究約 $91（蒐集 $41、示意圖說明 $46、文獻補充 $4）、初稿約 $268。對照：immune 的 lecture-write 同樣 57 個代理，含 output 約 $230。「surprisingly effective and economic」是教師的評語（2026-10-14）；token 數字本身撐不起「比較省」的說法。

## 續跑（DONE 表）
- **（Claude Code）同一台機器、run 的紀錄還在**：可以用 Workflow 的 `resumeFromRunId`。它沿用的是「從頭算起沒有改動的那一段 agent() 呼叫」：腳本或 args 一改，從第一個不同的呼叫之後全部重跑（提示裡嵌了 args，所以改 args 也算）；換到另一台機器（本機 ↔ 雲端）就沒有紀錄可以沿用。本專案續跑一律用 DONE 表，不用 `resumeFromRunId`。
- **跨 session、換環境（本機 ↔ 雲端）或改了腳本**：用 DONE 表。`args.done = {"<label>": "<輸出檔路徑>"}`，列在裡面的代理不重跑，直接把舊檔路徑交給下一步，log 出現 `reuse (not re-run): <label>`。

從執行紀錄重建 DONE 表：
1. 找到該次執行的 `journal.jsonl`（Claude Code 的位置）：`~/.claude/projects/<專案代號>/<session id>/subagents/workflows/<runId>/journal.jsonl`（runId 在 Workflow 工具的回傳結果裡，例 `wf_fb57daa3-ed7`；Windows 的 `~` 是使用者資料夾 `%USERPROFILE%`）。雲端 session 結束後這個檔就不見了，所以每跑完一個工作流（雲端尤其要緊）就把 journal 複製到教材庫 `courses/<課>/_archive/journals/<工作流>_<runId>.jsonl`，連同當次 args 存成 `<工作流>-args.json`、重建出來的 DONE 表存成 `<工作流>-done_<日期>.json`，一起 commit。續跑紀錄只放這個資料夾。
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

## 新課程的建議順序（對應 SOP 的步驟）

下面的編號是 `docs/SOP_新教案流程.md` 的「步」；四個階段（一個階段一個 session）怎麼對到這些步驟，見 SOP 總表的「階段」欄與 `docs/多session做法.md`。

- 步 0：在教材庫建 `courses/<課>/`：從 `templates/` 複製 `course.template.yaml` → `course.yaml`、`brief.template.md` → `brief.md`、`gather.template.json` → `gather.json`、`course.CLAUDE.template.md` → `CLAUDE.md`、`handoff.template.md` → `_archive/handoff.md`，逐項改寫。
- 步 1–2：教科書頁圖與 OCR：`render_pdf_pages.py --course <課>`（預設 jpg、不出半頁，輸出到 course.yaml 的 `textbook.pages_dir`；頁圖有版權，只放教材庫）。切教科書圖表：`robbins_crop.py --course <課> ...`（同時寫 `圖片清單.md`）。抽他舊投影片的圖：`extract_deck_images.py`。
- 步 4：`lecture-gather` → `merge_facts.py --course <課>`（產 `facts_R.json`、`facts_X.json`、`facts.md`）。
- 步 5：`lecture-blueprint` → 看 `blueprint_summary.md` 的待裁決事項（建議給老師看，見下方「老師看過藍圖後修訂」）；把用到的框架圖從 `_archive/blueprint/diagrams.yaml` 貼進 course.yaml `diagrams`。
- 步 6 之前（選做）：新課程的撰寫 brief：見下方「新課程的撰寫 brief」。
- 步 6：`make_batches.py <blueprint.json> <課>/_archive/written/batches.json` → `lecture-write` → `merge_written.py --course <課> --dir <written> --blueprint <blueprint.json>` → `assemble.py --course <課> <blueprint.json> <written.json>`。
- 步 5–6 的階段 2（ultracode 結構，新課照這個做）：上面兩支是 2026-09 immune 的結構（藍圖三視角、三評審；撰寫每批 3 位查核，沒有反駁與複查）。新課改用課程自寫的一支撰寫工作流做完步 5–6：大綱 → 大綱批評 → 修訂 → 分批撰寫 → 多面向批評＋2 位反駁 → 修訂 → 複查 → 全套完整性批評 → 跨批修正 → 用字審查，範本是私人 repo `courses/uro-a3/_archive/journals/uro-write.js`（`docs/多session做法.md`「四個階段」）。組裝（`assemble.py`）之後照常。
- 步 7–8：`gen_pptx.py --course <課>` → `style_check.py --course <課>` → `lecture-review`（1–2 輪；第 2 輪只跑需要的面向）→ `img_todo.py`。
- 步 7b（階段 3）：教師看過毛胚給評語時，先跑充實工作流（SOP 第 7b 步），再做步 7–8。
- 步 9–10：交件：成品 PPTX／PDF、待補圖清單、待教師裁決清單（一律是草稿，`docs/教師偏好與決策.md` 第 8 節）。
- 步 11：教師親手改稿後：`dump_pptx.py` 傾印改稿、`diff_decks.py` 和我的毛胚比對，放進教材庫 `corpus/`；把改動回灌來源檔；再用 `style-mining`（`dims` 只選受影響的面向）與 `style-guide`（`files` 只選對應檔）更新風格指南。

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

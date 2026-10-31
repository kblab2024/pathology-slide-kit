# AGENTS.md：病理學教案投影片工具組的操作守則

這個專案照一位病理科教師的風格，用 Robbins 11e 與多代理流程做病理學大堂課的 PowerPoint 投影片（繁體中文、專有名詞中英對照），交給他當草稿，他自己修過才上課。流程與工具的全貌見 `README.md`「這是什麼」。本檔是 kit 操作守則的正本，給所有程式代理（Claude Code、OpenAI Codex、Cursor、GitHub Copilot、Gemini CLI 等）與人讀。Claude Code 經 `CLAUDE.md` 匯入本檔，Gemini CLI 經 `GEMINI.md` 匯入，Copilot 讀 `.github/copilot-instructions.md` 再回到本檔；那三個檔只放各工具自己的附註，規則只寫在這裡。沒有 Claude Code 的工具，另讀 `docs/跨工具做法.md`。舊文件寫「CLAUDE.md 第 N 節」「硬規則 N」「CLAUDE.md 規則 N」，指的都是本檔的同一節、同一號。

本 repo 是 kit 的公開發佈版 `pathology-slide-kit`：維護者在私人的工作版改好、跑過 `check_public.py` 後同步過來，兩邊的規則相同，差別只在代稱、遮蔽與授權。課程內容在兄弟 repo `pathology-slide-materials`（私人）。使用者就是授課教師。

他的本機記憶（例：Claude Code 的記憶檔）在雲端與其他工具都看不到。規則與裁決一律寫進 repo（本 repo 的 `docs/`、`style/guide/`，私人 repo 各課的 `CLAUDE.md`、`brief.md`、`_archive/handoff.md`）；各工具的本機記憶放摘要、repo 不能放的原話與指向，兩邊不一致時以 repo 為準。kit 的上一層資料夾若有 `AGENTS.md`（教師 Mac 上的工作區：本機環境、OneDrive 寫檔規則、禁用檔名），開工時也要讀。

## 1. 開工第一件事：確認環境與 repo

```bash
uname -s 2>/dev/null; echo "$OS"   # Darwin＝Mac；Linux＝雲端容器或其他 Linux；Windows 的 Git Bash 會印 Windows_NT
# PowerShell：$env:OS（Windows 是 Windows_NT）；或不分 shell：python -c "import os,platform; print(os.name, platform.system())"
cd "<kit>/scripts" && PYTHONIOENCODING=utf-8 python -c "import common; print(common.ROOT); print(common.find_materials())"
```

| | Windows 本機 | Mac 本機 | Linux（含雲端 session） |
|---|---|---|---|
| 安裝 | `setup/windows.md` | `setup/mac.md` | `bash setup/cloud-setup.sh`（要 root 或 sudo） |
| PDF 匯出 | `export_pdf.py`（PowerPoint） | `export_pdf.py`（LibreOffice＋PowerPoint 內建的微軟正黑體，斷行與 PowerPoint 相同；第一次先跑 `bash scripts/lo_fonts_mac.sh`，見 `setup/mac.md`）；要 PowerPoint 本身定稿才用 `bash scripts/ppt_pdf_mac.sh <課>/成品/<檔>.pptx`（第一次會跳授權） | 沒有 PowerPoint，用 LibreOffice（`soffice`）；`SLIDEKIT_PDF_ENGINE=auto｜powerpoint｜libreoffice` 可強制指定 |
| 換行量測字型 | 微軟正黑體 | PowerPoint for Mac 內建的微軟正黑體（gen_pptx 自動找） | Noto Sans CJK TC（PPTX 內仍指定微軟正黑體，交件前在 PowerPoint 看一次） |
| `python` 指令 | `python` | `python`（找不到用 `python3`） | `python`（找不到用 `python3`） |
| 工作流腳本檢查 | `node workflows/tools/check_workflows.js`（只用內建參數空跑 kit 的腳本；這次 args 的代理數上限照 `workflows/README.md` 的公式數） | 沒有 node：`osascript -l JavaScript workflows/tools/wf_check_mac.js <腳本> <args.json>`（語法、假代理空跑、代理數、每個代理的 effort） | 同 Windows |
| 編碼 | 一律 `PYTHONIOENCODING=utf-8`（Windows 不設會 cp950 報錯） | 同左 | 同左 |

其他公司的雲端代理（Copilot coding agent、Codex cloud、Cursor background agent 等）多半只看得到一個 repo：在那裡只改 kit 的程式與文件，不做課；環境設定腳本用 `bash setup/cloud-setup.sh`；細節見 `docs/跨工具做法.md` 第 6 節。

找不到私人 repo（`find_materials()` 回 None）時：本機就 `git clone` 到 kit 旁邊；雲端 session 要請使用者把 `pathology-slide-materials` 加進 session（雲端的 GitHub proxy 可能只放行加進 session 的 repo），或設 `SLIDEKIT_MATERIALS`。`find_materials()` 的順序：`SLIDEKIT_MATERIALS` → `<kit>/../pathology-slide-materials` → `<kit>/..`（若含 `courses/`）→ None。語料：`SLIDEKIT_CORPUS` → `<materials>/corpus` → `<kit>/style/corpus`。

**指令的固定寫法**（工作流代理的 prompt 裡也一樣）：

```bash
cd "<kit>/scripts" && SLIDEKIT_MATERIALS="<materials>" PYTHONIOENCODING=utf-8 python <script>.py --course <course> ...
```

只有讀課程設定的工具收 `--course`；哪些收、哪些不收、每支怎麼用，見 `scripts/README.md` 開頭（每支也都有 `--help`）。`<kit>`、`<materials>` 用絕對路徑（先 `pwd`、`ls` 確認實際位置）。課程資料夾＝`<materials>/courses/<course>`。

## 2. 依任務的讀法

每個任務都先讀 `docs/教師偏好與決策.md` 與 `style/guide/01_權威順序.md`，再照下表：

| 任務 | 讀 |
|---|---|
| 接手一門正在做的課 | 該課 `_archive/handoff.md` → 該課 `CLAUDE.md` → `brief.md` → `course.yaml`（課程指引檔名叫 CLAUDE.md，內容對所有工具都適用，自己打開讀） |
| 一門課分好幾個 session 做 | `docs/多session做法.md`（四個階段，一個階段一個 session）、範本 `templates/handoff.template.md` |
| 做新教案 | `docs/SOP_新教案流程.md` → `style/guide/00_README.md` 任務 A → 該課的 `CLAUDE.md`、`brief.md`、`course.yaml` |
| 在他的 deck 上改版、衍生給另一班 | `00_README.md` 任務 B → `30_結構/38_課別差異.md` |
| 回灌他親手改過的稿 | `00_README.md` 任務 C → `40_範例/42_改稿前後對照.md`（EDIT-42）→ SOP 第 11 步 |
| 交付前檢查 | `00_README.md` 任務 D → `50_檢查/52_交付前檢查清單.md` |
| 只改一張、一句或一個標題 | `00_README.md` 任務 E |
| 改工具、檢查器、rules.yaml | `scripts/README.md`、`00_README.md` 任務 F |
| 跑或續跑工作流 | 本檔第 4 節、`workflows/README.md`、`docs/lessons_learned.md` |
| 雲端 session、費用 | `docs/cloud_session_教學.md`（第 9 節是費用與額度） |

誰說了算：

**說明檔的先後**（不採用「越靠近目前資料夾的檔越優先」）：
1. 教師在對話裡當次的指示（通用的當場寫進 repo）。
2. 本檔的硬規則（事實、隱私、UTF-8、不手改 PPTX 等），課程不能改。
3. 有日期的教師裁決：適用所有課的在 `docs/教師偏好與決策.md` 第 4 節，單課的在該課 `brief.md`；同一件事以較新的為準，單課明令只管那門課；已交件的課要不要照新的全課裁決重做，先問教師（教師偏好第 4 節各條寫了適用範圍）。
4. 風格指南（指南內的衝突照 `01_權威順序.md`）；指南還沒改到的地方以教師偏好第 4 節為準。指南以外的舊說法（舊 ENT 專案 CLAUDE.md 的「硬規則 v3」、舊記憶檔、v0 rules.yaml）排在指南之後。
5. 課程 `CLAUDE.md`、handoff、私人 repo `AGENTS.md` 的做法說明；和 kit 不一致時以 kit 為準，並在那門課的下一個 session 改掉。
6. 工作區 `AGENTS.md`（教師 Mac 上 kit 的上一層）只管那台 Mac 的環境與 OneDrive，這兩件事以它為準。

各工具的入口檔（`CLAUDE.md`、`GEMINI.md`、`.github/copilot-instructions.md`）與全域設定只放工具附註，和 `AGENTS.md` 不一致時以 `AGENTS.md` 為準；記憶與 repo 不一致時以 repo 為準。
- 事實以 Robbins 11e 為準（硬規則 1）。
- 指南裡寫的「CLAUDE.md」若指「硬規則 v3」「國考題節」，指的是舊 ENT 專案的 CLAUDE.md，不是本 repo 的檔。

## 3. 硬規則

1. **事實以 Robbins 11e 為唯一正典。** 每一句都要對得到事實帳（facts_R.json）或已查核的文獻（facts_X.json）。文獻只補充、句內或標題括號附出處、不得蓋過 Robbins。Robbins、文獻、老師舊投影片三者衝突時，選一個做法做進成品，並列進「待教師裁決清單」；不靜默改，也不靜默沿用。Robbins 和新文獻（指引、新分類）不同時依系別（`docs/教師偏好與決策.md` 第 4 節）：醫學系的課在投影片上並列兩者、各附出處，讓學生做文獻評析（2026-10-30「講義上同時列教科書與文獻」）；牙醫系等非醫學系的課直接照 Robbins，文獻的不同說法不上投影片（2026-10-31「文獻評析只對醫學系」）；兩種都仍列進待教師裁決清單。Robbins 自己前後不一（正文、表、KEY CONCEPTS、圖說的數字或說法不同）時，上投影片的那件事前後並陳、各附頁碼，不替學生挑一個（2026-10-31「Robbins 前後不一要前後並陳」）；明顯的印刷錯誤照正確寫法、不照抄。他的錯字照 `24_術語與中英對照.md` TERM-18 處理。
2. **不寫 LLM 語。** 全形雙破折號（U+2014 連寫兩個）、套語（值得注意的是、讓我們、總而言之、扮演…角色、關鍵在於、不僅…更…）、舞台指示、打氣句、戲劇化第二人稱、貫穿全套的比喻一律不寫。他自己的「其實」「不是 X，而是 Y」「因此」「=>」照用（份量見指南 23、25）。清單以 `20_文字/23_禁用語與LLM語.md` 為準。
3. **字級、中英對照、國考題版式照該課的明令。** 課程有明令（例：immune 的標題 36、內文 28、學生要讀的字 ≥20、出處 14）就照做，寫在該課 course.yaml（`sizes`、`bilingual`、`decks.<deck>.quiz_style`）與 brief.md；不要把某一課的明令套到別的課。兩條適用所有課（`docs/教師偏好與決策.md` 第 4 節）：**每一張的專有名詞都寫「中文(English)」**（2026-10-14；文字、圖上的標籤、表格、流程圖都一樣；course.yaml 一律寫 `bilingual: per_slide`；放不下就拆張，不拿掉英文）；新做的大堂課沒有字級明令時，**內文 24–35pt 依版型選、表格與標籤 24、只有出處行可以更小**（2026-10-14 晚；數值在 `templates/course.template.yaml` 的註解）。
4. **一張講一個主題，但不要單句張；內容要有深度、統整、連貫。** 2026-10-14 教師看完 uro-a3 毛胚後明令（`docs/教師偏好與決策.md` 第 4 節）：他舊 deck 的單句大字張是他唯一不喜歡的舊風格；每張內容張要有一個以上的重點（封面、分隔張、國考題張除外），照 Robbins 補深度、加比較表與銜接，版面比他的原檔精緻。深度不是把文獻細節搬上投影片（2026-10-20）：例數、試驗期別、體外或小鼠、作者推測放講稿，統整表字要少、語調要像上課講話。真的放不下才拆同標題連張；不做學習目標、大綱、總結、謝謝張；不產「圖片待補」佔位張或佔位框，缺圖寫 `<!-- img_wanted: … -->` 進待補圖清單。
5. **只改來源檔，不手改 PPTX。** 來源檔：`sources/*-pool.md`、`*-script.md`、`sources/decks/*.md`、`course.yaml`、`glossary.md`。藍圖與撰寫 JSON 被審查修改超越後，不要再拿它們重跑 `assemble.py`（會蓋掉 pool.md）。
6. **不覆蓋老師親手改過的檔。** 他改過的 PPTX 要先用 `dump_pptx.py`＋`diff_decks.py` 回灌 pool.md，才能重產；產檔前看 `成品/` 有沒有同名檔（gen_pptx 覆寫既有檔時會印「[注意] 覆寫既有檔」），有就換日期或用 `--name`。只是確認環境時用 `--name _smoketest`。
7. **綠燈不算數。** `check_deck.py`、`style_check.py` 全過之後，還要出逐張 PNG（`export_pdf.py`，Mac 也一樣），跑 `check_render.py` 量實排（框架圖格子溢出、兩段字互壓），再一張一張看溢出、孤字、行首標點、被壓小的圖。估算「放得下」的改法要渲染過才算完成。
8. **工作流的每個代理都寫死模型與強度。** 用 Claude 時一律 `model: 'opus'`，反駁與複查也一樣，不換成比 opus 更貴的型號（教師採用的第 2 條上限；lung 的費用失控在用更貴的型號跑多輪反駁）。每個代理明寫 effort：不寫會繼承主 session 當時的強度（2026-10-14 實測繼承到 medium）；各角色用哪一級照 `workflows/README.md`「角色與強度」。用其他公司的工具時，整個階段固定用該家一個主力的推理模型（不用標價更高的頂級型號，反駁與複查也一樣），強度照第 4.0 節的表；交付說明寫出用了什麼模型與設定。同一個階段用同一個工具，要換在階段的邊界換，寫進 handoff（2026-10-14 整理文件時加的，不是教師的上限）。
9. **做過的步驟不重做。** 續跑一律靠 DONE 表（`args.done = {label: 輸出檔路徑}`，列在裡面的代理直接沿用舊檔；Claude Code 的 `resumeFromRunId` 見 `CLAUDE.md`）；journal、當次 args 與 DONE 表存在 `<課程資料夾>/_archive/journals/`，重建用 `workflows/tools/done_from_journal.py`（journal 不見時加 `--scan`）。沒有 Workflow 工具時，輸出檔已存在且完整就跳過，DONE 表照 `docs/跨工具做法.md` 第 3 節手寫。
10. **額度保護與開跑前報價。** 任何代理回傳 null（多半是額度用完；沒有 Workflow 工具時，子代理失敗、沒寫出輸出檔、工具回報額度或速率限制，都照 null 處理）就停止派新代理，把完成清單寫成 DONE 表存檔，告訴使用者停在哪裡；額度或時間快用完時停在一個步驟的邊界，不要自行重試。每個工作流開跑前先數出代理數上限（Mac 用 `wf_check_mac.js` 帶這次的 args 空跑；其他環境照 `workflows/README.md` 的公式，沒有 Workflow 工具就列角色表），照上限報代理數、每個角色的強度、約略費用與時間（`workflows/README.md`「代理數與費用」），使用者說好才跑；沒有他同意不自動續跑長工作流。
11. **文字檔一律 UTF-8、LF 換行。** 兩個 repo 根目錄都有 `.gitattributes`（`eol=lf`）；工作流腳本含 `\r` 會被拒絕；Python 在 Windows 寫檔要 `newline="\n"`。長 heredoc（約 100 行以上）在 Windows 的 shell 可能被截斷，反斜線也可能被改寫：大檔先存成檔再執行。
12. **公開與私人的分界。** Robbins 頁圖、切圖、OCR、事實帳、老師與他人的投影片、語料、成品只放私人 repo；kit 不放任何課程內容、個人聯絡方式、教學評量資料或本機絕對路徑。第三人（同事）在公開文件一律用代稱（同事甲、同事乙；對照表只在私人 repo 的 `corpus/pseudonyms.tsv`），他人投影片的引句換成〔他人投影片引句，公開版省略；完整版在私人素材庫 style_evidence〕。**每次 commit 到 kit 前跑 `python check_public.py`，FAIL 要是 0**（它讀私人 repo 的代稱表與他人段落表，所以要在兩個 repo 都在的環境跑）。
13. **修稿取捨順序**：事實 ＞ 術語 ＞ 版面 ＞ 文風；圖片與國考題的修正讓位（`01_權威順序.md` AUTH-07）。
14. **Traditional Chinese（台灣用語）**：投影片、講稿、文件都用繁體中文；dysplasia 寫「分化不良」。
15. **示意圖：影像模型只產沒有字的母圖，標籤由做投影片的代理（或人）加。** Runway 或其他影像模型出母圖；設計標籤位置與引線，用 `scripts/label_image.py` 以微軟正黑體疊上中英對照標籤（至少 24pt）；不讓模型寫字（教師 2026-10-14 明令：「字最清晰」，`docs/教師偏好與決策.md` 第 4 節）。
16. **反駁與複查有上限**（教師 2026-10-14 採用）。反駁只做一輪：每份批評檔 2 位反駁者（不是每條意見各派一組）。兩位都推翻就丟，一推一留由修訂者回原始資料查過再決定；不反駁反駁者。只有「找新問題」的複查可以重來，最多 2 輪，第 2 輪只看第 1 輪改過的張；第 1 輪沒有事實問題就不跑第 2 輪。理由與實測見 `workflows/README.md`「反駁與複查的上限」。審查（`lecture-review.js`）的第 2 輪也算這裡的第 2 輪：要跑時只跑問題多的面向，另外報價。審查非事實面向減成 1 位是舊有的省錢選項，不屬於上限（那 1 位推翻就丟；用時報價寫明）。 **不重複審查**（2026-10-15）：審查前先列已查過的面向與之後的改動，只跑有變或需新證據的（例：充實後只跑版面、圖片）；`workflows/README.md` 上限第 5 條。

## 4. 工作流：多代理的步驟怎麼做

### 4.0 所有工具共通

- **先讀** `docs/多session做法.md` 與 `workflows/README.md`；沒有 Claude Code 的 Workflow 工具時另讀 `docs/跨工具做法.md`。
- **角色**：每個 `workflows/*.js` 裡的 prompt 就是該角色的完整任務說明。prompt 是 JS 樣板字串（`${KIT}`、`${RUN}` 等換成檔頭由 args 算出的值）；變數、`agent`、`parallel`、`pipeline`、`label`、`schema` 與 prompt 裡的工具名（Bash tool、WebSearch 等）怎麼讀，見 `docs/跨工具做法.md` 第 2 節。要看圖或連外網的角色，只交給做得到的工具。課程自己寫的工作流放在 `<materials>/courses/<課>/_archive/journals/*.js`，讀法相同。
- **三種做法，產出的檔相同**：
  1. 有 Claude Code 的 Workflow 工具：直接跑 `.js`。
  2. 能派子代理、但沒有 Workflow 工具：照 `.js` 的順序與平行關係，一個角色派一個子代理，把該角色展開後的 prompt 整段交給它，強度照下表設。
  3. 不能派子代理：每個角色開一個新對話或新 session 做，主對話只排順序、記 DONE 表、彙整；工具不能逐對話設定強度時，整段用這一階段最高的一級，寫進報價與交付說明（`docs/跨工具做法.md` 第 1 節）。
- **換一雙眼睛**：查核、反駁、複查角色要開新的對話或子代理，重新從磁碟讀檔，不憑寫稿時的記憶判斷；反駁者的工作是試著推翻前一個角色的結論；兩位反駁者就做兩次、分開寫檔。
- **強度對照**：各角色的等級照 `workflows/README.md`「角色與強度」，名稱用 Claude 的叫法；本專案的等級名稱最低是 high，對到其他工具時依名次對，可能是該工具叫 medium 的那一級。其他工具照下表設；做不到就用最接近的一級，並在交付說明寫出實際設定。

  | 本專案的等級 | 意思 | Claude `effort` | OpenAI `reasoning.effort`：模型有 xhigh／沒有 xhigh | Gemini（例） |
  |---|---|---|---|---|
  | max | 最高一級 | `max` | `xhigh`／`high` | `thinking_level: high`（Gemini 2.5 見 `docs/跨工具做法.md` 第 4 節） |
  | xhigh | 次高一級；只有三級可選時用最高一級 | `xhigh` | `high`／`high` | `high` |
  | high | 再下一級 | `high` | `medium`／`medium` | `medium`（沒有就 `high`） |

  沒有強度設定的工具，選它主力的推理模型（硬規則 8）。各家有哪些等級、在各工具哪裡設，見 `docs/跨工具做法.md` 第 4 節。kit 的通用工作流除了 lecture-gather（`effort`、`effort_hard`、`effort_light` 分角色）都只吃一個 effort，怎麼對到這張表見 `workflows/README.md`「角色與強度」的「程式現況」。
- **模型**：見硬規則 8。
- **上限與報價在每種做法都一樣**（硬規則 10、16）：代理數＝要做幾個角色（每個子代理或每次「換一雙眼睛」算一個）；三種數法見 `workflows/README.md`「開跑前先空跑拿上限」。

下表的檔名取自 immune 課程的實際產出，實際以 `.js` 內 prompt 寫的為準。

### 4.1 蒐集（`lecture-gather.js`；設定在課程的 `gather.json`，格式見 `templates/gather.template.json`）

| 軌 | 每個單位依序做 | 輸出（課程資料夾內） |
|---|---|---|
| 教科書事實 | 每段：抽取 → 反駁 1 → 反駁 2 → 裁決 | `facts/seg/<段>.json`、`<段>_review1.json`、`<段>_review2.json`、`<段>_final.json` |
| 國考題 | 兩個獨立分類 → 核對並選題 | `_archive/gather/exam/classify_a.json`、`classify_b.json`、`exam_candidates.json` |
| 文獻 | 每題：搜尋 → 對 PubMed 摘要逐條查核 → 找開放授權圖；`lit_verifiers: 2` 時查核改成兩位獨立查核 → 裁決 | `_archive/gather/lit/<題>.json`、（兩位查核時）`<題>_verify1.json`、`<題>_verify2.json`、`<題>_verified.json`、`<題>_images.json` |

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

Mac 也用 `export_pdf.py`（LibreOffice；先跑一次 `bash scripts/lo_fonts_mac.sh`）；要 PowerPoint 本身定稿才用 `bash scripts/ppt_pdf_mac.sh "<成品>/<檔名>.pptx"`。然後 `python check_render.py "<成品>/<檔名>.pptx" "<PDF>" --warn-pt 4`（RED 要 0），再逐張看 `_archive/render/png/` 的 PNG（或縮圖拼板 sheets）。

### 4.5 審查（`lecture-review.js`，一到兩輪）

六個面向：facts、voice、terms、layout、exam、images。每個面向：審查 → 兩個獨立反駁 → 最後一個修正者：兩位反駁者都推翻的不套用，都確認的套用，一推一留的回原始資料（教科書頁圖、事實帳、glossary、PNG）查過再決定；改來源檔、重產、修到 check_deck 無 RED 且 style_check RED 0。輸出在 `_archive/review/round<N>/`：`review_<面向>.json`、`verify_<面向>_1.json`、`verify_<面向>_2.json`、`fix_report.md`。第 2 輪是另一次工作流：第 1 輪沒有事實問題就不跑（硬規則 16）；要跑只跑問題多的面向，另外報價。充實後的審查只跑 layout、images（硬規則 16）。

### 4.6 交付與回灌

交付與老師改稿後的回灌步驟見 `docs/SOP_新教案流程.md` 第 10、11 步。

### 4.7 課程自己寫的工作流

撰寫、充實、審查的 ultracode 版目前是課程自寫的腳本（例：私人 repo `courses/uro-a3/_archive/journals/` 的 `uro-write.js`、`uro-deepen.js`、`uro-review.js`），kit 還沒有通用版。做法相同：照腳本的 phases 與 prompt 一個角色一個角色做，強度看腳本裡每個 `agent()` 的 effort（args `effort` 一般、`effort_hard` 查證）；之後寫的腳本，機械性的角色用 `effort_light`（預設 high）。課程腳本或課程文件若還是舊寫法（不寫 effort、反駁 3 位過半成立、複查不設上限），以本檔與 `workflows/README.md` 為準。拿不到私人 repo 的 uro-*.js 時，照 `docs/多session做法.md`「四個階段」與 `workflows/README.md`「角色與強度」的角色排出同樣的結構。

## 5. 產出放哪、怎麼交回

- 中間檔：`<materials>/courses/<course>/_archive/{gather,blueprint,written,review,render,journals}/`；交接檔 `_archive/handoff.md`。
- 成品：`<materials>/courses/<course>/成品/`：PPTX、PDF、同名 `_layout.json`（每張的 slug 與張號，回灌用）、`待教師裁決清單.md`、`待補圖清單.md`、HTML 版（`scripts/html_deck.py`，圖片內嵌的單一檔；教師偏好第 8 節）。檔名寫課程代碼不寫系名：`病理學{碼}_{講題}(PPTX)_{YYYYMMDD}.pptx`，PDF 同名改 `(PDF)`（`course.yaml` 的 `decks.<deck>.filename`）。
- **交給教師的一律是草稿**：檔名、資料夾、一起交的檔、交件管道（OneDrive、git、Dropbox）照 `docs/教師偏好與決策.md` 第 8 節。放進他的 OneDrive 的步驟與禁用檔名只在他那台 Mac 的工作區 `AGENTS.md`；讀不到那份檔的環境不要寫 OneDrive。用 git 交件的指令見 `docs/SOP_新教案流程.md` 第 10 步。
- 每跑完一個階段（蒐集、藍圖、撰寫、充實、每一輪審查）就 commit＋push 一次 `_archive/`（含 `journals/`）與來源檔：雲端 VM 閒置會被回收，沒 push 的檔案與正在跑的工作流不會回來。雲端 session 只能 push 到 session 目前的工作分支。commit 並 push 到這門課的工作分支（雲端是 session 的分支）不必問；開 PR、合併進 main、直接 push 到 main 照教師當次的指示，沒有指示先問（kit 的工作版同步到公開版，是教師 2026-10-14 已說好的）。
- 最後告訴使用者：分支名稱、成品路徑、張數、檢查結果、待他裁決的項目數。
- kit 的工具若有修改，另外 commit 在 kit（先跑 `check_public.py`）；課程檔案絕不 commit 到 kit。

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
| `workflows/journals/`、`workflows/resume/` | `<materials>/courses/<課程>/_archive/journals/`（見硬規則 9、`workflows/README.md`「續跑」） |
| 舊專案 CLAUDE.md、本機記憶檔 | `docs/教師偏好與決策.md`、`docs/lessons_learned.md`、`style/guide/` |
| 「CLAUDE.md 第 N 節」「硬規則 N」（本 repo 的） | 本檔同一節、同一號（2026-10-14 起守則正本從 CLAUDE.md 搬到本檔，編號不變） |

## 7. 其他

- 不確定老師要什麼時，照 `style/guide/50_檢查/51_撰寫前檢查清單.md` A 段的預設做，並把問題列進待教師裁決清單；不要停下來等。
- 課程 immune（病理學C 免疫疾病，牙醫系三年級，2026-10-02）是第一套照整條管線做完的課；uro-a3（病理學A3 泌尿，2026-10）是四階段、多 session 做法的範例。公開的精簡範例在 `examples/immune/`。
- 開新課的範本：課程指引 `templates/course.CLAUDE.template.md`、交接檔 `templates/handoff.template.md`。
- 常用程式放 kit，不要每門課各抄一份；兩門課以上用得到的就收進 `scripts/` 或 `workflows/tools/`，課程只留設定檔（教師 2026-10-14，`docs/教師偏好與決策.md` 第 5 節）。每支的用法見 `scripts/README.md`。
- 教師下了新的通用明令：寫進 `docs/教師偏好與決策.md`（正本，連日期與原話），規則有變時改本檔、指南、範本；只管一門課的寫進該課 `brief.md` 與 handoff。各工具的本機記憶放摘要、repo 不能放的原話與指向。
- 硬規則 3、4、8、15、16 重述了教師偏好第 4 節與 `workflows/README.md` 的要點（本檔是每個工具都會自動讀的檔，規則要寫完整）；改那兩處時，同一個 commit 改對應的硬規則。

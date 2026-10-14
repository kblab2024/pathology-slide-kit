# handoff：<課程>（<講題>）

> 複製到 `<materials>/courses/<課程>/_archive/handoff.md`。這是多 session 做法的交接檔（`<kit>/docs/多session做法.md`）：每個 session 開工先讀它，收尾時更新並 commit。
> 不寫學生資料、私人數字、整合考題幹與答案；路徑寫相對路徑或 `<kit>`、`<materials>`。

> 下一個 session 的第一句（貼給下一個 session 的代理；任何工具都用這一句）：
> **「先讀 pathology-slide-materials/courses/<課程>/_archive/handoff.md 與 pathology-slide-materials/courses/<課程>/CLAUDE.md，驗環境，然後做階段 <N>。」**
> 不會自動載入 `AGENTS.md` 的工具：先讀 kit 與 materials 的 `AGENTS.md`（在教師的 Mac 上再加工作區的）。

## 四個階段（一個階段一個 session）

| 階段 | 做什麼 | 日期 | 工作流（空跑的代理數上限） | 狀態 |
|---|---|---|---|---|
| 0 腳本與工具 | 主 session 寫程式（能用程式算的不交給代理，例 `fit_capacity.py`）、建課、下一階段的腳本先空跑 | <日期> | 不開工作流 | <未開始／做完> |
| 1 研究 | 事實帳、文獻、示意圖說明、國考選題 | <日期> | <名稱（數字）> | |
| 2 初稿 | 大綱 → 撰寫 → 組裝、產檔 → 交毛胚 | <日期> | <名稱（數字）> | |
| 3 充實 | 照教師對毛胚的評語充實 → 算圖 → 審查 → 交草稿 | <日期> | <名稱（數字）> | |

## 現況（<日期> 階段 <N> 結束）

**分支**
| repo | 分支 | 狀態 |
|---|---|---|
| kit | `<分支>` | <commit；有沒有 push；為什麼停在這個分支> |
| materials | `<分支>` | <commit；有沒有 push> |

**教師裁決**：見 `brief.md` §2（有日期）。這個階段新加的：<一行摘要>。

**這個階段做完的事**
1. <做了什麼、產出在哪、怎麼驗證的>

**DONE 表與 journal**：`_archive/journals/<工作流>-done_<日期>.json`、`<工作流>-args.json`、`journal.jsonl`（沒跑工作流就寫「沒跑」）。

## 下一步：階段 <N+1>（<日期>）
1. 驗環境（課程 CLAUDE.md）。
2. 報價前先：更新本檔、請教師壓縮對話（Claude Code：`/compact`）、確認筆電不闔蓋帶走、附目前用量（Claude Code：`/usage`；其他工具的指令見 `<kit>/docs/跨工具做法.md` 第 5 節）；一併問：<要他決定的事>。
3. 工作流：<名稱>，args <…>；空跑的代理數上限 <數字>；強度：一般 <xhigh>（`effort`）、查證 <max>（`effort_hard`）、機械性的角色 <high>（`effort_light`）（照 `<kit>/workflows/README.md`「角色與強度」，每個代理都明寫）；反駁一輪、每份批評檔 2 位，複查最多 2 輪；約 $<…>（照上限算）。
4. 工作流跑的同時主 session 做：<不需代理的事>。
5. 收尾：存 journal 與 DONE 表、更新本檔、隱私檢查、commit 並 push 到工作分支；開 PR、合併進 main 照教師當次的指示，沒有指示先問。

## 之後的階段
<照上面的總表；寫退路（例：審查來不及就先交未審版，清單註明）>

## 待辦與注意
- <撰寫時要查的名詞、要補的題、要問的事>

## 下一講待辦（不要在這一講期間動）
- <…>

# handoff：<課程>（<講題>）

> 複製到 `<materials>/courses/<課程>/_archive/handoff.md`。這是多 session 做法的交接檔（`<kit>/docs/多session做法.md`）：每個 session 開工先讀它，收尾時更新並 commit。
> 不寫學生資料、私人數字、整合考題幹與答案；路徑寫相對路徑或 `<kit>`、`<materials>`。

> 下一個 session 的第一句（貼給 Claude）：
> **「先讀 courses/<課程>/_archive/handoff.md 與 courses/<課程>/CLAUDE.md，驗環境，然後做階段 <N>。」**

## 現況（<日期> 階段 <N> 結束）

**分支**
| repo | 分支 | 狀態 |
|---|---|---|
| kit | `<分支>` | <commit；有沒有 push；為什麼停在這個分支> |
| materials | `<分支>` | <commit；有沒有 push> |

**教師裁決**：見 `brief.md` §2（有日期）。這個階段新加的：<一行摘要>。

**這個階段做完的事**
1. <做了什麼、產出在哪、怎麼驗證的>

**DONE 表與 journal**：`_archive/journals/<工作流>_DONE.json`、`<工作流>-args.json`、`journal.jsonl`（沒跑工作流就寫「沒跑」）。

## 下一步：階段 <N+1>（<日期>）
1. 驗環境（課程 CLAUDE.md）。
2. 報價前先：更新本檔、請教師 `/compact`、確認筆電不闔蓋帶走、附 `/usage`；一併問：<要他決定的事>。
3. 工作流：<名稱>，args <…>，代理數 <公式＝數字>，約 $<…>。
4. 工作流跑的同時主 session 做：<不需代理的事>。
5. 收尾：存 journal 與 DONE 表、更新本檔、隱私檢查、commit；push 與 merge 照教師指示。

## 之後的階段
<照計畫；寫退路（例：審查來不及就先交未審版，清單註明）>

## 待辦與注意
- <撰寫時要查的名詞、要補的題、要問的事>

## 下一講待辦（不要在這一講期間動）
- <…>

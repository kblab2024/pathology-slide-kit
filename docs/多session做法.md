# 多 session 的做法：一個階段一個 session

教師 2026-10-14：「這種多 session 的做法我覺得很棒，請作為範例寫進所有 master」。範例是 2026-10 的 A3 泌尿 L1（私人 repo `courses/uro-a3/`）。之後的課都照這個做法分階段、分 session。

## 為什麼這樣做
- **context 小。**
  - 每個 session 只做一個階段。開工時讀 handoff 就接得上，不必背前面的對話。
  - 工作流開跑前請他 `/compact`，結果回來時才有空間。
- **斷線也接得回來。**
  - 狀態寫在 repo 的 `_archive/handoff.md`，不在對話裡。
  - 遙控斷線、換電腦、雲端 VM 回收，新 session 讀 handoff 就能接。
- **他好核准。**
  - 每個階段開頭一次報價、一次核准，問題集中問。
  - 中途的新明令當場寫進主文件，下一個 session 自然就照做。

## 四份檔各管什麼

| 檔 | 放什麼 | 什麼時候改 |
|---|---|---|
| 計畫（plan） | 整門課的階段 × 日期 × 工作流 × 代理數與費用；教師已裁決表；每個階段的步驟；退路 | 開工那個 session 寫；範圍或交期改了才改 |
| `courses/<課>/_archive/handoff.md` | 交接的唯一狀態（格式見 `templates/handoff.template.md`）：<br>・下一個 session 的第一句<br>・分支表：每個 repo 的分支、commit、有沒有 push<br>・做完的事<br>・DONE 表與 journal 路徑<br>・下一步（含報價要寫的數字）<br>・待辦<br>・下一講的待辦 | 每個 session 收尾時改，並 commit |
| `courses/<課>/CLAUDE.md` | 不太變的規則：開工順序、環境檢查、單一事實來源、工作流規則、交件、隱私 | 規則變了才改 |
| `courses/<課>/brief.md` | 教師裁決（每列有日期） | 他每次裁決都改 |

## 一個 session 的流程
1. **第一句固定**：「先讀 courses/<課>/_archive/handoff.md 與 courses/<課>/CLAUDE.md，驗環境，然後做階段 N。」
   - 這一句寫在 handoff 最上面，上一個 session 收尾時就準備好。
2. **提醒掛載的 OneDrive 工作資料夾**（工作區的 CLAUDE.md 要求每個 session 第一次回覆時提醒）。
3. **驗環境**：照課程 CLAUDE.md 的指令跑，包括 kit 在哪個分支、套件、`common.ROOT`、`find_materials()`。
4. **準備工作流**：
   - 寫或改腳本與 args，每個 `agent()` 都寫 `model: 'opus'`，不傳 effort。
   - 沒有 node 的 Mac 用 `workflows/tools/wf_check_mac.js` 查語法、空跑、數代理數。
5. **更新 handoff，然後一次報價、一次問完**：
   - 報代理數、約略費用、約略時間。
   - 請他下 `/compact`，並看一下 `/usage`。
   - 確認筆電不會闔蓋帶出門。
   - 要開 PowerPoint、會跳 macOS 授權視窗的步驟，問他能不能在電腦前。
   - 其他要他決定的事一起問。
   - 他說好才開跑。
6. **工作流在背景跑的同時，主 session 做不需要代理的事**：
   - 例：圖片盤點、程式畫圖（`scripts/draw_flow.py`）、補切教科書圖；Runway 母圖回來後設計標籤並用 `scripts/label_image.py` 疊上（示意圖的標準做法）。
   - 代理會讀的檔，等工作流跑完再改。
   - 這段期間不要在同一個 repo 切分支。
7. **他中途下新明令**：
   - 先停下手上的事，當場寫進所有主文件：本課的 brief、CLAUDE.md、course.yaml、glossary、handoff；通用的寫進 kit 的教師偏好、CLAUDE.md、指南、範本，以及記憶檔。
   - 寫完再繼續。已經在跑的工作流照舊，結果回來時再依新明令修。
8. **收尾**：
   - 工作流的腳本、args、`journal.jsonl`、DONE 表存進 `_archive/journals/`。
   - 更新 handoff，寫好下一個 session 的第一句。
   - commit 前跑隱私檢查；push 與 merge 照他當次的指示。
   - repo 裡正在跑工作流時，要合併就把分支推上去，在 GitHub 開 PR 合併，不在本機切分支。

## 範例：A3 泌尿 L1（2026-10）

| 階段 | 日 | 內容 | 工作流（代理數） |
|---|---|---|---|
| 0 | 10/14 | repo 整理、題庫補 115-2、教科書頁圖、建課、讀素材、寫 handoff | 不開 |
| 1 | 10/14–15 | 切圖與圖片盤點；事實與文獻蒐集；Runway 重繪說明；程式畫圖 | gather 38、Runway 21 |
| 2 | 10/16 | 撰寫 → 組裝 → 產檔、算圖 → 審查 → 交 v1 草稿 | 撰寫約 18、審查 19 |
| 3 | 10/20 | 回灌他的改動、換 Runway 圖、第二輪審查，交草稿2 | 審查約 7–10 |

**階段 1 那天實際的流程：**
- **開工**：讀 handoff、驗環境，然後準備兩個工作流的腳本與 args。
- **報價**：一次報兩個工作流（59 個代理），連同 NCCN PDF 與 PowerPoint 試跑一起問，他核准後兩條同時開跑。
- **跑的同時，主 session**：做圖片盤點、補切 Robbins 圖、用程式畫機轉圖。
- **他看到圖時下了兩條新明令**：每張都要中英對照、張數上限放寬到 110。當場寫進本課與 kit 的所有主文件，再接著畫圖。

## 注意
- 續跑一律用 `args.done`，不用 `resumeFromRunId`（kit 硬規則 9）。
- 一個 session 只做一個階段；做不完的寫進 handoff 的「下一步」，不硬撐到 context 用完。
- 跨 repo 的分支要寫進 handoff 的分支表：哪個 repo 停在哪個分支、為什麼。

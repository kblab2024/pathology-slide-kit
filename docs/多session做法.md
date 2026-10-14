# 多 session 的做法：四個階段，一個階段一個 session

教師 2026-10-14：「這種多 session 的做法我覺得很棒，請作為範例寫進所有 master」。同一天晚上他看完結果，把建一套課的做法定成四個階段、一個階段一個 session、共 4 個 session：「i think this build script and tool => research with ultracode => draft with high/extra => deepen with ultracode workflow is surprisingly effective and economic」「stage 0 1 2 3 totally 4 session」。範例是 2026-10 的 A3 泌尿 L1（私人 repo `courses/uro-a3/`）。之後的課都照這個做法。

本檔寫給所有工具。Claude Code 的指令放在括號裡（例：壓縮對話（Claude Code：`/compact`））；沒有多代理執行器的工具照 `AGENTS.md` 第 4.0 節與 `docs/跨工具做法.md` 做同樣的角色。

## 四個階段

| 階段 | 做什麼 | 代理 | 交出什麼 |
|---|---|---|---|
| 0 腳本與工具 | 主 session 自己做：建課、教科書頁圖、切圖、素材池、組裝、檢查、算圖、隱私檢查要用的程式；下一階段的工作流腳本與 args 先空跑。能用程式算的不交給代理：例 版型容量跑 `scripts/fit_capacity.py --course <課>`，規劃、撰寫代理讀它的表，不自己試產校準（2026-10-14 uro-a3 充實的規劃代理自己試產校準，最後一次呼叫的 context 約 76 萬 token；教師同晚同意做這支程式） | 不開工作流 | 程式（兩門課以上用得到的收進 kit）、空跑過的腳本、handoff；（沒有 Workflow 工具時）下一階段的角色表：角色、label、順序與哪些可以同時做、強度、讀什麼、寫哪個檔；列數就是代理數上限，寫在 handoff 的「下一步」 |
| 1 研究 | 教科書逐段建事實帳（抽取 → 2 位反駁 → 裁決）、文獻（搜尋 → 查核）、示意圖說明（撰寫 → 2 位反駁 → 修訂）、國考選題 | ultracode 等級的工作流 | 事實帳、文獻、圖片清單、示意圖說明、待教師決定的清單 |
| 2 初稿 | 大綱 → 大綱批評 → 修訂；分批撰寫 → 多面向批評＋2 位反駁 → 修訂 → 複查；全套完整性批評 → 跨批修正 → 用字審查；組裝、產檔、檢查 | ultracode 規模的多輪結構；強度照 `workflows/README.md`「角色與強度」的「2 初稿」列：一般 xhigh、查證 max、機械性的角色（版面、用字與中英、國考與指引的反駁、第二輪複查、用字審查）high（uro-a3 實際跑的是 xhigh 30、max 27，教師 21:42 照實記，21:52 採用分角色的表） | 毛胚＋待教師裁決清單（教師要先看時，可以先不審查就交） |
| 3 充實 | 照教師對毛胚的具體評語：規劃 → 深度與連貫批評 → 修訂計畫；分批改寫 → 事實批評＋2 位反駁、版面與口吻、連貫 → 修訂 → 複查；全套檢查 → 跨批修正 → 用字審查；之後算圖、審查、交草稿 | ultracode 等級的充實工作流 | 草稿（交件照 `docs/教師偏好與決策.md` 第 8 節） |

- **ultracode** 是教師對 Claude Code 說的詞。本專案說的「ultracode 等級」指上表這種結構：先規劃再批評、多面向批評、每份批評檔 2 位反駁者、修訂、有上限的複查、全套完整性批評，查證步驟用最高強度。任何工具照這個結構做就算數。
- **階段 1 還沒有照這個結構跑過**：uro-a3 的研究是 kit 的標準結構（抽取 → 2 位反駁 → 裁決等），62 個代理全部 xhigh（腳本沒寫 effort，繼承 session），沒有 max、沒有複查；教師說的「research with ultracode」和實際跑的不同。`workflows/README.md` 表上研究階段的 max 分配還沒實測：第一次照表跑時，報價要和 uro-a3 的研究（62 個代理、subagent_tokens 10,850,106）對照，寫出多出來的費用。
- **每個角色用哪一級強度**、**反駁與複查的上限**、**代理數與報價**：見 `workflows/README.md`「角色與強度」「反駁與複查的上限」「代理數與費用」，以及 `AGENTS.md` 硬規則 8、10、16。每個代理都要明寫強度。
- **階段和 SOP 的「步」**：對應寫在 `docs/SOP_新教案流程.md` 總表的「階段」欄。教師改稿後的回灌（SOP 第 11 步）另開 session。
- **每個階段用哪一支工作流**（範本都在私人 repo `courses/uro-a3/_archive/journals/`；kit 還沒有通用版，拿不到私人 repo 時照上表的角色自己排，`AGENTS.md` 第 4.7 節）：
  - 階段 1：kit 的 `lecture-gather.js`；示意圖說明等課程專用的部分用課程自寫的腳本（範本 `uro-runway.js`）。
  - 階段 2：課程自寫的撰寫工作流，一支做完 SOP 第 5、6 步（上表第 2 列的結構），範本 `uro-write.js`。kit 的 `lecture-blueprint.js`（三視角草稿 → 三位評審 → 綜合 → 批評 → 修訂）與 `lecture-write.js`（每批 3 位查核，沒有反駁與複查）是 2026-09 immune 的結構，不是上表的做法；要用它們省錢，先在報價寫明、教師說好。
  - 階段 3：課程自寫的充實工作流（範本 `uro-deepen.js`），算圖後審查（範本 `uro-review.js`，跑之前先改成硬規則 16 的寫法；也可以用 kit 的 `lecture-review.js`）。
- **舊說法**：本檔 2026-10-14 上午的版本與 uro-a3 的 handoff 把「階段 3」寫成「回灌、換 Runway 圖、第二輪審查」；以本節為準。

## 為什麼這樣做
- **context 小。**
  - 每個 session 只做一個階段。開工時讀 handoff 就接得上，不必背前面的對話。
  - 工作流開跑前先壓縮對話（Claude Code：請教師下 `/compact`），結果回來時才有空間。
- **斷線也接得回來。**
  - 狀態寫在 repo 的 `_archive/handoff.md`，不在對話裡。
  - 遙控斷線、換電腦、雲端 VM 回收、換工具，新 session 讀 handoff 就能接。
- **他好核准。**
  - 每個階段開頭一次報價、一次核准，問題集中問。
  - 中途的新明令當場寫進主文件，下一個 session 自然就照做。
- **貴的步驟有結構管著。** 查證用最高強度，但反駁只做一輪、複查有上限（硬規則 16），代理數在開跑前就算好上限。

## 四份檔各管什麼

| 檔 | 放什麼 | 什麼時候改 |
|---|---|---|
| 計畫（plan） | 整門課的階段 × 日期 × 工作流 × 代理數與費用；教師已裁決表；每個階段的步驟；退路。放在課程的 `_archive/plan.md`，或直接寫進 handoff 的「四個階段」與「之後的階段」。Claude Code plan mode 存的計畫檔在使用者資料夾裡，只在本機，雲端與其他工具讀不到，要用的話複製進來 | 開工那個 session 寫；範圍或交期改了才改 |
| `courses/<課>/_archive/handoff.md` | 交接的唯一狀態（格式見 `templates/handoff.template.md`）：<br>・下一個 session 的第一句<br>・四個階段的總表<br>・分支表：每個 repo 的分支、commit、有沒有 push<br>・做完的事<br>・DONE 表與 journal 路徑<br>・下一步（含報價要寫的數字與每個角色的強度）<br>・待辦<br>・下一講的待辦 | 每個 session 收尾時改，並 commit |
| `courses/<課>/CLAUDE.md` | 不太變的規則：開工順序、環境檢查、單一事實來源、工作流規則、交件、隱私（檔名叫 CLAUDE.md，內容對所有工具都適用） | 規則變了才改 |
| `courses/<課>/brief.md` | 教師裁決（每列有日期） | 他每次裁決都改 |

2026-10-14 以前開的課（immune、headneck-dent 等）沒有 handoff，接續步驟寫在該課 CLAUDE.md 的「待辦」；新課以 handoff 為準。

## 一個 session 的流程
1. **第一句固定**：「先讀 pathology-slide-materials/courses/<課程>/_archive/handoff.md 與 pathology-slide-materials/courses/<課程>/CLAUDE.md，驗環境，然後做階段 N。」
   - 這一句寫在 handoff 最上面，上一個 session 收尾時就準備好。任何工具都用同一句。
   - 不會自動載入 `AGENTS.md` 的工具：開工先讀 kit 與 materials 的 `AGENTS.md`，在教師的 Mac 上再加工作區的。
2. **在教師的 Mac 上**：告訴教師這個工具寫得進哪些 OneDrive 工作資料夾（工作區 `AGENTS.md` 第 6 節；雲端與別台電腦沒有這一步）。
3. **驗環境**：照課程 CLAUDE.md 的指令跑，包括 kit 在哪個分支、套件、`common.ROOT`、`find_materials()`。
4. **準備工作流**：
   - 寫或改腳本與 args：用 Claude 時每個代理寫死 `model: 'opus'`（其他工具照 `AGENTS.md` 硬規則 8），並明寫 effort（照 `workflows/README.md`「角色與強度」）；反駁與複查照硬規則 16 的上限寫。
   - 數出代理數上限（三種數法見 `workflows/README.md`「開跑前先空跑拿上限」：Mac 用 `wf_check_mac.js` 帶這次的 args 空跑；有 node 用公式代入這次的段數、批數、面向數；沒有 Workflow 工具就列角色表）。確認 effort：課程自寫的腳本用 grep 確認每個 `agent()` 都有 effort；kit 的通用工作流確認 args 有 `effort`（腳本用包裝套到全部代理）。
5. **更新 handoff，然後一次報價、一次問完**：
   - 報代理數上限、每個角色的強度、約略費用（照上限算）、約略時間。
   - 請他先壓縮對話（Claude Code：`/compact`），並附目前用量（Claude Code：`/usage`）（其他工具的指令見 `docs/跨工具做法.md` 第 5 節；拿不到用量就在報價寫明）。
   - 確認筆電不會闔蓋帶出門。
   - 要開 PowerPoint、會跳 macOS 授權視窗的步驟，問他能不能在電腦前。
   - 其他要他決定的事一起問。
   - 他說好才開跑。
6. **工作流在背景跑的同時，主 session 做不需要代理的事**：
   - 例：圖片盤點、程式畫圖（`scripts/draw_flow.py`）、補切教科書圖；Runway 母圖回來後設計標籤並用 `scripts/label_image.py` 疊上（示意圖的標準做法）。
   - 代理會讀的檔，等工作流跑完再改。
   - 這段期間不要在同一個 repo 切分支；要改別的分支，另開 worktree。
7. **他中途下新明令**：
   - 先停下手上的事，當場寫進所有主文件：本課的 brief、CLAUDE.md、course.yaml、glossary、handoff；通用的寫進 kit 的教師偏好、`AGENTS.md`、指南、範本。各工具的本機記憶放摘要、repo 不能放的原話與指向。
   - 寫完再繼續。已經在跑的工作流照舊，結果回來時再依新明令修。
8. **收尾**：
   - 工作流的腳本、args、`journal.jsonl`、DONE 表存進 `_archive/journals/`。
   - 更新 handoff，寫好下一個 session 的第一句。
   - commit 前跑隱私檢查；commit 並 push 到這門課的工作分支不必問；開 PR、合併進 main 照他當次的指示，沒有指示先問。
   - repo 裡正在跑工作流時，要合併就把分支推上去，在 GitHub 開 PR 合併，不在本機切分支。

## 範例：A3 泌尿 L1（2026-10）

原計畫是階段 2 在 10/16、階段 3 在 10/20（回灌、換 Runway 圖、第二輪審查）。實際 10/14 一天做到階段 3：

| 階段 | 時間（10/14） | session | 內容 | 工作流（代理數） |
|---|---|---|---|---|
| 開工準備 | 10/13 | 另一個專案的 session | 寫開工指示 | 不開 |
| 0 | 07:57–09:14 | 階段 0 | 題庫補 115-2、kit 修改、頁圖、建課、素材池與切圖程式、隱私檢查程式、handoff | 不開（plan mode 的輔助子代理 4 個） |
| 1 | 09:22–約 10:44 | 階段 1 | 事實與文獻蒐集、Runway 重繪說明、CRPC 文獻補充；同時主 session 補程式（`label_image.py`、`draw_flow.py` 等） | 蒐集 38、示意圖說明 21、文獻補充 3，共 62（全部 xhigh，腳本沒寫 effort，繼承 session） |
| 2 | 12:41–約 20:50 | 階段 2＋3 | 撰寫 ultracode 版 → 組裝 → 產檔、檢查 → 交 110 張毛胚（OneDrive 傳不上大檔，改推 git） | 撰寫 57（xhigh 30、max 27），12:52–18:25 |
| 3 | 21:33 起 | 同上 | 教師看毛胚後的評語 → 充實 → 算圖 → 審查 → 交 v1 草稿 | 充實最多 34：23:30 照教師新明令停掉、用 DONE 表續跑，10/15 00:29 方案額度用完中斷（完成 12 步），03:30 再用 DONE 表續跑，結果跑完再補；審查 39–40（還沒跑，要先改成硬規則 16 的寫法） |

- uro-a3 的階段 2、3 在同一個 session；新課照四個 session 切。
- 第一次開撰寫（12:44）用的是沒寫 effort 的舊腳本，代理繼承主 session 當時的 medium；12:49 教師要求 ultracode 時一併發現，停掉、腳本改成明寫 effort，12:52 重開。
- 各階段的費用與 token 實測見 `workflows/README.md`「代理數與費用」。

**階段 1 那天實際的流程：**
- **開工**：讀 handoff、驗環境，然後準備兩個工作流的腳本與 args。
- **報價**：一次報兩個工作流（59 個代理），連同 NCCN PDF 與 PowerPoint 試跑一起問，他核准後兩條同時開跑。
- **跑的同時，主 session**：做圖片盤點、補切 Robbins 圖、用程式畫機轉圖。
- **他看到圖時下了兩條新明令**：每張都要中英對照、張數上限放寬到 110（同晚看完毛胚再放寬到 120）。當場寫進本課與 kit 的所有主文件，再接著畫圖。

## 注意
- 續跑一律用 DONE 表（`AGENTS.md` 硬規則 9）。
- 一個 session 只做一個階段；做不完的寫進 handoff 的「下一步」，不硬撐到 context 用完。
- 跨 repo 的分支要寫進 handoff 的分支表：哪個 repo 停在哪個分支、為什麼。
- 課程自己的文件或腳本若還是舊寫法（不寫 effort、反駁 3 位過半成立、複查到沒有新發現為止），以本檔與 `workflows/README.md` 為準，並在那門課的下一個 session 改掉。

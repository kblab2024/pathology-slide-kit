# Claude Code 雲端 session 入門（給老師）

寫給在 Windows 上用 Claude 桌面 app 的使用者。內容依 2026-09-25 查閱的官方文件整理；介面上的按鈕名稱會改版，標「請以官方說明為準」的地方是官方文件沒寫清楚、或我沒有親自確認的部分。

官方文件：

- 雲端 session：<https://code.claude.com/docs/en/claude-code-on-the-web>
- 雲端環境（網路、環境變數、Setup script）：<https://code.claude.com/docs/en/cloud-environments>
- 入門步驟：<https://code.claude.com/docs/en/web-quickstart>
- 費用與用量：<https://code.claude.com/docs/en/costs>

## 1. 雲端 session 是什麼

- Claude 在 Anthropic 的雲端電腦（Ubuntu Linux 虛擬機）上工作，不佔用您的電腦。關掉 app、闔上筆電，它照樣跑；可以從桌面 app、瀏覽器（claude.ai/code）或手機 Claude app 的 Code 分頁看進度、插話、回答它的問題。
- 雲端電腦每次都從 GitHub 複製（clone）repo 開始，做完把改動推（push）成一個新分支。您從 GitHub 拿回檔案。
- 它看不到您電腦上的任何東西：本機的 Claude 記憶檔、雲端硬碟同步資料夾裡的檔案、PowerPoint、微軟正黑體都沒有。所以要用的資料都要先在 GitHub 的兩個 repo 裡：
  - `kblab2024/pathology-slide-kit`（公開）：工具、工作流、風格指南、題庫、文件；
  - `kblab2024/pathology-slide-materials`（私人）：課程資料、教科書頁圖、您的投影片語料、成品。
- 有雲端 session 額度（cloud session credits）時先扣它；用完或過期後算進您的 Claude 方案用量。雲端電腦本身不另收運算費（見第 9 節）。

## 2. 開始前需要

- Claude 付費方案（Pro、Max、Team，或含 Claude Code 的 Enterprise 席位）。
- GitHub 帳號，對 kblab2024 底下兩個 repo 有權限；兩個 repo 已推上 GitHub，materials 設為 Private。

## 3. 一次性設定

### 3.1 連 GitHub、安裝 Claude GitHub App

1. 瀏覽器開 <https://claude.ai/code>，登入 Claude，照提示按 **Sign in with GitHub** 授權。
2. 安裝 Claude GitHub App：開 <https://github.com/apps/claude/installations/new> → 選 **kblab2024** → **Only select repositories** → 勾 `pathology-slide-materials`（私人 repo 一定要裝，否則雲端看不到）和 `pathology-slide-kit` → **Install**。kblab2024 是組織時，可能要組織擁有者核准。
3. 之後開 session 時，repo 清單裡若沒有私人 repo，多半是 App 沒裝到那個 repo，回到這一步檢查。

### 3.2 建立雲端環境（environment）

環境是「雲端電腦開機時要裝什麼、能連哪些網站」的設定，建一次就好。

1. 在 claude.ai/code 輸入框上方點雲朵圖示（環境選單），選 **Add cloud environment**。桌面 app 則是在輸入框的環境下拉選單選 **Cloud**，同一個選單裡有新增環境的選項。
2. **Name**：`pathology-slides`。
3. **Network access**：**Trusted**（可以連 GitHub、PyPI、Ubuntu 套件庫等常用網站）。
4. **Environment variables**：留空。兩個 repo 在同一個 session 時工具會自己找到對方。不要在這裡放密碼，使用這個環境的人都看得到。
5. **Setup script**：貼下面這段短的啟動腳本（2026-09-25 實際建立的 `pathology-slides` 環境就是這段）。它從公開 kit 抓最新的 `setup/cloud-setup.sh` 執行：用 apt 裝中文字型（Noto CJK）、Tesseract（OCR）、LibreOffice（沒有 PowerPoint 時轉 PDF），再裝 Python 套件。`raw.githubusercontent.com` 在 Trusted 名單內；不管成敗都 `exit 0`，session 一定開得起來。

   ```bash
   #!/bin/bash
   # 病理投影片工具包 pathology-slide-kit：抓公開 repo 最新的 setup/cloud-setup.sh 執行
   export SLIDEKIT_NO_CLONE=1
   curl -fsSL https://raw.githubusercontent.com/kblab2024/pathology-slide-kit/main/setup/cloud-setup.sh -o /tmp/slidekit-setup.sh      && bash /tmp/slidekit-setup.sh      || echo "[slidekit-setup] 警告：下載或執行失敗，session 照常啟動"
   exit 0
   ```

   `SLIDEKIT_NO_CLONE=1` 是故意的：Setup script 的結果會被快取約 7 天，若在這裡 clone kit，之後 7 天的 session 都會拿到舊版 kit。kit 一律在開 session 時從 repository selector 加進來（見第 4 節）。也可以改成把 `cloud-setup.sh` 整份貼進來，效果相同，只是 kit 更新時要重貼。
6. 按 **Create environment**。

補充：

- Setup script 以 root 身分在第一次開 session 時執行（官方要求 5 分鐘內跑完；非 0 結束碼會讓 session 開不起來），結果存成檔案系統快照，約 7 天內的新 session 直接用快照、不再重跑；改了 Setup script 或網路設定會重建快照。用上面的啟動腳本時，kit 的 `cloud-setup.sh` 更新會在下次重建快照時自動生效（最慢約 7 天）；要立刻生效，就在環境設定裡隨便改一下 Setup script 的註解再存檔。
- 環境本身不綁 repo：每次開 session 都要在 repository selector 同時加 `pathology-slide-materials` 與 `pathology-slide-kit`（兩個都選 `main`）。多 repo 的 session 從兩個 clone 的上一層開始，工具會自動找到同層的素材庫。
- 蒐集階段要連 PubMed／NCBI 查文獻、從 Wikimedia Commons、CDC PHIL、PMC 下載開放授權圖，或從考選部下載新一年的考題時，這些網站不在 Trusted 名單。可以把 Network access 改成 **Custom**，勾 **Also include default list of common package managers**，在 Allowed domains 加：

  ```text
  pubmed.ncbi.nlm.nih.gov
  eutils.ncbi.nlm.nih.gov
  www.ncbi.nlm.nih.gov
  pmc.ncbi.nlm.nih.gov
  europepmc.org
  doi.org
  commons.wikimedia.org
  upload.wikimedia.org
  phil.cdc.gov
  wwwq.moex.gov.tw
  ```

  這份清單依蒐集工作流的提示整理（文獻查核、`gather.template.json` 預設的三個圖源、考選部）；代理實際要連的網站可能更多，被擋時它會在回報的 notes 寫出來，再把網域補進來。Claude 的網頁搜尋工具是否也受這個名單限制，請以官方說明為準。另一個做法是這一部分在本機（Local）做完、commit 之後再到雲端接著做。

## 4. 開一個 session

### 用桌面 app

1. 開新 session，在輸入框的環境下拉選 **Cloud**，選 `pathology-slides` 環境。
2. 選 repo `kblab2024/pathology-slide-materials`，再按旁邊的 **+** 加 `kblab2024/pathology-slide-kit`。兩個 repo 各有分支選單，都選 `main`（接續舊工作時選上次 session 推上去的分支）。
3. 模型選 **Opus**。
4. 權限模式選 **Accept edits**（Claude 改檔不逐一問您）；想先看計畫再動手就選 **Plan**。雲端沒有逐項核准的 Manual 模式。
5. 貼上第 5 節的第一句話，按 Enter。

### 用瀏覽器（claude.ai/code）

點輸入框下方的 repository selector 選 repo，可以加多個 repo，每個 repo 有自己的分支選單；其餘同上。

### 用手機

Claude app 的 **Code** 分頁可以看進度、回答問題，不適合開新任務。

## 5. 第一句話（複製後改角括號內容）

```text
請先讀 pathology-slide-kit/CLAUDE.md 與 pathology-slide-materials/CLAUDE.md，
再讀 pathology-slide-kit/docs/教師偏好與決策.md 與 docs/SOP_新教案流程.md。

任務：做一份新教案。
- 主題：<例：呼吸系統病理>
- 課程代碼與對象：<例：A1，醫學系與中醫甲>
- 上課日期與節數：<例：2026-11-05，兩節，每節 50 分鐘講完>
- 教科書：<例：Robbins 11e 第15章；頁圖已在 textbook/robbins11e_ch15_lung/pages>
- 我舊的同講題投影片：<corpus 代號或 repo 內路徑；沒有就寫「無」>
- 國考題：<例：醫師國考，每節 3 題；或「不放」>

做法：
1. 先照 style/guide/50_檢查/51_撰寫前檢查清單.md A 段列出要問我的問題，一次問完。
   我沒回答的照預設做，並記進待教師裁決清單。
2. 課程資料夾叫 courses/<英文名>，照 SOP 第 0 步建立。
3. 每個工作流開始前，先告訴我預計派幾個代理、做哪些事、以 API 牌價估計約多少錢（kit 的 docs/cloud_session_教學.md 第 9 節），等我回「好」再跑。代理一律用 Opus。
4. 每完成一個階段，就在 pathology-slide-materials 的 session 分支 commit 並 push。
5. 做完後把成品 PPTX 用 git add -f 加入並 push，
   告訴我分支名稱、檔案路徑、張數、檢查結果、待我裁決的項目數。
```

之後接續舊工作的第一句話：

```text
請先讀兩個 repo 的 CLAUDE.md 與 courses/<英文名>/CLAUDE.md。
接續 <課程> 的 <階段，例：撰寫>：用 kit 的 workflows/tools/done_from_journal.py 重建 DONE 表
（courses/<英文名>/_archive/journals/ 有 journal 就用它，沒有就用 --scan 掃已有的輸出檔），
只跑還沒完成的代理；開跑前先告訴我剩幾個代理。
```

教科書頁圖要先在 repo 裡。Robbins 單章的掃描 PDF 常超過 100 MB，推不上 GitHub，所以「PDF 轉頁圖」與切圖（SOP 第 1、2 步）建議在您自己的電腦用桌面 app 的 **Local** 做（有 PDF 時切出來的圖比較清楚），commit 頁圖與切圖之後再到雲端做後面的步驟。

## 6. 看進度

- 側邊欄點 session 就能看；Claude 在跑工作流時會列出正在做的代理。
- Claude 工作中您也可以打字，訊息會排隊等它讀；還沒被讀到的訊息可以按 ✕ 收回。
- Claude 問問題時要回答它才會繼續；它等您的時候也算閒置。
- 關掉視窗不會停止；要停就按停止鈕。
- **閒置一段時間後雲端電腦會被回收。** 重開 session 會配一台新電腦、對話紀錄還在，但當時正在跑的代理、指令，以及沒 push 的檔案不會回來。這就是第一句話要求「每個階段都 push」的原因；接著說「從已有輸出重建 DONE 表續跑」即可。

## 7. 拿回 PPTX

Session 做到一個段落會把分支推上 GitHub（名稱通常以 `claude/` 開頭，Claude 會告訴您）。三種拿法：

1. **網頁下載（最簡單）**：GitHub 開 `pathology-slide-materials` → 左上分支選單切到該分支 → 進 `courses/<課程>/成品/` → 點 PPTX → 右上角 **Download raw file**（下載圖示）。網頁不能預覽 PPTX，直接下載即可。
2. **本機 git**：已經 clone 過的話，在私人 repo 資料夾執行 `git fetch` 再 `git switch <分支名稱>`（或用 GitHub Desktop 切分支），檔案就在 `courses/<課程>/成品/`。
3. **Create PR**：在 session 的 diff 檢視（顯示 `+數字 -數字` 的地方）按 **Create PR**，到 GitHub 檢查後按 Merge，成品與中間檔就進 `main`。建議等您確認成品再 merge。

注意：成品 PPTX 預設被 `.gitignore` 排除（檔案大、可重產），所以要 Claude 用 `git add -f` 加入交件的那一個檔。GitHub 單檔上限 100 MB（50 MB 以上會警告）；immune 的 184 張約 58 MB。每提交一版 PPTX，repo 歷史就多約 60 MB，所以同一門課只提交最後交件的那一版；中途要看的版本看 PDF（小很多）。要保留多個版本時，請 Claude 把 PPTX 放到 GitHub Release 的附件。

## 8. 之後繼續，或拉回自己的電腦

- **同一個 session 繼續**：側邊欄點回去打字即可。
- **開新 session 接續**：分支選單選上次 session 推上去的分支，用第 5 節「接續舊工作」那一句。
- **拉回本機終端機**：在本機該 repo 的資料夾（工作目錄要乾淨、登入同一個 claude.ai 帳號）執行 `claude --teleport`，從清單選 session；或 `claude --teleport <session-id>`。它會切到 session 的分支並載入對話。在雲端 session 裡打 `/teleport` 會回覆可以直接貼的指令。兩個 repo 的 session 能不能整個 teleport，官方文件沒有寫清楚，請以官方說明為準；最保險的做法是用 git 拉分支，再在桌面 app 選 **Local** 開新 session 接手。
- **桌面 app 的 Continue in**：這個選單是把「本機」session 送到雲端（Claude Code on the Web），不是反方向；需要工作目錄乾淨。

您直接改過的 PPTX 要回灌時，在本機做最簡單（檔案本來就在您電腦上）。要在雲端做，先用 git 或 GitHub Desktop 把檔案 commit 到私人 repo（例如 `courses/<課程>/成品/教師改稿/`；GitHub 網頁上傳單檔限 25 MB，超過要用 git）。

## 9. 費用：您的雲端額度怎麼花

**扣款順序**（依 2026-09-25 claude.ai 用量頁的說明文字）：

1. **雲端 session 額度（Cloud session credits）**：2026-09 雲端 session 正式推出時送的一次性額度（Pro $100、Max $250；須在 2026-10-07 前到 <https://claude.ai/code/claim-credit/10> 或在 CLI 打 `/claim-credit` 領取，要先連 GitHub）。用量頁原文：「Applies automatically to cloud sessions. After it's used or expires, your plan's regular usage applies.」所以**雲端 session 先扣這筆**，不必另外設定。到期時間寫在用量頁（2026-09 領取的約在 11 月初到期）。只用在雲端 session；本機 session（桌面 app 選 Local、終端機）不會用到它。
2. **方案用量（5 小時與每週上限）**：雲端額度用完或過期後，雲端 session 改算進方案用量，與 claude.ai 聊天、本機 Claude Code 共用。雲端電腦本身不另收運算費。
3. **Usage credits（自己買的額外用量）**：只有在用量頁把「Turn on usage credits to keep using Claude if you hit a plan limit」打開時，方案上限用完後才會扣。**這個開關關著，買的 credits 就一毛都不會動**；方案上限用完時 session 會停下來等重置。要保護買的 credits，就讓它維持關閉，碰到上限時跳出的「開啟 usage credits」提示也不要按。

看用量：claude.ai → **Settings → Usage**（<https://claude.ai/settings/usage>），有方案用量條、Cloud session credits 剩餘金額與到期時間、Usage credits 餘額與開關；session 裡打 `/usage` 也看得到（該指令的明細只統計那台電腦上的 session）。第一次雲端 session 前後各看一次：Cloud session credits 應該減少，Usage credits 金額不變。

費用按 token 算：每個代理都要讀大量檔案（事實帳、風格指南、教科書頁圖、投影片 PNG），代理數越多越貴。

**兩種數字不要混在一起**：

- **API 牌價換算**：下表的金額，是把 immune 各次執行實際用掉的 token，用 Opus 5.5 的 API 牌價（輸入 $4、快取寫入 $5、快取讀取 $0.20、輸出 $20／百萬 token）換算出來的等值金額。它用來比較各階段的大小，也是估計 credits 能撐多久最好的依據。
- **方案用量**：Pro／Max 方案內含的用量不以金額顯示，只顯示百分比。雲端額度用完之後，雲端工作改吃這裡；它和本機 session 共用，所以雲端額度還在的時候，把重的工作放雲端，就能把方案用量留給本機要做的事。雲端額度是否完全照 API 牌價扣，官方文件沒寫清楚；第一次用時對照用量頁的金額變化。

**錢主要花在多代理工作流**。以 immune（三節 184 張）為例（公式見 kit 的 `workflows/README.md`）：

| 工作流 | 代理數 | API 牌價換算（一次完整執行） | 需要重跑嗎 |
|---|---|---|---|
| 蒐集 `lecture-gather.js` | 97（教科書 13 段 × 4、文獻 14 題 × 3 減 1、國考 3、讀設定 1；更新題庫時 98） | 約 $300–420（該次由另一個模型執行，依 Opus 的 token 用量推估） | 每門新課一次 |
| 藍圖 `lecture-blueprint.js` | 10 | 約 $150–190 | 每門新課一次 |
| 撰寫 `lecture-write.js` | 57（11 批 × 5＋連貫性 1＋讀檔 1） | 約 $230（每批約 $18） | 每門新課一次 |
| 審查 `lecture-review.js` | 每輪 19（沒給 PNG 時 20） | 第 1 輪 $149；第 2 輪 $377，其中「圖」面向開圖過多花了 $235，提示已改成每張圖只看一次 | 一到兩輪 |
| 新課程的撰寫 brief（`style-mining.js` 只跑 brief） | 1 | 約 $10–20（推估） | 每門新課一次（選做） |
| 風格挖掘 `style-mining.js` 全跑 | 約 89 | 約 $750–850 | **已完成，不必重跑** |
| 風格指南 `style-guide.js` | 約 49 | $408 | **已完成，不必重跑** |

一門約 180 張的新課，從蒐集到兩輪審查約 $950–1,200；只做一輪審查約 $830–990。

**$250 能做到哪裡**（以 API 牌價換算；雲端 session 一開始就從這筆扣）：

- 不夠做完一門約 180 張的新課，約差 3–5 倍。
- 大約是其中一段：藍圖（$150–190）加撰寫的 3–5 批；或撰寫全部（約 $230）；或一輪審查（約 $150）加第二輪只審 2 個面向、1 位反駁（約 $50–80）；或蒐集只做教科書事實、1 位反駁（13 段 × 3 個代理，約 $80–200）。
- 全部用下面的省錢設定（反駁者 1 位、文獻題目減半、藍圖 2 個視角 2 位評審、撰寫每批 20 張、審查一輪），整門課依上表單價推估仍約 $550–800（未實測）。
- $250 用完後，雲端 session 接著吃方案用量（和本機共用），不會自動動到買的 usage credits（見上面扣款順序第 3 點）。額度有到期日，過期作廢，所以到期前把最重的階段排進雲端最划算。

**先量再估**：第一次在雲端做新課時，開跑藍圖（10 個代理）前後各看一次 Usage 頁的 Cloud session credits 剩餘金額，就能算出一個代理實際扣多少，再乘上後面各階段的代理數。每個工作流開跑前，Claude 會先報代理數與上表的估計金額，等您同意。

**省錢設定**：

1. **不重跑風格研究。** 風格挖掘與風格指南已經完成（合計約 140 個代理）。您有新的改稿時，照 `style/guide/00_README.md`「版本與更新規則」局部更新，不必開工作流。新課程只需要 1 個代理產撰寫 brief（kit `workflows/README.md`「新課程的撰寫 brief」）。
2. **審查只做一輪。** immune 第二輪的修正數明顯少於第一輪；需要第二輪時只審問題多的面向，例如參數加 `lenses: ["layout","facts"]`（6 個面向減成 2 個，19 個代理減成 7 個）。
3. **蒐集階段縮小範圍。** 課程的 `gather.json` 裡，文獻題目只留真的會上的（每題 3 個代理；不需要圖的題目設 `"images": false`，每題 2 個）；題庫已有就維持 `exam.update_bank: false`（不下載）；完全不要選國考題的課才用參數 `parts: ["facts","literature"]`（拿掉整個國考部分）；教科書分段不要切太細（每段 4 個代理）。
4. **反駁者從兩位減成一位。** 蒐集與審查都有 `refuters` 參數（預設 2）；設 `refuters: 1`，教科書每段從 4 個代理減成 3 個、審查每個面向從 3 個減成 2 個。藍圖的評審數用 `judges`（預設 3）、視角數用 `lenses`（預設 3）。這會降低查核強度，事實類的部分（教科書事實帳、facts 面向）建議保留兩位。
5. **撰寫批次大一點。** `make_batches.py --size 20` 可以減少批數（每批 5 個代理）；一批太大，撰寫者一次要顧的張數變多，品質可能下降，建議 16–20。
6. **分次跑。** 一次只給工作流幾批，看過用量再給下一批。中途停下時用 DONE 表續跑，已完成的代理一個都不重跑。
7. **絕不整批重跑。** `resumeFromRunId` 只在同一台電腦、紀錄還在時可用，而且改過工作流腳本或參數之後，從第一個改動的代理起全部重跑；跨 session、本機與雲端互換時一律用 DONE 表。
8. **對話保持精簡。** 一個 session 做一個階段；階段做完先 push，再開新 session 接下一個階段。看投影片 PNG 時先看縮圖拼板，只放大有問題的張。
9. **不需要 AI 的步驟**（產 PPTX、轉 PDF、PDF 轉頁圖）本身不花額度，只有 Claude 下指令、讀結果那一小部分算用量。
10. **模型一律 Opus 是既定規則。** 要省錢先減少代理數量，不要換模型。`effort: "medium"` 也能省，但品質差多少還沒實測，先在一批上比較。

**額度用完時**：代理回傳空結果，工作流會自動停止派新代理；Claude 會把完成清單記成 DONE 表、連同 journal 存進 `courses/<課程>/_archive/journals/` 並 push。等方案用量重置後再說「續跑」（除非您自己打開 usage credits 開關，否則不會動用買的 credits）。

## 10. 常見陷阱

1. **本機記憶不在雲端。** 您在本機告訴 Claude 的偏好，雲端看不到。重要決定要寫進 repo：課程的 `brief.md`、`course.yaml`、`CLAUDE.md`，一般偏好寫進 kit 的 `docs/教師偏好與決策.md`。每個 session 結束前請 Claude 把新決定寫進去並 push。
2. **沒有 PowerPoint 和微軟正黑體。** 雲端的 PDF 預覽用 LibreOffice＋Noto 字型，斷行、字距可能和您電腦上的 PowerPoint 略有不同。PPTX 內指定的字型仍是微軟正黑體；上課前在自己電腦用 PowerPoint 打開看一次。
3. **檔案大小。** GitHub 單檔上限 100 MB（50 MB 以上警告），網頁上傳限 25 MB。教科書 PDF 不放 repo，只放頁圖。
4. **著作權與隱私。** Robbins 的頁圖、切圖、事實帳，以及同事的講義，只放私人 repo。公開的 kit 不放任何課程檔案；kit 有改動時，請 Claude 先跑 `python check_public.py`（FAIL 要是 0），按 Create PR 前也看一下 kit 改了哪些檔。
5. **只能推到 session 自己的分支。** 不要請 Claude 直接推 `main`；用 Create PR 或手動 merge。
6. **兩個 repo 的 session** 不會讀各 repo 的 `.claude/settings.json`（hooks、權限規則）；各 repo 的 CLAUDE.md 什麼時候載入，官方沒有寫清楚，所以第一句話一定要叫 Claude 先讀兩份 CLAUDE.md。
7. **Workflow 工具**（多代理腳本）在雲端 session 能不能用、能同時跑幾個代理，還沒有實測，請以官方說明為準；雲端電腦的 CPU 數可能比您的電腦少，同時跑的代理數跟著變少，整體會比較慢。第一次請 Claude 先用小範圍試（例：蒐集只跑一段）。不能用時，請 Claude 照 kit 的 `AGENTS.md` 一步一步循序做（較慢，產出的檔案相同）。
8. **Setup 快取約 7 天**；`cloud-setup.sh` 更新後要重新貼進環境設定。
9. **閒置回收。** 見第 6 節；每個階段都要 push。

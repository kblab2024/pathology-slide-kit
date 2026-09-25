# 經驗教訓（管線踩過的坑）

2026-09 做頭頸部、呼吸系統、免疫疾病三門課時學到的事。每條寫「發生什麼 → 現在怎麼做」。投影片風格上的教訓在 `style/guide/40_範例/43_反例庫.md`，這裡只寫工具與流程。

## 1. 換行字元（CRLF）

- **發生什麼**：Claude Code 的 Workflow 工具拒絕含 `\r` 的腳本。Windows 上的 Python 寫檔預設 CRLF；Git for Windows 預設 `core.autocrlf=true`，clone 下來的 .js 也會變成 CRLF。
- **現在怎麼做**：
  - clone 時加 `-c core.autocrlf=false`（已 clone 的：`git config core.autocrlf false` 後重新 checkout）；
  - Python 寫文字檔一律 `open(path, "w", encoding="utf-8", newline="\n")`；
  - 跑工作流前檢查：`grep -c $'\r' workflows/*.js` 全部要是 0。

## 2. 續跑：DONE 表，而不是 resumeFromRunId

- **發生什麼**：額度在工作流中途用完好幾次（immune 的風格挖掘、藍圖、撰寫都停過）。`resumeFromRunId` 只能沿用「從頭算起沒改動的那一段 agent() 呼叫」，而且要在同一台電腦、run 的紀錄還在；當時為了改用 Opus 而改了每個代理的 model，第一個呼叫就不同，結果整批重跑。
- **現在怎麼做**：每支工作流都支援 `args.done = {"<label>": "<輸出檔路徑>"}`，列在裡面的代理直接回傳舊檔、不呼叫模型，log 會出現 `reuse (not re-run): <label>`。
  - 重建 DONE 表一律用 `workflows/tools/done_from_journal.py`：有 journal 就讀 journal（本機在 `~/.claude/projects/<專案>/<session>/subagents/workflows/<runId>/journal.jsonl`）；journal 不見了（雲端 VM 被回收）就用 `--scan` 依輸出檔名推回 label（例：`batch_3_check_voice.json` → `voice:3`）。
  - 被中斷當下正在跑的代理要重跑（它的輸出檔可能不完整，用 `--drop`）。
  - journal、當次 args 與 DONE 表都存在課程的 `_archive/journals/` 並 commit（`workflows/README.md`「續跑」）。
- 任何代理回傳 null（多半是額度用完）時，腳本停止派新代理；不要自動重試，等使用者同意再續跑。

## 3. 換行量測要用真的字型

- **發生什麼**：早期用「全形 1.0、半形 0.55 個字寬」估算換行，實際在 PowerPoint 裡常多一行而溢出；審查者用估算判斷「放得下」的改法，渲染後三條都放不下（immune 第二輪）。
- **現在怎麼做**：`gen_pptx.py` 用實際字型量測每一行（Windows 用微軟正黑體，雲端用 Noto Sans CJK TC，都沒有才退回估算），粗體另量；行高係數 1.12；表格列高含上下邊界；關掉 `hangingPunct`；left 版型文字欄依內容從 47% 自動加寬到 65%；條列區扣掉左下「資料來源」的高度；圖片不壓到出處。雲端量測字型與 PowerPoint 實際字型不同，最後仍要在 Windows 的 PowerPoint 看一次。

## 4. 綠燈不算數：一定要看 PNG

- **發生什麼**：check_deck ALL GREEN、style_check RED 0 的版本，渲染後仍有溢出、孤字、行首標點、英文字中間斷行、圖被壓小、圖說蓋到出處。
- **現在怎麼做**：每次重產都 `export_pdf.py --pngs` 出逐張 PNG 並實際看（先看縮圖拼板，再放大可疑張）；審查工作流有專門看 PNG 的 layout 面向；「估算放得下」的修正要渲染過才算完成。

## 5. 掃描版教科書的切圖

- **發生什麼**：Robbins 的章節 PDF 是掃描檔，`get_images()` 抽不到圖（頁面由數十條水平掃描帶拼成）；有的檔文字層是自訂編碼（字元落在 PUA 0xF0xx，解碼為 `chr(288 - (code & 0xff))`，0xF020 是空白；呼吸系統那一章就是這樣，這個解碼模式沒有收進 `robbins_crop.py`，遇到時走下面的 OCR 路線即可）；有的檔沒有文字層，只有浮水印。
- **現在怎麼做**：
  - 先把每頁渲染成圖（`render_pdf_pages.py`，約 200 dpi），用 Tesseract OCR 產文字與字詞座標（.txt、.tsv）；
  - `robbins_crop.py` 以 OCR 找「Fig. N.M」「Table N.M」圖說的位置，圖在圖說正上方，圖說寬度限制水平範圍；
  - 側邊圖說、反白圖說、label 與圖說分成兩塊、圖說縮排的圖，用 `--ovr` JSON 手動給 200 dpi 像素座標（immune 46 圖＋17 表，19 圖與全部表格用了手動座標）；
  - 多面板圖拆 A／B／C；一定要看 `contact_*.png` 拼板確認；
  - 舊講義裡的截圖常常就是 Robbins 舊版的圖，出處要寫 Robbins，並對照 11e 的圖號。
- 教科書 PDF 常超過 100 MB，不放 repo；只 commit 頁圖、OCR 與切圖（都在私人 repo）。

## 6. 國考題庫的解析

- **考選部網站**：「考畢試題查詢平臺」是 ASP.NET WebForms，要先 GET 取 `__VIEWSTATE`，選年度要 postback 才會列出考試代碼；下載 PDF 要在同一個 session cookie 內、帶 Referer，否則轉址到 NotFound（`fetch_moex_dent_exam.py` 已處理）。
- **PDF 文字層的瑕疵**（`parse_moex_exam.py` 已處理並印警告）：康熙部首區字元（例「⽣」）要 NFKC 還原；部首補充區（例「⻑」）用對照表還原；Big5 延伸碼位衝突讓圈號 ①–⑩ 變成西里爾字母；題號用「循序期待」切題，避免題幹以數字開頭時誤切；英文在 PDF 換行處要補空格；上標數字要接回。
- **答案**：更正檔（`_M.pdf`）要套用；一律給分記 `#`，複選給分記 `A,C`。選題時避開 `#`、多答案、題幹寫「如附圖」而題庫沒有圖的題。
- **醫師題庫只收病理段（題號 76–100）**；原本的 `questions-115-2.json` 來源 PDF 標頭寫的是「115 年第一次」，而且 76–100 題與 115-1 的題幹、答案相同（只差空白），已移到 `question_banks/醫師/_unconfirmed/`（工具不讀），這 25 題一律用 115-1 的 key（見 `question_banks/README.md`）。
- **年次題號一律由題庫 key 產生**：他舊投影片的年次標籤有 17 題與題庫不符，沿用舊張時要列清單。
- 題庫文字先 NFC 正規化；官方原文的錯字照抄，在講稿註明。

## 7. 單一事實來源與覆蓋風險

- 藍圖與撰寫 JSON 經過審查修改後就過時了；再拿它們跑 `assemble.py` 會蓋掉審查改過的 pool.md。組裝只在撰寫階段做一次。
- 他親手改過的檔是權威版本。重產前沒回灌，會把他的修改蓋掉（頭頸部與呼吸系統都差點發生）。回灌時：以 slug 或備註表頭配對、他刪的張只從選單或該班 `aud` 拿掉、複製出的同標題連張各存各的內容、PPTX 備註不寫回 script.md、先清掉被圖蓋住的佔位殘留文字。
- 素材池的 `<!-- … -->` 註解裡不能出現 `>`（例如 `=>`），會把註解截斷。
- glossary 的禁用變體不要收他親手寫過的字形，否則檢查器會擋他的寫法。
- 新的檢查 regex 先對他自製的檔跑一次；會命中他自己句子的規則，改寫或降級成 WARN（舊版 rules.yaml 曾把他的「沙包或磚頭」判成違規）。

## 8. 審查工作流

- 每個面向一位審查、兩位獨立反駁，只套用至少一位反駁者確認的項目；兩位給不同改法時，選較忠於 Robbins 與他原句的。
- 修正互相衝突時：事實 ＞ 術語 ＞ 版面 ＞ 文風；圖片與國考題的修正讓位。
- 課程明令優先於審查建議（例：審查建議某術語只寫英文，但該課明令每張中英對照，就不套用）。
- immune：第一輪 206 條、確認 192、套用 173；第二輪 129 條、確認 126、套用 117。第二輪仍有價值，但額度緊時一輪即可。

## 9. Windows 環境的小坑

- Python 印中文要設 `PYTHONIOENCODING=utf-8`，否則 cp950 報 `UnicodeEncodeError`。
- 在 Windows 的 Bash 工具裡寫超過約 100 行的 heredoc 會被截斷（報 unexpected EOF）；大檔用 Write 寫成檔再執行。
- PowerPoint 匯出 PDF 前先關掉開著的同名 PPTX；`export_pdf.py` 用 PowerShell 呼叫 PowerPoint，不需要 pywin32。

## 10. 檔案大小與 GitHub

- immune 184 張的 PPTX 約 58 MB，幾乎全是圖。GitHub 單檔上限 100 MB（50 MB 以上警告），網頁上傳限 25 MB。
- 接近上限時：分節輸出（`gen_pptx.py --section N`，檔名自動加「_第N節」，不會蓋掉全套檔）或把圖先降到投影片實際需要的解析度再放進素材池。
- 成品 PPTX 預設不進 git（`.gitignore`）；交件的那一個用 `git add -f`，同名 `_layout.json` 照常提交（回灌時對 slug 用）。同一門課只提交最後一版 PPTX，repo 歷史才不會一直長大。
- 教科書 PDF 放 repo 外；私人 repo 的 `.gitignore` 排除成品以外的所有 PDF。

## 11. 額度與費用管理

- 花費幾乎都在多代理工作流；每個代理都要讀事實帳、指南、頁圖等大檔。immune 整門課約 200 個代理（蒐集 97、藍圖 10、撰寫 57、審查兩輪 38），以 API 牌價換算約 $950–1,200；風格挖掘約 89、風格指南約 49 已完成不必重跑。
- 開跑前先報代理數、等使用者同意；分次跑、看用量；停下時存 DONE 表並 commit。
- 先用小階段（藍圖 10 個代理）量出每個代理的平均花費，再估整門課。
- 扣款順序：雲端 session 先扣雲端 session 額度（2026-09 送的一次性額度，會過期）→ 用完改吃方案用量（與本機共用）→ 使用者打開「usage credits」開關時才扣買的 credits。本機 session 不會用到雲端額度，所以方案每週用量吃緊時，把重的工作流放雲端。
- 雲端 VM 閒置會被回收，正在跑的代理與沒 push 的檔案會不見；每個階段結束就 commit＋push。
- 詳見 `docs/cloud_session_教學.md` 第 9 節。

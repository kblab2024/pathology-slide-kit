# scripts/：共用教案工具（只有一份，所有課程共用）

讀課程設定的工具用 `--course <課程>` 指定課程；`<課程>` 是課程資料夾名（例 `immune`），或直接給 course.yaml（或含它的資料夾）的路徑。
收 `--course` 的：gen_pptx、check_deck、style_check、img_todo、assemble、merge_facts、merge_written、validate_blueprint、check_written、render_pdf_pages、robbins_crop、to_claude_slides。
不收 `--course` 的（照下方各自的用法）：make_batches、export_pdf、extract_deck_images、dump_pptx、diff_decks、verify_quotes、check_public、fetch_moex_dent_exam、parse_moex_exam。每支都有 `--help`。
所有路徑、字級、色票、選單、國考題庫、框架圖都在 course.yaml；**換課程不改程式，只改 course.yaml**。
安裝見 `../setup/windows.md`（本機）與 `../setup/cloud-setup.sh`（Claude Code 雲端，Ubuntu）。

## 兩個 repo 與路徑規則

| 名稱 | 內容 | 位置 |
|---|---|---|
| 工具包（KIT，公開） | `scripts/`、`workflows/`、`templates/`、`style/`、`question_banks/`、`examples/` | 含 `scripts/` 的資料夾（`common.ROOT`＝`common.KIT`） |
| 教材庫（materials，私有） | `courses/<課程>/`、`textbook/`、`corpus/`、`style_evidence/` | 見下方 `find_materials()` |

- **教材庫** `common.find_materials()`：環境變數 `SLIDEKIT_MATERIALS` → 工具包同層的 `pathology-slide-materials` → 工具包的上一層（若含 `courses/`，也就是工具包放在教材庫裡面）→ 找不到回傳 `None`。
- **課程** `common.load_course(名稱或路徑)`，依序：
  1. 既有的路徑：course.yaml 本身，或含 course.yaml 的資料夾
  2. `<教材庫>/courses/<名稱>/course.yaml`
  3. `<工具包>/examples/<名稱>/course.yaml`
  4. 都沒有就報錯，列出每個試過的路徑
- **語料**（`verify_quotes.py` 與風格研究）`common.corpus_dir()`：`SLIDEKIT_CORPUS` → `<教材庫>/corpus` → `<工具包>/style/corpus`。
- **國考題庫**：`<工具包>/question_banks/<題庫>/*.json`（題庫名在 course.yaml 的 `decks.<deck>.question_bank`）；`醫師` 題庫只收題號 76–100（病理段）。
- **教科書頁圖**：course.yaml 的 `textbook.pages_dir`（相對於課程資料夾），檔名 `pNN_PPP.jpg|png`＋`.txt`（OCR）＋`.tsv`（字詞座標），NN＝PDF 頁、PPP＝印刷頁。`textbook.pdf` 與 `textbook.page_offset`（印刷頁＝PDF 頁＋offset）寫在同一段。程式內用 `course.textbook_path("pages_dir")` 取絕對路徑（舊鍵名 `pages_png` 仍可讀）。

工作流代理呼叫工具的固定寫法（不收 `--course` 的工具就不加）：

```bash
cd "<kit>/scripts" && SLIDEKIT_MATERIALS="<materials>" PYTHONIOENCODING=utf-8 python <script>.py --course <course> ...
```

Linux 沒有 `python` 指令時用 `python3`（雲端的 `setup/cloud-setup.sh` 會建好 `python` 連結）。

## 環境變數（都可不設）

| 變數 | 作用 | 預設 |
|---|---|---|
| `SLIDEKIT_MATERIALS` | 教材庫位置 | 同層的 `pathology-slide-materials`；再找工具包上一層 |
| `SLIDEKIT_CORPUS` | 語料位置 | `<教材庫>/corpus`，再退到 `<工具包>/style/corpus` |
| `SLIDEKIT_PDF_ENGINE` | `export_pdf.py` 引擎：`auto`／`powerpoint`／`libreoffice` | `auto`（Windows 先 PowerPoint，失敗或非 Windows 用 LibreOffice） |
| `SLIDEKIT_MEASURE_FONT` | gen_pptx 量字字型：字型檔路徑，或 `em`（不用字型、粗估） | 自動（見下表） |
| `SLIDEKIT_MEASURE_FONT_BOLD` | 配合上一項的粗體字型檔 | 同上一項 |
| `TESSERACT` | tesseract 執行檔 | PATH 上的 `tesseract` → `C:\Program Files\Tesseract-OCR\tesseract.exe` |
| `SOFFICE` | LibreOffice 執行檔 | PATH 上的 `soffice`／`libreoffice` → `C:\Program Files\LibreOffice\program\soffice.exe` |
| `PYTHONIOENCODING` | Windows 主控台請設 `utf-8`，否則中文輸出亂碼 | — |

## Windows 本機與雲端（Ubuntu）的差異

| 項目 | Windows 本機 | Claude Code 雲端 |
|---|---|---|
| PPTX 內的字型名稱 | 微軟正黑體（Microsoft JhengHei） | 同左（檔案內容一樣） |
| gen_pptx 量字寬（估算換行、溢出） | `C:\Windows\Fonts\msjh.ttc`／`msjhbd.ttc` | `fonts-noto-cjk` 的 Noto Sans CJK TC（`/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`、`-Bold.ttc`，自動挑 TC 字面）；都沒有就用 em() 粗估 |
| PPTX 轉 PDF | PowerPoint（COM，經 PowerShell） | LibreOffice `soffice --headless --convert-to pdf`（字型以 Noto Sans CJK TC 代替，換行略有差異，只供目視檢查） |
| OCR | Tesseract（UB Mannheim 版，預設路徑自動找） | `apt-get install tesseract-ocr` |
| 教科書 PDF | 可有可無 | 通常沒有：`robbins_crop.py` 直接裁 200dpi 頁圖 |

gen_pptx 每次會印出「量字字型：…」，也寫進 `_layout.json` 的 `measure_font`，方便對照雲端與本機的估算差異。

## 一條龍流程（新教案）

| 步驟 | 指令 | 產出 |
|---|---|---|
| 1 教科書轉圖＋OCR | `python render_pdf_pages.py --course <課程>`（或 `python render_pdf_pages.py <pdf> <out_dir> --offset <印刷頁−PDF頁>`） | 每頁整頁 jpg（預設；`--format png`、`--halves` 另出上下半頁）、OCR 文字、字詞座標 TSV（寫到 `textbook.pages_dir`） |
| 2 切教科書圖表 | `python robbins_crop.py --course <課程> --chapter N --out <課程>/assets/images/Robbins抽圖 --expect 圖數 [--ovr ovr.json]` | figN_M.png、面板、tableN_M.png、index.json、`圖片清單.md`（藍圖代理找圖用；已有手寫的清單時改寫 `圖片清單_auto.md`）、contact_*.png |
| 3 抽舊投影片的圖 | `python extract_deck_images.py <舊.pptx> <課程>/assets/images/舊講義抽圖 --code 代號 [--slides 1-47] [--author 作者]` | 圖檔＋`圖片清單.md` |
| 4 國考題庫 | `python parse_moex_exam.py …`（見該檔 docstring） | `question_banks/<醫師|牙醫師>/*.json` |
| 5 藍圖＋撰寫 | 由工作流產生（見 `workflows/README.md`），格式見 `templates/blueprint.schema.json`、`templates/written.schema.json` | blueprint.json、written.json |
| 6 組裝來源檔 | `python assemble.py --course <課程> blueprint.json written.json [--dry-run]` | `sources/*-pool.md`、`*-script.md`、`decks/<deck>.md`（有 RED 不寫檔） |
| 7 產投影片 | `python gen_pptx.py --course <課程> [--date YYYYMMDD] [--section N] [--name 檔名]` | `成品/<檔名>.pptx`＋`_layout.json`，並自動跑 check_deck。`--section N` 的檔名自動加「_第N節」；多套 deck 又給 `--name` 時自動加「_<deck>」；覆寫既有檔會印提醒 |
| 8 文字風格檢查 | `python style_check.py --course <課程>` | RED／WARN（讀 `style/rules.yaml`＋課程 glossary；中英對照範圍依 course.yaml `bilingual`：`per_slide` 逐張、`first_per_deck`（預設）看首見率、`off`） |
| 9 匯出 PDF＋縮圖 | `python export_pdf.py <pptx> --pdf <pdf> --sheets <資料夾> --pngs <資料夾> [--engine libreoffice]` | PDF、4×3 縮圖拼板、逐張 PNG |
| 10 待補圖清單 | `python img_todo.py --course <課程>` | `成品/待補圖清單.md` |

說明：
- `render_pdf_pages.py --course` 從 course.yaml 的 `textbook.pdf`、`textbook.pages_dir`、`textbook.page_offset` 補齊參數；預設 jpg、不出半頁（教材庫就存這個格式）；找不到 Tesseract 會報錯，只要圖時加 `--no-ocr`（切圖會少了圖說定位）。
- `robbins_crop.py` 的頁圖可以是 png 或 jpg；有 PDF 時以 `--dpi`（預設 300）從 PDF 重新算圖，沒有 PDF 時直接裁 200dpi 頁圖（jpg 頁圖的裁切框與 png 相差幾個像素）。`--out` 裡不在 index 內的 fig*/table* 舊檔會被刪除，不要指到別的資料夾。
- `export_pdf.py` 兩個引擎都不可用時，錯誤訊息列出各自的原因，結束碼 2。

中間工具（工作流代理也會呼叫）：
- `merge_facts.py --course <課程>`：分段事實 `facts/seg/S??_final.json` → `facts_R.json`；文獻 `_archive/gather/lit/*_verified.json` → `facts_X.json`；人讀版 `facts/facts.md`。
- `validate_blueprint.py --course <課程> <blueprint.json> [--diagrams diagrams.yaml]`：藍圖欄位、圖檔、國考 key、框架圖、各節張數與分鐘、有圖率。
- `make_batches.py <blueprint.json> <batches.json> [--size 16]`：切撰寫批次（不拆同標題連張、盡量在段落邊界切），輸出給 `workflows/lecture-write.js` 當 args。
- `check_written.py --course <課程> --blueprint <bp.json> <batch.json…>`：撰寫批次的自我檢查（rules.yaml、glossary（`bilingual: per_slide` 時逐張中英，其他模式只查禁用變體）、字數條數）。
- `merge_written.py --course <課程> --dir <written> --blueprint <bp.json>`：各批合併成 written.json，glossary_additions 併進 glossary.md，issues 彙整成 issues.md。
- `to_claude_slides.py --course <課程> …`：把素材池轉成 Claude Slides（網頁投影片）的檔案，見該檔 docstring。

風格研究與回灌工具（不收 `--course`）：
- `dump_pptx.py <in.pptx> <out_base>` 或 `dump_pptx.py --batch <list.tsv> <out_dir>`：逐張傾印成 `.json`＋`.txt`（字級取實際值、主題色解析）；語料一律寫到 `<materials>/corpus/decks/`。
- `diff_decks.py <mine.json> <his.json> <out.md> [--range a-b] [--layout <交件檔>_layout.json]`：我的毛胚 → 教師改稿逐張比對；`--layout` 在每個「原#N」標出素材池 slug，並多一張「新#→原#→slug」對照表（回灌用）。
- `verify_quotes.py [<指南資料夾或檔>…]`：風格指南引句逐字核對；語料見上方 `corpus_dir()`，找不到語料時結束碼 2；語料資料夾的 `pseudonyms.tsv` 讓代稱（同事甲…）也核對得到。
- `check_public.py [--kit <路徑>]`：推上 GitHub 前檢查公開 kit：CR 換行、本機絕對路徑、電子郵件、舊模型名、第三人真名（讀私人 `corpus/pseudonyms.tsv`）、他人投影片引句（`other_*` 代號與 `corpus/other_segments.tsv`）、圖檔與大檔。FAIL 要是 0。

## 來源檔格式（素材池 pool.md）

```
## 投影片 imm-s1-03-mast｜第一型過敏的主角是 IgE 與肥大細胞(mast cell)
<!-- type: left -->
<!-- aud: dent -->
<!-- IMG: assets/images/Robbins抽圖/fig6_13.png ｜ 出處：Robbins Fig. 6.13 ｜ 標籤：H&E -->
<!-- src: J Allergy Clin Immunol. 2019;143(4):1234-40. -->        ← 左下 14pt「資料來源：」
<!-- quiz: 113-1#45 ｜ 題下一行說明（選填） -->                    ← type: quiz 用；「｜」後是題下說明行
<!-- diagram: hyper | 亮:第一型,媒介 -->                          ← type: diagram 用
<!-- build: s1-typeI-mech -->                                    ← 同標題連張組
<!-- img_wanted: 肥大細胞 Giemsa 染色 -->                         ← 沒圖時；進待補圖清單，不畫框
<!-- facts: S04-012 S04-013 hae_dental-2 -->                   ← 這張依據的事實 id（assemble.py 寫入；審查工作流靠它查核）
<!-- robbins: p.185 -->                                         ← 選填：這張對應的教科書頁碼（人讀與審查用）
<!-- title:dent: 牙醫系版的標題 -->                              ← 選填：某一套 deck 用不同的標題
- 第一層條列，可含 [[橘:關鍵字]]、[[藍:最該記的]]、[[紅:單字]]
  - 第二層（兩個空白＋「- 」；與第一層同字級）
| 表頭 | 表頭 |
|---|---|
| 內容 | 內容 |
```

IMG 註解的欄位用「｜」分隔：路徑（必填）、`出處：`（圖下出處行）、`標籤：`（pair 版型的圖上標籤）、`內容：`（這張圖是什麼，給代理與審查看，不上投影片）。
IMG 路徑一律寫相對於課程資料夾的路徑（`assets/images/…`），不寫絕對路徑，雲端與本機才都找得到。
`aud` 只有一門課有多套 deck 時才寫；沒寫的張屬於 course.yaml `deck_order` 的全部 deck。註解裡不要出現 `>`（例如 `=>`），會把註解截斷。

## 版型（type）

| type | 用途 | 文字上限（4:3、28pt） |
|---|---|---|
| title | 封面 | 標題＋2–3 行 |
| divider | 節／段落分隔（深色底） | 名詞短語標題＋最多 2 行副標 |
| left | 條列＋右圖（無圖則全寬條列） | 有圖：每行約 10 字、共約 8 行；無圖：每行約 17 字、共約 9 行 |
| flash | 標題＋1–2 句＋全寬大圖 | 說明 ≤2 行 |
| big | 單句大字（44pt），可附圖 | 1–3 短句 |
| pair | 兩圖並排（可加標籤） | 說明 ≤2 行 |
| robbins | 整張教科書圖 | 說明 ≤1 行 |
| table3 | 表格（≥20pt；超過 table_max_rows 自動拆成同標題連張） | 每格短語 |
| quiz | 國考題：course.yaml `decks.<deck>.quiz_style` 乙（預設；年次標題＋題幹選項 24–28pt，正解整段藍）或 甲（1 列 3 欄表「正解字母粗體｜題號．題幹＋選項｜年度-次」，不放標題） | 官方原文 |
| stats | 大數字卡片（`數字｜說明`） | 2–4 張卡 |
| diagram | 框架圖（course.yaml diagrams） | 格子 ≥20pt；4 欄時每行約 7 個中文字，每格最多兩行（約 14 字，含英文） |

## 檢查門檻（course.yaml sizes）
字級：出處 ≥ credit（14）、其餘 ≥ min（20），內文 < body_warn（24）WARN；每張字元 > char_warn WARN、> char_red RED；有圖率 < img_rate_min RED；殘留佔位字、靜態頁碼 RED；國考題 key 不在題庫 RED；估算溢出 >15% RED。

## 常見錯誤
- `找不到課程 'xxx' 的 course.yaml。試過：…`：看列出的路徑；多半是教材庫沒放在工具包同層，設 `SLIDEKIT_MATERIALS`。
- `KeyError 選單引用不存在的 slug`：decks/<deck>.md 與 pool.md 不同步 → 重跑 assemble 或手改。
- PowerPoint 匯出失敗：先關掉已開啟的同名 pptx；export_pdf 用 PowerShell COM，不需 pywin32。仍失敗時加 `--engine libreoffice`。
- 雲端 `LibreOffice 匯出失敗`：確認 `cloud-setup.sh` 有裝 `libreoffice-impress`；大檔可加 `--timeout 1800`。
- 中文亂碼：沒設 `PYTHONIOENCODING=utf-8`。
- 雲端 `python: command not found`：用 `python3`，或重跑 `bash setup/cloud-setup.sh`（會建 `python` 連結）。
- `aud 含未知 deck`：素材池的 `<!-- aud: … -->` 寫了 course.yaml `decks` 沒有的名稱；單一 deck 的課不必寫 aud。
- `pip install -r requirements.txt` 在 Windows 報 cp950 解碼錯誤：requirements.txt 要維持純 ASCII（pip 用系統字碼頁讀檔）。
- 掃描 PDF 的圖說 OCR 不到（側邊圖說、反白圖說）：在 `--ovr` JSON 手動給 200dpi 像素座標。
- 雲端與本機的溢出 WARN 不同：量字字型不同，換行估算略有差異；定稿以本機 PowerPoint 為準。

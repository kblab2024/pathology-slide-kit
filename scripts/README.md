# scripts/：共用教案工具（只有一份，所有課程共用）

讀課程設定的工具用 `--course <課程>` 指定課程；`<課程>` 是課程資料夾名（例 `immune`），或直接給 course.yaml（或含它的資料夾）的路徑。
收 `--course` 的：gen_pptx、check_deck、style_check、img_todo、fit_capacity、assemble、merge_facts、merge_written、validate_blueprint、check_written、render_pdf_pages、robbins_crop、to_claude_slides、html_deck。
不收 `--course` 的（照下方各自的用法）：make_batches、export_pdf、extract_deck_images、dump_pptx、diff_decks、gen_lab_pptx、html_lab_deck、strip_notes、wsi_crop、annotate_shot、merge_annot、verify_quotes、check_public、fetch_moex_dent_exam、parse_moex_exam。每支都有 `--help`。
所有路徑、字級、色票、選單、國考題庫、框架圖都在 course.yaml；**換課程不改程式，只改 course.yaml**。
安裝見 `../setup/windows.md`、`../setup/mac.md`（本機）與 `../setup/cloud-setup.sh`（雲端或其他 Linux，Ubuntu）。

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

| 項目 | Windows 本機 | Linux（含各家雲端 session） |
|---|---|---|
| PPTX 內的字型名稱 | 微軟正黑體（Microsoft JhengHei） | 同左（檔案內容一樣） |
| gen_pptx 量字寬（估算換行、溢出） | `C:\Windows\Fonts\msjh.ttc`／`msjhbd.ttc` | `fonts-noto-cjk` 的 Noto Sans CJK TC（`/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`、`-Bold.ttc`，自動挑 TC 字面）；都沒有就用 em() 粗估 |
| PPTX 轉 PDF | PowerPoint（COM，經 PowerShell） | LibreOffice `soffice --headless --convert-to pdf`（字型以 Noto Sans CJK TC 代替，換行略有差異，只供目視檢查） |
| OCR | Tesseract（UB Mannheim 版，預設路徑自動找） | `apt-get install tesseract-ocr` |
| 教科書 PDF | 可有可無 | 通常沒有：`robbins_crop.py` 直接裁 200dpi 頁圖 |

Mac：量字用 PowerPoint for Mac 內建的微軟正黑體（gen_pptx 自動找）、PDF 與逐張 PNG 用 `export_pdf.py`（LibreOffice；先跑一次 `lo_fonts_mac.sh`）、要 PowerPoint 本身定稿才用 `ppt_pdf_mac.sh`、OCR 用 Homebrew 的 tesseract；見 `../setup/mac.md`。

gen_pptx 每次會印出「量字字型：…」，也寫進 `_layout.json` 的 `measure_font`，方便對照雲端與本機的估算差異。

## 一條龍流程（新教案）

| 步驟 | 指令 | 產出 |
|---|---|---|
| 1 教科書轉圖＋OCR | `python render_pdf_pages.py --course <課程>`（或 `python render_pdf_pages.py <pdf> <out_dir> --offset <印刷頁−PDF頁>`） | 每頁整頁 jpg（預設；`--format png`、`--halves` 另出上下半頁）、OCR 文字、字詞座標 TSV（寫到 `textbook.pages_dir`） |
| 2 切教科書圖表 | `python robbins_crop.py --course <課程> --chapter N --out <課程>/assets/images/Robbins抽圖 --expect 圖數 [--ovr ovr.json]` | figN_M.png、面板、tableN_M.png、index.json、`圖片清單.md`（藍圖代理找圖用；已有手寫的清單時改寫 `圖片清單_auto.md`）、contact_*.png |
| 3 抽舊投影片的圖 | `python extract_deck_images.py <舊.pptx> <課程>/assets/images/舊講義抽圖 --code 代號 [--slides 1-47] [--author 作者]` | 圖檔＋`圖片清單.md` |
| 4 國考題庫 | `python parse_moex_exam.py …`（見該檔 docstring） | `question_banks/<醫師|牙醫師>/*.json` |
| 4.5 版型容量 | `python fit_capacity.py --course <課程> [--json]` | 這門課的字級下每種版型每行幾字、幾行、表格幾列（用 gen_pptx 的量字函式，0.1 秒）；規劃、撰寫代理先讀這張表，不要自己試產校準 |
| 5 藍圖＋撰寫 | 由工作流產生（見 `workflows/README.md`），格式見 `templates/blueprint.schema.json`、`templates/written.schema.json` | blueprint.json、written.json |
| 6 組裝來源檔 | `python assemble.py --course <課程> blueprint.json written.json [--dry-run]` | `sources/*-pool.md`、`*-script.md`、`decks/<deck>.md`（有 RED 不寫檔） |
| 7 產投影片 | `python gen_pptx.py --course <課程> [--date YYYYMMDD] [--section N] [--name 檔名]` | `成品/<檔名>.pptx`＋`_layout.json`，並自動跑 check_deck。**不寫備忘稿**（`AGENTS.md` 硬規則 18；`course.yaml` 寫 `speaker_notes: true` 的課才把講稿放進去），check_deck 看到備忘稿有字就 RED。存檔前清掉檔案摘要資訊的作者、上次修改者與註解（`common.clear_doc_props`；範本預設是 python-pptx 的字樣，學生看得到；`gen_lab_pptx.py` 也一樣）。`--section N` 的檔名自動加「_第N節」；多套 deck 又給 `--name` 時自動加「_<deck>」；覆寫既有檔會印提醒 |
| 8 文字風格檢查 | `python style_check.py --course <課程>` | RED／WARN（讀 `style/rules.yaml`＋課程 glossary；中英對照範圍依 course.yaml `bilingual`：`per_slide` 逐張、`first_per_deck`（預設）看首見率、`off`）。教師看過、說這一講就這樣留的寫法，逐處寫進 course.yaml 的 `style_allow`（`{slide, text, why, rule?, n?}`），那幾處改列「教師核可」、不算 RED；不是通則，沒用到的項目會列 WARN |
| 9 匯出 PDF＋縮圖 | `python export_pdf.py <pptx> --pdf <pdf> --sheets <資料夾> --pngs <資料夾> [--engine libreoffice]` | PDF、4×3 縮圖拼板、逐張 PNG |
| 10 待補圖清單 | `python img_todo.py --course <課程>` | `成品/待補圖清單.md` |
| 11 Gemini 重寫（必做） | `python rewrite_pack.py make --course <課程> --deck <deck> --out <資料夾>` → 教師拿去 Gemini 跑 → `python rewrite_pack.py apply --course <課程> --deck <deck> <回覆檔…> [--write]` | 重寫包（一節一份 `.md`）；回來後 `_archive/revoice/` 的對照表、退回包、套用紀錄；`--write` 才套回來源檔（`AGENTS.md` 硬規則 17、SOP 第 9b 步） |

說明：
- `render_pdf_pages.py --course` 從 course.yaml 的 `textbook.pdf`、`textbook.pages_dir`、`textbook.page_offset` 補齊參數；預設 jpg、不出半頁（教材庫就存這個格式）；找不到 Tesseract 會報錯，只要圖時加 `--no-ocr`（切圖會少了圖說定位）。
- `robbins_crop.py` 的頁圖可以是 png 或 jpg；有 PDF 時以 `--dpi`（預設 300）從 PDF 重新算圖，沒有 PDF 時直接裁 200dpi 頁圖（jpg 頁圖的裁切框與 png 相差幾個像素）。`--out` 裡同一章、不在 index 內的 fig*/table* 舊檔會被刪除，不要指到別的資料夾。跨章的課（例：Robbins 第 13、14 章）兩章依序跑到同一個 `--out`：`index.json`、`圖片清單.md`、contact sheet 會保留別章的項目，`--ovr` 只套用 `--chapter` 那一章的鍵，兩章可共用一份 ovr（2026-10-30 起；以前第二章會把第一章清掉）。
- `export_pdf.py` 兩個引擎都不可用時，錯誤訊息列出各自的原因，結束碼 2。

中間工具（工作流代理也會呼叫）：
- `merge_facts.py --course <課程>`：分段事實 `facts/seg/S??_final.json` → `facts_R.json`；文獻 `_archive/gather/lit/*_verified.json` → `facts_X.json`；人讀版 `facts/facts.md`。
- `validate_blueprint.py --course <課程> <blueprint.json> [--diagrams diagrams.yaml]`：藍圖欄位、圖檔、國考 key、框架圖、各節張數與分鐘、有圖率。
- `make_batches.py <blueprint.json> <batches.json> [--size 16]`：切撰寫批次（不拆同標題連張、盡量在段落邊界切），輸出給 `workflows/lecture-write.js` 當 args。
- `check_written.py --course <課程> --blueprint <bp.json> <batch.json…>`：撰寫批次的自我檢查（rules.yaml、glossary（`bilingual: per_slide` 時逐張中英，其他模式只查禁用變體）、字數條數）。
- `merge_written.py --course <課程> --dir <written> --blueprint <bp.json>`：各批合併成 written.json，glossary_additions 併進 glossary.md，issues 彙整成 issues.md。
- `to_claude_slides.py --course <課程> …`：把素材池轉成 Claude Slides（網頁投影片）的檔案，見該檔 docstring。
- `html_deck.py --course <課程> [--max-side 1200] [--quality 75]`：產一個圖片內嵌的 HTML 檔（`成品/…(HTML)_日期.html`），不需上傳，手機或任何瀏覽器直接開；←／→ 換張。教師 2026-10-14「成品要有 html 版」。

Mac、任務 B 與交件工具（不收 `--course`，除了 draw_flow 的 `--course` 只讀配色）：
- `lo_fonts_mac.sh`：Mac 上把 PowerPoint for Mac 內建的微軟正黑體（與 Arial、Calibri、Times）放進 LibreOffice.app 的字型資料夾，`export_pdf.py --engine libreoffice` 就用和 PowerPoint 相同的字型排版（2026-10-20）。LibreOffice 更新後再跑一次。
- `check_render.py <in.pptx> <in.pdf> [--json 輸出] [--warn-pt 2]`：量 PDF 的實排（PowerPoint 或 LibreOffice 算的都可以）。RED：框架圖格子的字超出圓角框、兩段字互相壓到（例：條列壓到資料來源行）、字超出投影片；WARN：格子的字離邊不到 warn-pt、字超出自己的文字框但沒壓到別的字。check_deck 是估算，這支量實排；表格的格子只用來配對，不查溢出（LibreOffice 表格列高略高）。
- `ppt_pdf_mac.sh <課程>/成品/<in.pptx> [out.pdf] [png資料夾] [縮圖資料夾]`：Mac 用 PowerPoint for Mac 存 PDF，再用 export_pdf.py 的函式出拼板與逐張 PNG（預設放 `<課程>/_archive/render/{png,sheets}`）。只接受課程 `成品/` 底下的檔、拒絕 OneDrive 路徑；PowerPoint 開著別的簡報就停（結束碼 3），只開、只存、只關自己那一份。第一次跑會跳 macOS 自動化授權，要教師在電腦前按允許。PowerPoint 的沙盒容器寫不進去時（新版 macOS，2026-10-16 起這台 Mac 的 Claude Code 是這樣），自動改把暫存檔放課程 `_archive/render/_ppt_tmp`，PowerPoint 第一次開那裡的檔可能跳「授予檔案存取權」，請教師按允許。
- `shrink_pdf.py <in.pdf> <out.pdf> [長邊px=900] [品質=72]`：把 PDF 裡的 JPEG 縮小，給 OneDrive 放壓縮版（大檔可能整個傳不上：2026-10-02 是 21.5 MB 的 PDF，2026-10-14 晚 8.9–21 MB 的 PPTX 也卡住，同時段的小 md、docx 正常；大小與檔案類型都不是可靠的門檻，見 `../docs/教師偏好與決策.md` 第 8 節）。交件檔名用 `(PDF壓縮)`。
- `compose_from_pdf.py <in.pptx> <in.pdf> <代號> <輸出資料夾> [--config cfg.json] [--only 張號…]`：任務 B，從教師的 PDF 原樣切出每張的圖區；設定檔寫要留的標籤（文字開頭或 shape 名）與要丟的圖形。輸出 `<代號>_sNNN.png|jpg` 與 `<代號>_compose.json`。
- `label_image.py <規格.json> [--preview 縮圖.png]`：示意圖加標籤（標準做法：Runway 只產沒有字的母圖，標籤由做投影片的代理設計、用這支疊上）。每個標籤兩行「中文」「(English)」，引線＋圓點指到構造（母圖座標比例），標籤放白邊（margins 加寬）或白色圓角底；字級以版位寬換算，預設 24pt／標題 28pt；標籤重疊、超出畫布、引線交叉、低於 24pt 時結束碼 1。規格格式見該檔 docstring。`at` 的標籤（放在指定位置）預設墊白底，放在圖的空白處時寫 `"box": false`；`at` 加 `point` 會從文字框拉直線過去（程式畫的圖在圖裡留空白放標籤時用）；每個標籤可以另寫 `pt`、`bold`、`color`（例：圖上的編號、算式）。這支出的是**圖版**；同一份規格的**文字方塊版**見下一條。
- `label_shapes.py`（模組，gen_pptx 與 common 會匯入，不單獨執行）：把 `label_image.py` 的同一份規格畫成 PowerPoint 原生的文字方塊、指線與圓點（教師 2026-11-12：加標籤的圖「作一個圖版一個文字方塊版」）。素材池那一張寫 `<!-- IMG: <規格的 out> ｜ … -->` 加一行 `<!-- labels: <規格.json 相對課程資料夾> -->`：PPTX 上不放圖版，改放規格的 `image`（沒有字的母圖或程式畫的圖）並畫標籤，教師可以直接改字、拖、刪；`html_deck.py` 不認 labels，照舊用圖版。一張可以寫好幾行 labels（pair 的兩張圖各一份），用規格的 `out` 對 IMG 的路徑。字級是真的字級、不隨圖縮放，所以規格的 `slot_w` 要寫這張圖在投影片上實際的寬：left 版型的右欄會因為條列太長被擠窄（47% 文字欄時 4.37 吋，57% 時 3.47 吋，62% 時 3.02 吋），標籤多的圖用 flash（全寬 9 吋）比較穩。放得比 `slot_w` 窄、標籤互壓或超出投影片會記進 `_layout.json`，check_deck 報 WARN／RED；規格讀不到、`out` 對不到 IMG 也是 RED。標籤的字會進 style_check（中英對照與用語）；只有數字的標籤不會被 check_deck 當成頁碼。
- `gen_lab_pptx.py <deck.json> --out <輸出.pptx> [--report 報告.json] [--src-list 清單.md] [--notes] [--bg-pt 24]`：實驗講義版型（教師 2026 自製實驗講義：封面 54pt、藍底 143F9C 分隔張、內容張 30pt 標題＋6.14×5.32 吋圖框＋20.2pt 說明句）。每張內容張有 `kind`（沒寫＝`shot`）：`shot` 截圖張，有 `img.path` 就放那張截圖（2026-10-21 起：`wsi_crop.py` 從掃描檔切、`annotate_shot.py` 加註記），沒有就放不含字的淡灰空圖（形狀名「截圖待補 <id>」），教師用「變更圖片」換截圖；`bg` 背景知識張，標題下全寬條列（`--bg-pt`，預設 24），可加 `table`（第一列表頭，放不下接續一張、重複表頭）；`gx` 大體／影像張，`img.path`（相對 deck.json）的圖等比置中、`img.credit` 出處行放圖下不壓圖，沒有圖檔放淡灰空圖（「圖待補 <id>」）；`sc` 形態學示意圖張，有 `img.path` 就放圖，沒有就放淡灰空圖（「示意圖待換 <id>」）。某一節寫 `"divider": null` 就不放分隔張（例：封面後直接放玻片編號對照，2026-10-27）。deck.json 最上層 `"panel": true` 在圖與說明句底下墊淺灰底（EAE9E6），`"bullets": true` 說明句加「•」，兩個都是教師〈發炎〉的原樣（骨與關節實驗講義沒開）。教師 2026-10-15：實驗講義不可以只有截圖，要有背景知識跟形態學示意圖。用 gen_pptx 的字型量字，放不下時結束碼 1；報告另寫 `ids`（id → 張號）與各種圖位的格數。`--fit <deck.json 或節檔> [--bullets]` 只量字不產檔（撰寫代理自查）。標題裡的 `\n` 是手動換行（長的英文全名放第二行，不讓「低倍」單獨掉下去）；截圖多時加 `--img-max-side 1280 --jpeg-quality 82`（150 張約 50 MB）。shot 的 `img.marks`（annotate_shot 格式）疊成 PowerPoint 原生圖形：紅色直線箭頭（一般線條圖形，不用接點：LibreOffice 會把落在標籤框邊中點的接點吸附成折線）、紅圈、深灰底白字標籤，不群組、每個有名字（「註記 MC03-2 箭頭1」「標籤 MC03-2 透明細胞」），教師可以直接改（2026-10-27）；標籤超出圖、重疊、小於 24pt 寫進報告。bg 張的表格欄寬照字數比例分，但每欄至少放得下最長的一個英文字（粗體的表頭與第一欄也算）。 **備忘稿預設不寫字**（硬規則 18，2026-11-21）：截圖要拍的倍率與視野、每張的來源改寫到 `--src-list` 指定的清單（給教師看、不發給學生，和講義一起交）；`--notes` 才照舊寫進備忘稿，舊指令的 `--no-notes` 還收、等於預設。
- `wsi_crop.py info|overview|crop|batch …`：從全玻片掃描檔（Aperio .svs 等 tiled TIFF）切實驗講義的截圖，用 tifffile＋imagecodecs 直接解圖塊，不需要 openslide 或 QuPath（2026-10-21）。`overview <svs> --out <png> --grid 10` 出附座標格的總覽圖（座標是整片寬高的比例 0–1）；`crop <svs> --cx --cy --mag --out [--grid 4]` 切一個視野（mag 10＝每像素 1 µm，同一個 mag 在 20x、40x 掃描的片子看到的範圍一樣；預設 1600×1386 px＝實驗講義圖框比例）；`batch <crops.json> [--overview-dir 資料夾]` 依規格切一整例，另存一張用方框標出各截圖位置的總覽。不讀、不輸出玻片 label 與 macro 影像（有病理號）。
- `annotate_shot.py <規格.json>`：實驗講義截圖加註記（2026-10-27 起只出燒好的預覽給寫的人自查；成品改由 merge_annot＋gen_lab_pptx 畫成 PowerPoint 圖形），照教師在 QuPath 上的畫法：紅圈（circle）、紅箭頭（arrow）、雙頭箭頭標範圍（span）、虛線（line）、深灰底白字標籤（label：兩行「中文」「(English)」，或 lines 自己分行）。字級以 6.14 吋版位換算、至少 24pt；標籤超出圖會自動移進圖內，重疊時結束碼 1。規格可以是一整例的 `{"shots": […]}`；格式見該檔 docstring。
- `merge_annot.py <deck.json> --annot <annot.json…> --out <deck.json>`：把 annotate_shot 的規格帶進 deck.json：img.path 指到某規格的 out（燒好的圖）就改指它的 image（原始截圖），帶入 marks、label_pt，原圖記在 img.burned；路徑改寫成相對 --out。成品的註記從此由 gen_lab_pptx 畫成可改的 PowerPoint 圖形（教師 2026-10-27）。原始截圖不存在時結束碼 1。
- `html_lab_deck.py <deck.json> --out <檔案.html> [--max-side 760] [--quality 60]`：實驗講義的 HTML 版（deck.json → 一個圖片內嵌的 HTML，幾何同 gen_lab_pptx，淡灰圖位照畫；img.marks 畫成疊在圖上的 SVG）；放 OneDrive 的版本壓到 4 MB 以下。
- `strip_notes.py --check <檔.pptx …>`｜`strip_notes.py <來源.pptx> --out <新檔.pptx>`：查 PPTX 有沒有備忘稿（PowerPoint 的講者備註欄），或把備忘稿全部清掉另存新檔（硬規則 18；教師 2026-11-21「備忘稿全清掉 我不用那個東西 也不要讓學生看到」）。`--check` 只看：每份印張數、有字的備忘稿張數與字數，有字就結束碼 1；實驗講義、課程自己產的檔、要交的每一份 PPTX 交件前都跑。清的時候直接改 zip、不經 python-pptx 重存：只拿掉備忘稿頁、每張投影片指向它的關聯與登記，其他零件逐位元不變，寫完自己驗（CRC、張數、開得起來、沒有備忘稿頁）。不覆寫既有檔，也不直接寫進雲端同步資料夾；教師自己改過的定稿也可以清（另存新檔，原檔不動）。
- `draw_flow.py <規格.json> <輸出資料夾> [--course <課程>] [--only 圖名…]`：程式畫的中英對照流程圖（機轉、病程、治療流程），印出放進版位後的實際 pt，最小 < 24pt 或超出畫布時結束碼 1。規格格式見該檔 docstring。**2026-11-12 起 PNG 只給 HTML 版用**：PPTX 上的流程圖由 gen_pptx 照同一份規格畫成 PowerPoint 原生圖形（下一條），教師才能改字。
- `flow_shapes.py`（模組，gen_pptx 與 common 會匯入，不單獨執行）：素材池某張寫 `<!-- flow: <規格.json 相對課程資料夾>#<圖名> ｜ 出處：… -->`，gen_pptx 就在那張的圖區（flash／robbins／big 全寬、left 右欄）畫圓角框、箭頭、說明文字方塊與紅色 T 字線，不放 IMG 的圖檔；出處沒寫就用同張第一個 IMG 的出處。字級從 28 往下試到課程 `sizes.label`，放不下會記進 `_layout.json`（「流程圖」），check_deck 照報。規格裡的字會進 style_check（中英對照、用語）；check_deck 把這種張算成有圖。同張留著的 IMG（draw_flow 的 PNG）只有 html_deck 會用，規格改了要重畫。

Gemini 重寫（每一講必做；`AGENTS.md` 硬規則 17、SOP 第 9b 步）：
- `rewrite_pack.py make --course <課程> --deck <deck> --out <資料夾> [--only 12,13,20-25] [--per-pack 45]`：出重寫包，請別的模型（教師指定 Gemini）用它自己的話把每一張整個重寫。一節一份 `.md`（請它做的事、不能變的底線、輸出格式、研究資料、每張的原文與長度上限），另寫一份「怎麼用」；每張的原文記在 `<課程>/_archive/revoice/rewrite_manifest_<deck>.json`。封面、分隔張、國考題張、數字卡片與 `course.yaml` `rewrite.keep` 指定的行不給重寫。`--out` 放在 repo 與雲端同步資料夾以外，做好再複製過去。`--only` 只包內容改過的那幾張。
- `rewrite_pack.py apply --course <課程> --deck <deck> <回覆檔 …> [--tag gemini1] [--write] [--accept soft|張號] [--keep-titles]`：讀教師帶回來的回覆（`### 第 N 張`、`T｜`、`B｜`、`R0｜…`），整理寫法、把被改掉的照抄行換回去，逐張查數字、頁碼、英文、上色、行數或字數、表格形狀、禁用字，寫對照表（原來／改成／檢查／依據）與「退回給Gemini」（請對方自己修的張）。`--write` 才把檢查是 ok 的張寫回來源檔。意思有沒有跑掉查不到：套回以前主 session 要逐張對依據（程度詞、時態、誰對誰）。
- 設定（`course.yaml` 的 `rewrite:`，都選填）：`label` 檔名用的簡稱；`src` 句子所在的檔（預設素材池；素材池是從批檔組裝的課寫批檔）；`notes` 移下投影片的細節檔（預設讀講稿檔的【講義補充】）；`digest_dir` 各段事實摘要（沒有就從 `facts_R.json` 列）；`keep` 照抄的行（正規表示式）。對象讀 `audience`。
- 長度上限：上字下圖的版型（flash、pair、big、robbins）用 gen_pptx 的量字函式算說明句現在佔幾行，上限＝不比現在多行；其他版型＝原來字數的 1.1 倍。有圖的 left 張欄窄，字數在上限以內實排也可能多一行：套回以後要算圖逐張看。

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
<!-- order: img-first -->                                      ← 選填：big 版型空標題＋有圖時，圖在上、句子在圖下（實驗課「圖＋圖下說明句」）
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

標題與條列裡寫「⏎」＝同一段內換行（用在斷行位置要照原句語氣斷的地方）；量字、字數與風格檢查都當它不存在。文字裡的 `http://`、`https://` 網址會自動做成超連結。
course.yaml 選填 `layout: {left_min_frac: 0.30}`：left 版型的條列都很短、每條一行排得下時，文字欄可從 47% 縮到這個比例，圖放大（預設 0.47＝不縮）。
選填 `layout: {left_fit_image: true}`（2026-11-21，16:9 用；預設關）：left 版型的圖受高度限制、用不滿右欄的寬時（直幅或正方形的圖），把多出來的寬給文字欄，行數變少、圖的大小不變；右欄至少留 4.6 吋。打開以後斷行會變，要重看算圖。
單張的調整：素材池那一張寫 `<!-- left_frac: 0.52 -->`（2026-11-21），left 版型的文字欄就從這個比例起跳（0.30–0.65）。用在估算放得下、實排卻多折一行超出版面或留下孤字的張：欄窄、英文長詞多的張，估算差半個字就會多一行。圖跟著讓位，改完要算圖看。

## 版型（type）

| type | 用途 | 文字上限（4:3、28pt） |
|---|---|---|
| title | 封面 | 標題＋2–3 行 |
| divider | 節／段落分隔（深色底） | 名詞短語標題＋最多 2 行副標 |
| left | 條列＋右圖（無圖則全寬條列） | 有圖：每行約 10 字、共約 8 行；無圖：每行約 17 字、共約 9 行 |
| flash | 標題＋1–2 句＋全寬大圖 | 說明 ≤2 行 |
| big | 單句大字（sizes.big），可附圖；空標題沒圖時句子垂直置中；空標題有圖加 `<!-- order: img-first -->` 則圖上句下 | 1–3 短句 |
| pair | 兩圖並排（可加標籤） | 說明 ≤2 行 |
| robbins | 整張教科書圖 | 說明 ≤1 行 |
| table3 | 表格（≥20pt；超過 table_max_rows 自動拆成同標題連張）。可加 `<!-- tbl: style=clean; col_w=3,4,4; colors=3D8168,BF5B3C; align=center; fill=on -->`：style＝band（預設，深色表頭＋斑馬紋）／clean（只有表頭下粗線與列間細線）／accent（clean＋每列首欄左側色帶與淡色底，色依 colors）；col_w 各欄相對寬度；align=center 首欄以外置中；fill 把多的高度分給各列（clean／accent 預設 on）；pad=tight 把 clean／accent 的列距收小。2026-10-20 教師：「表格要做得漂亮」「字要少」 | 每格短語 |
| quiz | 國考題：course.yaml `decks.<deck>.quiz_style` 乙（預設；年次標題＋題幹選項 24–28pt，正解整段藍；標題格式 `quiz_label`，佔位 {年度} {第幾次}（一、二） {次}（1、2） {題號}；題幹色 `design.quiz_stem`，不寫＝deep）或 甲（1 列 3 欄表「正解字母粗體｜題號．題幹＋選項｜年度-次」，不放標題） | 官方原文 |
| stats | 大數字卡片（`數字｜說明`） | 2–4 張卡 |
| diagram | 框架圖（course.yaml diagrams）。多欄小字的地圖（例：教師 9 月 B2 呼吸的 9 欄氣道地圖）在該框架圖寫 `cell_pt`、`label_pt`、`name_pt`、`gap`、`pad`、`label_w`、`node_h`、`row_cap`、`legend: true`（各組色塊＋`groups.<g>.name`）、`bullets_below: true`（條列畫在圖下，字級 `below_pt`）；check_deck 對那一張的字級下限改用它寫的值。框架圖張另寫 IMG 時變成「地圖條＋圖」：上方只畫亮的列，下面最多兩條說明句與一或兩張圖（2026-11-12） | 格子 ≥20pt；4 欄時每行約 7 個中文字，每格最多兩行（約 14 字，含英文）；多欄小字時格子的字由框架圖自己定 |

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

# <課程>：<系級> 病理學<碼>「<講題>」課程指引

> 複製到 `<materials>/courses/<課程>/CLAUDE.md` 後把角括號換掉。本檔只寫這門課專屬的事：課程資訊、教師裁決摘要、單一事實來源、重產指令、素材位置、待辦。
> 通則（硬規則、環境、工作流、交件）在 kit 的 `CLAUDE.md`；風格在 kit 的 `style/guide/`；工具用法在 kit 的 `scripts/README.md`。
> 不寫本機絕對路徑、學生資料、教學評量資料；路徑一律寫 `<kit>`、`<materials>` 或相對於本課程資料夾。

## 課程
- <系級>（課程代碼 <碼>），<上課日 YYYY-MM-DD>，<節數> 節。
- 成品：`成品/<course.yaml decks.<deck>.filename 代入日期>.pptx`＋同名 PDF（<畫幅>，<張數> 張：<各節張數>）。
- 交教師：`成品/待教師裁決清單.md`、`成品/待補圖清單.md`。

## 教師的裁決（<裁決日期>）
<一段話摘要；完整表格與日期在 `brief.md`「教師已裁決」。字級、中英對照（course.yaml `bilingual`）、國考題庫只寫這門課的明令，沒有明令的項目寫「照指南」。>

## 單一事實來源（只改這些，別手改成品）
| 檔案 | 內容 |
|---|---|
| `sources/<主題>-pool.md` | 每張投影片：標題、type、圖、出處、條列、表格（格式見 `<kit>/scripts/README.md`） |
| `sources/<主題>-script.md` | 備註（教科書頁碼＋短提示） |
| `sources/decks/<deck>.md` | 張序與分節 |
| `course.yaml` | 字級、色票、框架圖、國考標題格式、中英對照範圍與白名單 |
| `glossary.md` | 中英對照唯一用字（style_check 檢查） |

藍圖與撰寫中間檔在 `_archive/`（gather、blueprint、written、review、journals）。assemble 之後來源檔就是唯一的真相，不要再用藍圖或撰寫 JSON 重組（會蓋掉 pool.md）。

## 重產
```bash
KIT="<kit 的絕對路徑>"; MAT="<materials 的絕對路徑>"; C=<課程>; CD="$MAT/courses/$C"
cd "$KIT/scripts"
SLIDEKIT_MATERIALS="$MAT" PYTHONIOENCODING=utf-8 python gen_pptx.py --course $C        # 產 PPTX＋自動 check_deck（先看 成品/ 有沒有老師改過的同名檔）
SLIDEKIT_MATERIALS="$MAT" PYTHONIOENCODING=utf-8 python style_check.py --course $C     # RED 必須 0
SLIDEKIT_MATERIALS="$MAT" PYTHONIOENCODING=utf-8 python export_pdf.py "$CD/成品/<PPTX 檔名>.pptx" --pdf "$CD/成品/<PDF 檔名>.pdf" \
    --sheets "$CD/_archive/render/sheets" --pngs "$CD/_archive/render/png"
SLIDEKIT_MATERIALS="$MAT" PYTHONIOENCODING=utf-8 python img_todo.py --course $C
```

## 素材
- 教科書頁圖與 OCR：course.yaml `textbook.pages_dir`（`../../textbook/<書>_<章>/pages`；印刷頁＝PDF 頁＋<offset>）。
- 教科書切圖：`assets/images/Robbins抽圖/`（`index.json`、`圖片清單.md`、`ovr.json` 手動座標）。
- 舊投影片抽圖：`assets/images/舊講義抽圖/`（`圖片清單.md`；寫明哪些是教師自製、哪些是他人的圖與致謝方式）。
- 開放授權圖：`assets/images/文獻圖/`（授權見 `_archive/gather/lit/*_images.json`）；總表 `assets/images/圖片總表.md`。
- 事實帳：`facts/facts_R.json`、`facts/facts_X.json`、人讀版 `facts/facts.md`。
- 國考題庫：`<kit>/question_banks/<題庫>/`。
- 撰寫 brief（若有）：`<materials>/style_evidence/writer_brief_<課程>.md`。

## 續跑紀錄
工作流的 journal、當次 args 與 DONE 表放 `_archive/journals/`（見 `<kit>/workflows/README.md`「續跑」）。

## 待辦
- <例：等教師回覆 `成品/待教師裁決清單.md` 後改 pool.md 再重產。>
- 教師若親手改了成品：先照 `<kit>/docs/SOP_新教案流程.md` 第 11b 步回灌，才可以重產。

# examples/：範例課程設定

## examples/immune/

課程 immune（病理學C 免疫疾病，牙醫系三年級，2026-10-02 三節、184 張）實際使用的設定，是第一門照整條管線從零做完的課：

| 檔案 | 內容 |
|---|---|
| `course.yaml` | 與私人 repo `courses/immune/course.yaml` 相同（2026-09-25 同步）：課程代碼、對象、上課日、教科書頁碼換算與 `pages_dir`、來源檔路徑、deck 設定（節數、張數範圍、國考題庫、國考標題格式、檔名）、畫幅、字級、強調色、封面、中英對照範圍（`bilingual: per_slide`）與白名單、框架圖（hyper4、imm_map） |
| `brief.md` | 課程簡報的公開精簡版：對象與時間、「教師已裁決」表、大綱草案、素材位置、他舊投影片的沿用原則。舊張的逐張錯誤清單、班級與同事素材的細節只在私人 repo 的 brief |

## 怎麼用

- **當範本看**：開新課時從 `templates/course.template.yaml`、`templates/brief.template.md` 複製（範本有逐欄註解）；這裡的兩個檔讓你看到填好的樣子。
- **注意課程明令不外推**：immune 的字級（標題 36、內文 28、學生要讀的字 ≥20、出處 14）、每張專有名詞中英對照（`bilingual: per_slide`）、牙醫師國考題，是老師只對這門課下的裁決。新課程沒有同樣的明令時，字級用 `templates/course.template.yaml` 註解裡「沒有明令時的預設」，`bilingual` 刪掉（預設 `first_per_deck`），不要照抄這裡的數字。
- **路徑**：`course.yaml` 裡的路徑都相對於課程資料夾。真正的課程資料夾在私人 repo `pathology-slide-materials/courses/immune/`，`textbook.pages_dir` 的 `../../textbook/robbins11e_ch06_immune/pages` 是從那裡算的；這裡的副本只當範例，在 kit 裡這個路徑不存在。

## 與工具的關係

`--course immune` 找設定的順序是：路徑本身 → `<materials>/courses/immune/course.yaml` → `examples/immune/course.yaml`。只有公開 kit、沒有私人 repo 時會用到這裡的副本，但素材池、講稿、圖片、事實帳都在私人 repo，所以 `gen_pptx.py` 等需要課程內容的工具在這種情況下跑不起來；能跑的只有不需要課程內容的部分（例：讀設定、檢查 course.yaml 格式）。

範例裡沒有、也不會放任何教科書內容、圖片或投影片。

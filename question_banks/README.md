# question_banks/：國考題庫

## 來源與著作權

題目與答案取自考選部「考畢試題查詢平臺」（<https://wwwq.moex.gov.tw/exam/wFrmExamQandASearch.aspx>）公開的試題、標準答案與更正答案 PDF。依著作權法第 9 條第 1 項第 5 款，依法令舉行之各類考試試題不得為著作權之標的，所以可以收在公開 repo。原始 PDF 沒有放進 repo，需要時可重新下載。

## 檔案

| 資料夾 | 檔案 | 內容 |
|---|---|---|
| `醫師/` | `questions-104-1_to_114-1.json` | 醫師(一) 醫學(二) 104-1～114-1，只收病理學段（題號 76–100），575 題 |
| `醫師/` | `questions-114-2_to_115-1.json` | 同上 114-2、115-1，50 題 |
| `醫師/_unconfirmed/` | `questions-115-2.json` | 次別未確認的一份醫學(二) 試卷，只留題號 76–100（25 題）；放在子資料夾，工具不會讀（見下方「已知問題」） |
| `牙醫師/` | `questions-dent-104-115.json` | 牙醫師(一) 牙醫學(二) 104-1～115-2，24 份、1,920 題（每份 80 題） |
| `牙醫師/` | `manifest.json` | 每場次的考試代號、類科與科目代號、題數、更正內容與公告原文、下載網址；由 `parse_moex_exam.py` 產生 |

醫學(二) 涵蓋微生物免疫學、寄生蟲學、藥理學、病理學、公共衛生學；病理學在題號 76–100。牙醫學(二) 涵蓋口腔病理學、牙科材料學、口腔微生物學、牙科藥理學。

## JSON 格式

每個 `questions-*.json` 是一個 list，每題：

```json
{"題號": 76, "年度": 114, "第幾次": 2, "科目": "牙醫學(二)",
 "question": "題幹", "options": {"A": "…", "B": "…", "C": "…", "D": "…"},
 "answer": "D", "src": "試題 PDF 網址"}
```

`科目` 與 `src` 只有牙醫師題庫有。`answer` 的值：

| 值 | 意思 |
|---|---|
| `A`～`D` | 單一正解（已套用更正，例如「答案更正為Ｄ」） |
| `#` | 一律給分（送分）；醫師題庫 10 題、牙醫師題庫 6 題 |
| `A,C` 等 | 複選給分（「答Ａ、Ｃ給分」「答Ａ或Ｃ或AC者均給分」都轉成逗號串） |

## key 格式

題目的 key 是 `{年度}-{第幾次}#{題號}`，例：`113-1#45`。素材池用 `<!-- quiz: 113-1#45 -->` 指定題目；`validate_blueprint.py` 與 `check_deck.py` 會檢查 key 在題庫裡。投影片上的年次標題由 key 產生（格式在 course.yaml 的 `decks.<deck>.quiz_label`，例：「{年度}年第{第幾次}次專技高考 牙醫學(二) {題號}題」），不要從老師舊投影片抄年次：他舊張的年次標籤有 17 題與題庫不符。

## 工具怎麼讀

`scripts/common.py` 的 `load_questions()`：讀 `question_banks/<bank>/*.json`（跳過 `manifest.json`），`<bank>` 是 course.yaml `decks.<deck>.question_bank` 的值（`醫師` 或 `牙醫師`）。**醫師題庫只收題號 76–100**；子資料夾（例如 `醫師/_unconfirmed/`）不會被讀到。

## 更正的處理

考選部公告的更正（`{年度}-{次}_M.pdf`，更正題以「＃」標示、備註寫更正內容）在解析時已套用到 `answer`；原始公告文字留在 `manifest.json` 各場次的 `corrections`、`correction_note`（例：105-2 第 40、65 題一律給分，第 73 題答 A、B 給分）。選題時避開 `#` 與複選給分的題。

## 加新一年的題

```bash
cd "<kit>/scripts"
# 牙醫師(一) 牙醫學(二)：下載試題、標準答案、更正（需要能連 wwwq.moex.gov.tw 的網路）
PYTHONIOENCODING=utf-8 python fetch_moex_dent_exam.py --out "<暫存資料夾>/raw" --start 116 --end 116
# 解析整個資料夾（檔名 {年度}-{次}_Q.pdf／_A.pdf／_M.pdf）
PYTHONIOENCODING=utf-8 python parse_moex_exam.py --raw "<暫存資料夾>/raw" \
    --out "../question_banks/牙醫師/questions-dent-{first}-{last}.json" \
    --manifest "../question_banks/牙醫師/manifest.json"
# 單一場次（醫師題也用這個方式）
PYTHONIOENCODING=utf-8 python parse_moex_exam.py --q 116-1_Q.pdf --a 116-1_A.pdf [--m 116-1_M.pdf] \
    --year 116 --session 1 --src "<試題 PDF 網址>" --out "../question_banks/醫師/questions-116-1.json"
```

- `fetch_moex_dent_exam.py` 需要 `requests` 套件；已存在且大於 1 KB 的檔不重抓。其他考科改 `--exam-keyword`、`--subject-keyword`。
- 原始 PDF 放在 repo 以外的暫存資料夾，不要 commit。
- 醫師題庫只存題號 76–100（病理段）：整份解析完先刪掉 1–75 題再存（工具本來就只讀 76–100，但檔案不要帶非病理科的題）。
- 解析時 stderr 的警告（部首字、圈號、題數不符）要逐條看過；每場次題數要對（醫學(二) 100 題、牙醫學(二) 80 題）。
- 新檔用同樣的欄位名稱，key 不要與舊檔重複。
- 雲端 session 預設的 Trusted 網路連不到考選部，要改 Custom 加 `wwwq.moex.gov.tw`，或在本機做。

## 已知問題

- **`醫師/_unconfirmed/questions-115-2.json` 的次別未確認**：來源 PDF（`115020_2301.pdf`）標頭寫「115 年第一次專門職業及技術人員高等考試」，而且第 76–100 題與 `questions-114-2_to_115-1.json` 的 115-1 第 76–100 題題幹與答案相同（25 題中 22 題逐字相同，3 題只差空白）。為了不讓 `115-2#76`～`#100` 這 25 個重複 key 通過 validate_blueprint 與 check_deck，這個檔已移到 `_unconfirmed/`（工具不讀），只留 76–100。引用這 25 題一律用 `115-1#…`。真正的 115 年第二次試卷公布後，下載解析成 `醫師/questions-115-2.json`，再刪掉 `_unconfirmed/` 這份。
- `牙醫師/manifest.json` 的 `files[].file` 只記原始 PDF 的檔名（PDF 不在 repo 裡，需要時用 `url` 重新下載）。
- 題幹寫「如附圖」的題，題庫沒有圖，不要選。

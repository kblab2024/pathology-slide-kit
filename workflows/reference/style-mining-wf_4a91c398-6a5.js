export const meta = {
  name: 'style-mining',
  description: 'Mine teacher style rules from 39-deck corpus + 3 edit diffs: 22 dimensions, each mined, refuted twice, revised; then writer brief',
  phases: [
    { title: 'Mine', detail: 'one miner per guide dimension' },
    { title: 'Refute', detail: 'two refuters per dimension search corpus for counterexamples and verify quotes' },
    { title: 'Revise', detail: 'miner-reviser applies refutations' },
    { title: 'Brief', detail: 'writer brief for the immune dental deck' },
  ],
}

// 歷史範例：2026-09 免疫課程（immune）原版腳本，只供對照，不要直接執行。
// 已去除本機路徑（<ROOT> 為舊專案根目錄的佔位字）並把模型改成 opus；新課程請用 workflows/ 下的通用版：
// style-mining.js（說明見 workflows/README.md）。

const ROOT = '<ROOT>'
const ROOT_BASH = '<ROOT in Git Bash>'
const W = ROOT + '/style/_work/mining'
const RET = { type: 'object', properties: { path: { type: 'string' }, count: { type: 'integer' }, notes: { type: 'string' } }, required: ['path', 'count', 'notes'] }
let aborted = false
async function A(prompt, opts) {
  if (aborted) return null
  const r = await agent(prompt, { model: 'opus', schema: RET, ...opts })
  if (r === null) { aborted = true; log('ABORT: agent returned null at ' + (opts && opts.label) + ' — stopping; resume later') }
  return r
}

const COMMON = `
Project root: ${ROOT} (Git Bash: ${ROOT_BASH}).
We are writing a VERY detailed, LLM-friendly style guide describing how the pathology teacher makes lecture slides, so that future LLM sessions can produce decks he will accept with minimal edits.
CORPUS (read ${ROOT}/style/corpus/index.md first): 39 decks dumped per slide in ${ROOT}/style/corpus/decks/{code}.json (full detail: shapes, positions in inches, effective font size per run 'sz', colour hex incl. theme colours 'col' + 'col_src', pictures, tables, notes, layout) and {code}.txt (LLM-readable: each paragraph followed by [size pt] and {colour「text」} marks; "===== #n [layout] 圖k" headers; 〔備註〕 = notes). Edit diffs (my draft -> his hand edit) in ${ROOT}/style/corpus/edits/*.md. Prior findings (to be re-verified, some old rules are wrong): ${ROOT}/style/_work/prior_findings_20260924.md. Old rule files: the earlier memory notes 版面記憶檔, 文字記憶檔, 結構記憶檔 (local only, not in this repository).
AUTHORITY ORDER: his hand edits of my drafts (2026_B2_* vs mine_*) > his own decks (2026 > 2025 > 2024) > my drafts (mine_*, counterexamples only) > other authors (other_*, contrast only). 2024 immune decks: only slides 1-47 (一) and 1-49 (二) are his; the rest are 同事甲 old slides. Several decks are duplicates (see index notes and prior findings E): dedupe before counting and say so.
Use Python (json module over the .json dumps) for counts and distributions; use grep on the .txt dumps for phrases. Every quantitative claim must state its denominator and which decks. Every example quote must be VERBATIM from the dumps with its deck code and slide number (e.g. 2026_A1_發炎一_0917 #25).
RULE FORMAT (JSON objects): {"id":"<DIM-PREFIX>-NN","level":"MUST|SHOULD|MAY|AVOID|NEVER","instruction":"one imperative sentence in Traditional Chinese","threshold":"numeric threshold or null","scope":"which aspect ratio / course / slide type / genre it applies to","examples_his":[{"quote":"...","deck":"...","slide":n}],"counterexamples_mine":[{"quote":"...","source":"mine_... #n or edits/...md","his_fix":"what he changed it to, if any"}],"check":"regex or metric that a script could test, or 'manual'","why":"reason, grounded in evidence","strength":"e.g. 7/9 unique decks, 74 runs","exceptions":"..."}
Write in Traditional Chinese (quotes stay verbatim). Your final answer is just {path, count, notes}.`

const DIMS = [
  { id: '11_畫幅與版面配置', p: 'LAY', f: 'Aspect ratio per deck/course/year; built-in layouts used vs Blank; share of text in placeholders vs text boxes; backgrounds (colour, images); where titles sit (x,y,w,h distributions); margins; slide numbers (none?); how images and text are arranged (text top + image below, text left + image right, full-bleed); grouping; SmartArt usage; consistency within a deck.' },
  { id: '12_字級', p: 'SIZE', f: 'Effective font-size distributions per ROLE (title, main statement, bullet level 1/2/3, single big sentence, labels on images, table text, exam-question stem/options, captions/credits, citations, divider text, cover) separately for 4:3 and 16:9 and for 2024/2025/2026. Where sizes are non-integers explain (scaling artefacts). Quantify: share of body characters below 20pt / 24pt per deck; what text is allowed to be small. Evidence of him ENLARGING text when revising (compare 2025 vs 2026 versions of the same deck, and edits). Sub-level vs parent sizes.' },
  { id: '13_密度與字數', p: 'DEN', f: 'Characters per slide (median, p90) per deck (dedupe); bullets per slide; bullet length; title length; zero-bullet (title+image) slides; text-only slides; slides per lecture hour (use deck sizes and the fact that one A1 deck = one 50-min period; he said he never wants to fill the whole period, target ~40 min); how density differs between his own decks and his edits of mine.' },
  { id: '14_色彩與強調', p: 'COL', f: 'Body text colour(s); emphasis colours by role (theme accents incl. ED7D31 orange, 4472C4 blue, rgb 143F9C, FF0000, C0504D, 2E414F, 62A8BB, F79646...), what gets coloured (single words, key phrases, whole lines, exam answers, classical quotes, citations); counts per deck; which colours he adds in edits of my drafts; colours of dividers/backgrounds.' },
  { id: '15_圖片與配對', p: 'IMG', f: 'Picture rate per deck (dedupe); pictures per slide; picture sizes and positions (single right, pair side by side, full width, bleed); picture-only slides; same image repeated across build slides; pairing logic (H&E + IHC, clinical + micro, normal vs lesion, two stains) inferred from captions/labels/text; labels placed on or next to images (e.g. "HE", "Wright-Giemsa") and their size; image sources inferred from captions (Robbins, ExpertPath, journals, Wikimedia, webpathology).' },
  { id: '16_出處與引用格式', p: 'CITE', f: 'Extract ALL citation/credit strings (regex: 圖片來源|圖源|資料來源|來源|Robbins|ROBBINS|Fig|圖[0-9]|http|www|doi|PMID|et al|Journal|J\\.|pp\\.|頁|第.章|AD\\)|《) from his decks and classify formats: in title parentheses, label under image, bottom-left 補充來源, full journal references, URLs (case, size), Robbins page/figure formats, chapter cross-references, classical-text attributions with dates. Give size and colour of each type, and counts.' },
  { id: '21_標題句式', p: 'TTL', f: 'Classify every title (use title field; for decks without title placeholders the top/biggest text) into: complete statement sentence / label "分類詞：子題(English)" / pure term or disease name / equation "X = Y" / question (with or without answer) / connective-start (不過、因此、所以、然而) / bracket-tail (圖說, 口訣, Robbins 圖號, 出處) / en dash sub-type "X – Y" / enumerated "之一、之二". Counts per deck; how the same title repeats across build slides; how he rewrote my titles in edits (list every retitle mine -> his and infer rules).' },
  { id: '22_條列與句型', p: 'BUL', f: 'Bullet/sentence patterns: sentence length, levels, parallel structure, plain words before terms (先白話再術語), use of ： labels, lists separated by spaces or 、, colloquialisms he uses vs ones he removes, how he states mechanisms, how he writes morphology, how he writes numbers/percentages, first/second person. Contrast his own bullets with my drafts and his rewrites of them.' },
  { id: '23_禁用語與LLM語', p: 'BAN', f: 'Build evidence-based RED/WARN phrase lists. (1) From edits: phrases/constructions in my drafts that he deleted or rewrote (verbs like 打這裡/打的是/可以回頭, question tails, connectives, dramatic phrasing, metaphors, 「——」, 其一其二...). (2) Candidate LLM phrases (值得注意的是, 不難發現, 讓我們, 總而言之, 綜上所述, 簡而言之, 至關重要, 扮演…角色, 關鍵在於, 深入探討, 揭開…面紗, 不僅…更, 雙面刃, 堪稱, 旨在, 意味著, 本質, 根本, 說穿了, 換句話說, 事實上, 可以說, 核心, 精準, 全方位, 此外, 進而, 從而, 透過...): count each in HIS decks vs MY drafts. A phrase he uses himself cannot be RED (say so). (3) Words he explicitly adopted from my drafts (kept unchanged). Output RED list, WARN list, ALLOWED-though-suspicious list, each with counts.' },
  { id: '24_術語與中英對照', p: 'TERM', f: 'Bilingual formats: 中文(English), 中文 (English), 中文（English）, English(中文), 中文English glued, abbreviations after ; or space, English-only allowed items (stains, markers, gene names, abbreviations). Frequencies per deck and in edits (he added +29 pairs in B2二). Build a GLOSSARY of his own Chinese renderings of pathology/immunology terms found in the corpus (Chinese | English | deck/slide), especially immunology terms (免疫, 過敏, 自體免疫, 排斥, 抗體, 淋巴球, T細胞, B細胞, 補體, 類澱粉, 紅斑性狼瘡, 修格蘭, 硬皮, etc.). Note his known typos (白班, cilitated, Sjogren) and term decisions (分化不良, uppercase P53/P16/P40/P63).' },
  { id: '25_符號與標點', p: 'SYM', f: 'Counts and usage of: => , -> , → , = (definitions), ： vs : , half-width vs full-width parentheses, spaces used as pauses (核大 核黑 核不規則), / , ？, …, 「」, 『』, en dash –, em dash —, 「——」, bullets characters, numbering styles, full-width digits. Per deck and in his edits of mine.' },
  { id: '26_語氣與態度', p: 'TONE', f: 'His voice: attitude toward exams (直白), toward the textbook, humor, admissions of uncertainty, rhetorical questions and how answered, 我們/你們 usage, encouragement, warnings, board instructions, statements of importance ("國考重要性：低"). Collect verbatim examples from slides AND notes with deck/slide. Contrast with the tone of my drafts that he removed.' },
  { id: '31_開場與結尾', p: 'OPEN', f: 'For every unique lecture deck: list the first 10 slides and last 5 slides (titles + type). Derive patterns: cover format (title text, subtitle, credits like 部分圖片感謝...), presence/absence of objectives/agenda/review, orientation slides, first exam question position, how the first topic starts, cliffhanger endings, no summary/thanks.' },
  { id: '32_段落節奏與同標題連張', p: 'RHY', f: 'Same-title consecutive runs (length distribution, % of slides, what changes between builds: one more bullet, new image, arrow moves, recoloured SmartArt); segment lengths (slides per topic); alternation of text and picture slides; question -> answer slide pairs; how mechanism explanations are paced; build devices he uses (SmartArt recolour, moving arrow, same image repeated).' },
  { id: '33_divider', p: 'DIV', f: 'Identify divider/section slides (標題投影片 layout, big centered text, "Section N" labels, dark backgrounds, 45-60pt topic): wording type (noun phrase, sentence, suspense/rhetorical sentence, question), subtitles, sizes/colours, frequency per deck, and how he changed my dividers in edits.' },
  { id: '34_國考題', p: 'EXAM', f: 'All exam-question slides in the corpus (regex 國考|專技|年第.次|題[)）]?|\\(A\\)|（A）|[A-D]\\s*\\|): formats (1-row 3-column table; title "107年第二次專技 78題" + large stem; one option per line; answer colouring blue 143F9C / orange F79646 / none; answer-key slide after, e.g. Robbins page), sizes, placement relative to topic, counts per deck, 醫師 vs 中醫 (中醫臨床) questions and his commentary lines, and how the 國考複習 decks teach exam content. Also the 2024 immune deck slide that says "國考重要性：低".' },
  { id: '35_中醫與古籍', p: 'TCM', f: 'Every classical Chinese medicine text slide (傷寒, 金匱, 溫熱論, 素問, 靈樞, 難經, 方證, 湯證): format (as title, as subtitle, quote + => modern mechanism), colours (light blue ACCENT_5, blue), sizes, dates attributions, placement (premise before framework vs aside), which ones he deleted from my drafts (associative) vs kept/added (explanatory), 中醫國考 questions with 方證 comments.' },
  { id: '36_備註', p: 'NOTE', f: 'Notes coverage per deck (dedupe), length distribution, content types (spoken script, board instructions （板書）, English pastes from Wikipedia/Robbins, exam comments, leftovers copied from other slides), language; whether he ever edits my notes (compare edits); recommendations for what notes an LLM should write for him.' },
  { id: '37_刪張與留張', p: 'CUT', f: 'From the three edit diffs: every slide he deleted, added, split, merged or moved; classify by reason (duplicate framework diagram, associative classical text, low-yield disease, cross-chapter content, placeholder-image slides, naming history, summary slides, text re-typed tables) and what he adds (concept-vs-disease slides, comparison tables, image slides, exam questions, split early/late). Give counts and slide references.' },
  { id: '38_課別差異', p: 'AUD', f: 'How content and style differ by audience/course code: A1 (醫學系+中醫甲), A2, B1 (中醫乙+學士後中醫), B2 (中醫), C (牙醫三), lab (實驗) and 國考複習 genres. IMPORTANT: first detect which C decks are copies of other decks (compare slide texts), then describe what (if anything) he changes for dental students; exam question types per course; 中醫 content per course; aspect ratio per course; slide counts per hour.' },
  { id: '41_他的原句庫', p: 'QUOTE', f: 'Collect 150-250 VERBATIM lines (titles, bullets, notes) that best characterize his voice, from his own decks and his own additions in the edits (never from mine_* or other_*). Tag each with function: 標題-陳述/標籤/問句/定義, 機轉說明, 形態描述, 考試態度, 課本態度, 幽默, 比喻, 過場, 板書, 國考題評語, 中醫對應. Include deck code + slide number. Write them in a JSON list and also as a markdown table.' },
  { id: '42_改稿前後對照', p: 'EDIT', f: 'Go through all three edit diffs line by line. For EVERY text change produce {mine, his, deck, slide, change_type (retitle, verb, simplify, add-English, delete-detail, fact-fix, split, enlarge, recolour, add-image...), inferred_rule}. Then aggregate into rules. Also produce 43_反例庫: every sentence of mine that he deleted or rewrote, with his replacement, grouped by the reason.' },
]

const results = await pipeline(DIMS,
  (d) => A(`${COMMON}

YOUR DIMENSION: ${d.id} (rule id prefix ${d.p}).
Focus: ${d.f}
Mine the corpus thoroughly for this dimension. Produce (a) statistics tables, (b) 8-30 rules in the RULE FORMAT, strongest first, (c) a list of open questions / conflicting evidence, (d) the specific implications for a NEW 4:3 deck for dental students (course C) on immune diseases, where the user additionally requires: no small fonts, every technical term written as 中文(English), no LLM-style phrasing.
Write JSON to ${W}/${d.id}.json as {"dimension":"${d.id}","stats":[{"name":"...","table_markdown":"..."}],"rules":[...],"open_questions":[...],"implications_immune_dental":[...]}.
Return count = number of rules.`, { label: 'mine:' + d.id, phase: 'Mine' }),
  (m, d) => m && parallel([1, 2].map(k => () => A(`${COMMON}

TASK: adversarial REFUTER #${k} for dimension ${d.id}. Read the candidate rules in ${m.path}.
For EACH rule: (1) verify every quoted example exists verbatim in the cited deck/slide (grep the .txt dump; report any that do not); (2) search the WHOLE corpus for counterexamples in his own decks (not mine_* / other_*) — ${k === 1 ? 'start with the 2026 decks and the edit diffs' : 'start with the 2025 and 2024 decks, the 國考複習 decks and the lab decks'}; (3) check the numbers/thresholds by recomputing them with Python; (4) judge whether level (MUST/SHOULD/...) is justified by the strength of evidence; (5) note rules that conflict with other dimensions known facts in prior_findings.
Also list important patterns in this dimension that the miner missed.
Write ${W}/${d.id}_refute${k}.json: {"rule_verdicts":[{"id":"...","verdict":"confirmed|narrow_scope|lower_level|wrong|bad_quote","evidence":"...","counterexamples":[{"quote":"...","deck":"...","slide":n}],"suggested_fix":"..."}],"missed_patterns":[...]}.
Return count = number of rules not confirmed + missed patterns.`, { label: `refute${k}:${d.id}`, phase: 'Refute' }))),
  (refs, d) => (refs && refs.every(Boolean)) ? A(`${COMMON}

TASK: REVISE dimension ${d.id}. Inputs: miner output ${W}/${d.id}.json ; refutations ${refs.map(r => r.path).join(' and ')}.
Apply every justified refutation (fix quotes, narrow scopes, adjust levels and thresholds, delete wrong rules, add missed patterns as new rules after verifying them in the corpus yourself). Keep ids stable where possible.
Write (1) ${W}/${d.id}_final.json (same schema as the miner output, plus "changelog":[...]) and (2) ${W}/${d.id}_final.md: a complete, LLM-friendly draft of the guide file for this dimension, in Traditional Chinese, with YAML frontmatter (id, scope, last_verified: 2026-09-24, evidence: list of decks), a one-paragraph summary, then each rule as a subsection "### <ID> <instruction>" with fields 等級 / 門檻 / 適用範圍 / 他的正例 / 我的反例 / 機械檢查 / 為什麼 / 證據強度 / 例外, then the statistics tables, then open questions.
Return count = number of final rules.`, { label: 'revise:' + d.id, phase: 'Revise' }) : null,
)

const done = results.filter(Boolean)
log(`style dimensions finished: ${done.length}/${DIMS.length}`)
phase('Brief')
const brief = await A(`${COMMON}

TASK: write the WRITER BRIEF for the immune-disease deck. Read every ${W}/*_final.md (and _final.json where needed).
Target deck: ONE 4:3 file, ~180 slides in three 50-minute periods (~60 slides each, paced to finish in ~40 min), 3rd-year DENTAL students (course code C), Robbins 11e ch.6 is the only canonical source; literature only as cited supplements; dental licensing exam (牙醫師國考) questions embedded next to their topic; normal immunity only a 10-15 slide review. User hard requirements: fonts not small (body 28pt, title 36pt, nothing students read below 20pt, credits 14pt), every technical term 中文(English) on each slide, no LLM-style language.
Write ${ROOT}/style/_work/writer_brief_immune.md (Traditional Chinese, <= 3500 Chinese characters + example lists) with: (1) the 25 most important MUST/NEVER rules for writing slide text (titles, bullets, terms, symbols, tone), each with one of his verbatim examples; (2) RED phrase list and WARN list; (3) title patterns with 10 examples each type; (4) how to write exam-question slides; (5) how to write notes; (6) structure/pacing rules (same-title builds, dividers, opening, ending); (7) 40 verbatim lines of his as voice anchors; (8) a list of my typical mistakes he fixed (mine -> his) as do/don't pairs.
Return count = number of rules in section 1.`, { label: 'brief:writer', phase: 'Brief' })
return { aborted, finished: done.length, brief }

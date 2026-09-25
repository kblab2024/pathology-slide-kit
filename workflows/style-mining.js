export const meta = {
  name: 'style-mining',
  description: 'Mine the teacher\'s slide-style rules from the deck corpus and edit diffs: per dimension one miner, independent refuters, one reviser; then an optional writer brief for a course. Generic: args {kit, materials, course?, dims?, ...}. Opus only.',
  whenToUse: 'When the corpus gained new teacher decks or hand edits, or before a course whose audience or genre the style guide does not cover yet. Feeds workflows/style-guide.js.',
  phases: [
    { title: 'Mine', detail: 'one miner per style dimension' },
    { title: 'Refute', detail: 'independent refuters search the corpus for counterexamples and verify quotes' },
    { title: 'Revise', detail: 'miner-reviser applies refutations, writes <dim>_final.json/.md' },
    { title: 'Brief', detail: 'writer brief for the target course (only when args.course is given)' },
  ],
}

// args: {kit, materials,                        required (absolute paths; forward slashes are safest)
//        course?,                               target course: implications + writer brief for it (optional)
//        dims?,                                 ids of default dimensions to run (e.g. ['12_字級','34_國考題']) or full objects [{id, p, f}]
//        corpus?, out?, date?, refuters?: 2, effort?, done?:{label: output path}}
const A0 = args || {}
const norm = (p) => (p ? String(p).replace(/\\/g, '/').replace(/\/+$/, '') : '')
const MISSING = ['kit', 'materials'].filter(k => !A0[k])
if (MISSING.length) {
  log('style-mining: missing args ' + MISSING.join(', ') + '. Pass {kit: "<path of pathology-slide-kit>", materials: "<path of pathology-slide-materials>", course: "<optional target course>"}; see workflows/README.md.')
  return { error: 'missing args: ' + MISSING.join(', ') }
}
const KIT = norm(A0.kit)
const MAT = norm(A0.materials)
const C = A0.course ? String(A0.course) : ''
const CD = C ? `${MAT}/courses/${C}` : ''
const CORPUS = norm(A0.corpus) || `${MAT}/corpus`
const EV = `${MAT}/style_evidence`
const W = norm(A0.out) || `${EV}/mining`
const DATE = A0.date ? String(A0.date) : '<today: run `date +%F`>'
const REF = Math.max(1, Math.min(3, parseInt(A0.refuters || 2, 10) || 2))
const DONE = Object.assign({}, A0.done || {})
const EFFORT = A0.effort || null
const RET = { type: 'object', properties: { path: { type: 'string' }, count: { type: 'integer' }, notes: { type: 'string' } }, required: ['path', 'count', 'notes'] }
let aborted = false
async function A(prompt, opts) {
  const lab = opts && opts.label
  if (lab && DONE[lab]) { log('reuse (not re-run): ' + lab); return { path: DONE[lab], count: 0, notes: 'reused from previous run' } }
  if (aborted) return null
  const o = { schema: RET, ...opts, model: 'opus' }
  if (EFFORT && !o.effort) o.effort = EFFORT
  const r = await agent(prompt, o)
  if (r === null) { aborted = true; log('ABORT: agent returned null at ' + lab + '; stopping. Resume later with args.done (see workflows/README.md).') }
  return r
}

const TARGET = C
  ? `the target course "${C}": read ${CD}/brief.md and ${CD}/course.yaml (audience, course code, aspect ratio, slide counts, exam bank, font sizes and other explicit teacher instructions)`
  : 'a new deck in general (4:3 and 16:9; note where the course code or audience changes the answer)'
const COMMON = `
Kit (public): ${KIT}. Materials (private): ${MAT}. Run shell commands with the Bash tool (Git Bash on Windows, bash in a cloud session); if "python" is not found use "python3".
We are writing a VERY detailed, LLM-friendly style guide describing how the pathology teacher (the user of these repos) makes lecture slides, so that future LLM sessions can produce decks he will accept with minimal edits.
CORPUS (read ${CORPUS}/index.md first): per-slide dumps of his decks in ${CORPUS}/decks/{code}.json (full detail: shapes, positions in inches, effective font size per run 'sz', colour hex incl. theme colours 'col' + 'col_src', pictures, tables, notes, layout) and {code}.txt (LLM-readable: each paragraph followed by [size pt] and {colour「text」} marks; "===== #n [layout] 圖k" headers; 〔備註〕 = notes). Edit diffs (my draft -> his hand edit) in ${CORPUS}/edits/*.md. Earlier conclusions (to be re-verified, some may be wrong): the current guide ${KIT}/style/guide/ and ${EV}/prior_findings_*.md if present.
AUTHORITY ORDER: his hand edits of my drafts (the edited "after" decks listed in index.md vs mine_*) > his own decks (newest year first) > my drafts (mine_*, counterexamples only) > other authors (other_*, contrast only). index.md marks decks that are only partly his (count only his slides) and decks that duplicate other decks: dedupe before counting and say so.
Use Python (json module over the .json dumps) for counts and distributions; use grep on the .txt dumps for phrases. Every quantitative claim must state its denominator and which decks. Every example quote must be VERBATIM from the dumps with its deck code and slide number (e.g. 2026_A1_發炎一_0917 #25).
RULE FORMAT (JSON objects): {"id":"<DIM-PREFIX>-NN","level":"MUST|SHOULD|MAY|AVOID|NEVER","instruction":"one imperative sentence in Traditional Chinese","threshold":"numeric threshold or null","scope":"which aspect ratio / course / slide type / genre it applies to","examples_his":[{"quote":"...","deck":"...","slide":n}],"counterexamples_mine":[{"quote":"...","source":"mine_... #n or edits/...md","his_fix":"what he changed it to, if any"}],"check":"regex or metric that a script could test, or 'manual'","why":"reason, grounded in evidence","strength":"e.g. 7/9 unique decks, 74 runs","exceptions":"..."}
Write in Traditional Chinese (quotes stay verbatim). Your final answer is just {path, count, notes}.`

const DEFAULT_DIMS = [
  { id: '11_畫幅與版面配置', p: 'LAY', f: 'Aspect ratio per deck/course/year; built-in layouts used vs Blank; share of text in placeholders vs text boxes; backgrounds (colour, images); where titles sit (x,y,w,h distributions); margins; slide numbers (none?); how images and text are arranged (text top + image below, text left + image right, full-bleed); grouping; SmartArt usage; consistency within a deck.' },
  { id: '12_字級', p: 'SIZE', f: 'Effective font-size distributions per ROLE (title, main statement, bullet level 1/2/3, single big sentence, labels on images, table text, exam-question stem/options, captions/credits, citations, divider text, cover) separately for 4:3 and 16:9 and per year. Where sizes are non-integers explain (scaling artefacts). Quantify: share of body characters below 20pt / 24pt per deck; what text is allowed to be small. Evidence of him ENLARGING text when revising (compare versions of the same deck across years, and the edits). Sub-level vs parent sizes.' },
  { id: '13_密度與字數', p: 'DEN', f: 'Characters per slide (median, p90) per deck (dedupe); bullets per slide; bullet length; title length; zero-bullet (title+image) slides; text-only slides; slides per lecture hour (one A1 deck = one 50-min period; he said he never wants to fill the whole period, target about 40 min); how density differs between his own decks and his edits of mine.' },
  { id: '14_色彩與強調', p: 'COL', f: 'Body text colour(s); emphasis colours by role (theme accents incl. ED7D31 orange, 4472C4 blue, rgb 143F9C, FF0000, C0504D, 2E414F, 62A8BB, F79646...), what gets coloured (single words, key phrases, whole lines, exam answers, classical quotes, citations); counts per deck; which colours he adds in edits of my drafts; colours of dividers/backgrounds.' },
  { id: '15_圖片與配對', p: 'IMG', f: 'Picture rate per deck (dedupe); pictures per slide; picture sizes and positions (single right, pair side by side, full width, bleed); picture-only slides; same image repeated across build slides; pairing logic (H&E + IHC, clinical + micro, normal vs lesion, two stains) inferred from captions/labels/text; labels placed on or next to images (e.g. "HE", "Wright-Giemsa") and their size; image sources inferred from captions (textbook, ExpertPath, journals, Wikimedia, webpathology).' },
  { id: '16_出處與引用格式', p: 'CITE', f: 'Extract ALL citation/credit strings (regex: 圖片來源|圖源|資料來源|來源|Robbins|ROBBINS|Fig|圖[0-9]|http|www|doi|PMID|et al|Journal|J\\.|pp\\.|頁|第.章|AD\\)|《) from his decks and classify formats: in title parentheses, label under image, bottom-left 補充來源, full journal references, URLs (case, size), textbook page/figure formats, chapter cross-references, classical-text attributions with dates. Give size and colour of each type, and counts.' },
  { id: '21_標題句式', p: 'TTL', f: 'Classify every title (use title field; for decks without title placeholders the top/biggest text) into: complete statement sentence / label "分類詞：子題(English)" / pure term or disease name / equation "X = Y" / question (with or without answer) / connective-start (不過、因此、所以、然而) / bracket-tail (圖說, 口訣, textbook figure number, 出處) / en dash sub-type "X – Y" / enumerated "之一、之二". Counts per deck; how the same title repeats across build slides; how he rewrote my titles in edits (list every retitle mine -> his and infer rules).' },
  { id: '22_條列與句型', p: 'BUL', f: 'Bullet/sentence patterns: sentence length, levels, parallel structure, plain words before terms (先白話再術語), use of ： labels, lists separated by spaces or 、, colloquialisms he uses vs ones he removes, how he states mechanisms, how he writes morphology, how he writes numbers/percentages, first/second person. Contrast his own bullets with my drafts and his rewrites of them.' },
  { id: '23_禁用語與LLM語', p: 'BAN', f: 'Build evidence-based RED/WARN phrase lists. (1) From edits: phrases/constructions in my drafts that he deleted or rewrote (verbs like 打這裡/打的是/可以回頭, question tails, connectives, dramatic phrasing, metaphors, 「——」, 其一其二...). (2) Candidate LLM phrases (值得注意的是, 不難發現, 讓我們, 總而言之, 綜上所述, 簡而言之, 至關重要, 扮演…角色, 關鍵在於, 深入探討, 揭開…面紗, 不僅…更, 雙面刃, 堪稱, 旨在, 意味著, 本質, 根本, 說穿了, 換句話說, 事實上, 可以說, 核心, 精準, 全方位, 此外, 進而, 從而, 透過...): count each in HIS decks vs MY drafts. A phrase he uses himself cannot be RED (say so). (3) Words he explicitly adopted from my drafts (kept unchanged). Output RED list, WARN list, ALLOWED-though-suspicious list, each with counts.' },
  { id: '24_術語與中英對照', p: 'TERM', f: 'Bilingual formats: 中文(English), 中文 (English), 中文（English）, English(中文), 中文English glued, abbreviations after ; or space, English-only allowed items (stains, markers, gene names, abbreviations). Frequencies per deck and in edits (count the pairs he added). Build a GLOSSARY of his own Chinese renderings of pathology terms found in the corpus (Chinese | English | deck/slide), covering every topic in the corpus and, when a target course is given, its topic first. Note his known typos (白班, cilitated, Sjogren) and term decisions (分化不良, uppercase P53/P16/P40/P63).' },
  { id: '25_符號與標點', p: 'SYM', f: 'Counts and usage of: => , -> , → , = (definitions), ： vs : , half-width vs full-width parentheses, spaces used as pauses (核大 核黑 核不規則), / , ？, …, 「」, 『』, en dash –, em dash —, 「——」, bullets characters, numbering styles, full-width digits. Per deck and in his edits of mine.' },
  { id: '26_語氣與態度', p: 'TONE', f: 'His voice: attitude toward exams (直白), toward the textbook, humor, admissions of uncertainty, rhetorical questions and how answered, 我們/你們 usage, encouragement, warnings, board instructions, statements of importance ("國考重要性：低"). Collect verbatim examples from slides AND notes with deck/slide. Contrast with the tone of my drafts that he removed.' },
  { id: '31_開場與結尾', p: 'OPEN', f: 'For every unique lecture deck: list the first 10 slides and last 5 slides (titles + type). Derive patterns: cover format (title text, subtitle, credits like 部分圖片感謝...), presence/absence of objectives/agenda/review, orientation slides, first exam question position, how the first topic starts, cliffhanger endings, no summary/thanks.' },
  { id: '32_段落節奏與同標題連張', p: 'RHY', f: 'Same-title consecutive runs (length distribution, % of slides, what changes between builds: one more bullet, new image, arrow moves, recoloured SmartArt); segment lengths (slides per topic); alternation of text and picture slides; question -> answer slide pairs; how mechanism explanations are paced; build devices he uses (SmartArt recolour, moving arrow, same image repeated).' },
  { id: '33_divider', p: 'DIV', f: 'Identify divider/section slides (標題投影片 layout, big centered text, "Section N" labels, dark backgrounds, 45-60pt topic): wording type (noun phrase, sentence, suspense/rhetorical sentence, question), subtitles, sizes/colours, frequency per deck, and how he changed my dividers in edits.' },
  { id: '34_國考題', p: 'EXAM', f: 'All exam-question slides in the corpus (regex 國考|專技|年第.次|題[)）]?|\\(A\\)|（A）|[A-D]\\s*\\|): formats (1-row 3-column table; title "107年第二次專技 78題" + large stem; one option per line; answer colouring blue 143F9C / orange F79646 / none; answer-key slide after, e.g. a textbook page), sizes, placement relative to topic, counts per deck, 醫師 vs 牙醫師 vs 中醫 (中醫臨床) questions and his commentary lines, how the 國考複習 decks teach exam content, and slides where he rates exam importance (e.g. "國考重要性：低").' },
  { id: '35_中醫與古籍', p: 'TCM', f: 'Every classical Chinese medicine text slide (傷寒, 金匱, 溫熱論, 素問, 靈樞, 難經, 方證, 湯證): format (as title, as subtitle, quote + => modern mechanism), colours (light blue ACCENT_5, blue), sizes, date attributions, placement (premise before framework vs aside), which ones he deleted from my drafts (associative) vs kept/added (explanatory), 中醫國考 questions with 方證 comments.' },
  { id: '36_備註', p: 'NOTE', f: 'Notes coverage per deck (dedupe), length distribution, content types (spoken script, board instructions （板書）, English pastes from Wikipedia/the textbook, exam comments, leftovers copied from other slides), language; whether he ever edits my notes (compare edits); recommendations for what notes an LLM should write for him.' },
  { id: '37_刪張與留張', p: 'CUT', f: 'From the edit diffs: every slide he deleted, added, split, merged or moved; classify by reason (duplicate framework diagram, associative classical text, low-yield disease, cross-chapter content, placeholder-image slides, naming history, summary slides, text re-typed tables) and what he adds (concept-vs-disease slides, comparison tables, image slides, exam questions, split early/late). Give counts and slide references.' },
  { id: '38_課別差異', p: 'AUD', f: 'How content and style differ by audience/course code: A1 (醫學系+中醫甲), A2, B1 (中醫乙+學士後中醫), B2 (中醫), C (牙醫), lab (實驗) and 國考複習 genres. IMPORTANT: first detect which decks for one course code are copies of decks for another (compare slide texts), then describe what (if anything) he changes for each audience; exam question types per course; 中醫 content per course; aspect ratio per course; slide counts per hour.' },
  { id: '41_他的原句庫', p: 'QUOTE', f: 'Collect 150-250 VERBATIM lines (titles, bullets, notes) that best characterize his voice, from his own decks and his own additions in the edits (never from mine_* or other_*). Tag each with function: 標題-陳述/標籤/問句/定義, 機轉說明, 形態描述, 考試態度, 課本態度, 幽默, 比喻, 過場, 板書, 國考題評語, 中醫對應. Include deck code + slide number. Write them in a JSON list and also as a markdown table.' },
  { id: '42_改稿前後對照', p: 'EDIT', f: 'Go through every edit diff line by line. For EVERY text change produce {mine, his, deck, slide, change_type (retitle, verb, simplify, add-English, delete-detail, fact-fix, split, enlarge, recolour, add-image...), inferred_rule}. Then aggregate into rules. Also produce 43_反例庫: every sentence of mine that he deleted or rewrote, with his replacement, grouped by the reason.' },
]
let DIMS = DEFAULT_DIMS
if (Array.isArray(A0.dims) && A0.dims.length) {
  DIMS = A0.dims.map(d => (typeof d === 'string' ? DEFAULT_DIMS.find(x => x.id === d || x.id.startsWith(d + '_') || x.p === d) : d)).filter(Boolean)
  if (DIMS.length < A0.dims.length) log('some args.dims were not recognised (use ids like "12_字級", prefixes like "SIZE", or full {id, p, f} objects)')
  log(`mining ${DIMS.length}/${DEFAULT_DIMS.length} dimensions: ${DIMS.map(d => d.id).join(', ')}`)
}
if (!DIMS.length) { log('no dimensions to mine'); return { error: 'no dims' } }
const KS = Array.from({ length: REF }, (_, i) => i + 1)
const REFUTER_START = ['start with the newest decks and the edit diffs', 'start with the oldest decks, the 國考複習 decks and the lab decks', 'start with the decks for course codes other than the target course, then the duplicates']

const results = await pipeline(DIMS,
  (d) => A(`${COMMON}

YOUR DIMENSION: ${d.id} (rule id prefix ${d.p}).
Focus: ${d.f}
Mine the corpus thoroughly for this dimension. Produce (a) statistics tables, (b) 8-30 rules in the RULE FORMAT, strongest first, (c) a list of open questions / conflicting evidence, (d) the specific implications for ${TARGET}.
Write JSON to ${W}/${d.id}.json as {"dimension":"${d.id}","stats":[{"name":"...","table_markdown":"..."}],"rules":[...],"open_questions":[...],"implications_target":[...]}.
Return count = number of rules.`, { label: 'mine:' + d.id, phase: 'Mine' }),
  (m, d) => m && parallel(KS.map(k => () => A(`${COMMON}

TASK: adversarial REFUTER #${k} for dimension ${d.id}. Read the candidate rules in ${m.path}.
For EACH rule: (1) verify every quoted example exists verbatim in the cited deck/slide (grep the .txt dump; report any that do not); (2) search the WHOLE corpus for counterexamples in his own decks (not mine_* / other_*); ${REFUTER_START[(k - 1) % REFUTER_START.length]}; (3) check the numbers/thresholds by recomputing them with Python; (4) judge whether level (MUST/SHOULD/...) is justified by the strength of evidence; (5) note rules that conflict with other dimensions or with the earlier conclusions.
Also list important patterns in this dimension that the miner missed.
Write ${W}/${d.id}_refute${k}.json: {"rule_verdicts":[{"id":"...","verdict":"confirmed|narrow_scope|lower_level|wrong|bad_quote","evidence":"...","counterexamples":[{"quote":"...","deck":"...","slide":n}],"suggested_fix":"..."}],"missed_patterns":[...]}.
Return count = number of rules not confirmed + missed patterns.`, { label: `refute${k}:${d.id}`, phase: 'Refute' }))),
  (refs, d) => (refs && refs.every(Boolean)) ? A(`${COMMON}

TASK: REVISE dimension ${d.id}. Inputs: miner output ${W}/${d.id}.json ; refutations ${refs.map(r => r.path).join(' and ')}.
Apply every justified refutation (fix quotes, narrow scopes, adjust levels and thresholds, delete wrong rules, add missed patterns as new rules after verifying them in the corpus yourself). Keep ids stable where possible.
Write (1) ${W}/${d.id}_final.json (same schema as the miner output, plus "changelog":[...]) and (2) ${W}/${d.id}_final.md: a complete, LLM-friendly draft of the guide file for this dimension, in Traditional Chinese, with YAML frontmatter (id, scope, last_verified: ${DATE}, evidence: list of decks), a one-paragraph summary, then each rule as a subsection "### <ID> <instruction>" with fields 等級 / 門檻 / 適用範圍 / 他的正例 / 我的反例 / 機械檢查 / 為什麼 / 證據強度 / 例外, then the statistics tables, then open questions.
Return count = number of final rules.`, { label: 'revise:' + d.id, phase: 'Revise' }) : null,
)

const done = results.filter(Boolean)
log(`style dimensions finished: ${done.length}/${DIMS.length}`)
if (!C) { log('no args.course: writer brief skipped. Next: workflows/style-guide.js'); return { aborted, finished: done.length } }
if (aborted) return { aborted, finished: done.length }
phase('Brief')
const brief = await A(`${COMMON}

TASK: write the WRITER BRIEF for course "${C}". Read every ${W}/*_final.md (and _final.json where needed) and the current guide ${KIT}/style/guide/ (00_README.md first).
Target deck: as described in ${CD}/brief.md and ${CD}/course.yaml (aspect ratio, slide count per period, audience and course code, canonical textbook, literature policy, exam bank and quiz count, font sizes, bilingual rule). Treat the teacher's explicit instructions there as course-scoped MUST rules.
Write ${EV}/writer_brief_${C}.md (Traditional Chinese, <= 3500 Chinese characters + example lists) with: (1) the 25 most important MUST/NEVER rules for writing slide text (titles, bullets, terms, symbols, tone), each with one of his verbatim examples; (2) RED phrase list and WARN list; (3) title patterns with 10 examples each type; (4) how to write exam-question slides for this course's exam; (5) how to write notes; (6) structure/pacing rules (same-title builds, dividers, opening, ending); (7) 40 verbatim lines of his as voice anchors; (8) a list of my typical mistakes he fixed (mine -> his) as do/don't pairs.
Return count = number of rules in section 1.`, { label: 'brief:writer', phase: 'Brief' })
return { aborted, finished: done.length, brief }

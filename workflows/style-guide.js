export const meta = {
  name: 'style-guide',
  description: 'Write the LLM-friendly teacher style guide style/guide/ from the verified style-mining dimensions: per-file writers -> consistency + completeness critics -> revisers -> index / checklists / rules.yaml. Generic: args {kit, materials, course?, ...}. Opus only.',
  whenToUse: 'After style-mining (or after new teacher edits were mined): rebuild or update the public style guide and style/rules.yaml.',
  phases: [
    { title: 'Write', detail: 'one writer per guide file; quotes verified with scripts/verify_quotes.py' },
    { title: 'Critique', detail: 'consistency critic + completeness critic over the whole guide' },
    { title: 'Revise', detail: 'revise files the critics flagged' },
    { title: 'Index', detail: '00_README, 01_權威順序, 50_檢查, 90_證據索引, style/rules.yaml' },
  ],
}

// args: {kit, materials,                        required (absolute paths; forward slashes are safest)
//        course?,                               newest course whose decisions and review lessons should be folded in (optional)
//        date?: 'YYYY-MM-DD',                   last_verified date written into the frontmatter (default: ask the shell)
//        files?: ['12_字級', ...],               only (re)write these guide files (matched by file name); critics and index still see the whole guide
//        mining?, corpus?, effort?, done?:{label: output path}}
const A0 = args || {}
const norm = (p) => (p ? String(p).replace(/\\/g, '/').replace(/\/+$/, '') : '')
const MISSING = ['kit', 'materials'].filter(k => !A0[k])
if (MISSING.length) {
  log('style-guide: missing args ' + MISSING.join(', ') + '. Pass {kit: "<path of pathology-slide-kit>", materials: "<path of pathology-slide-materials>", course: "<optional course folder name>"}; see workflows/README.md.')
  return { error: 'missing args: ' + MISSING.join(', ') }
}
const KIT = norm(A0.kit)
const MAT = norm(A0.materials)
const C = A0.course ? String(A0.course) : ''
const CD = C ? `${MAT}/courses/${C}` : ''
const G = `${KIT}/style/guide`
const EV = `${MAT}/style_evidence`
const M = norm(A0.mining) || `${EV}/mining`
const CORPUS = norm(A0.corpus) || `${MAT}/corpus`
const REVIEW = `${EV}/guide_review`
const DATE = A0.date ? String(A0.date) : '<today: run `date +%F`>'
const DONE = Object.assign({}, A0.done || {})
const EFFORT = A0.effort || null
const ENVVARS = `SLIDEKIT_MATERIALS="${MAT}"${A0.corpus ? ` SLIDEKIT_CORPUS="${CORPUS}"` : ''} PYTHONIOENCODING=utf-8`
const RUN = `cd "${KIT}/scripts" && ${ENVVARS} python`
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

const VERIFY = `${RUN} verify_quotes.py`
const COURSE_LESSONS = C ? `
ALSO record what the newest course built under these rules taught us (course "${C}"): ${CD}/course.yaml (font sizes the teacher asked for, slide types, diagrams), ${CD}/brief.md (teacher decisions), ${CD}/glossary.md (bilingual rule), ${KIT}/scripts/README.md (pipeline), ${CD}/_archive/review/ (review findings), ${CD}/成品/待教師裁決清單.md if present. Mark such items as「使用者（教師）明令」with the date when they are his explicit instructions for that course rather than habits observed in his decks, and scope them to that course.` : ''
const CTX = `
Kit (public): ${KIT}. Materials (private): ${MAT}. Run shell commands with the Bash tool (Git Bash on Windows, bash in a cloud session); if "python" is not found use "python3".
PURPOSE: a very detailed, LLM-friendly style guide describing how the pathology teacher (the user of these repos) builds lecture slides, so that any future LLM session can produce decks he accepts with minimal edits. Audience = LLMs first, the teacher second. Written in Traditional Chinese (台灣用語).
EVIDENCE (already mined, refuted and revised; reuse it, do not re-mine from scratch): ${M}/<dim>_final.md and <dim>_final.json (one pair per dimension), the course writer briefs ${EV}/writer_brief_*.md, prior findings ${EV}/prior_findings_*.md if present, the corpus index ${CORPUS}/index.md, per-slide dumps ${CORPUS}/decks/<code>.txt and .json, edit diffs ${CORPUS}/edits/*.md. The current guide in ${G} is the previous version: keep what the evidence supports.${COURSE_LESSONS}
PUBLIC REPOSITORY: ${G} and ${KIT}/style/rules.yaml are published openly. Quote only the teacher's own slides and his hand edits (never other authors' slides: write 〔他人投影片引句，公開版省略；完整版在私人素材庫 style_evidence〕 instead of their text; name colleagues only by the pseudonyms listed in ${MAT}/corpus/pseudonyms.tsv, e.g. 同事甲, or generically, e.g. 他人舊張), never copy textbook text beyond a short term or heading, and write no absolute local paths, e-mail addresses, phone numbers, student data or teaching-evaluation data. Refer to evidence by repository-relative paths such as materials/corpus/decks/<code>.txt or materials/style_evidence/mining/<dim>_final.md. Before finishing, run: cd "${KIT}/scripts" && SLIDEKIT_MATERIALS="${MAT}" PYTHONIOENCODING=utf-8 python check_public.py and fix every FAIL in the files you wrote.
AUTHORITY ORDER (state it wherever rules conflict): his hand edits of my drafts > his own decks, newest year first > his explicit instructions for a specific course (course-scoped) > my drafts (counterexamples only) > other authors.
FIXED RULE FORMAT (every rule, no exceptions):
### <ID> <一句話指令>
- 等級：MUST／SHOULD／MAY／AVOID／NEVER
- 門檻：<numbers or 無>
- 適用範圍：<aspect ratio / course code / slide type / genre>
- 他的正例：「原文」（<corpus code> #<slide>）… (verbatim, 1-4 examples)
- 我的反例：「原文」（<corpus code> #<slide>）→ 他改成「…」（<code> #<slide>）… (when evidence exists)
- 機械檢查：<regex / metric / manual>（對應 style/rules.yaml id，若有）
- 為什麼：…
- 證據強度：<counts with denominators, deduped decks>
- 例外：…
QUOTE FORMAT is mandatory for every verbatim example: 「原文」（代號 #張號）, e.g. 「炎 = 火 + 火」（2026_A1_發炎一_0917 #39）. Only quote what really exists; run \`${VERIFY} <your file>\` and fix every FAIL before returning.
Each file starts with YAML frontmatter: id, title, scope, last_verified: ${DATE}, evidence (list of corpus codes), related (other guide files). Then: 一段摘要 → 規則（strongest first）→ 統計表 → 常見錯誤 → 待教師確認的問題. Use the rule-id prefix of the dimension (LAY, SIZE, DEN, COL, IMG, CITE, TTL, BUL, BAN, TERM, SYM, TONE, OPEN, RHY, DIV, EXAM, TCM, NOTE, CUT, AUD, QUOTE, EDIT). No 「——」 anywhere; follow the guide's own banned-language rules in your prose. UTF-8, LF line endings.`

const ALL_FILES = [
  ['10_版面/11_畫幅與版面配置.md', ['11_畫幅與版面配置']],
  ['10_版面/12_字級.md', ['12_字級']],
  ['10_版面/13_密度與字數.md', ['13_密度與字數']],
  ['10_版面/14_色彩與強調.md', ['14_色彩與強調']],
  ['10_版面/15_圖片與配對.md', ['15_圖片與配對']],
  ['10_版面/16_出處與引用格式.md', ['16_出處與引用格式']],
  ['20_文字/21_標題句式.md', ['21_標題句式']],
  ['20_文字/22_條列與句型.md', ['22_條列與句型']],
  ['20_文字/23_禁用語與LLM語.md', ['23_禁用語與LLM語']],
  ['20_文字/24_術語與中英對照.md', ['24_術語與中英對照']],
  ['20_文字/25_符號與標點.md', ['25_符號與標點']],
  ['20_文字/26_語氣與態度.md', ['26_語氣與態度']],
  ['30_結構/31_開場與結尾.md', ['31_開場與結尾']],
  ['30_結構/32_段落節奏與同標題連張.md', ['32_段落節奏與同標題連張']],
  ['30_結構/33_divider.md', ['33_divider']],
  ['30_結構/34_國考題.md', ['34_國考題']],
  ['30_結構/35_中醫與古籍.md', ['35_中醫與古籍']],
  ['30_結構/36_備註.md', ['36_備註']],
  ['30_結構/37_刪張與留張.md', ['37_刪張與留張']],
  ['30_結構/38_課別差異.md', ['38_課別差異']],
  ['40_範例/41_他的原句庫.md', ['41_他的原句庫']],
  ['40_範例/42_改稿前後對照.md', ['42_改稿前後對照']],
  ['40_範例/43_反例庫.md', ['42_改稿前後對照', '23_禁用語與LLM語']],
]
const PICK = Array.isArray(A0.files) && A0.files.length ? A0.files : null
const FILES = PICK ? ALL_FILES.filter(([f]) => PICK.some(p => f.includes(p))) : ALL_FILES
if (PICK) log(`writing ${FILES.length}/${ALL_FILES.length} guide files (args.files): ${FILES.map(f => f[0]).join(', ')}`)
if (!FILES.length) { log('args.files matched no guide file'); return { error: 'no files' } }

phase('Write')
const written = await pipeline(FILES, ([file, dims]) => A(`${CTX}

TASK: write ${G}/${file}. Primary evidence: ${dims.map(d => `${M}/${d}_final.md and ${M}/${d}_final.json`).join(' ; ')}. Carry over EVERY verified rule, statistic and example from the evidence (this file must be at least as detailed as the evidence, not a summary of it); fix anything the evidence's changelog marked wrong; add the course lessons that belong to this topic. If ${G}/${file} already exists, start from it and keep every rule the evidence still supports (keep rule ids stable).
${file.includes('41_') ? 'This file is the quote bank: keep 150-250 verbatim lines grouped by function (標題-陳述/標籤/問句/定義, 機轉說明, 形態描述, 考試態度, 課本態度, 幽默, 比喻, 過場, 板書, 國考題評語, 中醫對應), each in the quote format.' : ''}${file.includes('42_') ? 'List every change in the edit diffs as a table row: 我寫的 | 他改成的 | 類型 | 推出的規則 (with slide refs), then the aggregated rules.' : ''}${file.includes('43_') ? 'Counterexample bank: every sentence of mine he deleted or rewrote, grouped by reason, each with his replacement when one exists, plus the LLM-language patterns that must never appear.' : ''}
Create folders as needed (UTF-8, LF line endings). Run ${VERIFY} "${G}/${file}" until FAIL = 0.
Return count = number of rules (or quotes/rows for 40_範例 files).`, { label: 'write:' + file, phase: 'Write' }))

if (written.filter(Boolean).length < FILES.length) return { aborted, written }

phase('Critique')
const [cons, comp] = await parallel([
  () => A(`${CTX}

TASK: CONSISTENCY CRITIC for the whole guide ${G} (all files under 10_版面, 20_文字, 30_結構, 40_範例). Find: rules in different files that contradict each other (quote both), duplicated rules that should live in one file and be cross-referenced, inconsistent thresholds or terminology, rule IDs reused, rules whose level does not match their evidence strength, prose that violates the guide's own banned-language rules, anything that must not be in a public repository (see PUBLIC REPOSITORY above).
Write ${REVIEW}/consistency.json: {"issues":[{"file":"...","rule_id":"...","problem":"...","fix":"exact instruction"}]}. Return count = number of issues.`, { label: 'critic:consistency', phase: 'Critique' }),
  () => A(`${CTX}

TASK: COMPLETENESS CRITIC for the whole guide ${G}. Compare against the evidence in ${M} (every *_final.json rule and statistic), the writer briefs, prior findings and the corpus: list anything an LLM would need to build a deck he accepts that is missing or too vague (missing rules, missing numbers, missing examples, uncovered slide types, missing guidance for 4:3 vs 16:9, for each course code, for exam formats of 醫師／牙醫師／中醫師, for images and citations, for notes). Also list evidence items not reflected anywhere.
Write ${REVIEW}/completeness.json: {"issues":[{"file":"...","missing":"...","evidence":"where it is","fix":"exact instruction"}]}. Return count = number of issues.`, { label: 'critic:completeness', phase: 'Critique' }),
])

phase('Revise')
const revised = await pipeline(FILES, ([file]) => A(`${CTX}

TASK: REVISE ${G}/${file} using the critics' issues that concern this file: ${cons ? cons.path : '(consistency critic missing)'} ; ${comp ? comp.path : '(completeness critic missing)'} (read both; apply only the issues whose "file" is this file or which explicitly require a change here). If nothing applies, make no changes. Keep the fixed rule format; re-run ${VERIFY} "${G}/${file}" until FAIL = 0. Append a short 「修訂紀錄」 section.
Return count = number of issues applied.`, { label: 'revise:' + file, phase: 'Revise' }))

phase('Index')
const idx = await A(`${CTX}

TASK: write the entry and index files of the guide, and the machine-readable rules.
1. ${G}/00_README.md: 讀法 (for an LLM: which files to read first for which task: new deck, editing his deck, checking a deck), 適用範圍, 檔案地圖 (every file with one line), 規則格式說明, 版本與更新規則 (how to add evidence when he edits a new deck: dump with scripts/dump_pptx.py, diff with scripts/diff_decks.py, re-run workflows/style-mining.js for the affected dimensions, then workflows/style-guide.js with args.files, re-run verify_quotes), and a 10-line 「最重要的規則」 digest with rule ids.
2. ${G}/01_權威順序.md: the authority order with reasons and worked examples of conflicts actually found (e.g. old rules overturned by newer evidence; course instructions vs habits).
3. ${G}/50_檢查/51_撰寫前檢查清單.md and 52_交付前檢查清單.md: checklists as numbered items, each pointing to rule ids and to the script that checks it (scripts/check_deck.py, style_check.py, check_written.py, validate_blueprint.py, verify_quotes.py).
4. ${G}/90_證據索引.md: corpus list (from ${CORPUS}/index.md; codes, not local paths), dump/diff scripts, statistics sources, dates, and where each dimension's raw evidence lives (materials/style_evidence/mining, private repository).
5. Regenerate ${KIT}/style/rules.yaml from all MUST/NEVER/AVOID rules that have a regex or count check: keep the existing ids and entries of the current file (scripts/style_check.py and check_written.py depend on them; read it first), add new entries with the guide's rule ids, fields id, level (RED for MUST/NEVER, WARN for SHOULD/AVOID), scope, kind (phrase/regex/count), pattern, max, message, example_bad, example_ok, evidence. Validate: python -c "import yaml;yaml.safe_load(open(r'${KIT}/style/rules.yaml',encoding='utf-8'))"${C ? ` and run ${RUN} style_check.py --course ${C} (it must still run; report its RED/WARN counts; do not weaken rules to make the course deck pass, list conflicts instead)` : ''}.
6. Run ${VERIFY} over the whole guide (${VERIFY} "${G}"); fix any FAIL. Finally grep ${G} and rules.yaml for 「——」, absolute local paths (drive letters, /home/, /Users/) and e-mail addresses; remove any hit.
Return count = number of rules in rules.yaml; notes = verify_quotes totals and style_check result.`, { label: 'index', phase: 'Index' })
return { aborted, written: written.filter(Boolean).length, revised: revised.filter(Boolean).length, idx }

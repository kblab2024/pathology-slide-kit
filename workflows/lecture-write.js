export const meta = {
  name: 'lecture-write',
  description: 'Write slide text for a blueprinted deck: per batch writer -> 3 checkers (facts / teacher voice / terms+density) -> reviser; then a cross-batch continuity editor. Generic: args {kit, materials, course, ...}. Opus only.',
  whenToUse: 'After lecture-blueprint and scripts/make_batches.py: turn blueprint.json into written batch files for scripts/merge_written.py and assemble.py.',
  phases: [
    { title: 'Load', detail: 'read the batches file when args.batches is not given' },
    { title: 'Write', detail: 'one writer per batch (~16 slides)' },
    { title: 'Check', detail: 'facts vs the textbook, teacher voice / LLM language, bilingual terms + density' },
    { title: 'Revise', detail: 'apply checks, run scripts/check_written.py until RED 0' },
    { title: 'Continuity', detail: 'read the whole deck in order, fix cross-batch issues' },
  ],
}

// args: {kit, materials, course,               required (absolute paths; forward slashes are safest)
//        blueprint?, out?,                     default <course>/_archive/blueprint/blueprint.json, <course>/_archive/written
//        batches? | batches_file?,             batches from scripts/make_batches.py (inline array, or the JSON file; default <out>/batches.json)
//        writer_brief?, pages?, effort?, done?:{label: output path}}
const A0 = args || {}
const norm = (p) => (p ? String(p).replace(/\\/g, '/').replace(/\/+$/, '') : '')
const MISSING = ['kit', 'materials', 'course'].filter(k => !A0[k])
if (MISSING.length) {
  log('lecture-write: missing args ' + MISSING.join(', ') + '. Pass {kit: "<path of pathology-slide-kit>", materials: "<path of pathology-slide-materials>", course: "<folder name under materials/courses>"}; see workflows/README.md.')
  return { error: 'missing args: ' + MISSING.join(', ') }
}
const KIT = norm(A0.kit)
const MAT = norm(A0.materials)
const C = String(A0.course)
const CD = `${MAT}/courses/${C}`
const G = `${KIT}/style/guide`
const BP = norm(A0.blueprint) || `${CD}/_archive/blueprint/blueprint.json`
const OUT = norm(A0.out) || `${CD}/_archive/written`
const WB = norm(A0.writer_brief) || `${MAT}/style_evidence/writer_brief_${C}.md`
const DONE = Object.assign({}, A0.done || {})
const EFFORT = A0.effort || null
const RUN = `cd "${KIT}/scripts" && SLIDEKIT_MATERIALS="${MAT}" PYTHONIOENCODING=utf-8 python`
const PAGES = A0.pages ? norm(A0.pages) : `the folder printed by: ${RUN} -c "from common import load_course; print(load_course('${C}').textbook_path())"`
const RET = { type: 'object', properties: { path: { type: 'string' }, count: { type: 'integer' }, notes: { type: 'string' } }, required: ['path', 'count', 'notes'] }
const JTXT = { type: 'object', properties: { ok: { type: 'boolean' }, json_text: { type: 'string' }, notes: { type: 'string' } }, required: ['ok', 'json_text', 'notes'] }
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

const ENV = `
Kit (public tools, style guide, templates, question banks): ${KIT}. Materials (private course files, textbook pages, corpus): ${MAT}. Course folder: ${CD}.
Run shell commands with the Bash tool (Git Bash on Windows, bash in a cloud session); if "python" is not found use "python3". Kit scripts are called as: ${RUN} <script>.py --course ${C} ...`

let BATCHES = Array.isArray(A0.batches) ? A0.batches : (A0.batches && Array.isArray(A0.batches.batches) ? A0.batches.batches : null)
if (!BATCHES) {
  phase('Load')
  const BF = norm(A0.batches_file) || `${OUT}/batches.json`
  const lj = await agent(`${ENV}

TASK (mechanical; do not create or change any file): return the content of the batches file ${BF} (written by scripts/make_batches.py).
Run: PYTHONIOENCODING=utf-8 python -c "import json,sys; print(json.dumps(json.load(open(sys.argv[1], encoding='utf-8')), ensure_ascii=False))" "${BF}"
Return ok=true and json_text = the printed line, copied exactly. If the file is missing or is not valid JSON, return ok=false, json_text="" and explain in notes (e.g. run ${RUN} make_batches.py "${BP}" "${BF}" first).`, { label: 'load:batches', phase: 'Load', schema: JTXT, model: 'opus', effort: 'low' })
  if (!lj || !lj.ok) { log('could not load batches from ' + BF + ': ' + (lj ? lj.notes : 'agent returned null')); return { error: 'no batches', notes: lj ? lj.notes : null } }
  try { const d = JSON.parse(lj.json_text); BATCHES = Array.isArray(d) ? d : d.batches } catch (e) { log('batches file is not valid JSON: ' + e); return { error: 'bad batches json' } }
}
if (!BATCHES || !BATCHES.length) { log('no batches: pass args.batches or run scripts/make_batches.py'); return { error: 'no batches' } }
log(`course ${C}: ${BATCHES.length} batches, ${BATCHES.reduce((n, b) => n + (b.slugs || []).length, 0)} slides; blueprint ${BP}`)

const CHECK = `${RUN} check_written.py --course ${C} --blueprint "${BP}"`
const READ = `${ENV}
READ FIRST: ${CD}/brief.md (the teacher's decisions and constraints for this course) and ${CD}/course.yaml (font sizes, slide types, bilingual scope and bilingual_whitelist, decks and exam bank).
How the teacher writes slides: the style guide ${G}/ (entry 00_README.md). Before writing read 50_檢查/51_撰寫前檢查清單.md, 20_文字/21_標題句式.md, 22_條列與句型.md, 23_禁用語與LLM語.md, 24_術語與中英對照.md, 25_符號與標點.md, 26_語氣與態度.md, 30_結構/34_國考題.md, 36_備註.md, 40_範例/41_他的原句庫.md, 42_改稿前後對照.md, 43_反例庫.md. Course writer brief (RED/WARN phrase lists, his verbatim lines, my typical mistakes he fixed), if the file exists: ${WB}.
Glossary (the ONLY allowed Chinese renderings; 禁用變體 must not appear): ${CD}/glossary.md. Output format: ${KIT}/templates/written.schema.json. Layout capacity per slide type: the table in ${KIT}/scripts/README.md (measured at 28pt body; scale it to the sizes in course.yaml).
Blueprint: ${BP} (each slide: type, img, fact_ids, lit_ids, quiz, brief, build). Facts: ${CD}/facts/facts_R.json (the canonical textbook named in course.yaml textbook.ref, the ONLY canonical source; look facts up by id; each fact has its printed page), ${CD}/facts/facts_X.json (verified literature claims with slide_cite). Textbook page images: ${PAGES} (files pNN_PPP.jpg or .png, PPP = printed page, NN = PDF page; .txt = OCR; _a/_b half pages when present). Exam bank: ${KIT}/question_banks/<bank>/*.json with <bank> = decks.<deck>.question_bank in course.yaml (key 年度-第幾次#題號; in the 醫師 bank only 題號 76-100 are pathology).
HARD RULES:
1. Every statement must rest on the slide's fact_ids (textbook) or lit_ids (literature). Never add facts from memory. Literature only supplements; it never replaces or contradicts a textbook statement; a slide using literature puts the short citation in "src" (rendered bottom-left as 資料來源：…, e.g. "J Periodontol. 2019;90(1):23-30.") and the full reference in "handout".
2. Bilingual terms follow the bilingual scope in course.yaml bilingual: per_slide (a course mandate such as immune) = every technical term on every slide is written 中文(English); first_per_deck (the default when the key is absent; style guide 24 TERM-07) = 中文(English) the first time a term appears in the deck, later slides may use the Chinese alone; off = no bilingual rule. brief.md may state the teacher's rule for this course. Always use the glossary rendering (abbreviation after a semicolon when useful, e.g. 鱗狀細胞癌(squamous cell carcinoma; SCC)); bare symbols listed in course.yaml bilingual_whitelist need no Chinese; 禁用變體 never appear. Terms missing from the glossary: use a standard Taiwanese rendering and list them in "glossary_additions" [{zh, en, abbr, page}].
3. Large fonts mean few words: title <= 2 lines (about 34 Chinese characters incl. English at 36pt); new slides 0-3 bullets, each <= about 30 characters; visible characters per slide <= sizes.char_warn in course.yaml (hard max sizes.char_red); a left-with-image text column holds about 10 Chinese characters per line at 28pt; flash/pair/robbins <= 2 short lines; big = 1-3 short sentences; table cells short phrases. Same-title build runs: identical titles, each slide adds one step.
4. No LLM language (23_禁用語與LLM語 and the writer brief RED/WARN lists): no 「——」, no 值得注意的是/讓我們/總而言之/扮演…角色/關鍵在於/不僅…更/本質/根本/換句話說, no stage directions, no dramatic second person, no device metaphors; no colloquial verbs he removed (打這裡、打的是、可以回頭的); no question tails in titles; titles do not start with 不過，/然而，. Use his devices sparingly: "=>" (at most about 1 per 15 slides), 「X = Y」 definitions, 「：」 labels, spaces as pauses, bracketed cross-references like (與第二型不同).
5. Emphasis markup only: [[藍:…]] = the one thing to remember on this slide (at most one per slide), [[橘:…]] keywords, [[紅:…]] single-word emphasis (colours in course.yaml emphasis). No Markdown.
6. Quiz slides: title "國考題" (the renderer builds the exam label), no bullets; optional "quiz_note" = one short line in his voice pointing to the textbook page that answers it. Verify the official answer against the textbook; if they disagree, keep the official answer and record it in "issues".
7. Notes ("notes"): short: textbook printed page(s) + 1-2 spoken sentences or a （板書） instruction, in his plain voice. Divider/title slides: bullets are subtitles (divider: noun phrases, at most 1 short line).`

phase('Write')
const results = await pipeline(BATCHES,
  (b) => A(`${READ}

TASK: WRITE batch ${b.k}: slides ${b.slugs.join(', ')} (in this order; segments ${(b.segments || []).join(', ')}). The slide before this batch is ${b.prev || '(none)'} and the one after is ${b.next || '(none)'}; read their blueprint briefs so transitions connect.
For each slide read its blueprint entry, its facts (and look at the textbook page image when wording matters), its assigned image(s) (open them with Read so the text matches what is shown; pair slides get one short line), then write title / bullets / table_rows / src / notes / handout (/ quiz_note for quiz slides).
Write ${OUT}/batch_${b.k}_draft.json as {"batch":${b.k},"slides":[...],"glossary_additions":[...],"issues":[...]}. Then run: ${CHECK} "${OUT}/batch_${b.k}_draft.json" and fix every RED (and WARNs where possible) before returning.
Return count = number of slides written.`, { label: 'write:' + b.k, phase: 'Write' }),
  (w, b) => w && parallel([
    () => A(`${READ}

TASK: FACT CHECK batch ${b.k} (${w.path}). For every slide and every sentence: is it supported by the slide's fact_ids (read the facts; open the textbook page image for anything doubtful) or lit_ids? Flag: unsupported claims, overstatement, wrong numbers, wrong mechanism, wrong page in notes, literature that overrides or contradicts the textbook or lacks src, quiz answer inconsistent with the textbook, image caption/label that does not match the image (open images).
Write ${OUT}/batch_${b.k}_check_facts.json: {"issues":[{"slug":"...","field":"title|bullets[i]|table|notes|src|quiz_note","severity":"high|medium|low","problem":"...","evidence":"fact id / page quote","fix":"exact replacement text"}]}.
Return count = number of high+medium issues.`, { label: 'facts:' + b.k, phase: 'Check' }),
    () => A(`${READ}

TASK: TEACHER-VOICE CHECK batch ${b.k} (${w.path}). Read it as the teacher would when he edits my drafts (see 40_範例/42_改稿前後對照.md, 43_反例庫.md and the writer brief's do/don't pairs). Flag: LLM phrasing, translationese, stiff or dramatic wording, colloquial verbs he removes, question tails, connective-start titles, title type misuse, too many words for the course font sizes, missing plain-words-before-terms, emphasis overuse, notes that read like a script instead of his short cues. Propose rewrites in his voice (quote a line of his that shows the pattern, from 41_他的原句庫.md).
Write ${OUT}/batch_${b.k}_check_voice.json: {"issues":[{"slug":"...","field":"...","severity":"high|medium|low","problem":"...","his_pattern":"verbatim example","fix":"exact replacement text"}]}.
Return count = number of high+medium issues.`, { label: 'voice:' + b.k, phase: 'Check' }),
    () => A(`${READ}

TASK: TERMS + DENSITY CHECK batch ${b.k} (${w.path}). (1) Run ${CHECK} "${w.path}" and report every RED/WARN. (2) Read every slide and find every technical term that breaks the bilingual scope (course.yaml bilingual: per_slide = not written 中文(English) on that slide; first_per_deck = not written 中文(English) at its first use in the deck as far as this batch and the blueprint order show), abbreviations without Chinese, English-only words, inconsistent renderings vs the glossary, and 禁用變體. (3) Estimate fit at the course sizes (course.yaml sizes; capacity table in scripts/README.md) for each slide's type; flag slides likely to overflow, bullets over about 30 characters, titles over 2 lines, table cells too long. (4) Propose glossary additions.
Write ${OUT}/batch_${b.k}_check_terms.json: {"issues":[{"slug":"...","field":"...","severity":"high|medium|low","problem":"...","fix":"exact replacement text"}],"glossary_additions":[{"zh":"...","en":"...","abbr":"","page":0}]}.
Return count = number of high+medium issues.`, { label: 'terms:' + b.k, phase: 'Check' }),
  ]),
  (checks, b) => (checks && checks.every(Boolean)) ? A(`${READ}

TASK: REVISE batch ${b.k}. Draft: ${OUT}/batch_${b.k}_draft.json (read "issues" and "glossary_additions" in it too). Checks: ${checks.map(c => c.path).join(' ; ')}.
Apply every high and medium issue; low ones when they improve the slide. Priority when fixes conflict: facts > bilingual terms > density/fit > voice. Keep build-run titles identical. Merge all glossary additions (dedupe) into the output.
Write ${OUT}/batch_${b.k}.json (same structure as the draft plus "changelog":[...]). Run ${CHECK} "${OUT}/batch_${b.k}.json" until RED = 0.
Return count = number of slides; notes = remaining WARNs.`, { label: 'revise:' + b.k, phase: 'Revise' }) : null,
)

const fin = results.filter(Boolean)
log(`batches revised: ${fin.length}/${BATCHES.length}`)
if (fin.length < BATCHES.length) return { aborted, finished: fin.length, results }
phase('Continuity')
const cont = await A(`${READ}

TASK: CONTINUITY EDITOR for the whole deck. Read every final batch in order: ${BATCHES.map(b => `${OUT}/batch_${b.k}.json`).join(' , ')} (slide order = blueprint order).
Fix only cross-batch problems, editing the batch files in place: repeated sentences or facts across slides, inconsistent terms or renderings between batches, broken same-title runs, abrupt transitions at batch boundaries and section starts, quiz slides not directly after the slide that teaches the tested point, emphasis overuse across the deck ("=>" at most about one per 15 slides), notes style drift. Do not rewrite slides that are fine.
After editing, run ${CHECK} ${BATCHES.map(b => `"${OUT}/batch_${b.k}.json"`).join(' ')} until RED = 0. Write a report ${OUT}/continuity_report.md (what changed, remaining WARNs, items for the teacher to decide).
Next step for the user (do not run it): ${RUN} merge_written.py --course ${C} --dir "${OUT}" --blueprint "${BP}".
Return count = number of slides changed.`, { label: 'continuity', phase: 'Continuity' })
return { aborted, finished: fin.length, continuity: cont }

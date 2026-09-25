export const meta = {
  name: 'lecture-review',
  description: 'Review a rendered deck on 6 lenses (facts / voice / terms / layout / exam / images), verify each lens with independent refuters, then one fixer applies confirmed fixes to the source files. Generic: args {kit, materials, course, pptx, ...}. Opus only.',
  whenToUse: 'After scripts/gen_pptx.py has produced a deck from the course source files; run 1-2 rounds before delivery.',
  phases: [
    { title: 'Render', detail: 'export PDF, contact sheets and one PNG per slide when args.pngs is not given' },
    { title: 'Review', detail: 'facts / voice+LLM / bilingual / layout (PNG) / exam / images' },
    { title: 'Verify', detail: 'refuters per lens; confirmed = reviewer + at least 1 refuter' },
    { title: 'Fix', detail: 'single fixer edits pool / script / deck menus / course.yaml, regenerates and rechecks' },
  ],
}

// args: {kit, materials, course, pptx,          required (absolute paths; forward slashes are safest)
//        round?, out?, deck?,                   default round 1, out <course>/_archive/review/round<N>
//        pngs?, sheets?,                        rendered slides; if pngs is missing a render agent runs scripts/export_pdf.py first
//        lenses?: ['facts','voice','terms','layout','exam','images'] subset, refuters?: 2,
//        writer_brief?, pages?, effort?, done?:{label: output path}}
const A0 = args || {}
const norm = (p) => (p ? String(p).replace(/\\/g, '/').replace(/\/+$/, '') : '')
const MISSING = ['kit', 'materials', 'course', 'pptx'].filter(k => !A0[k])
if (MISSING.length) {
  log('lecture-review: missing args ' + MISSING.join(', ') + '. Pass {kit, materials, course, pptx: "<path of the rendered .pptx>"}; see workflows/README.md.')
  return { error: 'missing args: ' + MISSING.join(', ') }
}
const KIT = norm(A0.kit)
const MAT = norm(A0.materials)
const C = String(A0.course)
const CD = `${MAT}/courses/${C}`
const G = `${KIT}/style/guide`
const ROUND = A0.round || 1
const OUT = norm(A0.out) || `${CD}/_archive/review/round${ROUND}`
const PPTX = norm(A0.pptx)
const DECK = A0.deck ? String(A0.deck) : ''
const DECKARG = DECK ? ` --deck ${DECK}` : ''
const WB = norm(A0.writer_brief) || `${MAT}/style_evidence/writer_brief_${C}.md`
const REF = Math.max(1, Math.min(3, parseInt(A0.refuters || 2, 10) || 2))
const DONE = Object.assign({}, A0.done || {})
const EFFORT = A0.effort || null
const RUN = `cd "${KIT}/scripts" && SLIDEKIT_MATERIALS="${MAT}" PYTHONIOENCODING=utf-8 python`
const PAGES = A0.pages ? norm(A0.pages) : `the folder printed by: ${RUN} -c "from common import load_course; print(load_course('${C}').textbook_path())"`
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

const ENV = `
Kit (public tools, style guide, templates, question banks): ${KIT}. Materials (private course files, textbook pages, corpus): ${MAT}. Course folder: ${CD}.
Run shell commands with the Bash tool (Git Bash on Windows, bash in a cloud session); if "python" is not found use "python3". Kit scripts are called as: ${RUN} <script>.py --course ${C} ...`

let PNGS = norm(A0.pngs)
let SHEETS = norm(A0.sheets)
if (!PNGS) {
  phase('Render')
  PNGS = `${OUT}/render/png`
  SHEETS = SHEETS || `${OUT}/render/sheets`
  const rd = await A(`${ENV}

TASK (mechanical): render the deck ${PPTX} for review. Run: ${RUN} export_pdf.py "${PPTX}" --pdf "${OUT}/render/deck.pdf" --sheets "${SHEETS}" --pngs "${PNGS}"
(On Windows the script uses PowerPoint; in a cloud session it uses LibreOffice. If it fails, read the error, fix what is fixable (e.g. a PowerPoint window holding the file) and retry once; do not edit the deck.)
Check that ${PNGS} has one slide_NNN.png per slide. Return path = ${PNGS}, count = number of slide PNGs, notes = renderer used and any warnings.`, { label: 'render', phase: 'Render' })
  if (!rd || (!rd.count && !DONE.render)) { log('render failed: ' + (rd ? rd.notes : 'agent returned null')); return { aborted, error: 'render failed', render: rd } }
}
const SHEETS_TXT = SHEETS ? `; 4x3 contact sheets in ${SHEETS}` : ''

const CTX = `${ENV}
Course: read ${CD}/brief.md (the teacher's decisions: counts, minutes, exam, bilingual rule, fonts) and ${CD}/course.yaml first.
The deck: ${PPTX} (one PNG per slide in ${PNGS}/slide_NNN.png; slide number = file number${SHEETS_TXT}). SOURCE FILES (the only place fixes go; paths from course.yaml "paths", relative to the course folder): the pool (paths.pool: slides in order "## 投影片 <slug>｜<title>", HTML comments, "- " bullets, tables), the notes file (paths.script), the deck menus (paths.decks_dir/<deck>.md: order and sections), and ${CD}/course.yaml itself (diagrams, sizes, cover). Formats: ${KIT}/scripts/README.md.
Facts: ${CD}/facts/facts_R.json (the canonical textbook named in course.yaml textbook.ref, the ONLY canonical source; each fact has its printed page), ${CD}/facts/facts_X.json (literature, supplements only); textbook page images: ${PAGES} (pNN_PPP.jpg or .png, PPP = printed page). Each pool slide has <!-- facts: ids --> listing its evidence.
Style: the teacher's style guide ${G}/ (00_README.md; 50_檢查/52_交付前檢查清單.md is the delivery checklist; 20_文字/ for wording; 40_範例/ for his lines and my typical mistakes) and the course writer brief ${WB} if it exists. Glossary ${CD}/glossary.md. Exam bank ${KIT}/question_banks/<bank>/*.json (<bank> = decks.<deck>.question_bank in course.yaml).
General requirements from the teacher: the textbook is canonical (literature never overrides it and is always cited); no LLM-style language; fonts not small (course.yaml sizes: nothing students read below sizes.min; only credits may be smaller); technical terms 中文(English) within the scope of course.yaml bilingual (per_slide or first_per_deck) and the glossary; slide counts, minutes per section and exam counts as brief.md says.
Each finding: {"id":"<lens>-NN","slide":<number>,"slug":"...","field":"title|bullet N|table|notes|image|layout|diagram","severity":"high|medium|low","problem":"...","evidence":"fact id + page quote / verbatim teacher example / what the PNG shows","fix":"exact replacement text or exact action"}.`

const ALL_LENSES = [
  { id: 'facts', d: 'FACTS: every sentence on every slide against its facts (open the textbook page when in doubt); wrong numbers, overstatement, unsupported claims, literature that overrides the textbook or lacks a citation, wrong textbook page in notes, mislabelled figure panels.' },
  { id: 'voice', d: 'TEACHER VOICE / LLM LANGUAGE: read every slide as the teacher would; flag LLM phrasing, translationese, stiff or dramatic wording, colloquial verbs he removes, question tails, connective-start titles, too many words, emphasis overuse; give rewrites in his voice with a verbatim example of his (style guide 40_範例/41_他的原句庫.md).' },
  { id: 'terms', d: `BILINGUAL TERMS: follow the bilingual scope in course.yaml bilingual: per_slide (a course mandate such as immune) = every technical term on every slide is written 中文(English); first_per_deck (the default when the key is absent; style guide 24 TERM-07) = 中文(English) the first time a term appears in the deck, later slides may use the Chinese alone; off = no bilingual rule. brief.md may state the teacher's rule for this course. Within that scope every technical term (titles, bullets, tables, diagram cells, image labels, captions) uses the glossary rendering; flag missing English, missing Chinese, abbreviations without Chinese, 禁用變體, inconsistent renderings across slides. Run: ${RUN} style_check.py --course ${C}${DECKARG} and include its REDs.` },
  { id: 'layout', d: `LAYOUT: look at EVERY slide (go through the contact sheets, then open the individual PNG of every slide that is dense, has a table or diagram, or looks doubtful on the sheet): text overflowing its box or the slide, text overlapping images, images too small to read, empty areas where an image was expected, small text, awkward line breaks inside English words, titles over 2 lines, credits overlapping. Also read the gen_pptx fit report next to the pptx (*_layout.json). If the PNGs were rendered by LibreOffice (cloud) instead of PowerPoint, the substitute CJK font wraps slightly differently: rate borderline overflow as low severity and lean on the *_layout.json estimates.` },
  { id: 'exam', d: 'EXAM QUESTIONS: each quiz slide: the key exists, stem/options/answer exactly match the bank, the answer highlight is on the official answer, the question sits 1-2 slides after the slide that teaches it, and the deck actually teaches what is needed to answer it (textbook-based). Also check the total number of quiz slides and their spread per section against brief.md.' },
  { id: 'images', d: 'IMAGES: for every image-bearing slide check that the picture shows what the title/bullets/labels say, panel labels (H&E vs IF vs IHC) are right, credits are present and correct (textbook figure numbers match the edition in course.yaml; literature credits with licence), no image is reused outside a same-title run, pair slides are real pairs. Budget: look at each slide PNG once (start from the contact sheets) and open an original image file named in the pool only when the slide PNG does not let you judge it; never re-open the same file.' },
]
const PICK = Array.isArray(A0.lenses) && A0.lenses.length ? A0.lenses : ALL_LENSES.map(l => l.id)
const LENSES = ALL_LENSES.filter(l => PICK.includes(l.id))
const SKIPPED = ALL_LENSES.filter(l => !PICK.includes(l.id)).map(l => l.id)
if (SKIPPED.length) log('lenses skipped this round (args.lenses): ' + SKIPPED.join(', '))
if (!LENSES.length) { log('args.lenses matched no lens; valid ids: ' + ALL_LENSES.map(l => l.id).join(', ')); return { error: 'no lenses' } }
const KS = Array.from({ length: REF }, (_, i) => i + 1)

phase('Review')
const reviewed = await pipeline(LENSES,
  (L) => A(`${CTX}

TASK: REVIEW round ${ROUND}, lens ${L.d}
Go through ALL slides. Write ${OUT}/review_${L.id}.json as {"lens":"${L.id}","findings":[...]}. Return count = number of findings.`, { label: 'review:' + L.id, phase: 'Review' }),
  (rv, L) => rv && parallel(KS.map(k => () => A(`${CTX}

TASK: independent REFUTER #${k} for the ${L.id} findings in ${rv.path}. For each finding, check it yourself against the slide PNG, the source files, the facts/textbook pages, the glossary and the teacher's style evidence. Verdict real = the problem exists AND the proposed fix is correct and consistent with the requirements; not_real = the problem does not exist or the fix would make things worse (say why); fix_needs_change = real problem, better fix given.
Write ${OUT}/verify_${L.id}_${k}.json: {"verdicts":[{"id":"...","verdict":"real|not_real|fix_needs_change","reason":"...","better_fix":"..."}]}. Return count = number of real + fix_needs_change.`, { label: `verify${k}:${L.id}`, phase: 'Verify' }))),
)

const ok = reviewed.filter(Boolean)
if (aborted) return { aborted, reviewed: ok.length }
phase('Fix')
const fix = await A(`${CTX}

TASK: FIXER for round ${ROUND}. For each lens, read ${OUT}/review_<lens>.json and its verification files ${KS.map(k => `${OUT}/verify_<lens>_${k}.json`).join(', ')} (lenses: ${LENSES.map(l => l.id).join(', ')}).
A finding is CONFIRMED when at least one refuter says real or fix_needs_change (use the better_fix when given; if refuters give different better fixes, choose the one most faithful to the textbook and the teacher's style). Ignore findings every refuter rejects.
Apply every confirmed fix to the source files (pool, notes file, deck menus, course.yaml). Keep the pool format exactly (see scripts/README.md). Do not change slugs. Priority when fixes collide: facts > terms > layout > voice.
Then regenerate and recheck: ${RUN} gen_pptx.py --course ${C}${DECKARG} --no-check --date <the YYYYMMDD in the file name of ${PPTX}, so the same file is overwritten; on Windows close it in PowerPoint first> && ${RUN} check_deck.py --course ${C}${DECKARG} --pptx "${PPTX}" && ${RUN} style_check.py --course ${C}${DECKARG}; fix until check_deck has no RED and style_check RED = 0.
Write ${OUT}/fix_report.md: confirmed findings applied (by lens, slide), rejected findings with reasons, anything the teacher must decide. Return count = number of fixes applied.`, { label: 'fix', phase: 'Fix' })
return { aborted, reviewed: ok.length, lenses: LENSES.map(l => l.id), fix }

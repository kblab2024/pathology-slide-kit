export const meta = {
  name: 'lecture-blueprint',
  description: 'Blueprint a lecture deck: glossary + lens drafts -> independent judges -> synthesize + validate -> completeness critic -> revise. Generic: args {kit, materials, course, ...}; lenses and counts from args with defaults. Opus only.',
  whenToUse: 'After lecture-gather and scripts/merge_facts.py (facts_R.json, facts_X.json, exam_candidates.json and image catalogs exist): plan every slide of the deck.',
  phases: [
    { title: 'Draft', detail: 'glossary builder + one complete draft per lens' },
    { title: 'Judge', detail: 'independent judges score all drafts' },
    { title: 'Synthesize', detail: 'merge winner + grafts, validate with scripts/validate_blueprint.py' },
    { title: 'Critique', detail: 'completeness / pacing / exam / image critic' },
    { title: 'Revise', detail: 'apply critique, final validation' },
  ],
}

// args: {kit, materials, course,               required (absolute paths; forward slashes are safest)
//        deck?,                                 deck name in course.yaml (default: every deck in deck_order)
//        total?, sections?, per_section?:[lo,hi], minutes?: 40, quiz?: '10-15 in total, 3-5 per section', img_rate?: 0.65,
//        slug_prefix?,                          default = course name
//        lenses?: [{id, d}], judges?: 3, out?, pages?, corpus?, effort?, done?:{label: output path},
//        teacher_notes?}                        the teacher's comments on blueprint_summary.md: a file path or the text itself;
//                                               read by the revise agent (to re-run only the revision: done = everything except 'revise')
const A0 = args || {}
const norm = (p) => (p ? String(p).replace(/\\/g, '/').replace(/\/+$/, '') : '')
const MISSING = ['kit', 'materials', 'course'].filter(k => !A0[k])
if (MISSING.length) {
  log('lecture-blueprint: missing args ' + MISSING.join(', ') + '. Pass {kit: "<path of pathology-slide-kit>", materials: "<path of pathology-slide-materials>", course: "<folder name under materials/courses>"}; see workflows/README.md.')
  return { error: 'missing args: ' + MISSING.join(', ') }
}
const KIT = norm(A0.kit)
const MAT = norm(A0.materials)
const C = String(A0.course)
const CD = `${MAT}/courses/${C}`
const G = `${KIT}/style/guide`
const CORPUS = norm(A0.corpus) || `${MAT}/corpus`
const OUT = norm(A0.out) || `${CD}/_archive/blueprint`
const DECK = A0.deck ? String(A0.deck) : ''
const DECKARG = DECK ? ` --deck ${DECK}` : ''
const DECKREF = DECK ? `decks.${DECK}` : 'decks.<deck>'
const PREFIX = A0.slug_prefix || C
const JUDGES = Math.max(1, Math.min(5, parseInt(A0.judges || 3, 10) || 3))
const DONE = Object.assign({}, A0.done || {})
const EFFORT = A0.effort || null
const TN = A0.teacher_notes ? String(A0.teacher_notes) : ''
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

// Constraints: from args when given, otherwise from course.yaml / brief.md (the agents read them).
const MIN = A0.minutes || 40
const LOHI = Array.isArray(A0.per_section) ? `${A0.per_section[0]}-${A0.per_section[1]}` : ''
const SIZE = (A0.total || A0.sections || LOHI)
  ? `${A0.total ? `about ${A0.total} slides` : `the slide target (course.yaml ${DECKREF}.target)`} in ${A0.sections ? A0.sections : `course.yaml ${DECKREF}.sections`} sections, ${LOHI || `course.yaml ${DECKREF}.per_section`} slides per section, each section <= ${MIN} minutes`
  : `the slide target, number of sections and per-section range in course.yaml ${DECKREF} (target, sections, per_section), each section <= ${MIN} minutes`
const TOTAL = A0.total ? `about ${A0.total} slides` : `course.yaml ${DECKREF}.target slides`
const QUIZ = A0.quiz ? String(A0.quiz) : 'the number of exam-question slides that brief.md asks for (if brief.md is silent: 3-5 per section when the deck has a question_bank in course.yaml, none otherwise)'
const IMG = A0.img_rate ? `${Math.round(A0.img_rate * 100)}%` : 'sizes.img_rate_min in course.yaml (65% if unset)'

const DEFAULT_LENSES = [
  { id: 'audience', d: 'AUDIENCE-RELEVANCE FIRST: within the textbook chapter, maximise what matters to this audience (brief.md says who they are and what they will do with it; e.g. for dental students: oral mucosa, salivary glands, tongue, gingiva, jaw, dental procedures and materials, oral lesions), using verified literature only as cited supplements; still cover the core mechanisms needed to understand them.' },
  { id: 'textbook', d: 'TEXTBOOK-COMPLETENESS FIRST: follow the chapter structure and KEY CONCEPTS boxes faithfully so a student can read the chapter afterwards with this deck as the map (「聽課應該是要回去知道怎麼唸書」); make sure every major heading is covered or deliberately skipped with a reason; use textbook figures and tables heavily.' },
  { id: 'teacher', d: 'TEACHER-FLOW FIRST: follow the flow the teacher himself uses: reuse the flow and sentences of his own earlier decks on this topic when the corpus has them, question-title slides followed by answer slides, same-title build runs with one step per slide, image-heavy pair slides, his exam-reality remarks, dividers as noun phrases, the lecture ends on the last disease.' },
]
const LENSES = Array.isArray(A0.lenses) && A0.lenses.length ? A0.lenses : DEFAULT_LENSES
const JUDGE_FOCUS = [
  'Pay extra attention to factual scope errors (slides planning content that the textbook does not support).',
  'Pay extra attention to images: open at least 25 assigned images and check they show what the brief says.',
  'Pay extra attention to pacing and the teacher-structure rules, and to whether the literature supplements are genuinely useful for this audience.',
  'Pay extra attention to the exam questions: keys valid, answerable from the chapter, placed 1-2 slides after the taught point.',
  'Pay extra attention to writability at the course font sizes: briefs specific, one point per slide, build runs that really add one step each.',
]

const INPUTS = `
Kit (public tools, style guide, templates, question banks): ${KIT}. Materials (private): ${MAT}. Course folder: ${CD}.
Run shell commands with the Bash tool (Git Bash on Windows, bash in a cloud session); if "python" is not found use "python3". Kit scripts are called as: ${RUN} <script>.py --course ${C} ...
READ FIRST: ${CD}/brief.md (course decisions, draft outline, material locations) and ${CD}/course.yaml (decks, sizes, cover, diagrams, bilingual scope and bilingual_whitelist)${DECK ? `; this run plans deck ${DECK}` : '; <deck> below means each deck in course.yaml deck_order'}. Tools/format: ${KIT}/scripts/README.md, ${KIT}/templates/blueprint.schema.json.
Facts: ${CD}/facts/facts_R.json (the canonical textbook named in course.yaml textbook.ref, the ONLY canonical source; ids like S07-144, each with printed page, heading, en, zh and any relevance field), ${CD}/facts/facts_X.json (verified literature claims with slide_cite), human-readable ${CD}/facts/facts.md; textbook tables transcribed inside facts_R.json "tables"; figure captions in "figures". Textbook page images: ${PAGES}.
Images (use ONLY files that exist; paths relative to ${CD}): the catalogs under ${CD}/assets/images/ (a 圖片總表.md if present, and each subfolder's 圖片清單.md or *_images.json; literature image licences in ${CD}/_archive/gather/lit/*_images.json). View an image with the Read tool when unsure what it shows.
Exam: ${CD}/_archive/gather/exam/exam_candidates.json ("recommended" + alternates + stats) when the course has one; bank ${KIT}/question_banks/<bank>/*.json with <bank> = ${DECKREF}.question_bank in course.yaml (key = 年度-第幾次#題號; in the 醫師 bank only 題號 76-100 are pathology).
Teacher style (structure-relevant), in the style guide ${G}/: 00_README.md (task A reading order), 10_版面/13_密度與字數.md, 15_圖片與配對.md, 20_文字/21_標題句式.md, 30_結構/31_開場與結尾.md, 32_段落節奏與同標題連張.md, 33_divider.md, 34_國考題.md, 37_刪張與留張.md, 38_課別差異.md. His past decks: ${CORPUS}/index.md lists the per-slide dumps in ${CORPUS}/decks/<code>.txt; read the ones on this lecture's topic (brief.md may say which slides of an old deck are his own).
Slide types and what fits at the course font sizes: the table in scripts/README.md (measured at 28pt body) and course.yaml sizes. New slides carry 0-3 bullets; flash/pair at most 2 short lines; big = 1-3 short sentences.
HARD CONSTRAINTS: ${SIZE} (give each slide a "minutes" estimate; typical 0.4-1.0); exam-question slides: ${QUIZ}, each placed 1-2 slides after the slide that teaches the tested point, only questions answerable from the textbook chapter plus the slides; picture rate >= ${IMG} of content slides (not counting title/divider/quiz) using REAL files (pairs: clinical + histology, H&E + IF/IHC, lesion + normal); no placeholder slides (if no image exists, set img_wanted and keep it text-only); follow the outline and per-topic slide counts in brief.md; every textbook fact the slide relies on listed in fact_ids; literature only as cited supplement in lit_ids (never replacing a textbook statement); no summary/Q&A/thank-you slide at the end (stop at the last disease); dividers = noun phrases; use same-title build runs (2-6 slides, about 15-20% of slides) for mechanisms and image series; framework diagrams may be defined in YAML (nodes <= 5, rows <= 3, each cell about 14 characters incl. English, i.e. at most two short lines such as 中文 + (English)); see scripts/gen_pptx.py L_diagram.
Opening: follow brief.md and 31_開場與結尾: the cover (title and subtitle from course.yaml cover) and, when the deck has an exam bank, at most one direct stats slide about exam weight using the exam_candidates stats, in his plain exam-reality voice; no objectives slide. When images by other authors are used, credit them as brief.md says (e.g. a line on the cover).
Slug format: ${PREFIX}-s{section}-{seq:03d}-{keyword} (ASCII). Segment ids: S1-01, S1-02 ... Write the briefs in Traditional Chinese (台灣用語).`

const validate = (bp, dia) => `${RUN} validate_blueprint.py --course ${C}${DECKARG} "${bp}" --diagrams "${dia}"`

phase('Draft')
const [gloss, ...drafts] = await parallel([
  () => A(`${INPUTS}

TASK: build the course GLOSSARY that scripts/style_check.py and check_written.py enforce. The scope comes from course.yaml bilingual: per_slide (a course mandate such as immune) = every technical term on every slide appears as 中文(English); first_per_deck (the default when the key is absent) = 中文(English) at the first use in the deck, later slides may use the Chinese alone; off = no bilingual check. The 禁用變體 column is enforced in every mode.
If ${CD}/glossary.md already exists, keep its entries and decisions and extend it; otherwise create it. Collect every technical term likely to appear on slides for this lecture: all pathology terms in facts_R.json (their zh fields already use 中文(English)), terms in facts_X.json, disease names, cells, molecules (only when a Chinese name is used), tests, stains, anatomical terms, drug names. Typical size 300-700 entries.
Chinese rendering priority: (1) the teacher's own usage (style guide 20_文字/24_術語與中英對照.md; grep the corpus dumps ${CORPUS}/decks/*.txt), e.g. 分化不良(dysplasia); (2) 國家教育研究院 樂詞網 standard; (3) common Taiwanese clinical usage. One Chinese form per concept; list common variants that must NOT be used in the 禁用變體 column (e.g. 異型增生 for dysplasia). Put the standard abbreviation in 縮寫 when one exists. Do NOT list bare molecular symbols that need no translation (IgE, CD4, IL-4 ...): those belong to bilingual_whitelist in course.yaml (list any you think are missing in your notes).
Write ${CD}/glossary.md as a markdown table with header exactly: | 中文 | English | 縮寫 | 首見頁 | 禁用變體 | 依據 | (首見頁 = textbook printed page of first use; 依據 = 教師用法 / 樂詞網 / 臨床慣用, with deck+slide when from his decks). Sort by first page. Add a short intro paragraph explaining the rules.
Return count = number of entries.`, { label: 'glossary', phase: 'Draft' }),
  ...LENSES.map(L => () => A(`${INPUTS}

TASK: write a COMPLETE blueprint draft for the whole lecture from this lens:
${L.d}
Produce valid JSON matching templates/blueprint.schema.json: sections (label 第一節/第二節/…, title, minutes_target, segments with ids and titles) and all slides (${TOTAL}), each with slug, segment, type, build (if part of a same-title run), img (existing files, with src credit like "Robbins Fig. 6.13" or the credit_line from the literature image JSON, and an optional label for pair slides), img_wanted (only when no file fits), quiz (for quiz slides), diagram + diagram_bright (if you define a framework diagram), fact_ids, lit_ids, minutes, and a concrete brief (what the slide says in one or two sentences, which fact it rests on, why it is here). Set "aud" only when the course has more than one deck.
If you use a framework diagram, write its YAML definition to ${OUT}/diagrams_${L.id}.yaml in the format {name: {nodes:[{label, group}], rows:[{name, cells:[...]}], groups:{g:{main:HEX, light:HEX}}}} with labels/cells bilingual 中文(English) where a technical term appears (every cell when course.yaml bilingual is per_slide) (an empty mapping {} if you use none).
Write the draft to ${OUT}/draft_${L.id}.json. Then run: ${validate(`${OUT}/draft_${L.id}.json`, `${OUT}/diagrams_${L.id}.yaml`)} and fix every RED (missing files, bad quiz keys, bad segments) and the WARNs about section size / minutes / picture rate before returning.
Return count = number of slides; notes = per-section counts, minutes, picture rate, number of quiz slides.`, { label: 'draft:' + L.id, phase: 'Draft' })),
])
const ok = drafts.filter(Boolean)
if (ok.length < Math.min(2, LENSES.length)) { log('not enough drafts'); return { aborted, gloss, drafts } }

phase('Judge')
const judges = await parallel(Array.from({ length: JUDGES }, (_, i) => i + 1).map(k => () => A(`${INPUTS}

TASK: independent JUDGE #${k}. Compare the blueprint drafts: ${ok.map(d => d.path).join(' ; ')}.
Score each draft 1-10 on: (a) coverage of the must-know textbook content for this audience (check headings in facts_R.json "headings"); (b) audience relevance and correct, subordinate use of literature (never overriding the textbook); (c) pacing: ${SIZE}, sensible minute estimates; (d) images: real files, right image for the point (open several with Read to verify), pairing logic, picture rate >= ${IMG}; (e) fit to the teacher's structure rules (builds, question->answer, dividers, opening/ending, exam placement 1-2 slides after the taught point, exam slides as required: ${QUIZ}); (f) writability at the course font sizes (briefs specific, not overloaded).
${JUDGE_FOCUS[(k - 1) % JUDGE_FOCUS.length]}
Write ${OUT}/judge_${k}.json: {"scores":{"<draft file>":{"a":n,...,"total":n,"strengths":[...],"weaknesses":[...]}},"winner":"<file>","grafts":[{"from":"<file>","what":"specific slides/segments/ideas to transplant into the winner","why":"..."}],"errors":[{"file":"...","slug":"...","problem":"..."}]}
Return count = number of grafts.`, { label: 'judge' + k, phase: 'Judge' })))

phase('Synthesize')
const synth = await A(`${INPUTS}

TASK: SYNTHESIZE the final blueprint. Drafts: ${ok.map(d => d.path).join(' ; ')}. Judges: ${judges.filter(Boolean).map(j => j.path).join(' ; ')}. Glossary: ${gloss ? gloss.path : '(missing)'}.
Take the draft the judges rank highest as the base, apply the grafts most judges support, fix every listed error. Keep ${SIZE}.
Write ${OUT}/blueprint_v1.json and ${OUT}/diagrams.yaml (merge the diagram definitions actually used), then run ${validate(`${OUT}/blueprint_v1.json`, `${OUT}/diagrams.yaml`)} and fix until RED = 0 and there are no section-size / minutes / picture-rate WARNs.
Also write ${OUT}/blueprint_summary.md: per section a table (segment | slides | minutes | quiz keys | main images) and the list of textbook headings deliberately skipped with reasons.
Return count = number of slides.`, { label: 'synthesize', phase: 'Synthesize' })
if (!synth) return { aborted, gloss, drafts: ok, judges }

phase('Critique')
const crit = await A(`${INPUTS}

TASK: COMPLETENESS CRITIC for ${OUT}/blueprint_v1.json (diagrams ${OUT}/diagrams.yaml, summary ${OUT}/blueprint_summary.md).
Check and list concrete issues (slug-level) for: (1) textbook coverage: walk through every heading in facts_R.json "headings" and every KEY CONCEPTS box: covered by which slug, or skipped with an acceptable reason for this audience; flag must-know items missing; (2) every slide's fact_ids actually support its brief (spot-check 40 slides by reading the facts); (3) literature: each lit_id exists in facts_X.json, is used as supplement only, and its slide also cites the textbook where the textbook has something to say; (4) exam: ${QUIZ}; each 1-2 slides after the taught point, answerable, keys valid, spread across sections; (5) images: 20 random image assignments opened with Read and checked; pair slides really are pairs; no two slides use the same image unless in a build run; (6) pacing and section balance; (7) teacher structure rules (opening, dividers, builds, no ending summary); (8) anything a pathology teacher would find wrong or boring for this audience.
Write ${OUT}/critique.json: {"issues":[{"slug":"...","severity":"high|medium|low","problem":"...","fix":"..."}],"missing":[{"heading":"...","page":0,"suggestion":"..."}]}.
Return count = number of high+medium issues.`, { label: 'critic', phase: 'Critique' })

phase('Revise')
const fin = await A(`${INPUTS}

TASK: REVISE the blueprint. Inputs: ${OUT}/blueprint_v1.json, ${OUT}/diagrams.yaml, critique ${crit ? crit.path : '(none)'}.
Apply every high and medium issue (and low ones that are cheap), keeping the hard constraints.${TN ? ` The teacher has commented on the blueprint summary; his comments outrank the critique (facts still follow the textbook) and must all be applied or, if impossible, listed as open questions: ${TN} (if this is a file path, read the file). Re-read ${CD}/brief.md too: it may have been updated with his decisions.` : ''} Write ${OUT}/blueprint.json and update ${OUT}/diagrams.yaml and ${OUT}/blueprint_summary.md. Run ${validate(`${OUT}/blueprint.json`, `${OUT}/diagrams.yaml`)} until RED = 0 with no section-size / minutes / picture-rate WARNs. Add to the summary a changelog of what the critique changed and a list of items the teacher must decide (e.g. literature vs textbook conflicts, textbook self-contradictions that affect slides, questionable exam keys).
Next steps for the user (do not run them): copy the diagrams into course.yaml diagrams, then ${RUN} make_batches.py "${OUT}/blueprint.json" "${CD}/_archive/written/batches.json" and run workflows/lecture-write.js.
Return count = number of slides; notes = final per-section counts, minutes, picture rate, quiz count.`, { label: 'revise', phase: 'Revise' })
return { aborted, gloss, drafts: ok, judges, synth, crit, fin }

export const meta = {
  name: 'lecture-blueprint',
  description: 'Blueprint a lecture deck: glossary + 3 lens drafts -> 3 judges -> synthesize+validate -> completeness critic -> revise',
  phases: [
    { title: 'Draft', detail: 'glossary builder + 3 drafts from different lenses' },
    { title: 'Judge', detail: '3 independent judges score all drafts' },
    { title: 'Synthesize', detail: 'merge winner + grafts, validate with scripts/validate_blueprint.py' },
    { title: 'Critique', detail: 'completeness / pacing / exam / image critic' },
    { title: 'Revise', detail: 'apply critique, final validation' },
  ],
}

// 歷史範例：2026-09 免疫課程（immune）原版腳本，只供對照，不要直接執行。
// 已去除本機路徑（<ROOT> 為舊專案根目錄的佔位字）並把模型改成 opus；新課程請用 workflows/ 下的通用版：
// lecture-blueprint.js（說明見 workflows/README.md）。

const A0 = args || {}
const ROOT = A0.root || '<ROOT>'
const C = A0.course || 'immune'
const CD = `${ROOT}/${C}`
const OUT = `${CD}/_archive/blueprint`
const TOTAL = A0.total || 180
const PER = A0.per_section || [55, 65]
const MIN = A0.minutes || 40
const RET = { type: 'object', properties: { path: { type: 'string' }, count: { type: 'integer' }, notes: { type: 'string' } }, required: ['path', 'count', 'notes'] }
let aborted = false
async function A(prompt, opts) {
  if (aborted) return null
  const r = await agent(prompt, { model: 'opus', schema: RET, ...opts })
  if (r === null) { aborted = true; log('ABORT: agent returned null at ' + (opts && opts.label) + ' — stopping; resume later') }
  return r
}

const INPUTS = `
READ FIRST: ${CD}/brief.md (course decisions, draft outline, material locations). Tools/format: ${ROOT}/scripts/README.md, ${ROOT}/templates/blueprint.schema.json, ${CD}/course.yaml.
Facts: ${CD}/facts/facts_R.json (Robbins, the ONLY canonical source; ids like S07-144, each with printed page, heading, en, zh, dental relevance), ${CD}/facts/facts_X.json (verified literature claims, ids like hae_dental-2, with slide_cite), human-readable ${CD}/facts/facts.md; Robbins tables transcribed inside facts_R.json "tables"; figure captions in "figures".
Images (use ONLY files that exist; paths relative to ${CD}): catalog ${CD}/assets/images/圖片總表.md; Robbins figure details ${CD}/assets/images/Robbins抽圖/圖片清單.md. View an image with the Read tool when unsure what it shows.
Exam: ${CD}/_archive/gather/exam/exam_candidates.json ("recommended" + alternates + stats); bank ${ROOT}/question_banks/牙醫師/questions-dent-104-115.json (key = 年度-第幾次#題號).
Teacher style (structure-relevant): ${ROOT}/style/_work/prior_findings_20260924.md, and whatever exists in ${ROOT}/style/_work/mining/ (prefer *_final.md; otherwise the miner .json) for 13_密度與字數, 15_圖片與配對, 21_標題句式, 31_開場與結尾, 32_段落節奏與同標題連張, 33_divider, 34_國考題, 37_刪張與留張, 38_課別差異. His past immune decks are dumped as text in ${ROOT}/style/corpus/decks/2024_A1_免疫疾病一_1018.txt and 2024_A1_免疫疾病二_排斥與免疫不全_1025.txt (his own slides are #1-47 and #1-49).
Slide types and what fits at the required large fonts (4:3; title 36pt, body 28pt): see the table in scripts/README.md. New slides carry 0-3 bullets; flash/pair at most 2 short lines; big = 1-3 short sentences.
HARD CONSTRAINTS: ~${TOTAL} slides in 3 sections, each ${PER[0]}-${PER[1]} slides and <= ${MIN} minutes (give each slide a "minutes" estimate; typical 0.4-1.0); 10-15 dental exam quiz slides in total (3-5 per section), each placed 1-2 slides after the slide that teaches the tested point, only questions answerable from Robbins ch.6 plus the slides; picture rate >= 65% of content slides (not counting title/divider/quiz) using REAL files (pairs: clinical + histology, H&E + IF/IHC, lesion + normal); no placeholder slides (if no image exists, set img_wanted and keep it text-only); normal immunity review 10-15 slides; every Robbins fact the slide relies on listed in fact_ids; literature only as cited supplement in lit_ids (never replacing a Robbins statement); no summary/Q&A/thank-you slide at the end — stop at the last disease; dividers = noun phrases; use same-title build runs (2-6 slides, 15-20% of slides) for mechanisms and image series; one diagram type may be defined in YAML (nodes <=5, rows <=3, each cell <= 14 Chinese characters incl. English) — see scripts/gen_pptx.py L_diagram.
Opening: cover (title "病理學：免疫疾病", subtitle with Robbins 11e 第6章) and one direct stats slide about exam weight using exam_candidates stats (e.g. 1920 題中 176 題與免疫有關、平均每份 7.3 題), in his plain exam-reality voice; no objectives slide. If any image from 同事甲 (b1/imm1old/imm2old) is used, the cover must add "(部分圖片感謝同事甲提供)".
Slug format: imm-s{section}-{seq:03d}-{keyword} (ASCII). Segment ids: S1-01, S1-02 ... Write Traditional Chinese in briefs.`

async function main() {
  phase('Draft')
  const LENSES = [
    { id: 'dental', d: 'DENTAL-RELEVANCE FIRST: within Robbins scope, maximise what matters to future dentists (oral mucosa, salivary glands, tongue, gingiva, jaw, dental procedures, dental materials, oral lesions of immunodeficiency/HIV, amyloid macroglossia), using verified literature only as cited supplements; still cover the core mechanisms needed to understand them.' },
    { id: 'robbins', d: 'ROBBINS-COMPLETENESS FIRST: follow the chapter structure and KEY CONCEPTS boxes faithfully so a student can read the chapter afterwards with this deck as the map ("聽課應該是要回去知道怎麼唸書"); make sure every major heading is covered or deliberately skipped with a reason; use Robbins figures and tables heavily.' },
    { id: 'teacher', d: 'TEACHER-FLOW FIRST: follow the flow the teacher himself uses: reuse the flow and sentences of his own 2024 immune slides where they fit, question-title slides followed by answer slides, same-title build runs with one step per slide, image-heavy pair slides, his exam-reality remarks, dividers as noun phrases, lecture ends on the last disease.' },
  ]
  const [gloss, ...drafts] = await parallel([
    () => A(`${INPUTS}

TASK: build the course GLOSSARY that a checker will enforce slide by slide ("every technical term must appear as 中文(English)").
Collect every technical term likely to appear on slides for this lecture: all immunology/pathology terms in facts_R.json (their zh fields already use 中文(English)), terms in facts_X.json, disease names, cells, molecules (only when a Chinese name is used), tests, stains, anatomical/oral terms, drug names. Target 400-700 entries.
Chinese rendering priority: (1) the teacher's own usage in his decks (see ${ROOT}/style/_work/mining/24_術語與中英對照*.json/.md if present, and grep the corpus .txt dumps in ${ROOT}/style/corpus/decks/), e.g. 分化不良(dysplasia), 修格蘭症候群; (2) 國家教育研究院 樂詞網 standard; (3) common Taiwanese clinical usage. One Chinese form per concept; list common variants that must NOT be used in the 禁用變體 column (e.g. 乾燥症 if 修格蘭症候群 is chosen, 異型增生 for dysplasia). Put the standard abbreviation in 縮寫 when one exists (SLE, HAE, LAD, CVID, AIDS...). Do NOT list bare molecular symbols that need no translation (IgE, CD4, IL-4, C3a...): those go to the whitelist in course.yaml.
Write ${CD}/glossary.md as a markdown table with header exactly: | 中文 | English | 縮寫 | 首見頁 | 禁用變體 | 依據 | (首見頁 = Robbins printed page of first use; 依據 = 教師用法 / 樂詞網 / 臨床慣用, with deck+slide when from his decks). Sort by first page. Add a short intro paragraph explaining the rules.
Return count = number of entries.`, { label: 'glossary', phase: 'Draft' }),
    ...LENSES.map(L => () => A(`${INPUTS}

TASK: write a COMPLETE blueprint draft for the whole lecture from this lens:
${L.d}
Produce valid JSON matching templates/blueprint.schema.json: sections (3, with label 第一節/第二節/第三節, title, minutes_target, segments with ids and titles) and ~${TOTAL} slides, each with slug, segment, type, build (if part of a same-title run), img (existing files, with src credit like "Robbins Fig. 6.13" or the credit_line from the literature image JSON and an optional label for pair slides), img_wanted (only when no file fits), quiz (for quiz slides), diagram + diagram_bright (if you define a framework diagram), fact_ids, lit_ids, minutes, and a concrete brief (what the slide says in one or two sentences, which fact it rests on, why it is here).
If you use a framework diagram, write its YAML definition to ${OUT}/diagrams_${L.id}.yaml in the format {name: {nodes:[{label, group}], rows:[{name, cells:[...]}], groups:{g:{main:HEX, light:HEX}}}} with every label/cell bilingual 中文(English) where a technical term appears.
Write the draft to ${OUT}/draft_${L.id}.json. Then run: cd "${ROOT}/scripts" && PYTHONIOENCODING=utf-8 python validate_blueprint.py --course ${C} "${OUT}/draft_${L.id}.json" --diagrams "${OUT}/diagrams_${L.id}.yaml" and fix every RED (missing files, bad quiz keys, bad segments) and the WARNs about section size / minutes / picture rate before returning.
Return count = number of slides; notes = per-section counts, minutes, picture rate, number of quiz slides.`, { label: 'draft:' + L.id, phase: 'Draft' })),
  ])
  const ok = drafts.filter(Boolean)
  if (ok.length < 2) { log('not enough drafts'); return { aborted, gloss, drafts } }

  phase('Judge')
  const judges = await parallel([1, 2, 3].map(k => () => A(`${INPUTS}

TASK: independent JUDGE #${k}. Compare the blueprint drafts: ${ok.map(d => d.path).join(' ; ')}.
Score each draft 1-10 on: (a) coverage of the must-know Robbins ch.6 content for dental students (check headings in facts_R.json "headings"); (b) dental relevance and correct, subordinate use of literature (never overriding Robbins); (c) pacing: 3 sections of ${PER[0]}-${PER[1]} slides, <= ${MIN} minutes each, sensible minute estimates; (d) images: real files, right image for the point (open several with Read to verify), pairing logic, picture rate >= 65%; (e) fit to the teacher's structure rules (builds, question->answer, dividers, opening/ending, exam placement 1-2 slides after the taught point, 10-15 quiz slides answerable from ch.6); (f) writability at 36/28pt (briefs specific, not overloaded).
${k === 1 ? 'Pay extra attention to factual scope errors (slides planning content that Robbins does not support).' : k === 2 ? 'Pay extra attention to images: open at least 25 assigned images and check they show what the brief says.' : 'Pay extra attention to pacing and the teacher-structure rules, and to whether the dental supplements are genuinely useful.'}
Write ${OUT}/judge_${k}.json: {"scores":{"<draft file>":{"a":n,...,"total":n,"strengths":[...],"weaknesses":[...]}},"winner":"<file>","grafts":[{"from":"<file>","what":"specific slides/segments/ideas to transplant into the winner","why":"..."}],"errors":[{"file":"...","slug":"...","problem":"..."}]}
Return count = number of grafts.`, { label: 'judge' + k, phase: 'Judge' })))

  phase('Synthesize')
  const synth = await A(`${INPUTS}

TASK: SYNTHESIZE the final blueprint. Drafts: ${ok.map(d => d.path).join(' ; ')}. Judges: ${judges.filter(Boolean).map(j => j.path).join(' ; ')}. Glossary: ${gloss ? gloss.path : '(missing)'}.
Take the draft the judges rank highest as the base, apply the grafts most judges support, fix every listed error. Keep ~${TOTAL} slides, 3 sections of ${PER[0]}-${PER[1]}, <= ${MIN} min each.
Write ${OUT}/blueprint_v1.json and ${OUT}/diagrams.yaml (merge the diagram definitions actually used), then run validate_blueprint.py (--course ${C} "${OUT}/blueprint_v1.json" --diagrams "${OUT}/diagrams.yaml") and fix until RED = 0 and there are no section-size / minutes / picture-rate WARNs.
Also write ${OUT}/blueprint_summary.md: per section a table (segment | slides | minutes | quiz keys | main images) and the list of Robbins headings deliberately skipped with reasons.
Return count = number of slides.`, { label: 'synthesize', phase: 'Synthesize' })
  if (!synth) return { aborted }

  phase('Critique')
  const crit = await A(`${INPUTS}

TASK: COMPLETENESS CRITIC for ${OUT}/blueprint_v1.json (diagrams ${OUT}/diagrams.yaml, summary ${OUT}/blueprint_summary.md).
Check and list concrete issues (slug-level) for: (1) Robbins coverage — walk through every heading in facts_R.json "headings" and every KEY CONCEPTS box: covered by which slug, or skipped with an acceptable reason for dental students; flag must-know items missing; (2) every slide's fact_ids actually support its brief (spot-check 40 slides by reading the facts); (3) literature: each lit_id exists in facts_X.json, is used as supplement only, and its slide also cites Robbins where Robbins has something to say; (4) exam: 10-15 quiz slides, each 1-2 slides after the taught point, answerable, keys valid, spread 3-5 per section; (5) images: 20 random image assignments opened with Read and checked; pair slides really are pairs; no two slides use the same image unless in a build run; (6) pacing and section balance; (7) teacher structure rules (opening, dividers, builds, no ending summary); (8) anything a pathology teacher would find wrong or boring for dental students.
Write ${OUT}/critique.json: {"issues":[{"slug":"...","severity":"high|medium|low","problem":"...","fix":"..."}],"missing":[{"heading":"...","page":0,"suggestion":"..."}]}.
Return count = number of high+medium issues.`, { label: 'critic', phase: 'Critique' })

  phase('Revise')
  const fin = await A(`${INPUTS}

TASK: REVISE the blueprint. Inputs: ${OUT}/blueprint_v1.json, ${OUT}/diagrams.yaml, critique ${crit ? crit.path : '(none)'}.
Apply every high and medium issue (and low ones that are cheap), keeping the hard constraints. Write ${OUT}/blueprint.json and update ${OUT}/diagrams.yaml and ${OUT}/blueprint_summary.md. Run validate_blueprint.py until RED = 0 with no section-size / minutes / picture-rate WARNs. Add to the summary a changelog of what the critique changed and a list of items the teacher must decide (e.g. literature vs Robbins conflicts, Robbins self-contradictions that affect slides, questionable exam keys).
Return count = number of slides; notes = final per-section counts, minutes, picture rate, quiz count.`, { label: 'revise', phase: 'Revise' })
  return { aborted, gloss, drafts: ok, judges, synth, crit, fin }
}
return await main()

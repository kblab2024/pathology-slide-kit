export const meta = {
  name: 'lecture-gather',
  description: 'Gather course evidence: textbook facts by segment (extract -> 2 refuters -> adjudicator), exam-bank classification and selection, literature search -> PubMed verification -> open-licence images. Each part optional; settings from <course>/gather.json (see templates/gather.template.json). Opus only.',
  whenToUse: 'First content step of a new lecture, after the textbook pages are rendered (scripts/render_pdf_pages.py) and course.yaml / brief.md / gather.json exist.',
  phases: [
    { title: 'Load', detail: 'read gather.json and resolve the textbook page folder' },
    { title: 'Exam', detail: 'optional bank update, 2 independent classifiers, verify & select' },
    { title: 'Literature', detail: 'per topic: search -> PubMed verify -> open-licence images' },
    { title: 'Textbook', detail: 'per segment: extract -> 2 refuters -> adjudicate' },
  ],
}

// args: {kit, materials, course,               required (absolute paths; forward slashes are safest)
//        gather?,                               the gather settings object inline (default: read <course>/gather.json)
//        gather_file?,                          another settings file
//        parts?: ['facts','exam','literature'], subset to run (default: every part present and not "enabled": false)
//        segments?: ['S01', ...], topics?: ['id', ...],   run only these segments / literature topics
//        refuters?: 2, effort?, done?:{label: output path}}
const A0 = args || {}
const norm = (p) => (p ? String(p).replace(/\\/g, '/').replace(/\/+$/, '') : '')
const MISSING = ['kit', 'materials', 'course'].filter(k => !A0[k])
if (MISSING.length) {
  log('lecture-gather: missing args ' + MISSING.join(', ') + '. Pass {kit: "<path of pathology-slide-kit>", materials: "<path of pathology-slide-materials>", course: "<folder name under materials/courses>"}; see workflows/README.md.')
  return { error: 'missing args: ' + MISSING.join(', ') }
}
const KIT = norm(A0.kit)
const MAT = norm(A0.materials)
const C = String(A0.course)
const CD = `${MAT}/courses/${C}`
const GATHER = `${CD}/_archive/gather`
const SEGDIR = `${CD}/facts/seg`
const REF = Math.max(1, Math.min(3, parseInt(A0.refuters || 2, 10) || 2))
const DONE = Object.assign({}, A0.done || {})
const EFFORT = A0.effort || null
const RUN = `cd "${KIT}/scripts" && SLIDEKIT_MATERIALS="${MAT}" PYTHONIOENCODING=utf-8 python`
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
Kit (public tools, style guide, templates, question banks): ${KIT}. Materials (private course files, textbook pages): ${MAT}. Course folder: ${CD}.
Run shell commands with the Bash tool (Git Bash on Windows, bash in a cloud session); if "python" is not found use "python3". Kit scripts are called as: ${RUN} <script>.py --course ${C} ...`

// ---------------- Load: gather settings + textbook page folder ----------------
phase('Load')
const GF = norm(A0.gather_file) || `${CD}/gather.json`
const INFO_PY = `import json,os,glob; from common import load_course; c=load_course('${C}'); d=c.textbook_path('pages_dir') or ''; fs=[f for f in glob.glob(os.path.join(d,'p*_*.*')) if f.lower().endswith(('.jpg','.jpeg','.png'))]; stems=sorted({os.path.splitext(os.path.basename(f))[0] for f in fs if not os.path.splitext(f)[0].endswith(('_a','_b'))}); exts=sorted({os.path.splitext(f)[1].lstrip('.').lower() for f in fs}); print(json.dumps({'pages_dir':d.replace(os.sep,'/'),'page_offset':(c.get('textbook') or {}).get('page_offset'),'stems':stems,'ext':(exts or [''])[0],'halves':any(os.path.splitext(f)[0].endswith('_a') for f in fs)},ensure_ascii=False))`
const LOADED = { type: 'object', properties: { ok: { type: 'boolean' }, gather_json: { type: 'string' }, pages_json: { type: 'string' }, notes: { type: 'string' } }, required: ['ok', 'gather_json', 'pages_json', 'notes'] }
const ld = await agent(`${ENV}

TASK (mechanical; do not create or change any file). Run the two commands below and return their printed output exactly (one JSON line each).
1. Gather settings${A0.gather ? ' (not needed: they were passed inline; return gather_json = "{}")' : ''}: PYTHONIOENCODING=utf-8 python -c "import json,sys; print(json.dumps(json.load(open(sys.argv[1], encoding='utf-8')), ensure_ascii=False))" "${GF}"
2. Textbook page folder: ${RUN} -c "${INFO_PY}"
Return ok=true, gather_json = output of 1, pages_json = output of 2. If a command fails (missing file, invalid JSON, course.yaml without textbook.pages_dir), return ok=false with the error in notes and whatever output you did get (use "{}" for a missing one).`, { label: 'load:gather', phase: 'Load', schema: LOADED, model: 'opus', effort: 'low' })
if (!ld) { log('loader returned null'); return { error: 'loader failed' } }
let G = A0.gather || null
let PG = {}
try { if (!G) G = JSON.parse(ld.gather_json) } catch (e) { log('gather settings are not valid JSON (' + GF + '): ' + e); return { error: 'bad gather.json', notes: ld.notes } }
try { PG = JSON.parse(ld.pages_json || '{}') } catch (e) { PG = {} }
if (!G || !Object.keys(G).length) { log('no gather settings: create ' + GF + ' from templates/gather.template.json. Loader notes: ' + ld.notes); return { error: 'no gather settings', notes: ld.notes } }

const PAGES_DIR = PG.pages_dir || ''
const OFFSET = Number.isInteger(PG.page_offset) ? PG.page_offset : (G.textbook && Number.isInteger(G.textbook.page_offset) ? G.textbook.page_offset : null)
const STEMS = Array.isArray(PG.stems) ? PG.stems : []
const EXT = PG.ext || 'jpg'
const HALVES = !!PG.halves
const on = (k) => G[k] && G[k].enabled !== false && (!Array.isArray(A0.parts) || A0.parts.includes(k))
const PARTS = ['exam', 'literature', 'facts'].filter(on)
log(`course ${C}: parts ${PARTS.join(', ') || '(none)'}; textbook pages ${STEMS.length} in ${PAGES_DIR || '(not found)'} (offset ${OFFSET})`)
if (!PARTS.length) return { error: 'nothing to do: no enabled part in gather settings / args.parts' }
if ((PARTS.includes('facts') || PARTS.includes('exam')) && !STEMS.length) log('WARNING: no textbook page images found; set textbook.pages_dir in course.yaml and run scripts/render_pdf_pages.py. Agents will report missing pages.')

const TB = (G.textbook && G.textbook.name) || 'the textbook named in course.yaml textbook.ref'
const pageNote = `Textbook page images: ${PAGES_DIR || '(textbook.pages_dir in course.yaml)'}/pNN_PPP.${EXT} (full page, about 200 dpi; NN = PDF page, PPP = printed page${OFFSET !== null ? ` = NN + ${OFFSET}` : ''})${HALVES ? ', pNN_PPP_a / _b (top / bottom half, more legible)' : ''}, pNN_PPP.txt (Tesseract OCR, may contain errors), pNN_PPP.tsv (OCR word boxes).`
const COMMON = `${ENV}
Context: ${G.context || `a pathology lecture; read ${CD}/brief.md`}
The ONLY canonical textbook: ${TB}. Literature may only SUPPLEMENT it (${(G.literature && G.literature.purpose) || 'see brief.md'}), must be cited, and must never override it; conflicts must be recorded, not resolved in favour of the paper.
All Chinese you write must be Traditional Chinese (台灣用語). Every technical term in Chinese text must be written as 中文(English), e.g. 分化不良(dysplasia). Use Taiwanese medical terms (the course glossary ${CD}/glossary.md if it exists; the teacher's renderings in ${KIT}/style/guide/20_文字/24_術語與中英對照.md).
${pageNote}
Write your main output to the file path given below (create folders as needed, UTF-8, LF line endings). Your final answer is just the small JSON {path, count, notes}.`
const KS = Array.from({ length: REF }, (_, i) => i + 1)

// ---------------- Exam track ----------------
async function examTrack() {
  const E = G.exam
  const BANK = E.bank
  if (!BANK) { log('exam: gather.exam.bank is missing'); return null }
  const BANKDIR = `${KIT}/question_banks/${BANK}`
  const onlyPath = BANK === '醫師' ? ' In the 醫師 bank only 題號 76-100 (the pathology part of each paper) count; ignore the rest.' : ''
  const cats = (E.categories || []).join(' | ') || 'free text'
  let bankRef = { path: BANKDIR, count: 0, notes: 'existing bank' }
  if (E.update_bank) {
    const U = typeof E.update_bank === 'object' ? E.update_bank : {}
    bankRef = await A(`${COMMON}

TASK: bring the exam question bank ${BANKDIR}/ up to date${U.sessions ? ` (sessions wanted: ${U.sessions})` : ' (add every session that is published but missing from the bank)'}.
Target exam and paper: ${U.exam || E.exam_name || BANK}. Source: ONLY the official 考選部 (Ministry of Examination, MOEX) website. Tools in the kit: ${KIT}/scripts/fetch_moex_dent_exam.py (downloads question/answer/correction PDFs from the MOEX search page; read its docstring; for other exams adjust --exam-keyword / --subject-keyword${U.fetch_args ? `; suggested: ${U.fetch_args}` : ''}) and ${KIT}/scripts/parse_moex_exam.py (docstring explains usage; handles 一律給分 -> "#", 複選 -> "A,C").
Save raw PDFs to ${GATHER}/exam/raw/ (never inside the kit). Write the parsed questions into ${BANKDIR}/ as JSON with keys exactly: 題號 (int), 年度 (int), 第幾次 (int), 科目 (str), question (str), options ({"A":..,"B":..,"C":..,"D":..}), answer (str, after corrections), src (question PDF URL); match the existing files in that folder, keep them, and update ${BANKDIR}/manifest.json (url, local file, bytes, exam code, subject code, session, questions parsed). Do not touch other banks.
Sanity-check: every paper parsed to its full question count (typically 80); spot-check 3 random questions against the PDF text.
Return path = the bank JSON file you wrote, count = total questions in the bank, notes = sessions covered/missing.`, { label: 'exam:download-parse', phase: 'Exam' })
    if (!bankRef) return null
  }
  const classify = (tag) => A(`${COMMON}

TASK (independent classifier ${tag}; another classifier does the same job separately): read the exam bank ${BANKDIR}/*.json (skip manifest.json).${onlyPath} Identify EVERY question whose content falls within this lecture's scope: ${E.scope || 'the textbook chapter of this course'}.${E.include_also ? ' Also include: ' + E.include_also : ''}
To judge answerability use the textbook pages (see above).
For each hit record: key "{年度}-{第幾次}#{題號}", topic (繁中), section (textbook heading), textbook_pages (printed), category (${cats}), answerable_from_text (yes | partial | no), needs (what other source would be needed if not yes), answer (from bank), your own answer reasoning in one sentence, agrees_with_key (true/false).
Write JSON {"hits":[...], "per_paper_counts":{"<年度>-<次>":n,...}} to ${GATHER}/exam/classify_${tag}.json. Return count = number of hits.`, { label: 'exam:classify-' + tag, phase: 'Exam' })
  const [ca, cb] = await parallel([() => classify('a'), () => classify('b')])
  if (!ca || !cb) return null
  const R = E.recommend || {}
  const secs = Array.isArray(R.sections) && R.sections.length ? ' Sections: ' + R.sections.join('; ') + '.' : ''
  return await A(`${COMMON}

TASK: verify and select exam questions for the lecture. Inputs: bank ${BANKDIR}/ ; two independent classifications ${ca.path} and ${cb.path}${E.update_bank ? `; official PDFs in ${GATHER}/exam/raw/` : ''}.${onlyPath}
1. Merge the two hit lists (union). For every candidate, re-check the official answer (bank answer; answer/correction PDFs when available) and re-judge whether it is answerable from the textbook chapter alone (cite printed page). Mark disagreements between classifiers and resolve them by reading the question yourself.
2. Write ${GATHER}/exam/exam_candidates.json: {"candidates":[{key, topic, category, textbook_pages, answerable_from_text, answer_official, answer_verified(bool), note}], "stats": {"per_paper_counts":{...}, "total_in_scope":n, "total_questions":n, "per_category":{...}}}.
3. Recommend ${R.candidates || '12-18'} questions for the lecture (the final deck will use ${R.final || 'the number brief.md asks for'}), ${R.per_section || '3-6'} per section.${secs} Only questions answerable from the textbook chapter (or from it plus a clearly cited supplementary fact). Prefer ${R.prefer || 'recent years, clear stems, relevance to the audience, no duplicates in concept'}. For each give: key, section, the topic slide it should follow, why chosen. Put this in the same JSON under "recommended".
Return path = exam_candidates.json, count = number recommended, notes = key stats (e.g. how many in-scope questions per paper on average) for an opening slide about exam weight.`, { label: 'exam:verify-select', phase: 'Exam' })
}

// ---------------- Literature track ----------------
async function litTrack() {
  const L = G.literature
  const pick = Array.isArray(A0.topics) && A0.topics.length ? A0.topics : null
  const TOPICS = (L.topics || []).filter(t => !pick || pick.includes(t.id))
  if (pick && TOPICS.length < pick.length) log('literature: some args.topics ids not found in gather settings')
  if (!TOPICS.length) { log('literature: no topics'); return [] }
  const imgDir = L.image_dir || 'assets/images/文獻圖'
  const imgSources = L.image_sources || 'Wikimedia Commons (check the licence on the file page: Public domain, CC0, CC BY, CC BY-SA), CDC Public Health Image Library (public domain), or figures from PMC Open Access articles whose licence is CC BY / CC BY-NC (verify the licence statement on the article page). No other sources.'
  return await pipeline(TOPICS,
    (t) => A(`${COMMON}

TASK: literature search for ONE supplement topic.
Topic: ${t.q}
What the textbook already says (canonical; our slides state these facts from the textbook): ${t.r || '(not given; check the textbook pages yourself)'}
Find ${L.claims_per_topic || '3-6'} short, slide-sized claims from peer-reviewed literature (prefer reviews, guidelines, consensus statements or large series from ${L.years || '2010 onwards'}${L.journals ? ` in journals such as ${L.journals}` : ''}${t.sources ? `; for this topic use ${t.sources}` : ''}) that ADD ${L.adds || 'relevance for this audience'} beyond the textbook. Use WebSearch and WebFetch (PubMed: https://pubmed.ncbi.nlm.nih.gov/?term=...). Each claim must come with an exact supporting sentence copied from the abstract/full text (quote), and full citation metadata.
Do not include claims that contradict the textbook; if the literature contradicts the textbook, record it under "conflicts" instead.
Write JSON to ${GATHER}/lit/${t.id}.json:
{"topic":"${t.id}","claims":[{"id":"${t.id}-1","claim_zh":"繁中一句（術語 中文(English)）","claim_en":"...","quote":"exact sentence","citation":{"authors":"First A, Second B, et al.","title":"...","journal":"NLM abbreviation","year":2019,"volume":"90","issue":"1","pages":"23-30","pmid":"...","doi":"..."},"slide_cite":"(資料來源: J Periodontol. 2019;90(1):23-30.)","evidence_type":"review|guideline|cohort|case series|official statistics","relation_to_textbook":"extends|consistent"}],"conflicts":[{"textbook":"...","paper":"...","citation":{...}}]}
Return count = number of claims.`, { label: 'lit:search:' + t.id, phase: 'Literature' }),
    (found, t) => found && A(`${COMMON}

TASK: adversarially VERIFY the literature claims in ${found.path} (topic ${t.id}). Textbook context: ${t.r || '(not given; check the textbook pages yourself)'}
For EACH claim: open https://pubmed.ncbi.nlm.nih.gov/<pmid>/ (or the DOI / official page) with WebFetch and confirm (a) the paper exists with exactly this title/journal/year/volume/issue/pages/PMID/DOI (fix any metadata error), (b) the quote really appears (or the abstract clearly states the claim), (c) claim_zh faithfully reflects the source without overstatement, (d) it does not contradict the textbook (if it does, move it to conflicts). Default to rejecting a claim you cannot verify. Also fix slide_cite to the format "(資料來源: <J Abbrev>. <year>;<vol>(<issue>):<pages>.)".
Write ${GATHER}/lit/${t.id}_verified.json with the same structure plus per-claim fields "verified": true/false and "verify_note". Return count = number of verified claims.`, { label: 'lit:verify:' + t.id, phase: 'Literature' }),
    (ver, t) => (ver && t.images !== false && L.images !== false) ? A(`${COMMON}

TASK: find 1-3 openly licensed images for the lecture topic: ${t.q}
Wanted: ${t.image_wanted || L.image_wanted || `clinical photos of the lesion and/or histology (H&E) that a pathology teacher would show ${G.audience || 'these students'}`}. Acceptable sources ONLY: ${imgSources}
Download each chosen image (curl -L -A "Mozilla/5.0") to ${CD}/${imgDir}/${t.id}_<k>.<ext> (max 2 MB each; prefer >= 800 px on the long side). Then LOOK at each downloaded file with the Read tool to confirm it shows what you claim and is not a thumbnail/placeholder; delete files that fail.
Write ${GATHER}/lit/${t.id}_images.json: {"images":[{"file":"${imgDir}/...","source_url":"file page URL","direct_url":"...","license":"CC BY 4.0","author":"...","title":"...","what_it_shows":"...","caption_zh":"繁中圖說（術語 中文(English)）","credit_line":"圖片來源：<author>, <license>, <source>"}]}
Return count = number of images kept.`, { label: 'lit:images:' + t.id, phase: 'Literature' }) : ver,
  )
}

// ---------------- Textbook facts track ----------------
const pageStems = (s) => STEMS.filter(st => { const m = /^p(\d+)_(\d+)$/.exec(st); return m && +m[1] >= s.pages[0] && +m[1] <= s.pages[1] })
const printed = (n) => (OFFSET !== null ? n + OFFSET : null)
const range = (s) => `PDF pages ${s.pages[0]}-${s.pages[1]}${OFFSET !== null ? ` (printed ${printed(s.pages[0])}-${printed(s.pages[1])})` : ''}`

async function factsTrack() {
  const F = G.facts
  const pick = Array.isArray(A0.segments) && A0.segments.length ? A0.segments : null
  const SEGS = (F.segments || []).filter(s => !pick || pick.includes(s.id))
  if (!SEGS.length) { log('facts: no segments'); return [] }
  const bad = SEGS.filter(s => !/^S\d\d$/.test(s.id)).map(s => s.id)
  if (bad.length) log('WARNING: segment ids ' + bad.join(', ') + ' do not match S01..S99; scripts/merge_facts.py only merges facts/seg/S??_final.json')
  const rel = F.relevance
  const relField = rel && rel.field ? `,"${rel.field}":"${rel.values || 'none|low|high'}${rel.high_means ? ` (high = ${rel.high_means})` : ''}"` : ''
  const yieldTxt = F.yield_per_page || '25-45'
  return await pipeline(SEGS,
    (s) => { const st = pageStems(s); return A(`${COMMON}

TASK: exhaustive fact extraction from ${TB}, segment ${s.id}: ${range(s)}.
Scope: ${s.scope}
Page stems for this segment: ${st.length ? st.join(', ') : '(none found: list the missing pages in notes and stop)'}. READ THE PAGE IMAGES with the Read tool (${HALVES ? 'use the _a/_b half pages, they are legible' : 'if small print is hard to read, crop the column or region with Python/PIL (the .tsv gives word coordinates) into ' + GATHER + '/tmp/ and read the crop'}) and use the OCR text only to speed up transcription; the image is authoritative. If a file is missing, report it in notes and continue with what exists. Pages are usually two-column; read the left column top-to-bottom, then the right column; include KEY CONCEPTS boxes, MORPHOLOGY sections, table contents and figure captions.
Extract EVERY factual statement in scope (aim for completeness: definitions, mechanisms, cells/molecules, numbers/percentages, morphology, clinical features, diagnosis, treatment, prognosis, examples, lists). Typical yield ${yieldTxt} facts per page. Do not merge unrelated facts. Do not add knowledge that is not on the page.
Output JSON to ${SEGDIR}/${s.id}.json:
{"segment":"${s.id}","facts":[{"id":"${s.id}-001","page":<printed page>,"heading":"MAJOR > Sub > Subsub","kind":"definition|mechanism|cell_molecule|number|morphology|clinical|diagnosis|treatment|epidemiology|example|classification|key_concept","en":"faithful English statement (close to the book wording)","quote":"exact short phrase from the page (<= 20 words) that supports it","zh":"繁中一句，術語寫成 中文(English)","fig":"6.13A or null","table":"6.1 or null"${relField}}],
 "figures":[{"fig":"6.13","page":<printed>,"panels":"A-C","caption_en":"full caption text","what_it_shows":"...","teaching_use":"which slide topic it suits"}],
 "tables":[{"table":"6.1","page":<printed>,"title":"...","markdown":"full table transcribed as a markdown table, English as printed"}],
 "headings":[{"page":<printed>,"level":1-4,"text":"..."}]}
Return count = number of facts.`, { label: 'robbins:extract:' + s.id, phase: 'Textbook' }) },
    (ex, s) => ex && parallel(KS.map(k => () => A(`${COMMON}

TASK: independent adversarial REVIEW #${k} of the textbook fact extraction ${ex.path} (segment ${s.id}, ${range(s)}; scope: ${s.scope}).
Page stems: ${pageStems(s).join(', ') || '(none found)'}${HALVES ? ' (use the _a/_b half pages)' : ''}. Check EVERY fact against the page image: is it on that printed page, is the English faithful (no overstatement, no numbers changed, no invented detail), is the zh translation accurate with correct 中文(English) terms (台灣醫學用語), is the quote real, is the heading right? Also transcribed tables and figure captions. Then look for MISSED statements: read the pages yourself paragraph by paragraph and list important facts that the extraction omitted.
Be strict: if you cannot confirm a fact on the page, mark it "unsupported". Reviewer ${k === 1 ? 'one: check in page order from the first page' : k === 2 ? 'two: check in reverse page order from the last page, and pay special attention to numbers, percentages, gene/protein names and table cells' : 'three: start with tables, figure captions and KEY CONCEPTS boxes, then the body text'}.
Write ${SEGDIR}/${s.id}_review${k}.json:
{"verdicts":[{"id":"S..-001","verdict":"ok|wrong|unsupported|page_wrong|zh_wrong","fix":{"en":"...","zh":"...","page":0},"reason":"..."}],"missed":[{"page":0,"heading":"...","en":"...","quote":"...","zh":"...","kind":"..."}],"table_fixes":[...],"figure_fixes":[...]}
Only list verdicts that are not "ok" plus a count of ok. Return count = number of problems (non-ok verdicts + missed).`, { label: `robbins:review${k}:${s.id}`, phase: 'Textbook' }))),
    (revs, s) => (revs && revs.every(Boolean)) ? A(`${COMMON}

TASK: ADJUDICATE the textbook fact extraction for segment ${s.id} (${range(s)}).
Inputs: extraction ${SEGDIR}/${s.id}.json ; reviews ${revs.map(r => r.path).join(' and ')} ; page stems ${pageStems(s).join(', ') || '(none found)'}.
For every disputed fact, look at the page yourself and decide: keep, fix (apply the correct wording/page), or drop. Add every genuinely missed fact (verify on the page first; give new ids ${s.id}-A01, A02...). Apply table/figure fixes that you confirm.
Write the final ledger to ${SEGDIR}/${s.id}_final.json with the same schema as the extraction, plus a top-level "adjudication":{"kept":n,"fixed":n,"dropped":n,"added":n,"notes":"..."}. Also add "contradictions":[...] if the textbook contradicts itself anywhere in this segment (quote both places).
Return count = number of facts in the final ledger.`, { label: 'robbins:adjudicate:' + s.id, phase: 'Textbook' }) : null,
  )
}

const run = (k, f) => (PARTS.includes(k) ? f() : Promise.resolve(null))
const [exam, lit, facts] = await parallel([() => run('exam', examTrack), () => run('literature', litTrack), () => run('facts', factsTrack)])
const nOk = (x) => (Array.isArray(x) ? x.filter(Boolean).length : (x ? 1 : 0))
log(`done: exam ${exam ? 'ok' : '-'}, literature topics ${nOk(lit)}, textbook segments ${nOk(facts)}${aborted ? ' (ABORTED: resume with args.done)' : ''}`)
if (!aborted && (PARTS.includes('facts') || PARTS.includes('literature'))) log(`next: ${RUN} merge_facts.py --course ${C}`)
return { aborted, parts: PARTS, exam, lit, facts }

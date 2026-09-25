export const meta = {
  name: 'immune-gather-content',
  description: 'Robbins ch.6 facts (13 segments, 2 refuters + adjudicator), dental licensing exam bank, dental literature + CC images',
  phases: [
    { title: 'Exam', detail: 'download MOEX dental papers, parse, classify immune questions, verify & select' },
    { title: 'Literature', detail: '14 dental-supplement topics: search -> PubMed verify -> CC image' },
    { title: 'Robbins', detail: '13 segments: extract -> 2 refuters -> adjudicate' },
  ],
}

// 歷史範例：2026-09 免疫課程（immune）原版腳本，只供對照，不要直接執行。
// 已去除本機路徑（<ROOT> 為舊專案根目錄的佔位字）並把模型改成 opus；新課程請用 workflows/ 下的通用版：
// lecture-gather.js＋templates/gather.template.json（說明見 workflows/README.md）。

const ROOT_WIN = '<ROOT>'
const ROOT_BASH = '<ROOT in Git Bash>'
const PNG = ROOT_WIN + '/immune/_archive/robbins_png'
const GATHER = ROOT_WIN + '/immune/_archive/gather'
const RET = { type: 'object', properties: { path: { type: 'string' }, count: { type: 'integer' }, notes: { type: 'string' } }, required: ['path', 'count', 'notes'] }

let aborted = false
async function A(prompt, opts) {
  if (aborted) return null
  const r = await agent(prompt, { model: 'opus', schema: RET, ...opts })
  if (r === null) { aborted = true; log('ABORT: an agent returned null (quota exhausted or skipped) at ' + (opts && opts.label) + ' — stopping all further agents; resume later with resumeFromRunId') }
  return r
}

const COMMON = `
Project root (Windows): ${ROOT_WIN}
Same path in Git Bash: ${ROOT_BASH}
Context: we are building a 3-hour "免疫疾病" pathology lecture for 3rd-year DENTAL students (牙醫三, course code C) of the course's pathology teacher. The ONLY canonical textbook is Robbins, Cotran & Kumar Pathologic Basis of Disease 11th ed, Chapter 6 "Diseases of the Immune System" (printed pages 167-235). Literature may only SUPPLEMENT Robbins (mostly oral/dental manifestations), must be cited, and must never override Robbins; conflicts must be recorded, not resolved in favour of the paper.
All Chinese you write must be Traditional Chinese (台灣用語). Every technical term in Chinese text must be written as 中文(English), e.g. 遺傳性血管性水腫(hereditary angioedema; HAE). Use Taiwanese medical terms; dysplasia = 分化不良.
Write your main output to the file path given below (create folders as needed, UTF-8). Your final answer is just the small JSON {path, count, notes}.`

// ---------------- Exam track ----------------
async function examTrack() {
  phase('Exam')
  const dl = await A(`${COMMON}

TASK: Build the Taiwanese DENTAL licensing exam question bank for the subject that contains oral pathology and oral microbiology & immunology.
Target exam: 專門職業及技術人員高等考試 牙醫師. Since 109年 the dental exam is staged: 牙醫師(一) = first stage (basic sciences). We need its paper "牙醫學(二)" (包括口腔病理學、牙科材料學、口腔微生物學與免疫學、牙科藥理學等科目及其臨床相關知識). Get every session from 109年 through 115年 (第一次 and 第二次 each year; 115年第二次 may exist as of 2026-09). Also get the corresponding pre-staged papers for 104-108年 (the dental exam paper that included 口腔病理學 and 口腔微生物學/免疫學), if they exist.
Source: ONLY the official 考選部 (Ministry of Examination, MOEX) website. Hints: the query UI is https://wwwq.moex.gov.tw/exam/wFrmExamQandASearch.aspx ; files are served by a handler like https://wwwq.moex.gov.tw/exam/wHandExamQandA_File.ashx?t=Q&code=<exam code e.g. 115020>&c=<category code>&s=<subject code>&q=1 (t=Q question PDF, t=S standard answers, t=M answer corrections/更正). Our existing medical files are named like 115020_2301.pdf and 115020_ANS2301.pdf (exam code 115020 = 115年第二次). Discover the dental category and subject codes (use WebFetch / curl -A "Mozilla/5.0"; the search page is ASP.NET, you may need to inspect its HTML/options or try plausible codes). If some sessions are unavailable, record that.
Save PDFs to ${ROOT_WIN}/immune/牙醫師國考/raw/ named {年度}-{次}_Q.pdf, {年度}-{次}_A.pdf, {年度}-{次}_M.pdf (M only if a correction file exists). Each file should be 0.05-2 MB; do not download anything else.
Then write a reusable parser ${ROOT_WIN}/scripts/parse_moex_exam.py (PyMuPDF text layer; handles numbered stems "1." and options (A)-(D); answer PDFs; corrections such as 一律給分 -> "#", 複選 -> "A,B"). Docstring must explain usage. Run it to produce ${ROOT_WIN}/question_banks/牙醫師/questions-dent-{firstyear}-{lastyear}.json as a JSON list with keys exactly: 題號 (int), 年度 (int), 第幾次 (int), 科目 (str), question (str), options ({"A":..,"B":..,"C":..,"D":..}), answer (str, after corrections), src (question PDF URL). Match the style of the existing medical bank ${ROOT_WIN}/questions-104-1_to_114-1.json.
Also write ${ROOT_WIN}/question_banks/牙醫師/manifest.json listing every downloaded file: url, local file, bytes, exam code, subject code, session, question count parsed. Sanity-check: every paper parsed to its full question count (typically 80); spot-check 3 random questions against the PDF text.
Return path = the questions JSON path, count = total questions, notes = sessions covered/missing.`, { label: 'exam:download-parse', phase: 'Exam' })
  if (!dl) return null
  const classify = (tag) => A(`${COMMON}

TASK (independent classifier ${tag}; another classifier does the same job separately): read the dental exam bank ${dl.path}. Identify EVERY question whose content falls within Robbins ch.6 scope: normal immune response (innate/adaptive, receptors, lymphocytes, MHC/HLA, cytokines, antibodies, lymphoid tissues), hypersensitivity types I-IV, tolerance & autoimmunity, SLE, Sjögren syndrome, systemic sclerosis, inflammatory myopathies, MCTD, vasculitis (as in ch.6), IgG4-related disease, transplant rejection, GVHD, primary immunodeficiencies (innate & adaptive defects, complement deficiencies incl. hereditary angioedema), secondary immunodeficiency, HIV/AIDS (incl. oral lesions of HIV), amyloidosis. Also include oral-medicine questions about these diseases (e.g., pemphigus as type II, lichenoid reaction as type IV, oral candidiasis in HIV).
To judge answerability use the rendered Robbins pages: ${PNG}/pNN_PPP.png (+ _a/_b half pages, .txt OCR), where NN = PDF page 01-69 and PPP = printed page (printed = NN+166).
For each hit record: key "{年度}-{第幾次}#{題號}", topic (繁中), ch6_section (Robbins heading), robbins_pages (printed), category (normal_immunity | hypersensitivity | autoimmunity | transplant | immunodeficiency | hiv | amyloid | oral_manifestation), answerable_from_ch6 (yes | partial | no), needs (what other source would be needed if not yes), answer (from bank), your own answer reasoning in one sentence, agrees_with_key (true/false).
Write JSON {"hits":[...], "per_paper_counts":{"109-1":n,...}} to ${GATHER}/exam/classify_${tag}.json. Return count = number of hits.`, { label: 'exam:classify-' + tag, phase: 'Exam' })
  const [ca, cb] = await parallel([() => classify('a'), () => classify('b')])
  if (!ca || !cb) return null
  return await A(`${COMMON}

TASK: verify and select dental exam questions for the lecture. Inputs: bank ${dl.path}; two independent classifications ${ca.path} and ${cb.path}; official PDFs in ${ROOT_WIN}/immune/牙醫師國考/raw/ ; Robbins pages ${PNG}.
1. Merge the two hit lists (union). For every candidate, re-check the official answer against the answer PDF and any correction PDF, and re-judge whether it is answerable from Robbins ch.6 alone (cite printed page). Mark disagreements between classifiers and resolve them by reading the question yourself.
2. Write ${GATHER}/exam/exam_candidates.json: {"candidates":[{key, topic, category, robbins_pages, answerable_from_ch6, answer_official, answer_verified(bool), note}], "stats": {"per_paper_immune_counts":{...}, "total_immune":n, "total_questions":n, "per_category":{...}}}.
3. Recommend 12-18 questions for the lecture (the final deck will use 10-15), 3-6 per hour: hour 1 = normal immunity review + hypersensitivity I-IV; hour 2 = autoimmunity (SLE, Sjögren, systemic sclerosis, IgG4-RD...) + transplant/GVHD; hour 3 = immunodeficiency (primary, HIV/AIDS with oral lesions) + amyloidosis. Only questions answerable from Robbins ch.6 (or from ch.6 plus a clearly cited oral-manifestation fact). Prefer recent years, clear stems, dental relevance, no duplicates in concept. For each give: key, hour, the topic slide it should follow, why chosen. Put this in the same JSON under "recommended".
Return path = exam_candidates.json, count = number recommended, notes = key stats (e.g. how many immune questions per paper on average) for an opening slide about exam weight.`, { label: 'exam:verify-select', phase: 'Exam' })
}

// ---------------- Literature track ----------------
const TOPICS = [
  { id: 'innate_defect_perio', q: '先天免疫缺陷與牙周炎：白血球黏附缺陷(leukocyte adhesion deficiency; LAD)、Chediak-Higashi 症候群、慢性肉芽腫病(chronic granulomatous disease; CGD)、嗜中性球減少的口腔表現（早發性／侵襲性牙周炎、口腔潰瘍）', r: 'Robbins p.213-214 (Table 6.12): LAD1 = defective beta2 integrin (CD18), LAD2 = absent sialyl-Lewis X (fucosyl transferase); recurrent bacterial infections; CGD = NADPH oxidase defect; Chediak-Higashi = defective lysosomal fusion (LYST). Robbins ch.6 does NOT mention periodontitis or gingivitis.' },
  { id: 'hae_dental', q: '遺傳性血管性水腫(hereditary angioedema; HAE)與牙科處置：拔牙等處置誘發上呼吸道水腫、術前預防', r: 'Robbins p.214: C1 inhibitor deficiency -> hereditary angioedema; episodic edema of skin and mucosal surfaces (larynx, GI tract) often precipitated by emotional stress or trauma; mediated by bradykinin; treated with C1 inhibitor.' },
  { id: 'local_anesthetic_allergy', q: '局部麻醉藥過敏的真實頻率（真正 IgE 媒介過敏罕見）與牙科診間的全身性過敏性反應(anaphylaxis)、乳膠(latex)過敏', r: 'Robbins p.184-185: type I hypersensitivity; systemic anaphylaxis can follow drugs (e.g. penicillin), insect venom, foods; minutes after exposure; laryngeal edema, bronchoconstriction, shock; epinephrine.' },
  { id: 'dental_material_type4', q: '牙科材料的第四型過敏：鎳(nickel)、甲基丙烯酸酯(methacrylates)接觸性過敏，汞合金(amalgam)相關的口腔苔蘚樣病變(oral lichenoid lesion)', r: 'Robbins p.189-191: type IV (T cell-mediated) hypersensitivity; contact dermatitis (e.g. poison ivy, nickel?) is a CD4 T cell reaction to modified self proteins; delayed-type reactions take 24-48 h.' },
  { id: 'pemphigus_oral', q: '尋常性天疱瘡(pemphigus vulgaris)的口腔病灶：常為首發部位、比例、desmoglein 3 抗體', r: 'Robbins Table 6.3 (p.187): pemphigus vulgaris is an antibody-mediated (type II) disease; antigen = proteins in intercellular junctions of epidermal cells (desmoglein); mechanism antibody-mediated activation of proteases, disruption of intercellular adhesions; manifestation skin vesicles (bullae).' },
  { id: 'sle_oral', q: '全身性紅斑性狼瘡(systemic lupus erythematosus; SLE)的口腔病灶：盛行率、型態（潰瘍、盤狀病灶）、分類標準中的口腔潰瘍', r: 'Robbins Table 6.9 (p.197): oral ulcers (oral or nasopharyngeal ulceration, usually painless) are a classification criterion; skin: malar rash, discoid rash, photosensitivity.' },
  { id: 'sjogren_oral', q: '修格蘭症候群(Sjögren syndrome)：唇部小唾液腺切片(labial minor salivary gland biopsy)與 focus score（2016 ACR/EULAR 分類標準）、口乾造成的齲齒(dental caries)與口腔念珠菌病', r: 'Robbins p.203-204: dry eyes (keratoconjunctivitis sicca) and dry mouth (xerostomia) from immune destruction of lacrimal and salivary glands; periductal and perivascular lymphocytic infiltrate, germinal centers; lip biopsy (minor salivary glands) essential for diagnosis(? verify on page); anti-SS-A (Ro)/SS-B (La); ~5% develop marginal zone lymphoma.' },
  { id: 'ssc_oral', q: '全身性硬化症(systemic sclerosis; scleroderma)的口腔表現：小口症(microstomia)、牙周韌帶間隙增寬(periodontal ligament space widening)、下顎骨吸收', r: 'Robbins p.204-206: fibrosis of skin and internal organs; face becomes a drawn mask; Raynaud phenomenon; GI involvement (esophagus) common.' },
  { id: 'igg4_salivary', q: 'IgG4 相關疾病(IgG4-related disease)的唾液腺表現：Mikulicz 病、Küttner 腫瘤（慢性硬化性唾液腺炎 chronic sclerosing sialadenitis）', r: 'Robbins p.207-208: IgG4-RD = tumor-like lesions with dense lymphoplasmacytic infiltrate rich in IgG4+ plasma cells, storiform fibrosis, obliterative phlebitis; elevated serum IgG4 in many; includes Mikulicz syndrome (lacrimal & salivary), Riedel thyroiditis, autoimmune pancreatitis; Fig 6.31C submandibular gland; responds to steroids/rituximab.' },
  { id: 'oral_gvhd', q: '口腔慢性移植物對抗宿主病(chronic graft-versus-host disease; cGVHD)：苔蘚樣變化、口乾、NIH 共識診斷標準', r: 'Robbins p.211-212: GVHD after hematopoietic stem cell transplantation; donor T cells attack host; acute GVHD skin, liver (bile ducts), GI mucosa ulceration; chronic GVHD resembles autoimmune diseases (skin fibrosis like systemic sclerosis, etc.).' },
  { id: 'hiv_oral', q: '人類免疫缺乏病毒(HIV)感染的口腔病灶分類（EC-Clearinghouse 1993）：口腔念珠菌病、口腔毛狀白斑(oral hairy leukoplakia)、卡波西肉瘤(Kaposi sarcoma)、非何杰金氏淋巴瘤、HIV 相關牙周病；抗反轉錄病毒治療後的變化', r: 'Robbins p.226-228: oral candidiasis (thrush) often an early sign of immune decline; herpes simplex ulcers; Kaposi sarcoma (KSHV/HHV8); B-cell lymphomas; oral hairy leukoplakia = EBV, white confluent patches on the tongue; incidence of many of these falls with ART.' },
  { id: 'amyloid_oral', q: '類澱粉症(amyloidosis)的口腔表現與診斷：巨舌症(macroglossia)、牙齦或唇腺切片的敏感度', r: 'Robbins p.233-234: tongue involvement -> macroglossia ("tumor-forming amyloid of the tongue"), hampers speech and swallowing; diagnosis by biopsy - abdominal fat aspirate, or gingival or rectal biopsy; Congo red with apple-green birefringence.' },
  { id: 'hyper_ige_teeth', q: '高 IgE 症候群(hyper-IgE syndrome; Job syndrome; STAT3 缺陷)的牙齒與口腔表現：乳牙滯留(retained primary teeth)、慢性黏膜皮膚念珠菌病', r: 'Robbins ch.6 p.217-218 (verify): defects in lymphocyte activation, Th17 defects -> chronic mucocutaneous candidiasis; hyper-IgE (Job) syndrome with STAT3 mutations and defective Th17 responses (check page).' },
  { id: 'taiwan_hiv', q: '台灣 HIV 流行病學在地數據（衛生福利部疾病管制署，最新年度新增通報數、主要傳染途徑、年齡層）', r: 'Robbins p.219: worldwide epidemiology; transmission sexual, parenteral, mother-to-infant; in the US men who have sex with men are the largest group.' },
]

async function litTrack() {
  phase('Literature')
  return await pipeline(TOPICS,
    (t) => A(`${COMMON}

TASK: literature search for ONE dental-supplement topic.
Topic: ${t.q}
What Robbins ch.6 already says (canonical; our slides state these facts from Robbins): ${t.r}
Find 3-6 short, slide-sized claims from peer-reviewed literature (prefer reviews, guidelines, consensus statements or large series from 2010-2026 in journals such as Oral Dis, Oral Surg Oral Med Oral Pathol Oral Radiol, J Oral Pathol Med, J Dent Res, J Periodontol, J Am Dent Assoc, Br Dent J, Ann Rheum Dis, Arthritis Rheumatol, Biol Blood Marrow Transplant/Transplant Cell Ther, J Allergy Clin Immunol; for taiwan_hiv use 衛生福利部疾病管制署 official statistics) that ADD dental/oral relevance beyond Robbins. Use WebSearch and WebFetch (PubMed: https://pubmed.ncbi.nlm.nih.gov/?term=...). Each claim must come with an exact supporting sentence copied from the abstract/full text (quote), and full citation metadata.
Do not include claims that contradict Robbins; if the literature contradicts Robbins, record it under "conflicts" instead.
Write JSON to ${GATHER}/lit/${t.id}.json:
{"topic":"${t.id}","claims":[{"id":"${t.id}-1","claim_zh":"繁中一句（術語 中文(English)）","claim_en":"...","quote":"exact sentence","citation":{"authors":"First A, Second B, et al.","title":"...","journal":"NLM abbreviation","year":2019,"volume":"90","issue":"1","pages":"23-30","pmid":"...","doi":"..."},"slide_cite":"(資料來源: J Periodontol. 2019;90(1):23-30.)","evidence_type":"review|guideline|cohort|case series|official statistics","relation_to_robbins":"extends|consistent"}],"conflicts":[{"robbins":"...","paper":"...","citation":{...}}]}
Return count = number of claims.`, { label: 'lit:search:' + t.id, phase: 'Literature' }),
    (found, t) => found && A(`${COMMON}

TASK: adversarially VERIFY the literature claims in ${found.path} (topic ${t.id}). Robbins context: ${t.r}
For EACH claim: open https://pubmed.ncbi.nlm.nih.gov/<pmid>/ (or the DOI / official page) with WebFetch and confirm (a) the paper exists with exactly this title/journal/year/volume/issue/pages/PMID/DOI (fix any metadata error), (b) the quote really appears (or the abstract clearly states the claim), (c) claim_zh faithfully reflects the source without overstatement, (d) it does not contradict Robbins ch.6 (if it does, move it to conflicts). Default to rejecting a claim you cannot verify. Also fix slide_cite to the format "(資料來源: <J Abbrev>. <year>;<vol>(<issue>):<pages>.)".
Write ${GATHER}/lit/${t.id}_verified.json with the same structure plus per-claim fields "verified": true/false and "verify_note". Return count = number of verified claims.`, { label: 'lit:verify:' + t.id, phase: 'Literature' }),
    (ver, t) => (ver && t.id !== 'taiwan_hiv') ? A(`${COMMON}

TASK: find 1-3 openly licensed images for the lecture topic: ${t.q}
Wanted: clinical photos of the oral lesion and/or histology (H&E) that a pathology teacher would show dental students. Acceptable sources ONLY: Wikimedia Commons (check the license on the file page: Public domain, CC0, CC BY, CC BY-SA), CDC Public Health Image Library (public domain), or figures from PMC Open Access articles whose license is CC BY / CC BY-NC (verify the license statement on the article page). No other sources.
Download each chosen image (curl -L -A "Mozilla/5.0") to ${ROOT_WIN}/immune/assets/images/文獻圖/${t.id}_<k>.<ext> (max 2 MB each; prefer >= 800 px on the long side). Then LOOK at each downloaded file with the Read tool to confirm it shows what you claim and is not a thumbnail/placeholder; delete files that fail.
Write ${GATHER}/lit/${t.id}_images.json: {"images":[{"file":"immune/assets/images/文獻圖/...","source_url":"file page URL","direct_url":"...","license":"CC BY 4.0","author":"...","title":"...","what_it_shows":"...","caption_zh":"繁中圖說（術語 中文(English)）","credit_line":"圖片來源：<author>, <license>, <source>"}]}
Return count = number of images kept.`, { label: 'lit:images:' + t.id, phase: 'Literature' }) : null,
  )
}

// ---------------- Robbins track ----------------
const SEGS = [
  { id: 'S01', pages: [1, 6], scope: 'chapter opener/contents (record the contents list with printed pages), NORMAL IMMUNE RESPONSE: innate immunity, components, receptors (TLR, NLR, inflammasome, cytosolic nucleic-acid receptors), NK cells, reactions of innate immunity, adaptive immunity, lymphocytes, lymphocyte diversity, T lymphocytes' },
  { id: 'S02', pages: [7, 11], scope: 'B lymphocytes, myeloid cells (dendritic cells, macrophages), tissues of the immune system, MHC molecules, cytokines, overview of lymphocyte activation, display and recognition of antigens, start of cell-mediated immunity' },
  { id: 'S03', pages: [12, 15], scope: 'cell-mediated immunity, humoral immunity, decline of immune responses and memory, KEY CONCEPTS normal immune response, HYPERSENSITIVITY intro and classification' },
  { id: 'S04', pages: [16, 19], scope: 'Table 6.1 and Immediate (Type I) hypersensitivity through its KEY CONCEPTS; STOP at the heading "Antibody-Mediated (Type II) Hypersensitivity" on p.185' },
  { id: 'S05', pages: [19, 25], scope: 'START at "Antibody-Mediated (Type II) Hypersensitivity" (p.185); types II, III, IV, KEY CONCEPTS; STOP at the heading AUTOIMMUNE DISEASES on p.191' },
  { id: 'S06', pages: [25, 30], scope: 'START at AUTOIMMUNE DISEASES (p.191): Table 6.6, immunologic tolerance (central, peripheral), mechanisms of autoimmunity, susceptibility genes, Tables 6.7-6.8, infections and environment, KEY CONCEPTS, general features of autoimmune diseases (through p.196)' },
  { id: 'S07', pages: [31, 37], scope: 'SYSTEMIC LUPUS ERYTHEMATOSUS: Tables 6.9-6.11, autoantibodies, ANA patterns, pathogenesis, morphology (all organs), clinical features, chronic discoid / subacute cutaneous / drug-induced LE, KEY CONCEPTS SLE; STOP at the heading Rheumatoid Arthritis on p.203' },
  { id: 'S08', pages: [37, 42], scope: 'START at Rheumatoid Arthritis (p.203): RA pointer, Sjögren syndrome (pathogenesis, morphology, clinical, KEY CONCEPTS), systemic sclerosis (pathogenesis, morphology, clinical, KEY CONCEPTS), inflammatory myopathies, mixed connective tissue disease, polyarteritis nodosa and other vasculitides, IgG4-related disease (incl. Fig 6.31); STOP at REJECTION OF TISSUE TRANSPLANTS on p.208' },
  { id: 'S09', pages: [42, 47], scope: 'START at REJECTION OF TISSUE TRANSPLANTS (p.208): recognition of alloantigens, patterns and mechanisms of rejection (hyperacute, acute cellular, acute antibody-mediated, chronic), morphology, methods of increasing graft survival, hematopoietic stem cell transplantation, GVHD, KEY CONCEPTS, Fig 6.36; STOP at IMMUNODEFICIENCY DISEASES on p.213' },
  { id: 'S10', pages: [47, 52], scope: 'START at IMMUNODEFICIENCY DISEASES (p.213): primary immunodeficiencies, defects in innate immunity (leukocyte function, Table 6.12, complement deficiencies incl. hereditary angioedema), defects in adaptive immunity (SCID, XLA, DiGeorge, hyper-IgM, CVID, IgA deficiency, XLP, other activation defects, immune regulatory disorders), immunodeficiencies with systemic diseases (Wiskott-Aldrich, ataxia telangiectasia), KEY CONCEPTS; STOP at Secondary Immunodeficiencies on p.218' },
  { id: 'S11', pages: [52, 58], scope: 'START at Secondary (Acquired) Immunodeficiencies (p.218): Table 6.13, AIDS epidemiology, transmission, etiology (HIV structure, genome), pathogenesis (life cycle, infection of cells, replication, T-cell depletion, non-T cells, Table 6.14, B-cell function, CNS), start of natural history (through p.224)' },
  { id: 'S12', pages: [59, 64], scope: 'HIV natural history (acute retroviral syndrome, clinical latency, AIDS), clinical features, Table 6.15, opportunistic infections, Table 6.16, tumors (Kaposi sarcoma, lymphomas, oral hairy leukoplakia, other tumors), CNS disease, effect of antiretroviral therapy, MORPHOLOGY, KEY CONCEPTS HIV/AIDS; STOP at AMYLOIDOSIS on p.230' },
  { id: 'S13', pages: [64, 68], scope: 'START at AMYLOIDOSIS (p.230): properties, physical and chemical nature, pathogenesis and classification (AL, AA, ATTR, Table 6.17, heredofamilial, hemodialysis-associated, localized, endocrine), morphology (kidney, spleen, liver, heart, other organs incl. tongue), clinical features, diagnosis, KEY CONCEPTS' },
]
const pad = (n) => String(n).padStart(2, '0')
const pageList = (s) => { const out = []; for (let p = s.pages[0]; p <= s.pages[1]; p++) out.push(`p${pad(p)}_${p + 166}`); return out.join(', ') }

async function robbinsTrack() {
  phase('Robbins')
  return await pipeline(SEGS,
    (s) => A(`${COMMON}

TASK: exhaustive fact extraction from Robbins 11e ch.6, segment ${s.id}: PDF pages ${s.pages[0]}-${s.pages[1]} (printed ${s.pages[0] + 166}-${s.pages[1] + 166}).
Scope: ${s.scope}
Page files in ${PNG}/ : for each page stem (${pageList(s)}) there is STEM.png (full page, 200 dpi), STEM_a.png (top half), STEM_b.png (bottom half), STEM.txt (Tesseract OCR, may contain errors). If a file is missing, report it in notes and continue with what exists. READ THE HALF-PAGE IMAGES with the Read tool (they are legible) and use the OCR text only to speed up transcription — the image is authoritative. Pages are two-column; read left column top-to-bottom then right column; include KEY CONCEPTS boxes, MORPHOLOGY sections, table contents and figure captions.
Extract EVERY factual statement in scope (aim for completeness: definitions, mechanisms, cells/molecules, numbers/percentages, morphology, clinical features, diagnosis, treatment, prognosis, examples, lists). Typical yield 25-45 facts per page. Do not merge unrelated facts. Do not add knowledge that is not on the page.
Output JSON to ${ROOT_WIN}/immune/facts/seg/${s.id}.json:
{"segment":"${s.id}","facts":[{"id":"${s.id}-001","page":<printed page>,"heading":"MAJOR > Sub > Subsub","kind":"definition|mechanism|cell_molecule|number|morphology|clinical|diagnosis|treatment|epidemiology|example|classification|key_concept","en":"faithful English statement (close to the book wording)","quote":"exact short phrase from the page (<= 20 words) that supports it","zh":"繁中一句，術語寫成 中文(English)","fig":"6.13A or null","table":"6.1 or null","dental":"none|low|high (high = mouth, teeth, salivary glands, tongue, gingiva, oral mucosa, jaw, face, pharynx/tonsil)"}],
 "figures":[{"fig":"6.13","page":<printed>,"panels":"A-C","caption_en":"full caption text","what_it_shows":"...","teaching_use":"which slide topic it suits"}],
 "tables":[{"table":"6.1","page":<printed>,"title":"...","markdown":"full table transcribed as a markdown table, English as printed"}],
 "headings":[{"page":<printed>,"level":1-4,"text":"..."}]}
Return count = number of facts.`, { label: 'robbins:extract:' + s.id, phase: 'Robbins' }),
    (ex, s) => ex && parallel([1, 2].map(k => () => A(`${COMMON}

TASK: independent adversarial REVIEW #${k} of the Robbins fact extraction ${ex.path} (segment ${s.id}, PDF pages ${s.pages[0]}-${s.pages[1]}, printed ${s.pages[0] + 166}-${s.pages[1] + 166}; scope: ${s.scope}).
Page images: ${PNG}/ (${pageList(s)}; use the _a/_b half pages). Check EVERY fact against the page image: is it on that printed page, is the English faithful (no overstatement, no numbers changed, no invented detail), is the zh translation accurate with correct 中文(English) terms (台灣醫學用語), is the quote real, is the heading right? Also transcribed tables and figure captions. Then look for MISSED statements: read the pages yourself paragraph by paragraph and list important facts that the extraction omitted.
Be strict: if you cannot confirm a fact on the page, mark it "unsupported". Reviewer ${k === 1 ? 'one: check in page order from the first page' : 'two: check in reverse page order from the last page, and pay special attention to numbers, percentages, gene/protein names and table cells'}.
Write ${ROOT_WIN}/immune/facts/seg/${s.id}_review${k}.json:
{"verdicts":[{"id":"S..-001","verdict":"ok|wrong|unsupported|page_wrong|zh_wrong","fix":{"en":"...","zh":"...","page":0} ,"reason":"..."}],"missed":[{"page":0,"heading":"...","en":"...","quote":"...","zh":"...","kind":"..."}],"table_fixes":[...],"figure_fixes":[...]}
Only list verdicts that are not "ok" plus a count of ok. Return count = number of problems (non-ok verdicts + missed).`, { label: `robbins:review${k}:${s.id}`, phase: 'Robbins' }))),
    (revs, s) => (revs && revs.every(Boolean)) ? A(`${COMMON}

TASK: ADJUDICATE the Robbins fact extraction for segment ${s.id} (PDF pages ${s.pages[0]}-${s.pages[1]}).
Inputs: extraction ${ROOT_WIN}/immune/facts/seg/${s.id}.json ; reviews ${revs.map(r => r.path).join(' and ')} ; page images ${PNG}/ (${pageList(s)}).
For every disputed fact, look at the page yourself and decide: keep, fix (apply the correct wording/page), or drop. Add every genuinely missed fact (verify on the page first; give new ids ${s.id}-A01, A02...). Apply table/figure fixes that you confirm.
Write the final ledger to ${ROOT_WIN}/immune/facts/seg/${s.id}_final.json with the same schema as the extraction, plus a top-level "adjudication":{"kept":n,"fixed":n,"dropped":n,"added":n,"notes":"..."}. Also add "contradictions":[...] if Robbins contradicts itself anywhere in this segment (quote both places).
Return count = number of facts in the final ledger.`, { label: 'robbins:adjudicate:' + s.id, phase: 'Robbins' }) : null,
  )
}

const [exam, lit, rob] = await parallel([() => examTrack(), () => litTrack(), () => robbinsTrack()])
return { aborted, exam, lit, rob }

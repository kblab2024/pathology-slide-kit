// check_workflows.js: static checks + a stub dry run for every workflow script in workflows/ (and workflows/reference/).
// Usage: node workflows/tools/check_workflows.js [--no-run]
// 1. file checks: no CR characters, no forbidden words or absolute local paths, meta is a pure literal;
// 2. syntax: wraps the body as the Workflow runtime does ("export const meta" -> "const meta", async IIFE with stub
//    agent/parallel/pipeline/phase/log/args/budget/workflow) and compiles it with vm.Script (same as node --check);
// 3. dry run (skip with --no-run): runs the top-level workflows with fake args and stub agents that return
//    {path, count, notes} (or loader JSON), and reports the agent labels each one would spawn.
'use strict'
const fs = require('fs')
const path = require('path')
const vm = require('vm')

const WF = path.resolve(__dirname, '..')
const files = []
for (const d of [WF, path.join(WF, 'reference')]) {
  if (!fs.existsSync(d)) continue
  for (const f of fs.readdirSync(d)) if (f.endsWith('.js')) files.push(path.join(d, f))
}
const BAD_WORDS = [['fab', 'le'].join(''), ['One', 'Drive'].join('')]
const ABS_PATH = /(^|[^A-Za-z0-9])[A-Za-z]:[\\/](?![\\/])|\/home\/[a-z]|\/Users\/[A-Za-z]|C:\\\\Users/
let failures = 0
const say = (ok, msg) => { if (!ok) failures++; console.log((ok ? 'ok   ' : 'FAIL ') + msg) }

function wrap(src) {
  const body = src.replace(/^export const meta\s*=/m, 'const meta =')
  return `(async () => {\n${body}\n})`
}

for (const f of files) {
  const rel = path.relative(path.resolve(WF, '..'), f).replace(/\\/g, '/')
  const src = fs.readFileSync(f, 'utf8')
  say(!src.includes('\r'), `${rel}: no CR characters`)
  for (const w of BAD_WORDS) say(!src.toLowerCase().includes(w.toLowerCase()), `${rel}: no "${w}"`)
  const abs = src.split('\n').map((l, i) => [i + 1, l]).filter(([, l]) => ABS_PATH.test(l))
  say(!abs.length, `${rel}: no absolute local paths${abs.length ? ' (lines ' + abs.map(a => a[0]).join(', ') + ')' : ''}`)
  say(/^export const meta = \{/.test(src), `${rel}: starts with "export const meta = {"`)
  const m = /^export const meta = (\{[\s\S]*?\n\})/m.exec(src)
  let pure = false
  if (m) {
    const code = m[1].replace(/'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*"/g, "''")   // drop string contents
    try { pure = !/\$\{|\.\.\.|`|\(/.test(code) && typeof vm.runInNewContext('(' + m[1] + ')', {}) === 'object' } catch (e) { pure = false }
  }
  say(pure, `${rel}: meta is a pure literal`)
  try { new vm.Script(wrap(src), { filename: rel }); say(true, `${rel}: syntax (wrapped like the Workflow runtime)`) } catch (e) { say(false, `${rel}: syntax: ${e.message}`) }
}

async function dryRun(file, args, loaderJson) {
  const labels = []
  const logs = []
  const agent = async (prompt, opts) => {
    opts = opts || {}
    labels.push(opts.label || '(no label)')
    if (opts.model !== 'opus') throw new Error('agent without model opus: ' + opts.label)
    if (typeof prompt !== 'string' || prompt.includes('undefined') || prompt.includes('[object Object]')) throw new Error('suspicious prompt text in ' + opts.label + ': ' + (prompt.match(/.{0,60}(undefined|\[object Object\]).{0,60}/) || [''])[0])
    if (opts.label && opts.label.startsWith('load:')) return loaderJson
    return { path: '/stub/' + (opts.label || 'x').replace(/[^A-Za-z0-9_-]/g, '_') + '.json', count: 3, notes: 'stub' }
  }
  const parallel = async (thunks) => Promise.all(thunks.map(t => t().catch(() => null)))
  const pipeline = async (items, ...stages) => Promise.all(items.map(async (it, i) => {
    let v = it
    for (let s = 0; s < stages.length; s++) { try { v = await stages[s](s === 0 ? it : v, it, i) } catch (e) { return null } }
    return v
  }))
  const ctx = { agent, parallel, pipeline, phase: () => {}, log: (m) => logs.push(m), args, budget: { total: null, spent: () => 0, remaining: () => Infinity }, workflow: async () => null, console }
  vm.createContext(ctx)
  const fn = vm.runInContext(wrap(fs.readFileSync(file, 'utf8')), ctx, { filename: file })
  const ret = await fn()
  return { ret, labels, logs }
}

async function main() {
  if (process.argv.includes('--no-run')) return
  const base = { kit: '/k/pathology-slide-kit', materials: '/m/pathology-slide-materials', course: 'immune' }
  const tpl = JSON.parse(fs.readFileSync(path.join(WF, '..', 'templates', 'gather.template.json'), 'utf8'))
  const stems = Array.from({ length: 69 }, (_, i) => `p${String(i + 1).padStart(2, '0')}_${i + 167}`)
  const gatherLoad = { ok: true, gather_json: JSON.stringify(tpl), pages_json: JSON.stringify({ pages_dir: '/m/textbook/pages', page_offset: 166, stems, ext: 'jpg', halves: false }), notes: '' }
  const batches = { batches: [{ k: 1, slugs: ['a', 'b'], segments: ['S1-01'], prev: '', next: 'c' }, { k: 2, slugs: ['c'], segments: ['S1-02'], prev: 'b', next: '' }] }
  const batchLoad = { ok: true, json_text: JSON.stringify(batches), notes: '' }
  const cases = [
    ['lecture-gather.js', base, gatherLoad, 13 * 4 + 3 + 14 * 3 - 1 + 1],
    ['lecture-gather.js', { ...base, parts: ['facts'], segments: ['S01', 'S02'], refuters: 1 }, gatherLoad, 2 * 3 + 1],
    ['lecture-blueprint.js', base, null, 1 + 3 + 3 + 3],
    ['lecture-write.js', base, batchLoad, 1 + 2 * 5 + 1],
    ['lecture-write.js', { ...base, batches: batches.batches, done: { 'write:1': '/old/batch_1_draft.json' } }, null, 2 * 5 + 1 - 1],
    ['lecture-review.js', { ...base, pptx: '/m/x.pptx' }, null, 1 + 6 * 3 + 1],
    ['lecture-review.js', { ...base, pptx: '/m/x.pptx', pngs: '/m/png', lenses: ['facts', 'layout'], refuters: 1 }, null, 2 * 2 + 1],
    ['style-mining.js', { kit: base.kit, materials: base.materials }, null, 22 * 4],
    ['style-mining.js', { ...base, dims: ['12_字級', 'EXAM'] }, null, 2 * 4 + 1],
    ['style-guide.js', { kit: base.kit, materials: base.materials, course: 'immune', date: '2026-09-25' }, null, 23 * 2 + 2 + 1],
    ['lecture-write.js', { kit: base.kit }, null, 0],
  ]
  for (const [f, a, lj, expect] of cases) {
    try {
      const r = await dryRun(path.join(WF, f), a, lj)
      const okN = r.labels.length === expect
      say(okN && !(r.ret && r.ret.error && expect > 0), `dry run ${f} ${JSON.stringify(Object.keys(a).filter(k => !['kit', 'materials', 'course'].includes(k)))}: ${r.labels.length} agents (expected ${expect})${r.ret && r.ret.error ? ' returned error: ' + r.ret.error : ''}`)
      if (!okN) console.log('     labels: ' + r.labels.join(', '))
    } catch (e) { say(false, `dry run ${f}: ${e.message}`) }
  }
}

main().then(() => { console.log(failures ? `${failures} FAIL` : 'all checks passed'); process.exit(failures ? 1 : 0) })

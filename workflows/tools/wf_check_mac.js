// 沒有 node 的 Mac：用 macOS 內建的 JavaScriptCore（osascript -l JavaScript）檢查工作流腳本的語法，並用假代理空跑、數代理數。
// 用法：osascript -l JavaScript wf_check_mac.js <腳本.js> <args.json> [load_mock.json]
//   load_mock.json：給 lecture-gather 之類有「讀設定代理」的腳本，假代理遇到 label 開頭為 load: 時回傳它的內容。
// 印出：代理數、每個代理的 label|model|effort|phase、各強度的代理數（effort_counts）、沒寫 effort 的代理（no_effort）、log、回傳值。
// 每個 agent() 都要是 model opus，也都要明寫 effort（kit AGENTS.md 硬規則 8）；no_effort 不是空的就要改腳本或 args。
ObjC.import('Foundation');
const rd = (p) => $.NSString.stringWithContentsOfFileEncodingError(p, $.NSUTF8StringEncoding, null).js;
async function main(argv) {
  const s = rd(argv[0]);
  const a = JSON.parse(rd(argv[1]));
  const LM = argv[2] ? JSON.parse(rd(argv[2])) : null;
  const body = s.replace(/^export const meta =/m, 'const meta =');
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
  let f;
  try { f = new AsyncFunction('args', 'agent', 'parallel', 'pipeline', 'log', 'phase', 'budget', 'workflow', body); }
  catch (e) { return 'SYNTAX ERROR: ' + e; }
  const labels = [], logs = [];
  const agent = async (p, o) => {
    labels.push((o.label || '?') + '|' + o.model + '|' + (o.effort || '-') + '|' + (o.phase || ''));
    if (LM && String(o.label || '').startsWith('load:')) return LM;
    return { path: '/dry/' + o.label, count: 1, notes: '' };
  };
  const parallel = async (th) => Promise.all(th.map(t => t().catch(() => null)));
  const pipeline = async (items, ...st) => Promise.all(items.map(async (it, i) => { let r = it; for (const x of st) { r = await x(r, it, i); if (r === null || r === undefined) return null; } return r; }));
  let out, err = null;
  try { out = await f(a, agent, parallel, pipeline, (m) => logs.push(m), () => {}, { total: null, spent: () => 0, remaining: () => Infinity }, null); }
  catch (e) { err = String(e); }
  const notOpus = labels.filter(l => l.split('|')[1] !== 'opus');
  const noEffort = labels.filter(l => l.split('|')[2] === '-');
  const effortCounts = {};
  labels.forEach(l => { const e = l.split('|')[2]; effortCounts[e] = (effortCounts[e] || 0) + 1; });
  return JSON.stringify({ syntax: 'OK', agents: labels.length, effort_counts: effortCounts, not_opus: notOpus, no_effort: noEffort, labels, logs, err, out }, null, 1);
}
function run(argv) { main(argv).then(r => console.log(r), e => console.log('ERR ' + e)); return ''; }

# -*- coding: utf-8 -*-
"""重建 Workflow 的 args.done（{label: 輸出檔路徑}），跨 session 續跑、換環境（本機 ↔ 雲端）或改了腳本之後用。

來源一（優先）：執行紀錄 journal.jsonl（每次執行一個資料夾）
  ~/.claude/projects/<專案代號>/<session id>/subagents/workflows/<runId>/journal.jsonl
  "started" 行有 label＋key＋agentId；"result" 行有 key＋agentId＋result（代理回傳的 {path, count, notes}）。
  同一資料夾的 agent-*.jsonl 是各代理的完整對話，出問題時用來查原因。
來源二（journal 不見時的備案，例如雲端 VM 已回收）：--scan 依輸出檔名推回 label。
  檔案存在不保證那個代理當時有做完（可能寫到一半額度就用完），掃描結果請先看過再用；最後一批步驟可用 --drop 強迫重跑。

用法：
  python done_from_journal.py <journal.jsonl 或 run 資料夾> [更多...] [選項]
  python done_from_journal.py --scan write --dir <課程>/_archive/written [選項]
      --scan 種類與 --dir：
        gather     課程資料夾 <materials>/courses/<課>（讀 facts/seg/、_archive/gather/exam/、_archive/gather/lit/）
        blueprint  藍圖輸出資料夾（預設 <課>/_archive/blueprint；課程的 glossary.md 存在時也收 glossary，不想沿用就 --drop glossary）
        write      撰寫輸出資料夾（預設 <課>/_archive/written）
        review     該輪資料夾（<課>/_archive/review/round<N>）
        mining     挖掘資料夾（<materials>/style_evidence/mining；brief:writer 不掃）
  選項：
  --args/--out    把 done 併進既有 args（既有 done 保留；同 label 以新結果為準），寫到 --out（預設印到螢幕）
  --map           改寫路徑前綴，可重複，例：雲端跑的結果拉回本機後
                  --map "/home/user/pathology-slide-materials=<本機教材庫路徑>"
  --drop          不收這些 label 開頭的步驟（要強迫重跑的，例 --drop continuity --drop fix）
  --keep-missing  （journal 模式）檔案不存在也收；預設只收真的存在的檔

多個 journal 依序合併，後面的蓋前面的：原始執行與每次續跑都要給，因為續跑時被沿用的步驟不會再寫進新的 journal。
輸出檔一律 UTF-8、LF 行尾。
"""
import argparse
import glob
import json
import os
import re
import sys


def read_journal(path):
    if os.path.isdir(path):
        path = os.path.join(path, "journal.jsonl")
    labels, results = {}, []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                d = json.loads(ln)
            except ValueError:
                continue
            t = d.get("type")
            if t == "started" and d.get("label"):
                for k in ("agentId", "key"):
                    if d.get(k):
                        labels[d[k]] = d["label"]
            elif t == "result":
                results.append(d)
    out = []
    for d in results:
        lab = labels.get(d.get("agentId")) or labels.get(d.get("key"))
        r = d.get("result")
        if lab and isinstance(r, dict) and isinstance(r.get("path"), str) and r["path"].strip():
            out.append((lab, r["path"].strip()))
    return out


def scan(kind, d):
    """依輸出檔名推回 label；回傳 [(label, path)]。"""
    d = os.path.abspath(d)
    out = []

    def add(pattern, rx, fmt):
        for p in sorted(glob.glob(os.path.join(d, pattern))):
            m = re.fullmatch(rx, os.path.basename(p))
            if m:
                out.append((fmt(m), p))

    if kind == "write":
        add("batch_*_draft.json", r"batch_(\d+)_draft\.json", lambda m: f"write:{m[1]}")
        for chk in ("facts", "voice", "terms"):
            add(f"batch_*_check_{chk}.json", rf"batch_(\d+)_check_{chk}\.json", lambda m, c=chk: f"{c}:{m[1]}")
        add("batch_*.json", r"batch_(\d+)\.json", lambda m: f"revise:{m[1]}")
        add("continuity_report.md", r"continuity_report\.md", lambda m: "continuity")
    elif kind == "review":
        add("review_*.json", r"review_([a-z]+)\.json", lambda m: f"review:{m[1]}")
        add("verify_*_*.json", r"verify_([a-z]+)_(\d)\.json", lambda m: f"verify{m[2]}:{m[1]}")
        add("fix_report.md", r"fix_report\.md", lambda m: "fix")
        if glob.glob(os.path.join(d, "render", "png", "slide_*.png")):
            out.append(("render", os.path.join(d, "render", "png")))
    elif kind == "blueprint":
        add("draft_*.json", r"draft_(.+)\.json", lambda m: f"draft:{m[1]}")
        add("judge_*.json", r"judge_(\d+)\.json", lambda m: f"judge{m[1]}")
        add("blueprint_v1.json", r"blueprint_v1\.json", lambda m: "synthesize")
        add("critique.json", r"critique\.json", lambda m: "critic")
        add("blueprint.json", r"blueprint\.json", lambda m: "revise")
        gl = os.path.normpath(os.path.join(d, "..", "..", "glossary.md"))  # lecture-blueprint 把用語表寫在課程資料夾
        if os.path.exists(gl):
            out.append(("glossary", gl))
    elif kind == "mining":
        add("*_final.json", r"(.+)_final\.json", lambda m: f"revise:{m[1]}")
        add("*_refute*.json", r"(.+)_refute(\d)\.json", lambda m: f"refute{m[2]}:{m[1]}")
        add("*.json", r"(\d\d_[^_]+(?:_[^_]+)*)\.json", lambda m: f"mine:{m[1]}")
        out = [(lab, p) for lab, p in out
               if not (lab.startswith("mine:") and re.search(r"_(final|refute\d)$", lab))]
    elif kind == "gather":
        seg = os.path.join(d, "facts", "seg")
        for p in sorted(glob.glob(os.path.join(seg, "S*.json"))):
            b = os.path.basename(p)
            m = re.fullmatch(r"(S\d\d)(?:_(review(\d)|final))?\.json", b)
            if not m:
                continue
            if m[2] is None:
                out.append((f"robbins:extract:{m[1]}", p))
            elif m[2] == "final":
                out.append((f"robbins:adjudicate:{m[1]}", p))
            else:
                out.append((f"robbins:review{m[3]}:{m[1]}", p))
        ex = os.path.join(d, "_archive", "gather", "exam")
        for tag in ("a", "b"):
            p = os.path.join(ex, f"classify_{tag}.json")
            if os.path.exists(p):
                out.append((f"exam:classify-{tag}", p))
        p = os.path.join(ex, "exam_candidates.json")
        if os.path.exists(p):
            out.append(("exam:verify-select", p))
        lit = os.path.join(d, "_archive", "gather", "lit")
        for p in sorted(glob.glob(os.path.join(lit, "*.json"))):
            b = os.path.basename(p)[:-5]
            if b.endswith("_verified"):
                out.append((f"lit:verify:{b[:-9]}", p))
            elif b.endswith("_images"):
                out.append((f"lit:images:{b[:-7]}", p))
            else:
                out.append((f"lit:search:{b}", p))
    else:
        sys.exit("--scan 只接受 gather／blueprint／write／review／mining")
    return [(lab, p.replace("\\", "/")) for lab, p in out]


def remap(p, maps):
    q = p.replace("\\", "/")
    for old, new in maps:
        o = old.replace("\\", "/").rstrip("/")
        if q == o or q.startswith(o + "/"):
            return new.replace("\\", "/").rstrip("/") + q[len(o):]
    return q


def main():
    ap = argparse.ArgumentParser(description="rebuild Workflow args.done from journal.jsonl files or from output files")
    ap.add_argument("journals", nargs="*")
    ap.add_argument("--scan", choices=["gather", "blueprint", "write", "review", "mining"])
    ap.add_argument("--dir")
    ap.add_argument("--args", dest="args_in")
    ap.add_argument("--out")
    ap.add_argument("--map", action="append", default=[])
    ap.add_argument("--drop", action="append", default=[])
    ap.add_argument("--keep-missing", action="store_true")
    a = ap.parse_args()
    if not a.journals and not a.scan:
        ap.error("給 journal.jsonl（或 run 資料夾），或用 --scan 種類 --dir 資料夾")
    if a.scan and not a.dir:
        ap.error("--scan 需要 --dir")
    maps = []
    for m in a.map:
        if "=" not in m:
            sys.exit("--map 要寫成 舊前綴=新前綴：" + m)
        old, new = m.split("=", 1)
        maps.append((old, new))
    pairs = []
    for j in a.journals:
        pairs += read_journal(j)
    if a.scan:
        pairs += scan(a.scan, a.dir)
    done, missing, dropped = {}, [], set()
    for lab, path in pairs:
        if any(lab.startswith(p) for p in a.drop):
            dropped.add(lab)
            continue
        p = remap(path, maps)
        if not a.keep_missing and not os.path.exists(p):
            missing.append((lab, p))
            continue
        done[lab] = p
    res = done
    if a.args_in:
        base = json.load(open(a.args_in, encoding="utf-8"))
        merged = dict(base.get("done") or {})
        merged.update(done)
        base["done"] = merged
        res = base
    text = json.dumps(res, ensure_ascii=False, indent=1) + "\n"
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    print(f"done labels: {len(done)}; skipped (file missing): {len(missing)}; dropped: {len(dropped)}", file=sys.stderr)
    for lab, p in missing[:20]:
        print(f"  missing: {lab} -> {p}", file=sys.stderr)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    main()

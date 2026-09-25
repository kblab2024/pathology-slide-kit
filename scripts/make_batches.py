# -*- coding: utf-8 -*-
"""把藍圖切成撰寫批次（給撰寫工作流的 args）：依序累加，每批約 --size 張，同一個 build（同標題連張）不拆開，
盡量在 segment 邊界切。輸出 JSON：{"batches":[{"k":1,"slugs":[...],"segments":[...],"prev":"前一張標題 slug","next":"後一張 slug"}]}

用法：python make_batches.py <blueprint.json> <out.json> [--size 16]
"""
import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blueprint")
    ap.add_argument("out")
    ap.add_argument("--size", type=int, default=16)
    a = ap.parse_args()
    S = json.load(open(a.blueprint, encoding="utf-8"))["slides"]
    batches, cur = [], []
    for i, s in enumerate(S):
        cur.append(s)
        nxt = S[i + 1] if i + 1 < len(S) else None
        same_build = nxt is not None and s.get("build") and nxt.get("build") == s.get("build")
        seg_end = nxt is None or nxt["segment"] != s["segment"]
        if nxt is None or (not same_build and (len(cur) >= a.size + 4 or (len(cur) >= a.size - 4 and seg_end))):
            batches.append(cur)
            cur = []
    out = []
    idx = {s["slug"]: i for i, s in enumerate(S)}
    for k, b in enumerate(batches, 1):
        i0, i1 = idx[b[0]["slug"]], idx[b[-1]["slug"]]
        out.append({"k": k, "slugs": [s["slug"] for s in b],
                    "segments": sorted({s["segment"] for s in b}),
                    "prev": S[i0 - 1]["slug"] if i0 > 0 else "", "next": S[i1 + 1]["slug"] if i1 + 1 < len(S) else ""})
    json.dump({"batches": out}, open(a.out, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print(len(out), "batches:", [len(b["slugs"]) for b in out])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

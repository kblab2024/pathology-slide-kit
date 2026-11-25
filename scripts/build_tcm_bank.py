#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_tcm_bank.py — 建中醫師國考題庫（question_banks/中醫師/）：抓考選部六科的試題、答案、更正 → 去重 → 逐科解析 → 合成一份。

中醫師考試沒有病理學科：六科都是中醫（中醫基礎醫學(一)(二)、中醫臨床醫學(一)～(四)）。教師 2026-11-22：
「不會有病理題 你要用器官去關聯」，所以題庫六科全收，挑題時照器官或臨床表現關聯（kit AGENTS.md 硬規則 19）。

和牙醫師題庫（fetch_moex_dent_exam.py＋parse_moex_exam.py）不同的地方：
  * 一場考六科，每科都從第 1 題編起 → 每題另加 "key"＝{年度}-{次}-{科號}#{題號}（科號見 SUBJ）與 "科號"；
    common.load_questions 有 "key" 就用它。
  * 同一場次有兩筆時（104-1 有兩個類科代碼、卷子相同；106-2 另有花東考區補辦考試的卷）：卷子相同只留一份，
    不同時留正式考試那一份（試題第一頁有「補辦」的排後面）。
  * 104–111 年是舊版試卷（題號單獨一行、選項是私用區框字、答案表寫「第1題」）：parse_moex_exam.py 2026-11-22 起支援。
  * 選項有 [圖] 的題加 "parse_note"（四個都是圖＝題目本來就是圖；只有幾個是圖＝舊版文字流把選項錯開，用之前對照 PDF）。
  * 解析錯位、對過試題 PDF 的題寫進 MANUAL_FIXES（題目多一欄 "fix_note"）；重建時照樣套用。

用法（原始 PDF 放 repo 與雲端資料夾以外；下載檔當不可信的資料，另開空資料夾）：
    python build_tcm_bank.py --raw <下載資料夾> --stage <暫存資料夾> --start 104 --end 115 \\
        --out ../question_banks/中醫師/questions-tcm-104-115.json --manifest ../question_banks/中醫師/manifest.json \\
        --mask <私人 repo>/corpus/pseudonyms.tsv
    已經下載過就加 --no-fetch。--mask 必給（有兩題提到教師服務的學校與醫院，不遮就過不了 check_public）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

import fitz
import requests

from fetch_moex_dent_exam import BASE, SEARCH, YS, YE, EC, BTN, LINK_RE, attrs, hidden_fields, select_options, cell_text

SUBJ = {1: "中醫基礎醫學(一)", 2: "中醫基礎醫學(二)", 3: "中醫臨床醫學(一)",
        4: "中醫臨床醫學(二)", 5: "中醫臨床醫學(三)", 6: "中醫臨床醫學(四)"}
SUBJ_FW = {k: v.replace("(", "（").replace(")", "）") for k, v in SUBJ.items()}   # 平臺上的科目名是全形括號
# 解析錯位、照考選部試題 PDF 手動改正的題：重建題庫時照樣套用，題目多一欄 fix_note（改了什麼、哪一天對過 PDF）。
# 只收對過試題 PDF 的；欄位可以有 question、options（只寫要改的選項）、answer。
MANUAL_FIXES = {
    "109-1-4#78": {"options": {"C": "臨床表現水腫、血尿或高血壓或急性腎衰竭",
                               "D": "9 成病人初期會有補體C3 明顯下降情況，6～8 週後恢復正常"},
                   "fix_note": "2026-11-25 照試題 PDF 改正選項 C、D：解析把 D 開頭的「9」接到 C 的末尾（PDF 上這個「9」自成一行，在 D 的記號旁）"},
}
HERE = os.path.dirname(os.path.abspath(__file__))


def fetch(raw: str, start: int, end: int, sleep: float = 0.5) -> list:
    S = requests.Session()
    S.headers["User-Agent"] = "Mozilla/5.0"
    page = S.get(SEARCH, timeout=60).text
    items = []
    for roc in range(start, end + 1):
        y = str(roc + 1911)
        d = hidden_fields(page)
        d.update({YS: y, YE: y, EC: "", "__EVENTTARGET": YS, "__EVENTARGUMENT": ""})
        page = S.post(SEARCH, data=d, timeout=60).text
        for code, title in [(v, t) for v, t in select_options(page, EC) if "中醫師" in t]:
            d = hidden_fields(page)
            d.update({YS: y, YE: y, EC: code, BTN: "查詢"})
            res = S.post(SEARCH, data=d, timeout=60).text
            m = re.search(r"(\d{3})年第([一二三])次", title.replace("第一梯次:", "").replace("第二梯次:", ""))
            ses = {"一": 1, "二": 2, "三": 3}[m.group(2)] if m else None
            for row in re.findall(r"<tr[^>]*>(.*?)</tr>", res, re.S):
                k = next((k for k, v in SUBJ_FW.items() if v in row), None)
                if not k:
                    continue
                links = {}
                for a in re.findall(r"<a [^>]*>", row):
                    mm = LINK_RE.match(attrs(a).get("href", ""))
                    if mm:
                        links[mm.group(1)] = {"url": BASE + attrs(a)["href"], "c": mm.group(3), "s": mm.group(4)}
                if "Q" not in links or ses is None:
                    continue
                cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
                subj = cell_text(cells[3]) if len(cells) > 3 else ""
                for _ in range(3):
                    subj = re.sub(r"\s*(試題|答案|更正答案)\s*$", "", subj)
                items.append({"k": k, "session": f"{roc}-{ses}", "year": roc, "n": ses, "exam_code": code,
                              "exam_title": title, "category_code": links["Q"]["c"], "subject_code": links["Q"]["s"],
                              "subject": subj, "links": links})
            time.sleep(sleep)
        print(f"{roc}: 累計 {len(items)} 筆", file=sys.stderr)
    out = []
    for it in items:
        dd = os.path.join(raw, str(it["k"]))
        os.makedirs(dd, exist_ok=True)
        stem = f"{it['session']}__{it['exam_code']}-{it['category_code']}"
        files = {}
        for t, lab in (("Q", "Q"), ("S", "A"), ("M", "M")):
            if t not in it["links"]:
                continue
            url, path = it["links"][t]["url"], os.path.join(dd, f"{stem}_{lab}.pdf")
            if not (os.path.exists(path) and os.path.getsize(path) > 1000):
                r = S.get(url, headers={"Referer": SEARCH}, timeout=120)
                if r.status_code == 200 and r.content[:4] == b"%PDF":
                    open(path, "wb").write(r.content)
                else:
                    print(f"[下載失敗] {stem} {lab} {r.status_code}", file=sys.stderr)
                time.sleep(sleep)
            if os.path.exists(path):
                files[lab] = {"url": url, "file": os.path.relpath(path, raw), "bytes": os.path.getsize(path),
                              "sha1": hashlib.sha1(open(path, "rb").read()).hexdigest()}
        rec = {k: v for k, v in it.items() if k != "links"}
        rec["files"] = files
        out.append(rec)
    json.dump(out, open(os.path.join(raw, "all_sources.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out


def text_of(path: str) -> str:
    return "".join(p.get_text() for p in fitz.open(path))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--raw", required=True)
    ap.add_argument("--stage", required=True)
    ap.add_argument("--start", type=int, default=104)
    ap.add_argument("--end", type=int, default=115)
    ap.add_argument("--out", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--mask", help="私人 repo 的 corpus/pseudonyms.tsv（真名<TAB>代稱）：題目裡出現的校名、院名換成代稱，"
                                   "題庫才過得了 check_public（公開 kit 不放這些名字；題目原文看試題 PDF）")
    a = ap.parse_args(argv)
    mask = []
    if a.mask:
        for ln in open(a.mask, encoding="utf-8"):
            if ln.startswith("#") or "\t" not in ln:
                continue
            real, alias = ln.rstrip("\n").split("\t")[:2]
            if real.strip():
                mask.append((real.strip(), alias.strip()))
        mask.sort(key=lambda x: -len(x[0]))
    items = (json.load(open(os.path.join(a.raw, "all_sources.json"), encoding="utf-8")) if a.no_fetch
             else fetch(a.raw, a.start, a.end))

    groups = {}
    for it in items:
        groups.setdefault((it["k"], it["session"]), []).append(it)
    chosen, dups = {}, []
    for (k, ses), its in sorted(groups.items()):
        its = [i for i in its if "Q" in i["files"] and "A" in i["files"]]
        if not its:
            print(f"[缺檔] 科{k} {ses}", file=sys.stderr)
            continue
        its.sort(key=lambda i: "補辦" in re.sub(r"\s", "", fitz.open(os.path.join(a.raw, i["files"]["Q"]["file"]))[0].get_text()))
        first = its[0]
        for o in its[1:]:
            same_bytes = first["files"]["Q"]["sha1"] == o["files"]["Q"]["sha1"]
            same_text = same_bytes or text_of(os.path.join(a.raw, first["files"]["Q"]["file"])) == text_of(os.path.join(a.raw, o["files"]["Q"]["file"]))
            dups.append({"科號": k, "session": ses, "kept": f"{first['exam_code']}-{first['category_code']}",
                         "other": f"{o['exam_code']}-{o['category_code']}", "same_bytes": same_bytes, "same_text": same_text})
        chosen[(k, ses)] = first

    bank, sessions_all, files_all, fails = [], [], [], 0
    for k in SUBJ:
        sd = os.path.join(a.stage, str(k))
        shutil.rmtree(sd, ignore_errors=True)
        os.makedirs(sd)
        srcs = []
        for (kk, ses), it in sorted(chosen.items()):
            if kk != k:
                continue
            files = {}
            for lab in ("Q", "A", "M"):
                if lab in it["files"]:
                    dst = os.path.join(sd, f"{ses}_{lab}.pdf")
                    shutil.copyfile(os.path.join(a.raw, it["files"][lab]["file"]), dst)
                    files[lab] = {"url": it["files"][lab]["url"], "file": os.path.basename(dst), "bytes": os.path.getsize(dst)}
            rec = {x: v for x, v in it.items() if x not in ("files", "k")}
            rec["files"] = files
            srcs.append(rec)
        json.dump(srcs, open(os.path.join(sd, "sources.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        out_k, man_k = os.path.join(a.stage, f"bank_{k}.json"), os.path.join(a.stage, f"manifest_{k}.json")
        r = subprocess.run([sys.executable, os.path.join(HERE, "parse_moex_exam.py"), "--raw", sd, "--out", out_k,
                            "--manifest", man_k, "--subject", SUBJ[k]], capture_output=True, text=True)
        open(os.path.join(a.stage, f"parse_{k}.log"), "w", encoding="utf-8").write(r.stderr)
        print(f"科{k} {SUBJ[k]}：結束碼 {r.returncode}（記錄 {a.stage}/parse_{k}.log）", file=sys.stderr)
        fails += bool(r.returncode)
        if not os.path.exists(out_k):
            continue
        for q in json.load(open(out_k, encoding="utf-8")):
            row = {"key": f"{q['年度']}-{q['第幾次']}-{k}#{q['題號']}", "科號": k}
            if mask:
                txt = json.dumps([q["question"], q["options"]], ensure_ascii=False)
                if any(r in txt for r, _ in mask):
                    for r, al in mask:
                        q["question"] = q["question"].replace(r, al)
                        q["options"] = {o: v.replace(r, al) for o, v in q["options"].items()}
                    row["mask_note"] = "原文有一個校名或院名，換成代稱（公開 kit 不放這些名字）；原文看試題 PDF"
            n_img = list(q["options"].values()).count("[圖]")
            if n_img == 4:
                row["parse_note"] = "選項是圖：題庫只有字，用之前看試題 PDF"
            elif n_img:
                row["parse_note"] = "選項可能錯開（舊版試卷的文字流），用之前對照試題 PDF"
            note = {x: row.pop(x) for x in ("mask_note", "parse_note") if x in row}
            row.update(q)
            row.update(note)
            fx = MANUAL_FIXES.get(row["key"])
            if fx:
                row["options"] = {**row["options"], **fx.get("options", {})}
                row.update({f: fx[f] for f in ("question", "answer") if f in fx})
                row["fix_note"] = fx["fix_note"]
            bank.append(row)
        man = json.load(open(man_k, encoding="utf-8"))
        for s in man["sessions"]:
            s["科號"] = k
            sessions_all.append(s)
        for f in man["files"]:
            f["科號"] = k
            files_all.append(f)
    keys = [q["key"] for q in bank]
    if len(keys) != len(set(keys)):
        sys.exit("key 重複")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(bank, open(a.out, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    json.dump({"generated_by": "scripts/build_tcm_bank.py（每科跑一次 parse_moex_exam.py，--subject 指定科目；之後每題加 key 與科號）",
               "source": "考選部考畢試題查詢平臺 https://wwwq.moex.gov.tw/exam/wFrmExamQandASearch.aspx",
               "科號": SUBJ, "questions_json": os.path.basename(a.out), "total_questions": len(bank),
               "parse_notes": {"選項是圖": sum(1 for q in bank if q.get("parse_note", "").startswith("選項是圖")),
                               "選項可能錯開": sum(1 for q in bank if q.get("parse_note", "").startswith("選項可能錯開"))},
               "manual_fixes": sorted(MANUAL_FIXES),
               "same_session_duplicates": dups, "sessions": sessions_all, "files": files_all},
              open(a.manifest, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print(f"題庫 {len(bank)} 題 → {a.out}；解析失敗的科 {fails}", file=sys.stderr)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

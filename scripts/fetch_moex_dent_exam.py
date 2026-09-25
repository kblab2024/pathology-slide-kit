#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_moex_dent_exam.py — 從考選部「考畢試題查詢平臺」抓牙醫師(一) 牙醫學(二) 的試題／答案／更正 PDF

平臺是 ASP.NET WebForms（wFrmExamQandASearch.aspx）：
  1. GET 查詢頁取得 __VIEWSTATE / __EVENTVALIDATION；
  2. 以 __EVENTTARGET = 年度下拉選單做 postback，考試簡稱下拉（ddlExamCode）才會列出該年度的考試代碼；
  3. 選考試代碼、按「查詢」，結果表每列一科，連結長這樣：
        wHandExamQandA_File.ashx?t=Q&code=115090&c=303&s=0302&q=1   (t=Q 試題, S 標準答案, M 更正答案)
     code=考試代碼（前三碼＝民國年度）、c=類科代碼、s=科目代碼。
  4. 檔案處理器要在同一個 session（cookie）內、帶 Referer 才回 PDF，否則 302 到 NotFound。

用法：
    python fetch_moex_dent_exam.py --out "immune/牙醫師國考/raw" --start 104 --end 115 \\
        [--exam-keyword 牙醫] [--subject-keyword "牙醫學(二)"]

輸出：
    {out}/{年度}-{次}_Q.pdf、_A.pdf、_M.pdf（M 只在平臺有更正檔時）
    {out}/sources.json  每場次的 url／考試代碼／類科代碼／科目代碼／科目名稱（parse_moex_exam.py 會讀）
已存在且大於 1 KB 的檔案不會重抓。
"""
from __future__ import annotations

import argparse
import html as H
import json
import os
import re
import sys
import time

import requests

BASE = "https://wwwq.moex.gov.tw/exam/"
SEARCH = BASE + "wFrmExamQandASearch.aspx"
YS = "ctl00$holderContent$wUctlExamYearStart$ddlExamYear"
YE = "ctl00$holderContent$wUctlExamYearEnd$ddlExamYear"
EC = "ctl00$holderContent$ddlExamCode"
BTN = "ctl00$holderContent$btnSearch"
LINK_RE = re.compile(r"wHandExamQandA_File\.ashx\?t=([QSM])&code=(\d+)&c=(\w+)&s=(\w+)&q=(\d+)")


def attrs(tag: str) -> dict:
    return {k: H.unescape(v) for k, v in re.findall(r'([\w:$-]+)="([^"]*)"', tag)}


def hidden_fields(page: str) -> dict:
    d = {}
    for tag in re.findall(r"<input[^>]*>", page):
        a = attrs(tag)
        if a.get("type") == "hidden" and "name" in a:
            d[a["name"]] = a.get("value", "")
    return d


def select_options(page: str, name: str):
    m = re.search(r'<select[^>]*name="%s"[^>]*>(.*?)</select>' % re.escape(name), page, re.S)
    if not m:
        return []
    return [(attrs(t).get("value", ""), H.unescape(txt).strip()) for t, txt in re.findall(r"(<option[^>]*>)([^<]*)</option>", m.group(1))]


def cell_text(td: str) -> str:
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", td))).strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", type=int, default=104, help="民國年度（起）")
    ap.add_argument("--end", type=int, default=115, help="民國年度（迄）")
    ap.add_argument("--exam-keyword", default="牙醫", help="考試簡稱要含的字串")
    ap.add_argument("--subject-keyword", default="牙醫學(二)", help="科目名稱要含的字串")
    ap.add_argument("--sleep", type=float, default=0.7)
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    S = requests.Session()
    S.headers["User-Agent"] = "Mozilla/5.0"
    page = S.get(SEARCH, timeout=60).text

    items = []
    for roc in range(args.start, args.end + 1):
        y = str(roc + 1911)
        data = hidden_fields(page)
        data.update({YS: y, YE: y, EC: "", "__EVENTTARGET": YS, "__EVENTARGUMENT": ""})
        page = S.post(SEARCH, data=data, timeout=60).text
        codes = [(v, t) for v, t in select_options(page, EC) if args.exam_keyword in t]
        for code, title in codes:
            data = hidden_fields(page)
            data.update({YS: y, YE: y, EC: code, BTN: "查詢"})
            res = S.post(SEARCH, data=data, timeout=60).text
            m = re.search(r"(\d{3})年第([一二三])次", title.replace("第一梯次:", "").replace("第二梯次:", ""))
            ses = {"一": 1, "二": 2, "三": 3}[m.group(2)] if m else None
            for row in re.findall(r"<tr[^>]*>(.*?)</tr>", res, re.S):
                if args.subject_keyword not in row:
                    continue
                cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
                subj = cell_text(cells[3]) if len(cells) > 3 else ""
                for _ in range(3):
                    subj = re.sub(r"\s*(試題|答案|更正答案)\s*$", "", subj)
                links = {}
                for a in re.findall(r"<a [^>]*>", row):
                    href = attrs(a).get("href", "")
                    mm = LINK_RE.match(href)
                    if mm:
                        links[mm.group(1)] = {"url": BASE + href, "c": mm.group(3), "s": mm.group(4)}
                if not links or ses is None:
                    continue
                items.append({"session": f"{roc}-{ses}", "year": roc, "n": ses, "exam_code": code, "exam_title": title,
                              "category_code": links["Q"]["c"], "subject_code": links["Q"]["s"], "subject": subj,
                              "links": links})
            time.sleep(args.sleep)
        print(f"{roc}: {[(c, t[:30]) for c, t in codes]}", file=sys.stderr)

    # 同一 session 內下載（處理器要 cookie + Referer）
    out_items = []
    for it in items:
        files = {}
        for t, lab in (("Q", "Q"), ("S", "A"), ("M", "M")):
            if t not in it["links"]:
                continue
            url = it["links"][t]["url"]
            path = os.path.join(args.out, f"{it['session']}_{lab}.pdf")
            if not (os.path.exists(path) and os.path.getsize(path) > 1000):
                r = S.get(url, headers={"Referer": SEARCH}, timeout=120)
                ok = r.status_code == 200 and r.content[:4] == b"%PDF"
                print(f"{it['session']} {lab} {r.status_code} {len(r.content)} {'OK' if ok else 'BAD ' + r.url}", file=sys.stderr)
                if ok:
                    with open(path, "wb") as fh:
                        fh.write(r.content)
                time.sleep(args.sleep)
            if os.path.exists(path):
                files[lab] = {"url": url, "file": os.path.basename(path), "bytes": os.path.getsize(path)}
        rec = {k: v for k, v in it.items() if k != "links"}
        rec["files"] = files
        out_items.append(rec)
    out_items.sort(key=lambda r: (r["year"], r["n"]))
    with open(os.path.join(args.out, "sources.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out_items, fh, ensure_ascii=False, indent=1)
    print(f"sources.json: {len(out_items)} 場次", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""每種版型在這門課的字級下放得下多少字（規劃、撰寫前先看，不必自己試產校準）。

直接用 gen_pptx 的量字函式（n_lines、line_h，量字字型同 gen_pptx）與版面幾何算，數字和產檔時的溢出判斷一致。
2026-10-14 一門課的充實版規劃代理為了校準剛改的字級，自己做了幾十次試產，對話長到約 67 萬 token；
這支把那件事變成幾秒鐘的程式（四階段做法的「階段 0：先寫工具」）。

用法：
  cd <kit>/scripts && SLIDEKIT_MATERIALS=<materials> PYTHONIOENCODING=utf-8 python fit_capacity.py --course <課程> [--json]

輸出（以「中」這類全形字計；英文約 2 個字母算 1 個全形字寬，中英對照的詞要照實際長度估）：
- 標題：一行幾字；超過 2 行改用 title_small。
- left：有圖時文字欄 47%（預設）與最寬 65% 兩種寬度下，每行幾字、可放幾行；無圖時整寬。
- flash／robbins／pair：標題下說明句每行幾字、最多幾行（還要留給圖的高度）。
- table3：2、3、4 欄平均欄寬下，每格每行幾字；一列一行時最多幾列（不含表頭），以及 course.yaml table_max_rows。
- big：每行幾字（教師 2026-10-14 不要單句張，只供參考）。
都分「標題一行」「標題兩行」，以及有無一行資料來源。實際張還是要產檔後看 _layout.json 的 overflow 與算圖。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_pptx as gp  # noqa: E402
from common import load_course  # noqa: E402

CJK = "中"


def per_line(size, width_in, bold=False):
    """一行最多放幾個全形字（用 gen_pptx 的 n_lines 量）。"""
    n = 1
    while gp.n_lines(CJK * (n + 1), size, width_in, bold) == 1 and n < 400:
        n += 1
    return n


def title_h(lines, size):
    return 0.30 + lines * gp.line_h(size, 1.1) + 0.30


def src_h(lines):
    return (lines * 0.25 + 0.05) if lines else 0.0


def capacity(course_name):
    course = load_course(course_name)
    gp.setup(course)
    S, SW, SH, M = gp.G.S, gp.G.SW, gp.G.SH, gp.G.M
    out = {"course": course_name, "slide_in": [SW, SH], "sizes": {k: S[k] for k in
           ("title", "title_small", "body", "body_noimg", "lead", "big", "table", "table_min", "label", "credit", "min")
           if k in S}, "char_warn": S.get("char_warn"), "char_red": S.get("char_red"),
           "table_max_rows": S.get("table_max_rows"), "types": {}}
    tw_title = SW - 2 * M - 0.26
    out["types"]["title"] = {"每行字數": per_line(S["title"], tw_title, True),
                             "小字標題每行字數": per_line(S["title_small"], tw_title, True)}
    rows = {}
    for tl in (1, 2):
        for sl in (0, 1):
            key = f"標題{tl}行" + ("＋出處1行" if sl else "")
            y0 = title_h(tl, S["title"])
            r = {}
            # left 有圖：avail＝SH−y0−0.45−src_h；每條 8pt 段距，條列縮排 0.32 in
            avail = SH - y0 - 0.45 - src_h(sl)
            lh = gp.line_h(S["body"])
            for frac in (0.47, 0.65):
                w = (SW - 2 * M) * frac - 0.32
                r[f"left有圖{int(frac*100)}%"] = {"每行字數": per_line(S["body"], w),
                                                 "最多行數(單條)": int((avail - 8 / 72) // lh),
                                                 "圖寬in": round(SW - M - (M + (SW - 2 * M) * frac + 0.40), 2)}
            w = SW - 2 * M - 0.2 - 0.32
            lhn = gp.line_h(S["body_noimg"])
            r["left無圖"] = {"每行字數": per_line(S["body_noimg"], w), "最多行數(單條)": int((avail - 8 / 72) // lhn)}
            # 說明句（flash／robbins／pair）：整寬；flash 要留 2.0 in 給圖，pair 2.2 in
            wl = SW - 2 * M - 0.26
            lhl = gp.line_h(S["lead"]) + 4 / 72
            r["flash說明句"] = {"每行字數": per_line(S["lead"], wl), "最多行數": int(((SH - 2.0) - y0) // lhl)}
            r["pair說明句"] = {"每行字數": per_line(S["lead"], wl), "最多行數": int(((SH - 2.2) - y0) // lhl)}
            # table3：平均欄寬，格內左右邊界約 0.2 in；一列高＝行數×line_h(table,1.1)＋0.14
            tavail = SH - y0 - 0.45 - src_h(sl)
            tb = {}
            for ncol in (2, 3, 4):
                cw = (SW - 2 * M) / ncol - 0.2
                rh1 = gp.line_h(S["table"], 1.1) + 0.14
                rh2 = 2 * gp.line_h(S["table"], 1.1) + 0.14
                tb[f"{ncol}欄"] = {"每格每行字數": per_line(S["table"], cw),
                                  "一行列最多列數(不含表頭)": max(0, int(tavail // rh1) - 1),
                                  "兩行列最多列數(不含表頭)": max(0, int((tavail - rh1) // rh2))}
            r["table3"] = tb
            r["big(不建議)"] = {"每行字數": per_line(S["big"], wl)}
            rows[key] = r
    out["types"]["by_title"] = rows
    return out


def as_markdown(c):
    L = [f"# fit_capacity：{c['course']}（{c['slide_in'][0]}×{c['slide_in'][1]} in）", "",
         "字級：" + "、".join(f"{k} {v}" for k, v in c["sizes"].items()),
         f"每張可見字元：>{c['char_warn']} 提醒、>{c['char_red']} RED；表格超過 {c['table_max_rows']} 列自動拆同標題連張。",
         "字數以全形字計；英文約 2 個字母算 1 字寬。實際放不放得下以產檔後 _layout.json 與算圖為準。", "",
         f"- 標題每行 {c['types']['title']['每行字數']} 字（超過 2 行改小字標題，每行 {c['types']['title']['小字標題每行字數']} 字）", ""]
    for key, r in c["types"]["by_title"].items():
        L += [f"## {key}", "", "| 版型 | 每行字數 | 最多行數／列數 | 備註 |", "|---|---|---|---|"]
        for t in ("left有圖47%", "left有圖65%"):
            v = r[t]
            L.append(f"| {t} | {v['每行字數']} | {v['最多行數(單條)']} 行 | 圖寬約 {v['圖寬in']} in；文字放不下時 gen_pptx 會自動把文字欄從 47% 加寬到 65% |")
        v = r["left無圖"]
        L.append(f"| left 無圖 | {v['每行字數']} | {v['最多行數(單條)']} 行 | |")
        for t in ("flash說明句", "pair說明句"):
            v = r[t]
            L.append(f"| {t} | {v['每行字數']} | {v['最多行數']} 行 | 其餘高度給圖 |")
        for n, v in r["table3"].items():
            L.append(f"| table3 {n} | {v['每格每行字數']} | 一行列 {v['一行列最多列數(不含表頭)']} 列；兩行列 {v['兩行列最多列數(不含表頭)']} 列 | 平均欄寬估算，實際依內容調欄寬 |")
        L.append(f"| big（不建議） | {r['big(不建議)']['每行字數']} | | 教師不要單句張 |")
        L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--course", required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    c = capacity(a.course)
    print(json.dumps(c, ensure_ascii=False, indent=1) if a.json else as_markdown(c))

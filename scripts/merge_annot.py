# -*- coding: utf-8 -*-
"""把截圖註記（annotate_shot.py 的規格）帶進實驗講義的 deck.json，讓 gen_lab_pptx.py 畫成 PowerPoint 原生圖形。

教師 2026-10-27：「上次你把那個投影片上面的切片截圖指針render成死的圖片 結果你錯的時候我不能改
可不可以render成powerpoint上面的箭頭啊」。所以成品的截圖不再用 annotate_shot.py 燒好的 JPG：
deck.json 的 shot 改指沒加註記的原始截圖（規格的 image），註記放進 img.marks，
gen_lab_pptx.py 疊成紅箭頭、紅圈、深灰底白字標籤（可以點選、拖曳、改字），html_lab_deck.py 畫成同位置的 SVG。

對法：deck.json 裡 img.path 指到的檔，等於某個規格的 out（燒好的圖）→ 換成那個規格的 image，帶入 marks、label_pt；
原本燒好的圖記在 img.burned（只是備查，不會被用到）。已經合併過的 deck 再跑一次也一樣（用 img.burned 對）。

用法：python merge_annot.py <deck.json> --annot <annot.json> [更多 annot.json …] --out <新 deck.json>
      annot.json 可以是一張的規格，或 {"shots": [規格, …]}；image、out 相對規格檔所在的資料夾。
      --out 可以和輸入同一個檔；路徑一律改寫成相對 --out 所在的資料夾。
報出：合併幾張、deck 裡有圖但沒有註記規格的 shot、規格裡有但 deck 沒用到的截圖、原始截圖不存在的。
原始截圖不存在時結束碼 1（gen_lab_pptx 會放淡灰空圖，不能交）。
"""
import argparse
import glob
import json
import os
import sys


def load_specs(paths):
    specs = {}
    for pat in paths:
        for p in sorted(glob.glob(pat)) or [pat]:
            S = json.load(open(p, encoding="utf-8"))
            base = os.path.dirname(os.path.abspath(p))
            for one in (S["shots"] if "shots" in S else [S]):
                out = os.path.normpath(os.path.join(base, one["out"]))
                specs[out] = {"image": os.path.normpath(os.path.join(base, one["image"])),
                              "marks": one.get("marks", []), "label_pt": one.get("label_pt"), "spec": p}
    return specs


def main():
    ap = argparse.ArgumentParser(description="annot.json 的註記帶進 deck.json（成品畫成 PowerPoint 原生圖形）")
    ap.add_argument("deck")
    ap.add_argument("--annot", nargs="+", required=True, help="annotate_shot 的規格檔（可用萬用字元，例 'shots/*/annot.json'）")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    deck = json.load(open(a.deck, encoding="utf-8"))
    src_dir = os.path.dirname(os.path.abspath(a.deck))
    out_dir = os.path.dirname(os.path.abspath(a.out))
    specs = load_specs(a.annot)
    rel = lambda p: os.path.relpath(p, out_dir).replace(os.sep, "/")

    merged, no_spec, missing, used = [], [], [], set()
    for sec in deck.get("sections", []):
        for c in sec.get("slides", []):
            img = c.get("img")
            if not img:
                continue
            for k in ("path", "burned"):
                if img.get(k):
                    img[k] = os.path.normpath(os.path.join(src_dir, img[k]))
            key = img.get("burned") or img.get("path")
            sp = specs.get(key) if key else None
            if sp:
                used.add(key)
                img["burned"] = key
                img["path"] = sp["image"]
                img["marks"] = sp["marks"]
                if sp["label_pt"]:
                    img["label_pt"] = sp["label_pt"]
                merged.append(c.get("id", "?"))
                if not os.path.exists(sp["image"]):
                    missing.append(f"{c.get('id', '?')}：{sp['image']}")
            elif (c.get("kind") or "shot") == "shot" and img.get("path"):
                no_spec.append(c.get("id", "?"))
            for k in ("path", "burned"):
                if img.get(k):
                    img[k] = rel(img[k])

    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(deck, f, ensure_ascii=False, indent=1)
    unused = sorted(os.path.basename(k) for k in specs if k not in used)
    print(f"合併 {len(merged)} 張（註記 {sum(len(specs[k]['marks']) for k in used)} 個）-> {a.out}")
    if no_spec:
        print("有圖但沒有註記規格的 shot（照原圖放）：" + "、".join(no_spec))
    if unused:
        print("規格裡有、deck 沒用到：" + "、".join(unused))
    for m in missing:
        print("原始截圖不存在：" + m)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

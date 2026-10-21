# -*- coding: utf-8 -*-
"""從全玻片掃描檔（Aperio .svs 等 tiled TIFF）切實驗講義的截圖：附座標格的總覽圖、指定倍率的視野。

用法：
  python wsi_crop.py info <slide.svs>
  python wsi_crop.py overview <slide.svs> --out <總覽.png> [--max-side 1800] [--grid 10] [--boxes <batch.json>]
  python wsi_crop.py crop <slide.svs> --cx 0.55 --cy 0.40 --mag 10 --out <視野.png> [--w 1600 --h 1386] [--grid 4]
  python wsi_crop.py batch <batch.json> [--overview-dir <資料夾>]

座標：cx、cy 是整片（最高解析度那層）寬、高的比例 0–1，指視野的中心。總覽圖與 --grid 的格線標的就是這個比例，
      所以在總覽圖上看到要的區域，讀格線的數字就能切；切出來的圖再加 --grid 可以細調。
倍率：照顯微鏡物鏡的說法，mag 10 等於每像素 1 µm（µm/px＝10／mag）。同一個 mag 在 20x、40x 掃描的片子看到的範圍一樣大：
      輸出 1600 px 寬時，mag 1.25 約 12.8 mm、2 約 8 mm、4 約 4 mm、10 約 1.6 mm、20 約 0.8 mm、40 約 0.4 mm。
      超過片子掃描倍率（AppMag）時照最高解析度放大，並印出提醒。
輸出：預設 1600×1386 px，等於實驗講義圖框 6.14×5.32 吋的比例（gen_lab_pptx.py），圖填滿圖框、不留白。
隱私：不讀、不輸出玻片的 label 與 macro 影像（上面有病理號）；輸出圖與報告不寫病理號。

batch.json：
  {"shots": [{"id": "DC05-2", "slide": "<…/DC05_….svs>", "cx": 0.52, "cy": 0.40, "mag": 4,
              "out": "<…/DC05-2_raw.png>", "w": 1600, "h": 1386}]}
  slide、out 可寫相對 batch.json 的路徑。--overview-dir 給了就另存每片一張總覽，用方框標出各截圖的位置與 id（核對用）。

需要：tifffile、imagecodecs（解 JPEG、JPEG 2000 的圖塊）、numpy、Pillow。不需要 openslide。
"""
import argparse
import json
import os
import re
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
OUT_W, OUT_H = 1600, 1386
FONT_CANDIDATES = [
    "/Applications/Microsoft PowerPoint.app/Contents/Resources/DFonts/MSJH.ttf",
    os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "msjh.ttc"),
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]


def _font(px):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return ImageFont.truetype(p, px)
    return ImageFont.load_default()


class Slide:
    """一張掃描檔的金字塔（只用 series 0 的各層）。"""

    def __init__(self, path):
        self.path = path
        self.tf = tifffile.TiffFile(path)
        s = self.tf.series[0]
        self.levels = []
        for lv in s.levels:
            pg = lv.pages[0]
            h, w = lv.shape[:2]
            self.levels.append({"page": pg, "w": w, "h": h})
        self.w0, self.h0 = self.levels[0]["w"], self.levels[0]["h"]
        desc = self.levels[0]["page"].description or ""
        m = re.search(r"MPP\s*=\s*([0-9.]+)", desc)
        self.mpp = float(m.group(1)) if m else 0.25
        m = re.search(r"AppMag\s*=\s*([0-9.]+)", desc)
        self.appmag = float(m.group(1)) if m else round(10 / self.mpp)
        for L in self.levels:
            L["down"] = self.w0 / L["w"]
            L["mpp"] = self.mpp * L["down"]

    def close(self):
        self.tf.close()

    def read_region(self, li, x, y, w, h):
        """第 li 層、左上 (x, y)、寬高 w×h（該層像素）的 RGB 陣列；超出片子的部分補白。"""
        L = self.levels[li]
        pg = L["page"]
        out = np.full((h, w, 3), 255, np.uint8)
        if not pg.is_tiled:
            arr = pg.asarray()[..., :3]
            x0, y0 = max(0, x), max(0, y)
            x1, y1 = min(L["w"], x + w), min(L["h"], y + h)
            if x1 > x0 and y1 > y0:
                out[y0 - y:y1 - y, x0 - x:x1 - x] = arr[y0:y1, x0:x1]
            return out
        tw, th = pg.tilewidth, pg.tilelength
        ntx = (L["w"] + tw - 1) // tw
        fh = self.tf.filehandle
        tx0, ty0 = max(0, x // tw), max(0, y // th)
        tx1 = min(ntx - 1, (x + w - 1) // tw)
        ty1 = min((L["h"] + th - 1) // th - 1, (y + h - 1) // th)
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                idx = ty * ntx + tx
                if idx >= len(pg.dataoffsets) or pg.databytecounts[idx] == 0:
                    continue
                fh.seek(pg.dataoffsets[idx])
                data = fh.read(pg.databytecounts[idx])
                tile = pg.decode(data, idx, jpegtables=pg.jpegtables)[0]
                if tile is None:
                    continue
                tile = np.asarray(tile).reshape(th, tw, -1)[..., :3]
                gx, gy = tx * tw, ty * th
                ax0, ay0 = max(gx, x), max(gy, y)
                ax1 = min(gx + tw, x + w, L["w"])
                ay1 = min(gy + th, y + h, L["h"])
                if ax1 <= ax0 or ay1 <= ay0:
                    continue
                out[ay0 - y:ay1 - y, ax0 - x:ax1 - x] = tile[ay0 - gy:ay1 - gy, ax0 - gx:ax1 - gx]
        return out

    def pick_level(self, um_per_px):
        """取「每像素微米數 ≤ 目標」裡最粗的一層（從較細的層縮下來，畫質才好）。"""
        best = 0
        for i, L in enumerate(self.levels):
            if L["mpp"] <= um_per_px * 1.001:
                best = i
        return best

    def crop(self, cx, cy, mag, w=OUT_W, h=OUT_H):
        um = 10.0 / mag
        warn = None
        if um < self.mpp * 0.97:
            warn = f"mag {mag} 超過掃描倍率（AppMag {self.appmag:g}，{self.mpp:.3f} µm/px），照最高解析度放大"
        li = self.pick_level(um)
        L = self.levels[li]
        scale = um / L["mpp"]                    # 輸出 1 px＝該層幾 px
        rw, rh = max(1, round(w * scale)), max(1, round(h * scale))
        x = round(cx * L["w"] - rw / 2)
        y = round(cy * L["h"] - rh / 2)
        arr = self.read_region(li, x, y, rw, rh)
        im = Image.fromarray(arr)
        if (rw, rh) != (w, h):
            im = im.resize((w, h), Image.LANCZOS)
        box = (x * L["down"] / self.w0, y * L["down"] / self.h0,
               (x + rw) * L["down"] / self.w0, (y + rh) * L["down"] / self.h0)
        return im, box, warn

    def overview(self, max_side=1800):
        li = len(self.levels) - 1
        for i, L in enumerate(self.levels):
            if max(L["w"], L["h"]) <= max_side * 1.6:
                li = i
                break
        L = self.levels[li]
        arr = self.read_region(li, 0, 0, L["w"], L["h"])
        im = Image.fromarray(arr)
        r = max_side / max(im.size)
        if r < 1:
            im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
        return im


def draw_grid(im, n, box=(0.0, 0.0, 1.0, 1.0), color=(0, 110, 200)):
    """格線＋邊上的座標（整片的比例）。box＝這張圖在整片的範圍 (x0, y0, x1, y1)。"""
    im = im.convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    f = _font(max(14, im.width // 60))
    x0, y0, x1, y1 = box
    for k in range(1, n):
        gx = x0 + (x1 - x0) * k / n
        gy = y0 + (y1 - y0) * k / n
        px = round(im.width * k / n)
        py = round(im.height * k / n)
        d.line([(px, 0), (px, im.height)], fill=color + (150,), width=1)
        d.line([(0, py), (im.width, py)], fill=color + (150,), width=1)
        for txt, pos in ((f"{gx:.3f}" if n > 10 or (x1 - x0) < 0.5 else f"{gx:.2f}", (px + 3, 2)),
                         (f"{gy:.3f}" if n > 10 or (y1 - y0) < 0.5 else f"{gy:.2f}", (3, py + 2))):
            b = d.textbbox(pos, txt, font=f)
            d.rectangle(b, fill=(255, 255, 255, 200))
            d.text(pos, txt, font=f, fill=color + (255,))
    return im


def draw_boxes(im, boxes):
    """總覽圖上標出各截圖的範圍。boxes：[(id, (x0, y0, x1, y1)), …]（整片比例）。"""
    im = im.convert("RGB")
    d = ImageDraw.Draw(im)
    f = _font(max(14, im.width // 70))
    for sid, (a, b, c, e) in boxes:
        r = (a * im.width, b * im.height, c * im.width, e * im.height)
        d.rectangle(r, outline=(220, 20, 20), width=2)
        d.text((r[0] + 2, r[1] + 1), sid, font=f, fill=(220, 20, 20))
    return im


def cmd_info(a):
    s = Slide(a.slide)
    print(f"檔案：{os.path.basename(a.slide)}")
    print(f"掃描倍率 AppMag {s.appmag:g}；最高解析度 {s.mpp:.4f} µm/px；整片 {s.w0}×{s.h0} px"
          f"（{s.w0 * s.mpp / 1000:.1f}×{s.h0 * s.mpp / 1000:.1f} mm）")
    for i, L in enumerate(s.levels):
        print(f"  第 {i} 層：{L['w']}×{L['h']}，{L['mpp']:.3f} µm/px（約 mag {10 / L['mpp']:.2g}）")
    s.close()


def cmd_overview(a):
    s = Slide(a.slide)
    im = s.overview(a.max_side)
    if a.grid:
        im = draw_grid(im, a.grid)
    if a.boxes:
        spec = json.load(open(a.boxes, encoding="utf-8"))
        bs = [(x["id"], tuple(x["box"])) for x in spec.get("shots", []) if x.get("box")
              and os.path.basename(x.get("slide", "")) == os.path.basename(a.slide)]
        im = draw_boxes(im, bs)
    im.save(a.out)
    print(f"總覽：{a.out}（{im.width}×{im.height}；整片 {s.w0 * s.mpp / 1000:.1f}×{s.h0 * s.mpp / 1000:.1f} mm）")
    s.close()


def cmd_crop(a):
    s = Slide(a.slide)
    im, box, warn = s.crop(a.cx, a.cy, a.mag, a.w, a.h)
    if warn:
        print("提醒：" + warn)
    if a.grid:
        im = draw_grid(im, a.grid, box)
    im.save(a.out)
    fov = a.w * 10 / a.mag / 1000
    print(f"視野：{a.out}（mag {a.mag:g}，寬約 {fov:.2f} mm；範圍 x {box[0]:.4f}–{box[2]:.4f}、y {box[1]:.4f}–{box[3]:.4f}）")
    s.close()


def cmd_batch(a):
    spec_path = os.path.abspath(a.spec)
    base = os.path.dirname(spec_path)
    P = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    spec = json.load(open(spec_path, encoding="utf-8"))
    cache = {}
    for x in spec.get("shots", []):
        sp = P(x["slide"])
        if sp not in cache:
            cache[sp] = Slide(sp)
        s = cache[sp]
        im, box, warn = s.crop(float(x["cx"]), float(x["cy"]), float(x["mag"]),
                               int(x.get("w", OUT_W)), int(x.get("h", OUT_H)))
        out = P(x["out"])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        im.save(out)
        x["box"] = [round(v, 5) for v in box]
        print(f"{x.get('id', '')}：{os.path.basename(out)}（mag {float(x['mag']):g}）" + (f"　提醒：{warn}" if warn else ""))
    if a.overview_dir:
        os.makedirs(a.overview_dir, exist_ok=True)
        for sp, s in cache.items():
            bs = [(x.get("id", ""), tuple(x["box"])) for x in spec["shots"] if P(x["slide"]) == sp]
            im = draw_boxes(s.overview(1600), bs)
            out = os.path.join(a.overview_dir, os.path.splitext(os.path.basename(sp))[0] + "_shots.png")
            im.save(out)
            print(f"位置核對：{out}")
    for s in cache.values():
        s.close()


def main():
    ap = argparse.ArgumentParser(description="全玻片掃描檔（.svs）切實驗講義截圖")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info")
    p.add_argument("slide")
    p = sub.add_parser("overview")
    p.add_argument("slide")
    p.add_argument("--out", required=True)
    p.add_argument("--max-side", type=int, default=1800)
    p.add_argument("--grid", type=int, default=10, help="格線數（0＝不畫）")
    p.add_argument("--boxes", help="batch.json：標出已切截圖的位置（要先跑過 batch，box 才有值）")
    p = sub.add_parser("crop")
    p.add_argument("slide")
    p.add_argument("--cx", type=float, required=True)
    p.add_argument("--cy", type=float, required=True)
    p.add_argument("--mag", type=float, required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--w", type=int, default=OUT_W)
    p.add_argument("--h", type=int, default=OUT_H)
    p.add_argument("--grid", type=int, default=0, help="格線數（細調用；交件的圖不要加）")
    p = sub.add_parser("batch")
    p.add_argument("spec")
    p.add_argument("--overview-dir")
    a = ap.parse_args()
    {"info": cmd_info, "overview": cmd_overview, "crop": cmd_crop, "batch": cmd_batch}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())

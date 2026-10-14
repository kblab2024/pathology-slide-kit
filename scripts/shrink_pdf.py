# -*- coding: utf-8 -*-
"""把成品 PDF 的 JPEG 圖縮小（長邊 900 px、品質 72），給 OneDrive 用。

教師 Mac 上的 OneDrive（商務版）常傳不上大檔：會一直重試、卡住整個上傳佇列
（2026-10-02：21.5 MB 的 PDF 失敗 6 萬多次，11 MB 的半份可以；2026-10-14 晚：8.9–21 MB 的 PPTX 也卡住，小的 md、docx 正常）。
所以 OneDrive 放壓縮版，repo 的 成品/ 留原解析度。字是向量，不受影響。壓了還傳不上的，改用 git 交件。
卡住時：把那個檔移出 OneDrive（不要刪、不要同名放回），記下檔名，新版本用新檔名（docs/教師偏好與決策.md 第 8 節）。

用法：python shrink_pdf.py <in.pdf> <out.pdf> [長邊px=900] [品質=72]
"""
import io, os, sys
import fitz
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
MAXSIDE = int(sys.argv[3]) if len(sys.argv) > 3 else 900
Q = int(sys.argv[4]) if len(sys.argv) > 4 else 72
d = fitz.open(src)
n = 0
for x in range(1, d.xref_length()):
    try:
        if (d.xref_get_key(x, "Subtype")[1] != "/Image" or d.xref_get_key(x, "Filter")[1] != "/DCTDecode"
                or d.xref_get_key(x, "SMask")[0] != "null"):
            continue
    except Exception:
        continue
    raw = d.xref_stream_raw(x)
    try:
        im = Image.open(io.BytesIO(raw)); im.load()
    except Exception:
        continue
    im = im.convert("L" if im.mode == "L" else "RGB")
    if max(im.size) > MAXSIDE:
        f = MAXSIDE / max(im.size)
        im = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "JPEG", quality=Q, optimize=True); nb = b.getvalue()
    if len(nb) >= len(raw) * 0.95:
        continue
    # 圖在 Quartz PDF 的巢狀物件裡，page.replace_image 碰不到，直接換串流
    d.update_stream(x, nb, compress=False)
    for k, v in (("Filter", "/DCTDecode"), ("Width", str(im.width)), ("Height", str(im.height)),
                 ("ColorSpace", "/DeviceGray" if im.mode == "L" else "/DeviceRGB"),
                 ("BitsPerComponent", "8"), ("DecodeParms", "null")):
        d.xref_set_key(x, k, v)
    n += 1
d.save(out, garbage=4, deflate=True)
print(f"{n} images -> {out} {os.path.getsize(out) / 1e6:.1f} MB")

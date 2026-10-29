"""PC 端字体生成:Bahnschrift → 抗锯齿字形(4bpp alpha)→ weatherstation/font.py
板上由 ui.aa_text 做 alpha 混合绘制。用法:
  venv/Scripts/python.exe code/makefont.py
"""
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "C:/Windows/Fonts/bahnschrift.ttf"
SIZES = (64, 24)   # 64=大数字(时钟/温度), 24=标签/正文
CHARSET = sorted(set("0123456789 :.-%°?/" +
                     "".join(chr(c) for c in range(0x41, 0x5B)) +   # A-Z
                     "".join(chr(c) for c in range(0x61, 0x7B))))   # a-z


def pack4(pixels):
    """0-15 灰度列表 → 4bpp 打包字节(奇数宽度补 0 nibble)。"""
    out = bytearray()
    for i in range(0, len(pixels), 2):
        hi = pixels[i]
        lo = pixels[i + 1] if i + 1 < len(pixels) else 0
        out.append((hi << 4) | lo)
    return bytes(out)


def render_glyph(font, ch, height):
    """单字形 → (宽, 逐行 4bpp bytes,行长 = ceil(w/2))。与板上 ui.aa_text 索引对齐。"""
    if ch == " ":   # 空格:给正常宽度,全透明
        w = max(3, height // 3)
        return w, bytes(((w + 1) // 2) * height)
    l, t, r, b = font.getbbox(ch)
    w = max(1, r - l)
    img = Image.new("L", (w, height), 0)
    ImageDraw.Draw(img).text((-l, 0), ch, font=font, fill=255)
    px = img.tobytes()
    rows = (pack4([p >> 4 for p in px[y * w:(y + 1) * w]])
            for y in range(height))
    return w, b"".join(rows)


heights = {}
glyphs = {}
for px in SIZES:
    f = ImageFont.truetype(FONT_PATH, px)
    asc, desc = f.getmetrics()
    H = asc + desc
    heights[px] = H
    glyphs[px] = {ch: render_glyph(f, ch, H) for ch in CHARSET}

with open("font.py", "w", encoding="utf-8") as fp:
    fp.write("# 自动生成(makefont.py),勿手改:Bahnschrift 4bpp 抗锯齿字形\n")
    fp.write("HEIGHTS = {}\n".format(repr(heights)))
    fp.write("GLYPHS = {}\n".format(repr(glyphs)))

import os
sz = os.path.getsize("font.py")
print("font.py written: {:.0f} KB, heights={}".format(sz / 1024, heights))

"""PC 端字体生成:TTF/TTC → 抗锯齿字形(4bpp alpha)→ font.py
板上由 ui.aa_text 做 alpha 混合绘制。

用法(字体路径可用环境变量覆盖,见下方 FONTS):
  python makefont.py
  FONT_BOLD=/path/NotoSansCJK-Bold.ttc FONT_REGULAR=/path/NotoSansCJK-Regular.ttc python makefont.py

字库子集策略:大字号(96/64/56)只生成数字和符号;中文只出现在 24/18/16 三档,
且只生成 CHARSET_CN 里列出的字。新增界面文字时,先把字加进对应档位的字符集再重新生成。
"""
import os
from PIL import Image, ImageDraw, ImageFont

# ---- 字体文件(Noto Sans CJK,SIL OFL,可免费商用)。.ttc 里的 index:0=JP 1=KR 2=SC 3=TC 4=HK ----
BOLD = (os.environ.get("FONT_BOLD", "C:/Windows/Fonts/NotoSansCJKsc-Bold.otf"),
        int(os.environ.get("FONT_BOLD_INDEX", "0")))
REGULAR = (os.environ.get("FONT_REGULAR", "C:/Windows/Fonts/NotoSansCJKsc-Regular.otf"),
           int(os.environ.get("FONT_REGULAR_INDEX", "0")))

DIGITS = "0123456789"
ASCII_LABEL = DIGITS + " -.:%°?/C·"
# 界面用到的全部汉字(与 main.py 的文案、WMO_CN、PERIODS、comfort() 一一对应)
CHARSET_CN = ("星期一二三四五六日年月"        # 日期
              "晨昼傍晚夜间清凌上午下"         # 时段
              "晴多云阴雾凇小中大毛冻雨阵雪暴雷"  # 天况
              "最高低湿度温室内外舒适干燥潮"     # 标签
              "暂无天气数据未接传感器"          # 降级文案
              "北京")                           # 城市名:config.CITY_NAME 改成别的城市时把字加进来

# 档位 → (字体, 字符集)。键就是 font.GLYPHS 的键(像素字号),所以同一字号只能有一种字重。
SIZES = {
    96: (BOLD, DIGITS + "-"),                 # 天气页 室外温度
    64: (BOLD, DIGITS + ":"),                 # 时钟页 HH:MM
    56: (BOLD, DIGITS + ".-"),                # 温湿度页 两个大数
    24: (BOLD, ASCII_LABEL + CHARSET_CN),     # 卡片数值 / 日期
    18: (REGULAR, ASCII_LABEL + CHARSET_CN +   # 城市、时段、天况、页面标签
         "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"),  # 城市名若用拼音也能显示
    16: (REGULAR, ASCII_LABEL + CHARSET_CN),  # 卡片小标签
}
OUT = os.environ.get("FONT_OUT", "font.py")


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
    if ch == " ":
        w = max(3, height // 3)
        return w, bytes(((w + 1) // 2) * height)
    l, t, r, b = font.getbbox(ch)
    w = max(1, r - l)
    img = Image.new("L", (w, height), 0)
    ImageDraw.Draw(img).text((-l, 0), ch, font=font, fill=255)
    px = img.tobytes()
    rows = (pack4([p >> 4 for p in px[y * w:(y + 1) * w]]) for y in range(height))
    return w, b"".join(rows)


def build():
    heights, glyphs = {}, {}
    for px, ((path, index), chars) in SIZES.items():
        f = ImageFont.truetype(path, px, index=index)
        asc, desc = f.getmetrics()
        H = asc + desc
        g = {ch: render_glyph(f, ch, H) for ch in sorted(set(chars))}
        # 裁掉本档所有字形共同的上下空白行(Noto 行高很松,96px 档 H=140):
        # 省内存,也让 aa_text 少扫空行。裁剪后 y 坐标 = 本档"墨迹带"顶边。
        top, bot = H, 0
        for w, data in g.values():
            st = (w + 1) // 2
            for y in range(H):
                if any(data[y * st:(y + 1) * st]):
                    top, bot = min(top, y), max(bot, y + 1)
        heights[px] = bot - top
        glyphs[px] = {ch: (w, data[top * ((w + 1) // 2):bot * ((w + 1) // 2)]) for ch, (w, data) in g.items()}
    with open(OUT, "w", encoding="utf-8") as fp:
        fp.write("# 自动生成(makefont.py),勿手改:Noto Sans CJK SC 4bpp 抗锯齿字形子集\n")
        fp.write("HEIGHTS = {}\n".format(repr(heights)))
        fp.write("GLYPHS = {}\n".format(repr(glyphs)))
    sz = os.path.getsize(OUT)
    print("{} written: {:.0f} KB, heights={}, glyphs={}".format(
        OUT, sz / 1024, heights, {k: len(v) for k, v in glyphs.items()}))


if __name__ == "__main__":
    build()

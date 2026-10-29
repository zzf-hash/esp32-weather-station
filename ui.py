"""UI 小工具:方向二「暖色渐变卡片」配色/背景色带/圆角卡片/矢量天气图标 + 抗锯齿字体。
全部只用 framebuf 原语(fill_rect/ellipse/line),不用位图;整屏推送仍是 ~1s,不做动画。"""
import framebuf


def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


BLACK  = 0
WHITE  = rgb565(255, 255, 255)
GREY   = rgb565(120, 120, 130)
RED    = rgb565(255, 70, 70)
GREEN  = rgb565(60, 220, 120)
BLUE   = rgb565(70, 130, 255)
CYAN   = rgb565(0, 225, 225)
YELLOW = rgb565(255, 215, 60)

# ---------- 方向二配色(RGB565 值见 设计规范.md)----------
CARD    = rgb565(255, 247, 238)   # 0xFFBD 卡片奶白
INK     = rgb565(58, 40, 32)      # 0x3944 卡片主字 深棕
SUB     = rgb565(150, 120, 104)   # 0x93CD 卡片次要字
SUN     = rgb565(255, 184, 48)    # 0xFDC6
CLOUD   = WHITE                   # 0xFFFF 前景云
CLOUD_D = rgb565(214, 222, 234)   # 0xD6FD 卡片上的云(白卡上需要灰一点)
MOON    = rgb565(255, 230, 170)   # 0xFF35
RAIN    = rgb565(120, 190, 255)   # 0x7DFF
TEAL    = rgb565(46, 150, 160)    # 0x2CB4 低温/湿度
HOT     = rgb565(226, 110, 60)    # 0xE367 高温/干燥
OK      = rgb565(40, 140, 90)     # 0x2C6B 舒适
TRACK   = rgb565(236, 222, 208)   # 0xEEFA 进度条底
BOLT    = rgb565(255, 220, 60)    # 0xFEE7 闪电
TXT_ON  = WHITE                   # 色带上的字
TXT_SUB = rgb565(255, 236, 220)   # 0xFF7B 色带上的次要字

# 背景色带:键 → (顶 RGB888, 底 RGB888, 页码点颜色)。10 条 × 32px,每条一个 RGB565 色。
SKY = {
    'dawn':  ((255, 170, 130), (255, 226, 190), WHITE),   # 晨 5-8
    'day':   ((96, 168, 236), (196, 228, 250), WHITE),    # 昼 8-17
    'dusk':  ((70, 60, 140), (250, 140, 100), WHITE),     # 暮 17-20
    'night': ((16, 24, 60), (52, 60, 116), WHITE),        # 夜 20-5
    'cloud': ((130, 150, 180), (236, 214, 196), WHITE),   # 多云/阴
    'fog':   ((150, 150, 160), (220, 214, 206), WHITE),   # 雾
    'rain':  ((60, 80, 112), (140, 160, 184), WHITE),     # 雨
    'snow':  ((150, 180, 220), (236, 242, 250), WHITE),   # 雪
    'storm': ((40, 36, 70), (110, 90, 130), WHITE),       # 雷
    'home':  ((255, 214, 170), (255, 244, 226), rgb565(190, 140, 110)),  # 室内
}


def bands(fb, key, n=10):
    """竖向 n 条均匀色带模拟渐变(10 次 fill_rect)。不要逐行插值:RGB565 低饱和过渡会出现不规则色带。"""
    (r0, g0, b0), (r1, g1, b1), _ = SKY[key]
    h = 320 // n
    for i in range(n):
        t = i * 255 // (n - 1)
        fb.fill_rect(0, i * h, 240, h, rgb565(r0 + (r1 - r0) * t // 255,
                                              g0 + (g1 - g0) * t // 255,
                                              b0 + (b1 - b0) * t // 255))


def rrect(fb, x, y, w, h, r, c):
    """圆角矩形 = 2 个 fill_rect + 4 个填充 ellipse。"""
    fb.fill_rect(x + r, y, w - 2 * r, h, c)
    fb.fill_rect(x, y + r, w, h - 2 * r, c)
    for cx, cy in ((x + r, y + r), (x + w - r - 1, y + r),
                   (x + r, y + h - r - 1), (x + w - r - 1, y + h - r - 1)):
        fb.ellipse(cx, cy, r, r, c, True)


def page_dots(fb, page, n, c, y=302):
    """页码:当前页为 22×8 胶囊,其余为 6px 圆点。"""
    for i in range(n):
        x = 96 + i * 18 + (8 if i > page else 0)
        if i == page:
            fb.fill_rect(x + 3, y + 1, 16, 7, c)
            fb.ellipse(x + 3, y + 4, 3, 3, c, True)
            fb.ellipse(x + 18, y + 4, 3, 3, c, True)
        else:
            fb.ellipse(x + 4, y + 4, 3, 3, c, True)


def deg(fb, x, y, r, c, bg):
    """度数圈:外圆 r 实心 + 内圆 r/2 背景色。"""
    fb.ellipse(x, y, r, r, c, True)
    fb.ellipse(x, y, r // 2, r // 2, bg, True)


# ---------- 矢量天气图标(s=1 约 72×56px;s=2 为一半大小,给时钟页卡片用)----------
_RAYS = ((10, 0), (7, 7), (0, 10), (-7, 7), (-10, 0), (-7, -7), (0, -10), (7, -7))


def icon_sun(fb, cx, cy, r, c=SUN):
    for dx, dy in _RAYS:
        x0, y0 = cx + dx * (r + 5) // 10, cy + dy * (r + 5) // 10
        x1, y1 = cx + dx * (r + 11) // 10, cy + dy * (r + 11) // 10
        for o in (-1, 0, 1):
            fb.line(x0 + o, y0, x1 + o, y1, c)
    fb.ellipse(cx, cy, r, r, c, True)


def icon_moon(fb, cx, cy, r, bg):
    fb.ellipse(cx, cy, r, r, MOON, True)
    fb.ellipse(cx + r // 2, cy - r // 3, r - 2, r - 2, bg, True)   # bg = 该处背景色带色


def icon_cloud(fb, x, y, c, s=1):
    """x,y = 云底左角;宽 ≈ 74/s。"""
    fb.ellipse(x + 22 // s, y - 16 // s, 16 // s, 16 // s, c, True)
    fb.ellipse(x + 44 // s, y - 22 // s, 20 // s, 20 // s, c, True)
    fb.ellipse(x + 62 // s, y - 12 // s, 12 // s, 12 // s, c, True)
    rrect(fb, x + 6 // s, y - 14 // s, 68 // s, 14 // s, 7 // s, c)


def icon_rain(fb, x, y, c=RAIN):
    for i in range(4):                       # 4 根 3px 宽斜雨线
        xx = x + 16 + i * 14
        for o in (0, 1, 2):
            fb.line(xx + o, y + 6, xx - 6 + o, y + 18, c)


def icon_snow(fb, x, y, c=WHITE):
    for i, (dx, dy) in enumerate(((16, 10), (32, 18), (48, 10), (64, 18))):
        fb.ellipse(x + dx, y + dy, 3, 3, c, True)


def icon_fog(fb, x, y, c):
    for i in range(3):
        rrect(fb, x + 4 + i * 6, y - 30 + i * 12, 64 - i * 6, 6, 3, c)


def icon_bolt(fb, x, y, c=BOLT):
    for o in range(4):
        fb.line(x + 40 + o, y + 2, x + 30 + o, y + 14, c)
        fb.line(x + 30 + o, y + 14, x + 42 + o, y + 14, c)
        fb.line(x + 42 + o, y + 14, x + 32 + o, y + 28, c)


def weather_icon(fb, group, night, x, y, bg, small=False):
    """group 见 main.wx_group;x,y = 图标区左下角。small=True 给时钟页卡片(白底)。"""
    if small:
        cc = CLOUD_D
        if group == 'clear':
            (icon_moon(fb, x + 36, y - 14, 12, bg) if night else icon_sun(fb, x + 36, y - 14, 10))
        else:
            if group == 'cloud':
                icon_sun(fb, x + 42, y - 26, 7)
            icon_cloud(fb, x, y, cc if group != 'storm' else SUB, 2)
            if group == 'rain':
                for i in range(3):
                    fb.line(x + 10 + i * 10, y + 3, x + 7 + i * 10, y + 9, RAIN)
            elif group == 'snow':
                for i in range(3):
                    fb.ellipse(x + 10 + i * 10, y + 6, 2, 2, CLOUD_D, True)
        return
    if group == 'clear':
        if night:
            icon_moon(fb, x + 44, y - 30, 24, bg)
        else:
            icon_sun(fb, x + 44, y - 30, 20)
    elif group == 'cloud':
        icon_sun(fb, x + 54, y - 44, 16)
        icon_cloud(fb, x, y, CLOUD)
    elif group == 'fog':
        icon_fog(fb, x, y, CLOUD)
    elif group == 'rain':
        icon_cloud(fb, x, y - 12, CLOUD)
        icon_rain(fb, x, y - 12)
    elif group == 'snow':
        icon_cloud(fb, x, y - 12, CLOUD)
        icon_snow(fb, x, y - 12)
    else:  # storm
        icon_cloud(fb, x, y - 12, CLOUD_D)
        icon_bolt(fb, x, y - 12)

_MONO = getattr(framebuf, 'MONO_VLSB', getattr(framebuf, 'MVLSB', 1))
_tmp = framebuf.FrameBuffer(bytearray(8 * 8), 8, 8, _MONO)


def text_scaled(fb, s, x, y, scale, color):
    """8x8 字体放大 scale 倍绘制,返回结束 x 坐标。"""
    for ch in s:
        _tmp.fill(0)
        _tmp.text(ch, 0, 0, 1)
        for py in range(8):
            for px in range(8):
                if _tmp.pixel(px, py):
                    fb.fill_rect(x + px * scale, y + py * scale, scale, scale, color)
        x += 8 * scale
    return x


def center_text(fb, s, y, scale, color, width=240):
    text_scaled(fb, s, max(0, (width - len(s) * 8 * scale) // 2), y, scale, color)


# ---------- 抗锯齿字体(makefont.py 生成 font.py,默认 Noto Sans CJK SC 4bpp 子集) ----------
import font


def aa_width(s, px):
    g = font.GLYPHS[px]
    return sum(g[c][0] + 2 for c in s if c in g) - 2


def _expand(color):
    """RGB565 → 展开的 (r8, g8, b8)。"""
    r = (color >> 11) & 0x1F
    g = (color >> 5) & 0x3F
    b = color & 0x1F
    return (r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)


def aa_text(fb, s, x, y, px, color):
    """抗锯齿绘制:实心段 fill_rect 批处理,边缘像素逐点 alpha 混合。返回结束 x。"""
    glyphs = font.GLYPHS[px]
    H = font.HEIGHTS[px]
    fr, fg, fb_ = _expand(color)
    for ch in s:
        if ch not in glyphs:          # 字库子集里没有的字:跳过(不崩站);新增文案记得重新 makefont
            continue
        w, data = glyphs[ch]
        stride = (w + 1) // 2
        for gy in range(H):
            row = gy * stride
            yy = y + gy
            gx = 0
            while gx < w:
                byte = data[row + gx // 2]
                a = (byte >> 4) if (gx % 2 == 0) else (byte & 0xF)
                if a == 15:                       # 实心段:整段一次画
                    gs = gx
                    gx += 1
                    while gx < w:
                        b2 = data[row + gx // 2]
                        a2 = (b2 >> 4) if (gx % 2 == 0) else (b2 & 0xF)
                        if a2 != 15:
                            break
                        gx += 1
                    fb.fill_rect(x + gs, yy, gx - gs, 1, color)
                elif a == 0:
                    gx += 1
                else:                             # 边缘:RGB565 alpha 混合
                    pc = fb.pixel(x + gx, yy)
                    pr = (pc >> 11) & 0x1F
                    pg = (pc >> 5) & 0x3F
                    pb = pc & 0x1F
                    pr = (pr << 3) | (pr >> 2)
                    pg = (pg << 2) | (pg >> 4)
                    pb = (pb << 3) | (pb >> 2)
                    nr = (fr * a + pr * (15 - a)) // 15
                    ng = (fg * a + pg * (15 - a)) // 15
                    nb = (fb_ * a + pb * (15 - a)) // 15
                    fb.pixel(x + gx, yy,
                             ((nr >> 3) << 11) | ((ng >> 2) << 5) | (nb >> 3))
                    gx += 1
        x += w + 2
    return x


def aa_center(fb, s, y, px, color, width=240, cx=None):
    if cx is None:
        cx = width // 2
    return aa_text(fb, s, max(0, cx - aa_width(s, px) // 2), y, px, color)


def aa_right(fb, s, xr, y, px, color):
    return aa_text(fb, s, xr - aa_width(s, px), y, px, color)

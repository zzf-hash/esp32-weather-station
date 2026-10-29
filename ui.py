"""UI 小工具:配色 + 放大字体(framebuf 内置 8x8 字体的整数倍放缩)。"""
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


# ---------- 抗锯齿字体(makefont.py 生成 font.py,Bahnschrift 4bpp) ----------
import font


def aa_width(s, px):
    g = font.GLYPHS[px]
    return sum(g[c][0] + 2 for c in s) - 2


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


def aa_center(fb, s, y, px, color, width=240):
    aa_text(fb, s, max(0, (width - aa_width(s, px)) // 2), y, px, color)

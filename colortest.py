"""校色色板:方向二主要色块 + 纯红/绿/蓝/白,ASCII 标注(framebuf 内置 8x8 字体)。
刷写运行(不覆盖板上 main.py):
    mpremote connect COM7 cp ili9341.py config.py :/ + run colortest.py
屏幕初始化与 main.py 完全相同(SoftSPI 2MHz + ili9341.ILI9341 + config 引脚)。
判读与修正见 设计规范.md「校色」一节;下面两个开关用来现场试:"""
SWAP_BYTES = False   # True:每个颜色先做高低字节交换再画(验证"颜色发花"是不是字节序问题)
MADCTL = None        # None=用驱动默认 0x48;红蓝互换时试 0x40(去掉 BGR 位)


def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def sw(c):
    return ((c & 0xFF) << 8) | (c >> 8) if SWAP_BYTES else c


# (标注, RGB888) —— 与 ui.py 同值
SW = [('RED', (255, 0, 0)), ('GREEN', (0, 255, 0)), ('BLUE', (0, 0, 255)),
      ('WHITE', (255, 255, 255)), ('BLACK', (0, 0, 0)), ('CARD', (255, 247, 238)),
      ('INK', (58, 40, 32)), ('SUB', (150, 120, 104)), ('SUN', (255, 184, 48)),
      ('TEAL', (46, 150, 160)), ('HOT', (226, 110, 60)), ('OK', (40, 140, 90)),
      ('CLOUD_D', (214, 222, 234)), ('TRACK', (236, 222, 208)), ('RAIN', (120, 190, 255)),
      ('DUSK_T', (70, 60, 140)), ('DUSK_B', (250, 140, 100)), ('NIGHT_T', (16, 24, 60)),
      ('DAY_T', (96, 168, 236)), ('HOME_T', (255, 214, 170)), ('FOG_T', (150, 150, 160))]


def draw(fb):
    fb.fill(0)
    for i, (name, (r, g, b)) in enumerate(SW):       # 3 列 x 7 行,每格 80x40
        x, y = (i % 3) * 80, (i // 3) * 40
        c = rgb565(r, g, b)
        fb.fill_rect(x, y, 80, 40, sw(c))
        dark = (r * 3 + g * 6 + b) // 10 > 150        # 浅色块用黑字,深色块用白字
        tc = sw(0) if dark else sw(0xFFFF)
        fb.text(name, x + 3, y + 6, tc)
        fb.text('{:04X}'.format(c), x + 3, y + 26, tc)
    # 底部 40px:暮色 10 条色带(界面里真实使用的渐变方式),检查色带台阶是否均匀
    (r0, g0, b0), (r1, g1, b1) = (70, 60, 140), (250, 140, 100)
    for i in range(10):
        t = i * 255 // 9
        fb.fill_rect(i * 24, 280, 24, 40, sw(rgb565(r0 + (r1 - r0) * t // 255,
                                                       g0 + (g1 - g0) * t // 255,
                                                       b0 + (b1 - b0) * t // 255)))
    fb.text('SWAP=%d MADCTL=%s' % (SWAP_BYTES, 'def' if MADCTL is None else hex(MADCTL)),
            4, 284, sw(0xFFFF))


if __name__ == '__main__':
    import config
    from machine import Pin, SoftSPI
    from ili9341 import ILI9341
    spi = SoftSPI(baudrate=2_000_000, sck=Pin(config.PIN_TFT_SCK),
                  mosi=Pin(config.PIN_TFT_MOSI), miso=Pin(9))
    tft = ILI9341(spi, cs=Pin(config.PIN_TFT_CS, Pin.OUT), dc=Pin(config.PIN_TFT_DC, Pin.OUT),
                  rst=Pin(config.PIN_TFT_RST, Pin.OUT), bl=Pin(config.PIN_TFT_BL, Pin.OUT))
    if MADCTL is not None:
        tft._write(0x36, bytes([MADCTL]))
    draw(tft.fb)
    tft.show()
    print('colortest shown: SWAP_BYTES=%s MADCTL=%s' % (SWAP_BYTES, MADCTL))

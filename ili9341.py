"""ILI9341 240x320 SPI TFT driver — RGB565 full-frame buffer, one-shot blit."""
import framebuf
import utime

# (cmd, data, delay_ms) — 经典 ILI9341 上电序列
_INIT = (
    (0x01, None, 150),                       # SWRESET
    (0x28, None, 0),                         # display off
    (0xCF, b'\x00\xc1\x30', 0),              # PWCTRB
    (0xED, b'\x64\x03\x12\x81', 0),          # PWRSEQ
    (0xE8, b'\x85\x00\x78', 0),              # DRVCTLA
    (0xCB, b'\x39\x2c\x00\x34\x02', 0),      # PWCTRA
    (0xF7, b'\x20', 0),                      # GMCTRL
    (0xEA, b'\x00\x00', 0),                  # DRVCTLB
    (0xC0, b'\x23', 0),                      # PWCTR1
    (0xC1, b'\x10', 0),                      # PWCTR2
    (0xC5, b'\x3e\x28', 0),                  # VMCTR1
    (0xC7, b'\x86', 0),                      # VMCTR2
    (0x36, b'\x48', 0),                      # MADCTL: 竖屏 240x320, BGR, MX(横向不镜像)
    (0x3A, b'\x55', 0),                      # COLMOD: 16bit 色
    (0xB1, b'\x00\x18', 0),                  # FRMCTR1
    (0xB6, b'\x08\x82\x27', 0),              # DISCTRL
    (0xF2, b'\x00', 0),                      # 3GFUNC off
    (0x26, b'\x01', 0),                      # GAMSET
    (0xE0, b'\x0f\x31\x2b\x0c\x0e\x08\x4e\xf1\x37\x07\x10\x03\x0e\x09\x00', 0),
    (0xE1, b'\x00\x0e\x14\x03\x11\x07\x31\xc1\x48\x08\x0f\x0c\x31\x36\x0f', 0),
    (0x11, None, 120),                       # SLPOUT
    (0x29, None, 20),                        # DISPON
)


class ILI9341:
    def __init__(self, spi, cs, dc, rst, bl, width=240, height=320):
        self.w, self.h = width, height
        self.spi = spi
        self.cs, self.dc, self.rst = cs, dc, rst
        rst.value(0); utime.sleep_ms(20)
        rst.value(1); utime.sleep_ms(150)
        for cmd, data, delay in _INIT:
            self._write(cmd, data)
            if delay:
                utime.sleep_ms(delay)
        self.buf = bytearray(width * height * 2)
        self.fb = framebuf.FrameBuffer(self.buf, width, height, framebuf.RGB565)
        if height < 320:   # 帧缓冲比面板矮:把底部余下的行刷黑,避免残留花屏
            self._write(0x2A, bytes((0, 0, 0, width - 1)))
            self._write(0x2B, bytes(((height >> 8) & 0xFF, height & 0xFF, 0x01, 0x3F)))
            self.cs.value(0)
            self.dc.value(0)
            self.spi.write(b'\x2C')
            self.dc.value(1)
            self.spi.write(bytes(4096) * 7 + bytes(1920))   # 240*(320-height)*2 = 30720
            self.cs.value(1)
        bl.value(1)   # 点亮背光

    def _write(self, cmd, data=None):
        self.cs.value(0)
        self.dc.value(0)
        self.spi.write(bytes([cmd]))
        self.dc.value(1)
        if data:
            self.spi.write(data)
        self.cs.value(1)

    def show(self):
        """整帧推屏(150KB @40MHz SPI,约几十毫秒)"""
        self._write(0x2A, bytes((0, 0, (self.w - 1) >> 8, (self.w - 1) & 0xFF)))  # CASET
        self._write(0x2B, bytes((0, 0, (self.h - 1) >> 8, (self.h - 1) & 0xFF)))  # PASET
        self.cs.value(0)
        self.dc.value(0)
        self.spi.write(b'\x2C')   # RAMWR
        self.dc.value(1)
        self.spi.write(self.buf)
        self.cs.value(1)

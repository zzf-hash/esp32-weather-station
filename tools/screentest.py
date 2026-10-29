"""ILN9341 全链路分步探针:构造→首个命令写→若干命令→帧缓冲分配→150KB 整帧写。
哪一步之后没有下一个标记 = 死在那一步。用法: python screentest.py [COM7]
"""
import sys
import time

import serial

port = sys.argv[1] if len(sys.argv) > 1 else 'COM7'

code = (
    "from machine import SPI, Pin\n"
    "import utime\n"
    "print('A: start')\n"
    "spi = SPI(2, baudrate=40000000, sck=Pin(12), mosi=Pin(11))\n"
    "print('B: spi constructed')\n"
    "cs=Pin(10,Pin.OUT); dc=Pin(14,Pin.OUT); rst=Pin(13,Pin.OUT); bl=Pin(18,Pin.OUT)\n"
    "print('C: pins ok')\n"
    "rst.value(0); utime.sleep_ms(20); rst.value(1); utime.sleep_ms(150)\n"
    "print('D: reset pulse ok')\n"
    "def w(cmd, data=None):\n"
    "    cs.value(0); dc.value(0); spi.write(bytes([cmd])); dc.value(1)\n"
    "    if data: spi.write(data)\n"
    "    cs.value(1)\n"
    "w(0x01); utime.sleep_ms(150)\n"
    "print('E: first cmd write ok (SWRESET)')\n"
    "w(0x28); w(0xCF, b'\\x00\\xc1\\x30'); w(0xED, b'\\x64\\x03\\x12\\x81')\n"
    "print('F: init cmds ok')\n"
    "buf = bytearray(240*320*2)\n"
    "print('G: fb alloc ok', len(buf))\n"
    "w(0x2A, bytes((0,0,0,239))); w(0x2B, bytes((0,0,0x01,0x3F)))\n"
    "cs.value(0); dc.value(0); spi.write(b'\\x2C'); dc.value(1)\n"
    "print('H: RAMWR ok')\n"
    "spi.write(buf)\n"
    "cs.value(1)\n"
    "print('I: 150KB frame write ok')\n"
    "bl.value(1)\n"
    "print('J: backlight on - ALL OK')\n"
)

s = serial.Serial(port, 115200, timeout=0.1)
s.setDTR(False)
s.setRTS(False)
time.sleep(0.1)
deadline = time.time() + 5
buf = b''
while time.time() < deadline and b'>>>' not in buf:
    buf += s.read(4096)
if b'>>>' not in buf:
    print('[screentest] WARN: no prompt seen, sending anyway')
time.sleep(0.2)
s.write(b'\x03')
time.sleep(0.3)
s.reset_input_buffer()
s.write(b'\x05')
time.sleep(0.2)
s.write(code.encode())
s.write(b'\x04')
print('[screentest] code sent, watching 15s...')
end = time.time() + 15
while time.time() < end:
    d = s.read(4096)
    if d:
        sys.stdout.write(d.decode('utf-8', 'replace'))
        sys.stdout.flush()
s.close()
print('\n[screentest] done')

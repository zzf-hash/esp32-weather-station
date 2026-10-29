"""经 UART REPL 粘贴一段代码并观察 8 秒输出。
用法: python spitest.py [COM7]
用途:测 SPI(2) 构造是否击穿芯片(老板伤情复现),崩了能看到 Guru Meditation 现场 dump。
"""
import sys
import time

import serial

port = sys.argv[1] if len(sys.argv) > 1 else 'COM7'

code = (
    "from machine import SPI, Pin\n"
    "print('importing ok')\n"
    "spi = SPI(2, baudrate=40_000_000, sck=Pin(12), mosi=Pin(11))\n"
    "print('CONSTRUCT_OK')\n"
    "import utime\n"
    "spi.write(bytearray(2048))\n"
    "print('WRITE_OK')\n"
    "spi.deinit()\n"
    "print('ALL_DONE')\n"
)

s = serial.Serial(port, 115200, timeout=0.1)
s.setDTR(False)
s.setRTS(False)
time.sleep(0.1)
# 开口可能触发 CH343 自动复位 → 先等 REPL 提示符出现(最多 5s),字节不再打进启动过程里
deadline = time.time() + 5
buf = b''
while time.time() < deadline and b'>>>' not in buf:
    buf += s.read(4096)
if b'>>>' not in buf:
    print('[spitest] WARN: no prompt seen, sending anyway')
time.sleep(0.2)
s.write(b'\x03')          # Ctrl-C 打断
time.sleep(0.3)
s.reset_input_buffer()
s.write(b'\x05')          # 进粘贴模式
time.sleep(0.2)
s.write(code.encode())
s.write(b'\x04')          # Ctrl-D 执行
print('[spitest] code sent, watching 8s...')
end = time.time() + 8
while time.time() < end:
    d = s.read(4096)
    if d:
        sys.stdout.write(d.decode('utf-8', 'replace'))
        sys.stdout.flush()
s.close()
print('\n[spitest] done')

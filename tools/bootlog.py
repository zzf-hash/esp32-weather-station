"""抓 ESP32 的 UART0 启动日志:开 COM 口 → DTR/RTS 都拉 False → 脉冲 RTS 复位 → 读 N 秒。
用法: python bootlog.py [COM7] [波特率] [秒数]
"""
import sys
import time

import serial

port = sys.argv[1] if len(sys.argv) > 1 else 'COM7'
baud = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
secs = float(sys.argv[3]) if len(sys.argv) > 3 else 5

s = serial.Serial(port, baud, timeout=0.1)
s.setDTR(False)          # 全程拉 False,一直 Low 会把板子按进下载模式
s.setRTS(False)
time.sleep(0.1)
s.setRTS(True)           # RTS → EN,脉冲一下 = 按复位
time.sleep(0.05)
s.setRTS(False)
s.reset_input_buffer()

print('[bootlog] {} @{}, reading {}s...'.format(port, baud, secs))
end = time.time() + secs
while time.time() < end:
    data = s.read(4096)
    if data:
        sys.stdout.write(data.decode('utf-8', 'replace'))
        sys.stdout.flush()
s.close()
print('\n[bootlog] done')

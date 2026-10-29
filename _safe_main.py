# 二分排查用:最简 main.py,不 import 项目代码、不碰引脚
import utime
n = 0
while True:
    print('[safe]', n)
    n += 1
    utime.sleep_ms(500)

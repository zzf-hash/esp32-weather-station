"""桌面气象站:时钟页 / 天气页(Open-Meteo)/ 室内温湿度页(AHT20)。
BOOT 键翻页,自动轮换;屏幕未接入时降级为 USB 口打印状态。"""
import utime
import config
import ui
from machine import Pin

# ---------- 硬件初始化(屏和 AHT20 各自独立 try,缺哪个都不影响另一个) ----------
# 固件:SPIRAM_OCT v1.28.0(8MB PSRAM,堆 ~8MB——v1.29 的 SPI(2) 有崩溃 bug,别升)。
tft = None
aht = None
if config.HARDWARE_PRESENT:
    try:
        from machine import SoftSPI
        from ili9341 import ILI9341
        # SPIRAM_OCT 固件的硬件 SPI(2) 全系列崩溃(1.26.1~preview 实测)——改 SoftSPI,
        # 实测 2MHz 档 151KB/s,整屏 ~1s;主循环按内容签名重绘,不逐秒刷。miso 给个空脚。
        spi = SoftSPI(baudrate=2_000_000,
                      sck=Pin(config.PIN_TFT_SCK), mosi=Pin(config.PIN_TFT_MOSI), miso=Pin(9))
        tft = ILI9341(spi,
                      cs=Pin(config.PIN_TFT_CS, Pin.OUT),
                      dc=Pin(config.PIN_TFT_DC, Pin.OUT),
                      rst=Pin(config.PIN_TFT_RST, Pin.OUT),
                      bl=Pin(config.PIN_TFT_BL, Pin.OUT))
        print('[hw] screen ready')
    except Exception as e:
        print('[hw] screen init failed:', e)
        tft = None
    try:
        from machine import SoftI2C
        from aht20 import AHT20
        i2c = SoftI2C(scl=Pin(config.PIN_I2C_SCL), sda=Pin(config.PIN_I2C_SDA), freq=100_000)
        aht = AHT20(i2c)
        print('[hw] AHT20 ready')
    except Exception as e:
        print('[hw] AHT20 init failed (未接/未焊?):', e)
        aht = None

btn = Pin(0, Pin.IN, Pin.PULL_UP)   # BOOT 键翻页

# ---------- 网络(帧缓冲已就位后再起 WiFi;整体 try 包住,任何错误都不许崩站) ----------
wlan = None

def ensure_wifi():
    global wlan
    if not config.WIFI_SSID:
        return False
    if wlan and wlan.isconnected():
        return True
    try:
        import network
        if wlan is None:
            wlan = network.WLAN(network.STA_IF)
            wlan.active(True)
        if not wlan.isconnected():
            wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
            for _ in range(40):
                if wlan.isconnected():
                    break
                utime.sleep_ms(250)
    except Exception as e:
        print('[wifi] error:', e)
        utime.sleep_ms(1000)
    ok = wlan is not None and wlan.isconnected()
    print('[wifi]', 'ok' if ok else 'fail')
    return ok

ensure_wifi()


t_adj = config.TIMEZONE_OFFSET   # NTP 校准前先按 UTC+8 估

def sync_ntp():
    global t_adj
    try:
        import socket, struct
        q = bytearray(48)
        q[0] = 0x1B
        addr = socket.getaddrinfo('ntp.aliyun.com', 123)[0][-1]
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(5)
        s.sendto(q, addr)
        msg = s.recv(48)
        s.close()
        t = struct.unpack('!I', msg[40:44])[0] - 2208988800
        t_adj = t + config.TIMEZONE_OFFSET - utime.time()
        print('[ntp] ok')
        return True
    except Exception as e:
        print('[ntp] fail:', e)
        return False


def local_time():
    return utime.localtime(utime.time() + t_adj)


weather = {'ok': False}

def fetch_weather():
    global weather
    try:
        import requests
        url = ('http://api.open-meteo.com/v1/forecast?latitude={}&longitude={}'  # http 省掉 TLS 的 ~50KB 内存峰值
               '&current=temperature_2m,relative_humidity_2m,weather_code'
               '&daily=temperature_2m_max,temperature_2m_min&timezone=auto'
               ).format(config.LAT, config.LON)
        r = requests.get(url)
        d = r.json()
        r.close()
        c = d['current']
        weather = {'ok': True,
                   'temp': c['temperature_2m'],
                   'humi': c['relative_humidity_2m'],
                   'code': c['weather_code'],
                   'tmax': d['daily']['temperature_2m_max'][0],
                   'tmin': d['daily']['temperature_2m_min'][0]}
        print('[weather] ok', weather['temp'], 'C')
    except Exception as e:
        print('[weather] fail:', e)


# WMO weather_code → (中文天况, 分组)。分组决定背景色带和图标,见 设计规范.md
WMO_CN = {0: ('晴', 'clear'), 1: ('晴间多云', 'clear'), 2: ('多云', 'cloud'), 3: ('阴', 'cloud'),
          45: ('雾', 'fog'), 48: ('雾凇', 'fog'),
          51: ('毛毛雨', 'rain'), 53: ('毛毛雨', 'rain'), 55: ('毛毛雨', 'rain'),
          56: ('冻毛毛雨', 'rain'), 57: ('冻毛毛雨', 'rain'),
          61: ('小雨', 'rain'), 63: ('中雨', 'rain'), 65: ('大雨', 'rain'),
          66: ('冻雨', 'rain'), 67: ('冻雨', 'rain'),
          71: ('小雪', 'snow'), 73: ('中雪', 'snow'), 75: ('大雪', 'snow'), 77: ('小雪', 'snow'),
          80: ('阵雨', 'rain'), 81: ('阵雨', 'rain'), 82: ('暴雨', 'rain'),
          85: ('阵雪', 'snow'), 86: ('阵雪', 'snow'),
          95: ('雷阵雨', 'storm'), 96: ('雷阵雨', 'storm'), 99: ('雷阵雨', 'storm')}

def wx_info(code):
    return WMO_CN.get(code, ('多云', 'cloud'))

home = {'temp': None, 'humi': None}

def read_home():
    if not aht:
        return
    try:
        home['temp'], home['humi'] = aht.read()
    except Exception as e:
        print('[aht] fail:', e)

# ---------- 页面绘制(方向二:暖色渐变卡片)----------
PAGES = 3
WEEK_CN = ('星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日')

def period(h):
    """小时 → (时段文案, 背景色带键)。只由 NTP 本地时间推导,无额外数据源。"""
    if h < 5:
        return '凌晨', 'night'
    if h < 8:
        return '清晨', 'dawn'
    if h < 12:
        return '上午', 'day'
    if h < 17:
        return '下午', 'day'
    if h < 20:
        return '傍晚', 'dusk'
    return '夜间', 'night'

def is_night(h):
    return h >= 19 or h < 6

def comfort(rh):
    """湿度评语(阈值推导):<35 干燥 / 35~65 舒适 / >65 潮湿。"""
    if rh < 35:
        return '干燥', ui.HOT
    if rh > 65:
        return '潮湿', ui.TEAL
    return '舒适', ui.OK

def deg_str(v):
    return '{}°'.format(round(v))

def draw_clock(no):
    f = tft.fb
    t = local_time()
    name, sky = period(t[3])
    ui.bands(f, sky)
    ui.aa_center(f, '{:02d}:{:02d}'.format(t[3], t[4]), 36, 64, ui.TXT_ON)
    ui.aa_center(f, WEEK_CN[t[6]] + ' · ' + name, 112, 18, ui.TXT_SUB)
    ui.rrect(f, 16, 186, 208, 98, 14, ui.CARD)
    ui.aa_text(f, '{}月{}日'.format(t[1], t[2]), 32, 200, 24, ui.INK)
    ui.aa_text(f, '{}年'.format(t[0]), 32, 232, 16, ui.SUB)
    if weather['ok']:
        txt, grp = wx_info(weather['code'])
        ui.aa_text(f, txt, 32, 258, 16, ui.SUB)
        ui.weather_icon(f, grp, is_night(t[3]), 160, 238, ui.CARD, small=True)
        ui.aa_right(f, deg_str(weather['temp']), 208, 252, 24, ui.INK)
    else:
        ui.aa_text(f, '暂无天气数据', 32, 258, 16, ui.SUB)
    ui.page_dots(f, no, PAGES, ui.SKY[sky][2])

def draw_weather(no):
    f = tft.fb
    h = local_time()[3]
    if not weather['ok']:
        ui.bands(f, 'cloud')
        ui.aa_center(f, '暂无天气数据', 140, 18, ui.TXT_ON)
        ui.page_dots(f, no, PAGES, ui.WHITE)
        return
    txt, grp = wx_info(weather['code'])
    sky = period(h)[1] if grp == 'clear' else grp
    ui.bands(f, sky)
    ui.aa_text(f, config.CITY_NAME, 20, 16, 18, ui.TXT_ON)
    ui.aa_right(f, txt, 220, 16, 18, ui.TXT_ON)
    t = str(round(weather['temp']))
    x = ui.aa_text(f, t, 18, 58, 96, ui.TXT_ON)
    ui.deg(f, x + 6, 66, 6, ui.TXT_ON, f.pixel(x + 6, 66))
    ui.weather_icon(f, grp, is_night(h), 146, 150, f.pixel(190, 120))
    for i, (k, v, c) in enumerate((('最高', deg_str(weather['tmax']), ui.HOT),
                                   ('最低', deg_str(weather['tmin']), ui.TEAL),
                                   ('湿度', '{}%'.format(round(weather['humi'])), ui.INK))):
        x0 = 16 + i * 72
        ui.rrect(f, x0, 196, 64, 92, 12, ui.CARD)
        ui.aa_center(f, k, 210, 16, ui.SUB, cx=x0 + 32)
        ui.aa_center(f, v, 244, 24, c, cx=x0 + 32)
    ui.page_dots(f, no, PAGES, ui.WHITE)

def draw_home(no):
    f = tft.fb
    ui.bands(f, 'home')
    ui.aa_text(f, '室内', 20, 16, 18, ui.INK)
    if home['temp'] is None:
        ui.rrect(f, 16, 120, 208, 80, 16, ui.CARD)
        ui.aa_center(f, '未接传感器', 150, 18, ui.SUB)
        ui.page_dots(f, no, PAGES, ui.SKY['home'][2])
        return
    rh = round(home['humi'])                      # 室内湿度取整显示(AHT20 给的是 1 位小数)
    word, wc = comfort(rh)
    ui.aa_right(f, word, 220, 16, 18, wc)
    ui.rrect(f, 16, 48, 208, 116, 16, ui.CARD)
    ui.aa_text(f, '温度', 32, 62, 16, ui.SUB)
    x = ui.aa_text(f, '{:.1f}'.format(home['temp']), 30, 92, 56, ui.INK)
    ui.aa_text(f, '°C', x + 4, 98, 18, ui.SUB)
    ui.rrect(f, 16, 176, 208, 116, 16, ui.CARD)
    ui.aa_text(f, '湿度', 32, 190, 16, ui.SUB)
    x = ui.aa_text(f, str(rh), 30, 214, 56, ui.INK)
    ui.aa_text(f, '%', x + 4, 220, 18, ui.SUB)
    ui.rrect(f, 32, 270, 176, 10, 5, ui.TRACK)
    w = 176 * min(100, max(0, rh)) // 100
    if w >= 10:
        ui.rrect(f, 32, 270, w, 10, 5, ui.TEAL)
    ui.page_dots(f, no, PAGES, ui.SKY['home'][2])

def render(page):
    if not tft:
        return
    (draw_clock, draw_weather, draw_home)[page](page)
    tft.show()

# ---------- 主循环 ----------
page = 0
last = {'flip': 0, 'home': 0, 'ntp': -3600, 'weather': -10**6, 'tick': -1, 'sig': None}
last_btn = 1
print('[main] station start, hardware={}'.format(config.HARDWARE_PRESENT))

while True:
    now = utime.time()

    if last_btn == 1 and btn.value() == 0:          # BOOT 按下 → 翻页
        page = (page + 1) % PAGES
        last['flip'] = now
        render(page)
    last_btn = btn.value()

    if now - last['flip'] >= config.PAGE_ROTATE:    # 自动轮换
        page = (page + 1) % PAGES
        last['flip'] = now
        render(page)

    if aht and now - last['home'] >= 10:
        last['home'] = now
        read_home()

    if now - last['ntp'] >= config.NTP_EVERY:
        last['ntp'] = now
        if ensure_wifi():
            sync_ntp()

    if now - last['weather'] >= config.WEATHER_EVERY:
        last['weather'] = now
        if ensure_wifi():
            fetch_weather()

    if now != last['tick']:                          # 内容变化才刷屏(SoftSPI 整屏 ~1s,禁逐秒刷)
        last['tick'] = now
        if tft:
            t = local_time()
            if page == 0:
                sig = ('clk', t[1], t[2], t[3], t[4], t[6])
            elif page == 1:
                sig = ('wx', str(weather))
            else:
                sig = ('home', home['temp'], home['humi'])
            if sig != last['sig']:
                last['sig'] = sig
                render(page)
        elif now % 10 == 0:
            print('[idle] waiting: wifi_set={} hardware={}'.format(
                bool(config.WIFI_SSID), config.HARDWARE_PRESENT))

    utime.sleep_ms(100)

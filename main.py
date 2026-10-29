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


WMO = {0: 'Clear', 1: 'Mainly Clear', 2: 'Partly Cloudy', 3: 'Overcast',
       45: 'Fog', 48: 'Rime Fog', 51: 'Drizzle', 53: 'Drizzle', 55: 'Drizzle',
       61: 'Light Rain', 63: 'Rain', 65: 'Heavy Rain', 66: 'Freezing Rain',
       71: 'Light Snow', 73: 'Snow', 75: 'Heavy Snow',
       80: 'Showers', 81: 'Showers', 82: 'Heavy Showers',
       95: 'Thunderstorm', 96: 'Thunderstorm', 99: 'Thunderstorm'}

home = {'temp': None, 'humi': None}

def read_home():
    if not aht:
        return
    try:
        home['temp'], home['humi'] = aht.read()
    except Exception as e:
        print('[aht] fail:', e)

# ---------- 页面绘制 ----------
PAGES = 3

def header(title, no):
    f = tft.fb
    f.fill(0)
    f.fill_rect(0, 0, 240, 34, ui.BLUE)
    ui.aa_text(f, title, 10, 3, 24, ui.WHITE)
    s = '{}/{}'.format(no + 1, PAGES)
    ui.aa_text(f, s, 230 - ui.aa_width(s, 24), 3, 24, ui.WHITE)

def draw_clock(no):
    header('Clock', no)
    t = local_time()
    f = tft.fb
    ui.aa_center(f, '{:02d}:{:02d}'.format(t[3], t[4]), 72, 64, ui.WHITE)
    ui.aa_center(f, '{}-{:02d}-{:02d}'.format(t[0], t[1], t[2]), 180, 24, ui.CYAN)
    ui.aa_center(f, ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')[t[6]], 222, 24, ui.GREY)

def draw_weather(no):
    header('Weather', no)
    f = tft.fb
    if not weather['ok']:
        ui.aa_center(f, 'no data', 110, 24, ui.GREY)
        return
    ui.aa_center(f, '{}°'.format(round(weather['temp'])), 42, 64, ui.YELLOW)
    ui.aa_center(f, WMO.get(weather['code'], 'Code ' + str(weather['code'])), 145, 24, ui.CYAN)
    ui.aa_center(f, 'H {}°  L {}°'.format(round(weather['tmax']), round(weather['tmin'])), 190, 24, ui.WHITE)
    ui.aa_center(f, 'RH {}%'.format(round(weather['humi'])), 232, 24, ui.GREY)

def draw_home(no):
    header('Home', no)
    f = tft.fb
    if home['temp'] is None:
        ui.aa_center(f, 'no sensor', 110, 24, ui.GREY)
        return
    ui.aa_center(f, '{}°'.format(home['temp']), 45, 64, ui.GREEN)
    ui.aa_center(f, '{}%'.format(home['humi']), 158, 64, ui.CYAN)
    f.rect(20, 265, 200, 14, ui.GREY)                       # 湿度条
    f.fill_rect(20, 265, min(200, int(2 * home['humi'])), 14, ui.CYAN)

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

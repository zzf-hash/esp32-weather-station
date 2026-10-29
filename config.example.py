# ===== 桌面气象站配置模板:复制为 config.py 并填入真实值 =====

WIFI_SSID = 'YOUR_WIFI_NAME'
WIFI_PASSWORD = 'YOUR_WIFI_PASSWORD'

# 天气地点(城市名 + 经纬度)
CITY_NAME = 'Beijing'
LAT = 39.9042
LON = 116.4074

TIMEZONE_OFFSET = 8 * 3600   # UTC+8

# 接线完成后保持 True(屏初始化失败会自动降级为串口打印模式)
HARDWARE_PRESENT = True

# --- 引脚分配(ESP32-S3 N16R8) ---
PIN_TFT_SCK  = 12   # 屏 SCK
PIN_TFT_MOSI = 11   # 屏 SDI/MOSI
PIN_TFT_CS   = 10   # 屏 CS
PIN_TFT_DC   = 14   # 屏 DC/RS
PIN_TFT_RST  = 13   # 屏 RESET
PIN_TFT_BL   = 18   # 屏 LED(背光;该屏丝印为 LED 不是 BL)
PIN_I2C_SCL  = 4    # AHT20 SCL
PIN_I2C_SDA  = 5    # AHT20 SDA

# --- 刷新节奏(秒) ---
PAGE_ROTATE  = 10   # 自动翻页间隔
WEATHER_EVERY = 900 # 天气拉取间隔
NTP_EVERY    = 3600 # 对时间隔

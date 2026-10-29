"""AHT20 温湿度传感器(I2C 0x38,DHT20 协议兼容)。"""
import utime


class AHT20:
    def __init__(self, i2c, addr=0x38):
        self.i2c = i2c
        self.addr = addr
        utime.sleep_ms(40)   # 上电稳定
        status = self.i2c.readfrom(addr, 1)[0]
        if not status & 0x08:                     # 校准位丢失 → 重新初始化
            self.i2c.writeto(addr, b'\xBE\x08\x00')
            utime.sleep_ms(10)

    def read(self):
        """返回 (温度C, 湿度%RH)"""
        self.i2c.writeto(self.addr, b'\xAC\x33\x00')   # 触发测量
        utime.sleep_ms(80)
        b = self.i2c.readfrom(self.addr, 7)
        if b[0] & 0x80:
            raise OSError('AHT20 busy')
        humi = ((b[1] << 12) | (b[2] << 4) | (b[3] >> 4)) * 100 / 1048576
        temp = (((b[3] & 0x0F) << 16) | (b[4] << 8) | b[5]) * 200 / 1048576 - 50
        return round(temp, 1), round(humi, 1)

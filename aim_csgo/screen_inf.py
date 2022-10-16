import cv2
import numpy as np
from ctypes import *

u32 = windll.user32
g32 = windll.gdi32


class Screen(object):
    def __init__(self, args):
        self.region = args.region
        self.top_x, self.top_y = 0, 0
        self.len_x, self.len_y = 0, 0
        self.bmp = None
        self.srcdc, self.memdc = self.__get_screenhandle_etc()
        self.update_parameters()

    def update_parameters(self):  # 更新参数
        x, y = self.get_real_resolution().values()
        self.len_x, self.len_y = int(x * self.region[0]), int(y * self.region[1])
        self.top_x, self.top_y = int(x // 2 * (1. - self.region[0])), int(y // 2 * (1. - self.region[1]))
        self.bmp = g32.CreateCompatibleBitmap(self.srcdc, self.len_x, self.len_y)

    def get_real_resolution(self):
        wide = g32.GetDeviceCaps(self.srcdc, 118)
        high = g32.GetDeviceCaps(self.srcdc, 117)
        return {"wide": wide, "high": high}

    def grab_screen_win32(self):  # 抓屏
        g32.SelectObject(self.memdc, self.bmp)
        g32.BitBlt(self.memdc, 0, 0, self.len_x, self.len_y, self.srcdc, self.top_x, self.top_y, 13369376)

        total_bytes = self.len_x * self.len_y * 4
        buffer = bytearray(total_bytes)
        byte_array = c_ubyte * total_bytes
        g32.GetBitmapBits(self.bmp, total_bytes, byte_array.from_buffer(buffer))

        img = np.frombuffer(buffer, dtype=np.uint8).reshape(self.len_y, self.len_x, 4)

        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def __get_screenhandle_etc(self):
        srcdc = u32.GetDC(0)
        memdc = g32.CreateCompatibleDC(srcdc)

        return srcdc, memdc

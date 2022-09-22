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
        self.update_parameters()

        self.hwnd, self.srcdc, self.memdc, self.bmp = self.__get_screenhandle_etc()

    def update_parameters(self):
        x, y = self.get_real_resolution().values()
        self.hwnd, self.srcdc, self.memdc, self.bmp = self.__get_screenhandle_etc()
        self.len_x, self.len_y = int(x * self.region[0]), int(y * self.region[1])
        self.top_x, self.top_y = int(x // 2 * (1. - self.region[0])), int(y // 2 * (1. - self.region[1]))

    @staticmethod
    def get_scaling():  # 随便写的，获取缩放大小的，没用到
        real_resolution = Screen.get_real_resolution()
        screen_size = Screen.get_screen_size()
        proportion = round(real_resolution['wide'] / screen_size['wide'], 2)
        return proportion

    @staticmethod
    def get_parameters():
        x, y = Screen.get_screen_size().values()
        return 0, 0, x, y

    @staticmethod
    def get_screen_size():
        wide = u32.GetSystemMetrics(0)
        high = u32.GetSystemMetrics(1)
        return {"wide": wide, "high": high}

    @staticmethod
    def get_real_resolution():
        hDC = u32.GetDC(0)
        wide = g32.GetDeviceCaps(hDC, 118)
        high = g32.GetDeviceCaps(hDC, 117)
        return {"wide": wide, "high": high}

    def grab_screen_win32(self):
        g32.SelectObject(self.memdc, self.bmp)
        g32.BitBlt(self.memdc, 0, 0, self.len_x, self.len_y, self.srcdc, self.top_x, self.top_y, 13369376)

        total_bytes = self.len_x * self.len_y * 4
        buffer = bytearray(total_bytes)
        byte_array = c_ubyte * total_bytes

        g32.GetBitmapBits(self.bmp, total_bytes, byte_array.from_buffer(buffer))

        img = np.frombuffer(buffer, dtype=np.uint8).reshape(self.len_y, self.len_x, 4)

        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def __get_screenhandle_etc(self):
        hwnd = u32.GetDesktopWindow()
        srcdc = u32.GetWindowDC(hwnd)
        memdc = g32.CreateCompatibleDC(srcdc)
        bmp = g32.CreateCompatibleBitmap(srcdc, self.len_x, self.len_y)

        return hwnd, srcdc, memdc, bmp

    def release_handle(self):
        g32.DeleteDC(self.bmp)
        g32.DeleteDC(self.memdc)
        u32.ReleaseDC(self.hwnd, self.srcdc)
        # u32.DeleteObject(self.bmp.GetHandle())


import ctypes
import cv2
import numpy as np
from ctypes.wintypes import DWORD, LONG, WORD


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", DWORD),
        ("biWidth", LONG),
        ("biHeight", LONG),
        ("biPlanes", WORD),
        ("biBitCount", WORD),
        ("biCompression", DWORD),
        ("biSizeImage", DWORD),
        ("biXPelsPerMeter", LONG),
        ("biYPelsPerMeter", LONG),
        ("biClrUsed", DWORD),
        ("biClrImportant", DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", DWORD * 3)]


Gdi32 = ctypes.windll.gdi32
User32 = ctypes.windll.user32


class capture:

    def __init__(self, x, y, width, height, j):
        self.x = int(x / 2 - width / 2)
        self.y = int(y / 2 - height / 2)
        self.width = width
        self.height = height
        self.hwin = User32.FindWindowW(j, None)
        self.srcdc = User32.GetDC(self.hwin)
        self.memdc = Gdi32.CreateCompatibleDC(self.srcdc)
        self.bmi = BITMAPINFO()
        self.bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        self.bmi.bmiHeader.biPlanes = 1
        self.bmi.bmiHeader.biBitCount = 32
        self.bmi.bmiHeader.biWidth = width
        self.bmi.bmiHeader.biHeight = -height
        self._data = ctypes.create_string_buffer(width * height * 4)
        self.bmp = Gdi32.CreateCompatibleBitmap(self.srcdc, width, height)
        Gdi32.SelectObject(self.memdc, self.bmp)

    def cap(self):
        Gdi32.BitBlt(self.memdc, 0, 0, self.width, self.height, self.srcdc, self.x, self.y, 0x00CC0020)
        Gdi32.GetDIBits(self.memdc, self.bmp, 0, self.height, self._data, self.bmi, 0)
        self.p = np.frombuffer(self._data, dtype='uint8').reshape(self.height, self.width, 4)

        Gdi32.DeleteObject(self.bmp)
        return cv2.cvtColor(self.p, cv2.COLOR_BGRA2BGR)

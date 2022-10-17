import cv2
import numpy as np
from ctypes import *
import win32print
import win32api
import win32con
import win32gui
import time
from math import *

u32 = windll.user32
g32 = windll.gdi32

count = 0


def show_top_most():
    hwnd = win32gui.FindWindow(None, 'detect')
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)


def show_fps(cv2, lock_mode, img0, t0):
    global count
    count = count + 1

    cv2.putText(img0, "FPS:{:.1f}".format(1. / (time.time() - t0)), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1,
                (27, 0, 221), 2)
    cv2.putText(img0, "lock:{:.1f}".format(lock_mode), (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (27, 0, 221),
                2)
    # 打印fps 控制频率
    if int(count) % 100 == 0:
        print(1. / (time.time() - t0))
        count = 0

    cv2.imshow('detect', img0)


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

    def __get_screenhandle_etc(self):
        srcdc = u32.GetDC(0)
        memdc = g32.CreateCompatibleDC(srcdc)

        return srcdc, memdc

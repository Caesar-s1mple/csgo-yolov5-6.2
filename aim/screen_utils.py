import cv2
import numpy as np
import win32gui
import win32ui
import win32con
import mss
import win32print
import win32api


def grab_screen_win32(region):
    h_win = win32gui.GetDesktopWindow()
    left, top, x2, y2 = region
    width = x2 - left + 1  # 少取一像素，无所谓
    height = y2 - top + 1

    h_win_dc = win32gui.GetWindowDC(h_win)
    sr_cdc = win32ui.CreateDCFromHandle(h_win_dc)
    me_mdc = sr_cdc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(sr_cdc, width, height)
    me_mdc.SelectObject(bmp)
    me_mdc.BitBlt((0, 0), (width, height), sr_cdc, (left, top), win32con.SRCCOPY)

    signedIntsArray = bmp.GetBitmapBits(True)
    img = np.fromstring(signedIntsArray, dtype='uint8')
    img.shape = (height, width, 4)

    sr_cdc.DeleteDC()
    me_mdc.DeleteDC()
    win32gui.ReleaseDC(h_win, h_win_dc)
    win32gui.DeleteObject(bmp.GetHandle())

    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


cap = mss.mss()


def grab_screen_mss(monitor):
    return cv2.cvtColor(np.array(cap.grab(monitor)), cv2.COLOR_BGRA2BGR)


def get_real_resolution():
    hDC = win32gui.GetDC(0)
    return {"wide": win32print.GetDeviceCaps(hDC, win32con.DESKTOPHORZRES),
            "high": win32print.GetDeviceCaps(hDC, win32con.DESKTOPVERTRES)}


def get_screen_size():
    return {"wide": win32api.GetSystemMetrics(0), "high": win32api.GetSystemMetrics(1)}


def get_scaling():
    return round(get_real_resolution()['wide'] / get_screen_size()['wide'], 2)


def get_parameters():
    x, y = get_screen_size().values()
    return 0, 0, x, y

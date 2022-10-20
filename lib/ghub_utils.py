from ctypes import windll, c_long, c_ulong, Structure, Union, c_int, POINTER, sizeof, CDLL
from os import path

try:
    basedir = path.dirname(path.abspath(__file__))
    dlldir = path.join(basedir, 'ghub_device.dll')
    LONG = c_long
    DWORD = c_ulong
    ULONG_PTR = POINTER(DWORD)
    gm = CDLL(dlldir)
    gm_ok = gm.device_open()
    if not gm_ok:
        print('未安装ghub或者lgs驱动!!!')
    else:
        print('初始化成功!')
except FileNotFoundError:
    print('重要键鼠文件缺失')
    gm_ok = 0


# ↓↓↓↓↓↓↓↓↓ 简易鼠标行为模拟,使用SendInput函数或者调用ghub驱动 ↓↓↓↓↓↓↓↓↓

class MOUSEINPUT(Structure):
    _fields_ = (('dx', LONG),
                ('dy', LONG),
                ('mouseData', DWORD),
                ('dwFlags', DWORD),
                ('time', DWORD),
                ('dwExtraInfo', ULONG_PTR))


class _INPUTunion(Union):
    _fields_ = (('mi', MOUSEINPUT), ('mi', MOUSEINPUT))


class INPUT(Structure):
    _fields_ = (('type', DWORD),
                ('union', _INPUTunion))


def SendInput(*inputs):
    nInputs = len(inputs)
    LPINPUT = INPUT * nInputs
    pInputs = LPINPUT(*inputs)
    cbSize = c_int(sizeof(INPUT))
    return windll.user32.SendInput(nInputs, pInputs, cbSize)


def Input(structure):
    return INPUT(0, _INPUTunion(mi=structure))


def MouseInput(flags, x, y, data):
    return MOUSEINPUT(x, y, data, flags, 0, None)


def Mouse(flags, x=0, y=0, data=0):
    return Input(MouseInput(flags, x, y, data))


def mouse_xy(x, y):  # for import
    if gm_ok:
        return gm.moveR(x, y)
    return SendInput(Mouse(0x0001, x, y))


def mouse_down(key=1):  # for import
    if gm_ok:
        return gm.press(key)
    if key == 1:
        return SendInput(Mouse(0x0002))
    elif key == 2:
        return SendInput(Mouse(0x0008))


def mouse_up(key=1):  # for import
    if gm_ok:
        return gm.release()
    if key == 1:
        return SendInput(Mouse(0x0004))
    elif key == 2:
        return SendInput(Mouse(0x0010))


def mouse_close():  # for import
    if gm_ok:
        return gm.mouse_close()
# ↑↑↑↑↑↑↑↑↑ 简易鼠标行为模拟,使用SendInput函数或者调用ghub驱动 ↑↑↑↑↑↑↑↑↑

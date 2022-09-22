import pynput
import csv
import time
from math import *
from ctypes import *

u32 = windll.user32


# class PointAPI(Structure):
#     _fields_ = [("x", c_ulong), ("y", c_ulong)]
#
#
# po = PointAPI()
flag = 0


class KalmanFilter(object):
    def __init__(self):
        pass

    def kf_predict(self):
        pass


class Locker(object):
    def __init__(self, args):
        self.Kp, self.Ki, self.Kd = args.p_i_d
        self.error_sum_x = 0
        self.error_sum_y = 0
        self.pre_error_x = 0
        self.pre_error_y = 0
        self.pre_time = time.time()

    def __pid(self, error_x, error_y):
        # 离散形式PID
        Pout_x = self.Kp * error_x
        self.error_sum_x += error_x
        Iout_x = self.Ki * self.error_sum_x
        Dout_x = self.Kd * (error_x - self.pre_error_x)
        self.pre_error_x = error_x

        Pout_y = self.Kp * error_y
        self.error_sum_y += error_y
        Iout_y = self.Ki * self.error_sum_y
        Dout_y = self.Kd * (error_y - self.pre_error_y)
        self.pre_error_y = error_y

        print(Pout_x, Iout_x, Dout_x)
        return int(Pout_x + Iout_x + Dout_x), int(Pout_y + Iout_y + Dout_y)

    def reset_params(self):
        global flag
        flag = 0
        self.error_sum_x = 0
        self.error_sum_y = 0
        self.pre_error_x = 0
        self.pre_error_y = 0

    def lock(self, aims, top_x, top_y, len_x, len_y, args):
        # u32.GetCursorPos(byref(po))
        mouse_pos_x, mouse_pos_y = top_x + len_x // 2, top_y + len_y // 2
        aims_copy = aims.copy()
        aims_copy = [x for x in aims_copy if x[0] in args.lock_choice]
        k = 4.07
        if len(aims_copy):
            dist_list = []
            tag_list = [x[0] for x in aims_copy]
            if args.head_first:
                if args.lock_tag[0] in tag_list or args.lock_tag[2] in tag_list:  # 有头
                    aims_copy = [x for x in aims_copy if x[0] in [args.lock_tag[0], args.lock_tag[2]]]
            for det in aims_copy:
                _, x_c, y_c, _, _ = det
                dist = (len_x * float(x_c) + top_x - mouse_pos_x) ** 2 + (len_y * float(y_c) + top_y - mouse_pos_y) ** 2
                dist_list.append(dist)

            det = aims_copy[dist_list.index(min(dist_list))]
            tag, x_center, y_center, width, height = det
            x_center, width = len_x * float(x_center) + top_x, len_x * float(width)
            y_center, height = len_y * float(y_center) + top_y, len_y * float(height)
            rel_x = int(k / args.lock_sen * atan((mouse_pos_x - x_center) / 640) * 640)
            if tag in [args.lock_tag[0], args.lock_tag[2]]:
                rel_y = int(k / args.lock_sen * atan((mouse_pos_y - y_center) / 640) * 640)
                if flag:
                    return
                if args.lock_strategy == 'pid':
                    rel_x, rel_y = self.__pid(rel_x, rel_y)
                u32.mouse_event(0x0001, int(-rel_x / args.lock_smooth), int(-rel_y / args.lock_smooth), 0, 0)
            elif tag in [args.lock_tag[1], args.lock_tag[3]]:
                rel_y = int(k / args.lock_sen * atan((mouse_pos_y - y_center + 1 / 6 * height) / 640) * 640)
                if flag:
                    return
                if args.lock_strategy == 'pid':
                    rel_x, rel_y = self.__pid(rel_x, rel_y)
                rel_x, rel_y = self.__pid(rel_x, rel_y)
                u32.mouse_event(0x0001, int(-rel_x / args.lock_smooth), int(-rel_y / args.lock_smooth), 0, 0)

    def lock2(self, aims, top_x, top_y, len_x, len_y, args):
        # global flag
        # u32.GetCursorPos(byref(po))
        mouse_pos_x, mouse_pos_y = top_x + len_x // 2, top_y + len_y // 2
        aims_copy = aims.copy()
        aims_copy = [x for x in aims_copy if x[0] in args.lock_choice]
        # k = 4.07
        if len(aims_copy):
            dist_list = []
            tag_list = [x[0] for x in aims_copy]
            if args.head_first:
                if args.lock_tag[0] in tag_list or args.lock_tag[2] in tag_list:  # 有头
                    aims_copy = [x for x in aims_copy if x[0] in [args.lock_tag[0], args.lock_tag[2]]]
            for det in aims_copy:
                _, x_c, y_c, _, _ = det
                dist = (len_x * float(x_c) + top_x - mouse_pos_x) ** 2 + (len_y * float(y_c) + top_y - mouse_pos_y) ** 2
                dist_list.append(dist)

            det = aims_copy[dist_list.index(min(dist_list))]
            tag, x_center, y_center, width, height = det
            x_center, width = len_x * float(x_center) + top_x, len_x * float(width)
            y_center, height = len_y * float(y_center) + top_y, len_y * float(height)

            theta_x = atan((mouse_pos_x - x_center) / 640) * 180 / pi
            theta_y = atan((mouse_pos_y - y_center) / 640) * 180 / pi

            x = (theta_x / args.lock_sen) / 0.022
            y = (theta_y / args.lock_sen) / 0.03

            if args.lock_smooth > 1.00:
                rel_x = 0.
                rel_y = 0.
                if rel_x > x:
                    rel_x += 1. + (x / args.lock_smooth)
                elif rel_y < x:
                    rel_x -= 1. - (x / args.lock_smooth)
                if rel_y > y:
                    rel_y += 1. + (y / args.lock_smooth)
                elif rel_y < y:
                    rel_y -= 1. - (y / args.lock_smooth)
            else:
                rel_x = x
                rel_y = y

            if tag in [args.lock_tag[0], args.lock_tag[2]]:
                if flag:
                    return
                if args.lock_strategy == 'pid':
                    rel_x, rel_y = self.__pid(rel_x, rel_y)
                u32.mouse_event(0x0001, int(-rel_x), int(-rel_y), 0, 0)
                # flag = 1
            elif tag in [args.lock_tag[1], args.lock_tag[3]]:
                if flag:
                    return
                if args.lock_strategy == 'pid':
                    rel_x, rel_y = self.__pid(rel_x, rel_y)
                rel_x, rel_y = self.__pid(rel_x, rel_y)
                u32.mouse_event(0x0001, int(-rel_x / args.lock_smooth), int(-rel_y / args.lock_smooth), 0, 0)
                # flag = 1


def recoil_control(args):
    global flag
    ak47_recoil = []
    m4a1_recoil = []
    m4a4_recoil = []
    galil_recoil = []
    famas_recoil = []
    aug_recoil = []
    bizon_recoil = []
    cz75_recoil = []
    m249_recoil = []
    mac10_recoil = []
    mp5sd_recoil = []
    mp7_recoil = []
    mp9_recoil = []
    p90_recoil = []
    sg553_recoil = []
    ump45_recoil = []

    for i in csv.reader(open('./aim_csgo/ammo_path/ak47.csv', encoding='utf-8-sig')):
        ak47_recoil.append([float(x) for x in i])
    for i in csv.reader(open('./aim_csgo/ammo_path/m4a1.csv', encoding='utf-8-sig')):
        m4a1_recoil.append([float(x) for x in i])
    for i in csv.reader(open('./aim_csgo/ammo_path/m4a4.csv', encoding='utf-8-sig')):
        m4a4_recoil.append([float(x) for x in i])
    for i in csv.reader(open('./aim_csgo/ammo_path/galil.csv', encoding='utf-8-sig')):
        galil_recoil.append([float(x) for x in i])
    for i in csv.reader(open('./aim_csgo/ammo_path/famas.csv', encoding='utf-8-sig')):
        famas_recoil.append([float(x) for x in i])
    for i in csv.reader(open('./aim_csgo/ammo_path/aug.csv', encoding='utf-8-sig')):
        aug_recoil.append([float(x) for x in i])
    for i in csv.reader(open('./aim_csgo/ammo_path/bizon.csv', encoding='utf-8-sig')):
        bizon_recoil.append([float(x) for x in i])
    for i in csv.reader(open('./aim_csgo/ammo_path/cz75.csv', encoding='utf-8-sig')):
        cz75_recoil.append([float(x) for x in i])
    for i in csv.reader(open('./aim_csgo/ammo_path/m249.csv', encoding='utf-8-sig')):
        m249_recoil.append([float(x) for x in i])
    for i in csv.reader(open('./aim_csgo/ammo_path/mac10.csv', encoding='utf-8-sig')):
        mac10_recoil.append([float(x) for x in i])
    for i in csv.reader(open('./aim_csgo/ammo_path/mp5sd.csv', encoding='utf-8-sig')):
        mp5sd_recoil.append([float(x) for x in i])
    for i in csv.reader(open('./aim_csgo/ammo_path/mp7.csv', encoding='utf-8-sig')):
        mp7_recoil.append([float(x) for x in i])
    for i in csv.reader(open('./aim_csgo/ammo_path/mp9.csv', encoding='utf-8-sig')):
        mp9_recoil.append([float(x) for x in i])
    for i in csv.reader(open('./aim_csgo/ammo_path/p90.csv', encoding='utf-8-sig')):
        p90_recoil.append([float(x) for x in i])
    for i in csv.reader(open('./aim_csgo/ammo_path/sg553.csv', encoding='utf-8-sig')):
        sg553_recoil.append([float(x) for x in i])
    for i in csv.reader(open('./aim_csgo/ammo_path/ump45.csv', encoding='utf-8-sig')):
        ump45_recoil.append([float(x) for x in i])

    k = -args.recoil_sen
    recoil_mode = False
    with pynput.mouse.Events() as events:
        for event in events:
            if isinstance(event, pynput.mouse.Events.Click):
                if event.button == event.button.left:
                    if event.pressed:
                        flag = 1
                    else:
                        flag = 0
                if event.button == eval('event.button.' + args.recoil_button_ak47) and event.pressed:
                    recoil_mode = not recoil_mode
                    print('recoil mode', 'on' if recoil_mode else 'off')

            if flag and recoil_mode:
                i = 0
                a = next(events)
                while True:
                    u32.mouse_event(0x0001, int(-ak47_recoil[i][0] * k), int(ak47_recoil[i][1] * k), 0, 0)
                    # ghub.mouse_xy(int(-ak47_recoil[i][0] * k), int(ak47_recoil[i][1] * k))
                    time.sleep(ak47_recoil[i][2] / 1000 - 0.01)
                    i += 1
                    if i == 30:
                        break
                    if a is not None and isinstance(a,
                                                    pynput.mouse.Events.Click) and a.button == a.button.left and not a.pressed:
                        break
                    a = next(events)
                    while a is not None and not isinstance(a, pynput.mouse.Events.Click):
                        a = next(events)
                flag = 0

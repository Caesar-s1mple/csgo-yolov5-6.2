import csv
import time
from math import *
from ctypes import *

u32 = windll.user32


class Locker(object):
    def __init__(self, args):
        self.top_x = 0
        self.top_y = 0
        self.len_x = 0
        self.len_y = 0

        self.locked = False

        self.lock_sen = args.lock_sen
        self.head_first = args.head_first
        self.lock_tag = args.lock_tag
        self.lock_choice = args.lock_choice
        self.lock_smooth = args.lock_smooth
        self.lock_strategy = args.lock_strategy

        self.lock_mode = False
        self.Kp, self.Ki, self.Kd = args.p_i_d
        self.error_sum_x = 0
        self.error_sum_y = 0
        self.pre_error_x = 0
        self.pre_error_y = 0
        self.pre_time = time.time()

        self.recoil_mode = False
        self.left_pressed = False
        self.shot_time = 0
        self.recoil_k = args.recoil_sen

        self.ak47_recoil = []
        self.__get_recoil_path()

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

        return int(Pout_x + Iout_x + Dout_x), int(Pout_y + Iout_y + Dout_y)

    def reset_params(self):
        self.error_sum_x = 0
        self.error_sum_y = 0
        self.pre_error_x = 0
        self.pre_error_y = 0
        self.locked = False

    def lock(self, aims):
        mouse_pos_x, mouse_pos_y = self.top_x + self.len_x // 2, self.top_y + self.len_y // 2
        aims_copy = aims.copy()
        aims_copy = [x for x in aims_copy if x[0] in self.lock_choice]
        if len(aims_copy):
            dist_list = []
            tag_list = [x[0] for x in aims_copy]
            if self.head_first:
                if self.lock_tag[0] in tag_list or self.lock_tag[2] in tag_list:  # 有头
                    aims_copy = [x for x in aims_copy if x[0] in [self.lock_tag[0], self.lock_tag[2]]]
            for det in aims_copy:
                _, x_c, y_c, _, _ = det
                dist = (self.len_x * float(x_c) + self.top_x - mouse_pos_x) ** 2 + (self.len_y * float(y_c) + self.top_y - mouse_pos_y) ** 2
                dist_list.append(dist)

            det = aims_copy[dist_list.index(min(dist_list))]
            tag, x_center, y_center, width, height = det
            x_center, width = self.len_x * float(x_center) + self.top_x, self.len_x * float(width)
            y_center, height = self.len_y * float(y_center) + self.top_y, self.len_y * float(height)

            theta_x = atan((mouse_pos_x - x_center) / 640) * 180 / pi
            theta_y = atan((mouse_pos_y - y_center) / 640) * 180 / pi

            x = (theta_x / self.lock_sen) / 0.022
            y = (theta_y / self.lock_sen) / 0.03

            if self.lock_smooth > 1.00:
                rel_x = 0.
                rel_y = 0.
                if rel_x > x:
                    rel_x += 1. + (x / self.lock_smooth)
                elif rel_y < x:
                    rel_x -= 1. - (x / self.lock_smooth)
                if rel_y > y:
                    rel_y += 1. + (y / self.lock_smooth)
                elif rel_y < y:
                    rel_y -= 1. - (y / self.lock_smooth)
            else:
                rel_x = x
                rel_y = y

            if self.lock_strategy == 'pid':
                rel_x, rel_y = self.__pid(rel_x, rel_y)
            # u32.mouse_event(0x0001, int(-rel_x / self.lock_smooth), int(-rel_y / self.lock_smooth), 0, 0)

            recoil_x, recoil_y = 0., 0.
            if self.recoil_mode and self.left_pressed:
                t = time.time()
                sum_t = 0
                for i in self.ak47_recoil:
                    if t - self.shot_time > sum_t / 1000:
                        sum_t += i[2]
                        recoil_x += i[0]
                        recoil_y += i[1]
                    else:
                        break
            u32.mouse_event(0x0001,
                            int(-rel_x / self.lock_smooth + recoil_x * self.recoil_k),
                            int(-rel_y / self.lock_smooth - recoil_y * self.recoil_k), 0, 0)
            self.locked = True
        else:
            self.locked = False

    def recoil_only(self):
        if self.recoil_mode and self.left_pressed:
            recoil_x, recoil_y = 0., 0.
            t = time.time()
            sum_t = 0
            for i in self.ak47_recoil:
                if t - self.shot_time > sum_t / 1000:
                    sum_t += i[2]
                    recoil_x = i[0]
                    recoil_y = i[1]
                else:
                    u32.mouse_event(0x0001,
                                    int(recoil_x * self.recoil_k),
                                    int(-recoil_y * self.recoil_k), 0, 0)
                    break

    def __get_recoil_path(self):
        # m4a1_recoil = []
        # m4a4_recoil = []
        # galil_recoil = []
        # famas_recoil = []
        # aug_recoil = []
        # bizon_recoil = []
        # cz75_recoil = []
        # m249_recoil = []
        # mac10_recoil = []
        # mp5sd_recoil = []
        # mp7_recoil = []
        # mp9_recoil = []
        # p90_recoil = []
        # sg553_recoil = []
        # ump45_recoil = []

        for i in csv.reader(open('./aim_csgo/ammo_path/ak47.csv', encoding='utf-8-sig')):
            self.ak47_recoil.append([float(x) for x in i])
        # for i in csv.reader(open('./aim_csgo/ammo_path/m4a1.csv', encoding='utf-8-sig')):
        #     m4a1_recoil.append([float(x) for x in i])
        # for i in csv.reader(open('./aim_csgo/ammo_path/m4a4.csv', encoding='utf-8-sig')):
        #     m4a4_recoil.append([float(x) for x in i])
        # for i in csv.reader(open('./aim_csgo/ammo_path/galil.csv', encoding='utf-8-sig')):
        #     galil_recoil.append([float(x) for x in i])
        # for i in csv.reader(open('./aim_csgo/ammo_path/famas.csv', encoding='utf-8-sig')):
        #     famas_recoil.append([float(x) for x in i])
        # for i in csv.reader(open('./aim_csgo/ammo_path/aug.csv', encoding='utf-8-sig')):
        #     aug_recoil.append([float(x) for x in i])
        # for i in csv.reader(open('./aim_csgo/ammo_path/bizon.csv', encoding='utf-8-sig')):
        #     bizon_recoil.append([float(x) for x in i])
        # for i in csv.reader(open('./aim_csgo/ammo_path/cz75.csv', encoding='utf-8-sig')):
        #     cz75_recoil.append([float(x) for x in i])
        # for i in csv.reader(open('./aim_csgo/ammo_path/m249.csv', encoding='utf-8-sig')):
        #     m249_recoil.append([float(x) for x in i])
        # for i in csv.reader(open('./aim_csgo/ammo_path/mac10.csv', encoding='utf-8-sig')):
        #     mac10_recoil.append([float(x) for x in i])
        # for i in csv.reader(open('./aim_csgo/ammo_path/mp5sd.csv', encoding='utf-8-sig')):
        #     mp5sd_recoil.append([float(x) for x in i])
        # for i in csv.reader(open('./aim_csgo/ammo_path/mp7.csv', encoding='utf-8-sig')):
        #     mp7_recoil.append([float(x) for x in i])
        # for i in csv.reader(open('./aim_csgo/ammo_path/mp9.csv', encoding='utf-8-sig')):
        #     mp9_recoil.append([float(x) for x in i])
        # for i in csv.reader(open('./aim_csgo/ammo_path/p90.csv', encoding='utf-8-sig')):
        #     p90_recoil.append([float(x) for x in i])
        # for i in csv.reader(open('./aim_csgo/ammo_path/sg553.csv', encoding='utf-8-sig')):
        #     sg553_recoil.append([float(x) for x in i])
        # for i in csv.reader(open('./aim_csgo/ammo_path/ump45.csv', encoding='utf-8-sig')):
        #     ump45_recoil.append([float(x) for x in i])

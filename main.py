# THIS FILE IS PART OF Caesar PROJECT
# main_nonblock.py - The core part of the AI assistant
#
# THIS PROGRAM IS A FREE PROGRAM, WHICH IS LICENSED UNDER Caesar
# DO NOT FORWARD THIS PROGRAM TO ANYONE

from aim_csgo.screen_inf import Screen
from aim_csgo.cs_model import load_model
import cv2
from ctypes import *
from ctypes.wintypes import HWND
import torch
import numpy as np
from utils.general import non_max_suppression, scale_coords, xyxy2xywh
from utils.augmentations import letterbox
import pynput
from aim_csgo.aim_lock_pi import Locker, recoil_control
from aim_csgo.verify_args import verify_args
from threading import Thread
import winsound
import warnings
import argparse
import time
import os

"参数请认真修改，改好了效果就好"
"游戏与桌面分辨率不一致时需要开启全屏模式，不能是无边框窗口"
"鼠标移动在fov为90的游戏中下最准确 其他fov能用，但可能效果没那么好"
"此版本不支持在桌面试用，因为默认鼠标在屏幕中心"
parser = argparse.ArgumentParser()
parser.add_argument('--model-path', type=str, default='aim_csgo/models/1200.pt', help='模型地址，pytorch模型请以.pt结尾，onnx模型请以.onnx结尾，tensorrt模型请以.trt结尾')
parser.add_argument('--imgsz', type=list, default=640, help='和你训练模型时imgsz一样')
parser.add_argument('--conf-thres', type=float, default=0.6, help='置信阈值')
parser.add_argument('--iou-thres', type=float, default=0.05, help='交并比阈值')
parser.add_argument('--use-cuda', type=bool, default=True, help='是否使用cuda')
parser.add_argument('--half', type=bool, default=True, help='是否使用半浮点运算')

parser.add_argument('--show-window', type=bool, default=True, help='是否显示实时检测窗口(若为True，若想关闭窗口请结束程序！)')
parser.add_argument('--top-most', type=bool, default=True, help='是否保持实时检测窗口置顶')
parser.add_argument('--resize-window', type=float, default=1/3, help='缩放实时检测窗口大小')
parser.add_argument('--thickness', type=int, default=3, help='画框粗细，必须大于1/resize-window')
parser.add_argument('--show-fps', type=bool, default=True, help='是否显示帧率')
parser.add_argument('--show-label', type=bool, default=True, help='是否显示标签')

parser.add_argument('--region', type=tuple, default=(1, 1), help='检测范围；分别为横向和竖向，(1.0, 1.0)表示全屏检测，越低检测范围越小(始终保持屏幕中心为中心)')

parser.add_argument('--hold-lock', type=bool, default=False, help='lock模式；True为按住，False为切换')
parser.add_argument('--lock-sen', type=float, default=1, help='lock幅度系数；为游戏中(csgo)灵敏度')
parser.add_argument('--lock-smooth', type=float, default=1, help='lock平滑系数；越大越平滑，最低1.0')
parser.add_argument('--lock-button', type=str, default='x2', help='lock按键；只支持鼠标按键')
parser.add_argument('--lock-sound', type=bool, default=True, help='切换到lock模式时是否发出提示音')
parser.add_argument('--lock-strategy', type=str, default='', help='lock模式移动改善策略，为空时无策略，为pid时使用PID控制算法，暂未实现其他算法捏')
parser.add_argument('--p-i-d', type=tuple, default=(1.1, 0.1, 0.1), help='PID控制算法p,i,d参数调整')
parser.add_argument('--head-first', type=bool, default=True, help='是否优先瞄头')
parser.add_argument('--lock-tag', type=list, default=[1, 0, 3, 2], help='对应标签；缺一不可，自己按以下顺序对应标签，ct_head ct_body t_head t_body')
parser.add_argument('--lock-choice', type=list, default=[1, 3], help='目标选择；可自行决定锁定的目标，从自己的标签中选')

"除了前两行以外其他看个乐，因为懒并没有写通用压枪代码^^"
parser.add_argument('--recoil-sen', type=float, default=3, help='压枪幅度；自己调，调到合适')
parser.add_argument('--recoil-button-ak47', type=str, default='x1', help='ak47压枪按键；压枪时不会lock，只支持鼠标按键,用不到置为0')
parser.add_argument('--recoil-button-m4a1', type=str, default='0', help='m4a1压枪按键；同上')
parser.add_argument('--recoil-button-m4a4', type=str, default='0', help='m4a4压枪按键；同上')
parser.add_argument('--recoil-button-galil', type=str, default='0', help='galil压枪按键；同上')
parser.add_argument('--recoil-button-famas', type=str, default='0', help='famas压枪按键；同上')
parser.add_argument('--recoil-button-aug', type=str, default='0', help='aug压枪按键；同上')
parser.add_argument('--recoil-button-bizon', type=str, default='0', help='bizon压枪按键；同上')
parser.add_argument('--recoil-button-cz75', type=str, default='0', help='cz75枪按键；同上')
parser.add_argument('--recoil-button-m249', type=str, default='0', help='m249压枪按键；同上')
parser.add_argument('--recoil-button-mac10', type=str, default='0', help='mac10压枪按键；同上')
parser.add_argument('--recoil-button-mp5', type=str, default='0', help='mp5压枪按键；同上')
parser.add_argument('--recoil-button-mp7', type=str, default='0', help='mp7压枪按键；同上')
parser.add_argument('--recoil-button-mp9', type=str, default='0', help='mp9压枪按键；同上')
parser.add_argument('--recoil-button-p90', type=str, default='0', help='p90压枪按键；同上')
parser.add_argument('--recoil-button-sg553', type=str, default='0', help='sg553压枪按键；同上')
parser.add_argument('--recoil-button-ump45', type=str, default='0', help='ump45压枪按键；同上')

args = parser.parse_args()

'------------------------------------------------------------------------------------'
"有问题的话，以下代码无需修改，好好考虑分界线上面的参数有没有填错即可。"
"想自行修改相应功能请自便修改下面代码。"
"准星乱飘记得先把准星改淡一点，尽量不遮挡人物。"
"有问题一定不是我代码有问题.jpg（也许可能真有问题呢？"

verify_args(args)
warnings.filterwarnings('ignore')

u32 = windll.user32
g32 = windll.gdi32


cur_dir = os.path.dirname(os.path.abspath(__file__)) + '\\'

args.model_path = cur_dir + args.model_path
args.lock_tag = [str(i) for i in args.lock_tag]
args.lock_choice = [str(i) for i in args.lock_choice]

device = 'cuda' if args.use_cuda else 'cpu'
imgsz = args.imgsz

conf_thres = args.conf_thres
iou_thres = args.iou_thres

screen = Screen(args)

model = load_model(args)
stride, names, pt = model.stride, model.names, model.pt

lock_mode = False
lock_button = eval('pynput.mouse.Button.' + args.lock_button)
locker = Locker(args)

t = Thread(target=recoil_control, kwargs={'args': args})
t.start()

if args.show_window:
    cv2.namedWindow('csgo-detect', 0)
    cv2.resizeWindow('csgo-detect', int(screen.len_x * args.resize_window), int(screen.len_y * args.resize_window))


def on_click(x, y, button, pressed):
    global lock_mode
    if button == lock_button:
        if args.hold_lock:
            if pressed:
                lock_mode = True
                if args.lock_sound:
                    winsound.Beep(1000, 300)
            else:
                lock_mode = False
                if args.lock_sound:
                    winsound.Beep(500, 300)
        else:
            if pressed:
                lock_mode = not lock_mode
                if args.lock_sound:
                    winsound.Beep(1000 if lock_mode else 500, 300)
                if not lock_mode:
                    locker.reset_params()


listener = pynput.mouse.Listener(on_click=on_click)
listener.start()

print('device: {}'.format(device))
print('enjoy yourself!')
t0 = time.time()
cnt = 0
while True:
    if cnt % 20 == 0:
        screen.update_parameters()
        cnt = 0

    img0 = screen.grab_screen_win32()

    img = letterbox(img0, imgsz, stride=stride)[0]

    img = img.transpose((2, 0, 1))[::-1]
    img = np.ascontiguousarray(img)
    img = torch.from_numpy(img).to(device)
    img = img.half() if args.half else img.float()
    img /= 255
    if len(img.shape) == 3:
        img = img[None]

    pred = model(img, augment=False, visualize=False)

    det = non_max_suppression(pred, conf_thres, iou_thres, agnostic=False)[0]

    aims = []
    gn = torch.tensor(img0.shape)[[1, 0, 1, 0]]
    if len(det):
        det[:, :4] = scale_coords(img.shape[2:], det[:, :4], img0.shape).round()
        for *xyxy, conf, cls in reversed(det):
            # bbox:(tag, x_center, y_center, x_width, y_width)
            xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
            line = (cls, *xywh)  # label format
            aim = ('%g ' * len(line)).rstrip() % line
            aim = aim.split(' ')
            aims.append(aim)

    if len(aims):
        if lock_mode:
            locker.lock2(aims, screen.top_x, screen.top_y, screen.len_x, screen.len_y, args)

        if args.show_window:
            for i, det in enumerate(aims):
                tag, x_center, y_center, width, height = det
                x_center, width = screen.len_x * float(x_center), screen.len_x * float(width)
                y_center, height = screen.len_y * float(y_center), screen.len_y * float(height)
                top_left = (int(x_center - width / 2.), int(y_center - height / 2.))
                bottom_right = (int(x_center + width / 2.), int(y_center + height / 2.))
                cv2.rectangle(img0, top_left, bottom_right, (0, 255, 0), thickness=args.thickness)
                if args.show_label:
                    cv2.putText(img0, tag, top_left, 0, 0.7, (235, 0, 0), 4)

    if args.show_window:
        if args.show_fps:
            cv2.putText(img0, "FPS:{:.1f}".format(1. / (time.time() - t0)), (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 235), 4)
            t0 = time.time()
        cv2.imshow('csgo-detect', img0)

        if args.top_most:
            hwnd = u32.FindWindowW(None, 'csgo-detect')
            u32.SetWindowPos(hwnd, HWND(-1), 0, 0, 0, 0, 0x0001 | 0x0002)

        cv2.waitKey(1)

    cnt += 1

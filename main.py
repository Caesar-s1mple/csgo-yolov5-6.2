from aim_csgo.screen_inf import Screen
from aim_csgo.cs_model import load_model
import cv2
from widget import ui_mainFrom
import sys
from ctypes import *
from ctypes.wintypes import HWND
import torch
import pynput
import numpy as np
from PyQt5.QtWidgets import QWidget, QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from utils.general import non_max_suppression, scale_coords, xyxy2xywh
from aim_csgo.screen_utils import grab_screen_mss, grab_screen_win32, get_parameters
from utils.augmentations import letterbox
from aim_csgo.screen_inf import show_fps, show_top_most
from aim_csgo.aim_lock_pi import Locker
from aim_csgo.verify_args import verify_args
import winsound
import warnings
import argparse
import pid
import time
import os

"参数请认真修改，改好了效果就好"
"游戏与桌面分辨率不一致时需要开启全屏模式，不能是无边框窗口"
"此版本不支持在桌面试用，因为默认鼠标在屏幕中心"
"默认参数在csgo中1280*960(4:3)分辨率下为一帧锁"
"检测帧率高于15，锁人出现明显抖动时，把lock-smooth上调"
"你可以尝试同时开启lock_mode和recoil_mode，然后试着在靶场按住左键不松手^^（只支持ak47）"
parser = argparse.ArgumentParser()
parser.add_argument('--model-path', type=str, default='aim_csgo/models/yolov5n_cf7000.pt',
                    help='模型地址，pytorch模型请以.pt结尾，onnx模型请以.onnx结尾，tensorrt模型请以.trt结尾')
parser.add_argument('--imgsz', type=list, default=640, help='和你训练模型时imgsz一样')
parser.add_argument('--conf-thres', type=float, default=0.6, help='置信阈值')
parser.add_argument('--iou-thres', type=float, default=0.05, help='交并比阈值')
parser.add_argument('--use-cuda', type=bool, default=True, help='是否使用cuda')
parser.add_argument('--half', type=bool, default=True, help='是否使用半浮点运算')
parser.add_argument('--sleep-time', type=int, default=8, help='检测帧率控制(ms)，防止因快速拉枪导致的残影误检')

parser.add_argument('--show-window', type=bool, default=False,
                    help='是否显示实时检测窗口(若为True，若想关闭窗口请结束程序！)')
parser.add_argument('--top-most', type=bool, default=True, help='是否保持实时检测窗口置顶')
parser.add_argument('--resize-window', type=float, default=1 / 3, help='缩放实时检测窗口大小')
parser.add_argument('--thickness', type=int, default=3, help='画框粗细，必须大于1/resize-window')
parser.add_argument('--show-fps', type=bool, default=True, help='是否显示帧率')
parser.add_argument('--show-label', type=bool, default=True, help='是否显示标签')

parser.add_argument('--region', type=list, default=[0.4, 0.7],
                    help='检测范围；分别为横向和竖向，(1.0, 1.0)表示全屏检测，越低检测范围越小(始终保持屏幕中心为中心)')
parser.add_argument('--use_mss', type=str, default=True, help='是否使用mss截屏；为False時使用win32截屏')
parser.add_argument('--hold-lock', type=bool, default=True, help='lock模式；True为按住，False为切换')
parser.add_argument('--lock-sen', type=float, default=1, help='lock幅度系数；为游戏中(csgo)灵敏度')
parser.add_argument('--lock-smooth', type=float, default=3, help='lock平滑系数；越大越平滑，最低1.0')
parser.add_argument('--lock-button', type=str, default='right', help='lock按键；只支持鼠标按键，不能是左键')
parser.add_argument('--lock-strategy', type=str, default='pid',
                    help='lock模式移动改善策略，为空时无策略，为pid时使用PID控制算法，暂未实现其他算法捏')
parser.add_argument('--p-i-d', type=tuple, default=(1, 0.2, 0.02), help='PID控制算法p,i,d参数调整')
parser.add_argument('--head-first', type=bool, default=True, help='是否优先瞄头')
parser.add_argument('--lock-tag', type=list, default=[1, 0], help='对应标签；缺一不可，自己按以下顺序对应标签，ct_head ct_body t_head '
                                                                  't_body')
parser.add_argument('--lock-choice', type=list, default=[1, 0], help='目标选择；可自行决定锁定的目标，从自己的标签中选')
parser.add_argument('--head-to-foot', type=float, default=0, help='准星位置，从头到脚')
parser.add_argument('--recoil-sen', type=float, default=1.3, help='压枪幅度；自己调，调到合适')
parser.add_argument('--recoil-button', type=str, default='x1', help='ak47压枪按键；只支持鼠标按键,用不到置为0')

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
half = device != 'cpu'
imgsz = args.imgsz

conf_thres = args.conf_thres
iou_thres = args.iou_thres

top_x, top_y, x, y = get_parameters()
len_x, len_y = int(x * args.region[0]), int(y * args.region[1])
top_x, top_y = int(top_x + x // 2 * (1. - args.region[0])), int(top_y + y // 2 * (1. - args.region[1]))

monitor = {'left': top_x, 'top': top_y, 'width': len_x, 'height': len_y}

model = load_model(args)
stride = int(model.stride.max())
names = model.module.names if hasattr(model, 'module') else model.names

screen = Screen(args)
locker = Locker(args)

mouse = pynput.mouse.Controller()
# pid係數可自行調整(以下為我自己使用的參數)

if args.show_window:
    cv2.namedWindow('detect', 0)
    cv2.resizeWindow('detect', int(screen.len_x * args.resize_window), int(screen.len_y * args.resize_window))

lock_mode = False

exit_loop = False
lock_mode_toggle = True


def on_click(x, y, button, pressed):
    global lock_mode
    if button == eval('pynput.mouse.Button.' + args.lock_button):  # 如果右键按下
        lock_mode = pressed
        if not pressed:
            locker.reset_params()
    else:  # 如果其他键按下
        lock_mode = False


listener = pynput.mouse.Listener(on_click=on_click)
listener.start()


# 继承QThread
class My_thread(QThread):
    # 定义信号
    lockingSig = pyqtSignal(object)
    showFpsSig = pyqtSignal(object, object, object, object)
    showTopMost = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        # 要定义的行为，比如开始一个活动什么的
        print('start....')
        t0 = time.time()
        cnt = 0
        while True:
            if not globals()['lock_mode_toggle']:
                time.sleep(1)
                print("globals()['lock_mode_toggle'] ", globals()['lock_mode_toggle'])
                continue
            if cnt % 20 == 0:
                screen.update_parameters()
                locker.top_x = screen.top_x
                locker.top_y = screen.top_y
                locker.len_x = screen.len_x
                locker.len_y = screen.len_y
                cnt = 0

            if args.use_mss:
                img0 = grab_screen_mss(monitor)
                img0 = cv2.resize(img0, (len_x, len_y))
            else:
                img0 = grab_screen_win32(region=(top_x, top_y, top_x + len_x, top_y + len_y))
                img0 = cv2.resize(img0, (len_x, len_y))

            img = letterbox(img0, imgsz, stride=stride)[0]

            img = img.transpose((2, 0, 1))[::-1]
            img = np.ascontiguousarray(img)

            img = torch.from_numpy(img).to(device)
            img = img.half() if half else img.float()
            img /= 255.

            if len(img.shape) == 3:
                img = img[None]

            pred = non_max_suppression(model(img, augment=False, visualize=False)[0],
                                       conf_thres, iou_thres, agnostic=False)

            aims = []
            for i, det in enumerate(pred):
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
                        print("lock_mode", lock_mode)
                        self.lockingSig.emit(aims)

                if args.show_window:
                    for i, det in enumerate(aims):
                        tag, x_center, y_center, width, height = det
                        x_center, width = len_x * float(x_center), len_x * float(width)
                        print("width:", width)
                        print("x_center:", x_center)
                        y_center, height = len_y * float(y_center), len_y * float(height)
                        top_left = (int(x_center - width / 2.), int(y_center - height / 2.))
                        print("top_left:", top_left)
                        bottom_right = (int(x_center + width / 2.), int(y_center + height / 2.))
                        print("bottom_right:", bottom_right)
                        cv2.rectangle(img0, top_left, bottom_right, (197, 229, 85), thickness=args.thickness)
                        if args.show_label:
                            cv2.putText(img0, tag, top_left, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (7, 91, 142), 4)
            if args.show_window:
                if args.show_fps:
                    self.showFpsSig.emit(cv2, lock_mode, img0, t0)
                    t0 = time.time()

                if args.top_most:
                    self.showTopMost.emit()
                cv2.waitKey(1)
            cnt += 1
            if globals()['exit_loop']:
                break
        print('end....')


def setParam(ui):
    args.conf_thres = ui.value_belive.value()
    args.iou_thres = ui.iou.value()
    args.use_cuda = ui.cuda.isChecked()
    args.lock_smooth = ui.smooth.value()
    args.hold_lock = True if ui.plan.currentIndex() == 0 else False
    args.show_window = ui.debug.isChecked()
    args.lock_button = 'right' if ui.mouse.currentIndex() == 0 else 'left'
    args.use_mss = ui.mess.isChecked()
    args.region[0] = ui.x_value.value()
    args.region[1] = ui.y_value.value()
    args.head_to_foot = ui.headtofoot.value()

    globals()['lock_mode_toggle'] = ui.start_lock.isChecked()
    print("globals()['lock_mode_toggle'] ", globals()['lock_mode_toggle'])


def exit_loop_func():
    globals()['exit_loop'] = True


app = QApplication(sys.argv)
main_window = QMainWindow()
auto_ui_window = ui_mainFrom.Ui_MainWindow()  # 实例化部件
auto_ui_window.setupUi(main_window)  # 调用setupUi()方法，并传入 主窗口 参数。

auto_ui_window.pushButton.clicked.connect(lambda: setParam(auto_ui_window))
auto_ui_window.exit_btn.clicked.connect(lambda: exit_loop_func())
auto_ui_window.exit_btn.clicked.connect(lambda: os._exit(0))  # 强退进程

main_window.setWindowTitle('AI')
main_window.show()

# 瞄准线程实例化
aim_worker = My_thread()
aim_worker.start()

# lock函数在主线程
aim_worker.lockingSig.connect(locker.lock)
aim_worker.showFpsSig.connect(show_fps)
aim_worker.showTopMost.connect(show_top_most)

main_window.activateWindow()
app.exec()
exit_loop_func()

# 等待AI线程结束
time.sleep(1)
os._exit(0)  # 强退进程

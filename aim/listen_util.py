import pynput.mouse as pm
import threading


def on_click(x, y, button, pressed):
    # 监听鼠标点击
    if pressed:
        print("按下坐标")
        mxy = "{},{}".format(x, y)
        print(mxy)
        print(button)
    if not pressed:
        # Stop listener
        return False


def ls_k_thread():
    while (1):
        with pm.Listener(on_click=on_click) as pmlistener:
            pmlistener.join()


def analyse_pic_thread():
    r = threading.Thread(target=ls_k_thread)
    r.start()


analyse_pic_thread()

if __name__ == '_main_':
    analyse_pic_thread()

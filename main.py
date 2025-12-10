# main.py

import tkinter as tk
# 从 src 包中导入 GUI 类
from src.gui import RenamerApp
# 导入 ctypes 用于解决 Windows 高清屏模糊问题
try:
    from ctypes import windll
except ImportError:
    # 非 Windows 系统或环境不支持时忽略
    windll = None


if __name__ == "__main__":
    # 使用 ctypes 解决高分辨率屏幕上的显示模糊问题 (Windows)
    if windll:
        try:
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

    root = tk.Tk()
    app = RenamerApp(root)
    root.mainloop()
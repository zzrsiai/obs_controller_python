"""
obs_gui_main.py  ——  OBS 全功能控制台 GUI 入口
用法：
    python obs_gui_main.py

依赖：
    pip install ttkbootstrap pillow obsws-python
"""
import sys
import os

# 确保工作目录在 sys.path，便于导入 obs_controller
sys.path.insert(0, os.path.dirname(__file__))

from gui.app import OBSGui


def main():
    app = OBSGui()
    app.run()


if __name__ == "__main__":
    main()

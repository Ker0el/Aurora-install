#!/usr/bin/env python3
"""
Aurora Install（极光入库）入口
"""
import sys
import os
import json
from pathlib import Path

# 确保项目根目录在 Python 路径中
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.fluent_app import MainWindow, load_theme_config
from qfluentwidgets import setTheme, Theme, setThemeColor

def main():
    """主入口函数"""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt, QSharedMemory

    # 崩溃转储：未捕获异常写入 logs/crash_<ts>.log，方便定位 PyInstaller 下无法看到的问题
    def _excepthook(exc_type, exc_value, exc_tb):
        try:
            import traceback, time
            from pathlib import Path
            log_dir = Path(__file__).resolve().parent / 'logs'
            log_dir.mkdir(exist_ok=True)
            with open(log_dir / f'crash_{time.strftime("%Y%m%d_%H%M%S")}.log', 'w', encoding='utf-8') as f:
                f.write(''.join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    sys.excepthook = _excepthook

    # 单实例锁：防止多开导致 Qt6Core 崩溃（多实例并发写 config/日志 + PyInstaller _MEI 冲突）
    shared_memory = QSharedMemory("AuroraInstall_SingleInstance")
    if not shared_memory.create(1):
        # 已有实例在运行，直接激活已有窗口后退出
        try:
            shared_memory.attach()
            shared_memory.detach()
        except Exception:
            pass
        return 0

    # 启用高 DPI 缩放
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)

    app = QApplication(sys.argv)
    
    # 加载主题配置
    theme_config = load_theme_config()
    
    # 应用主题设置
    theme_mode = theme_config["theme_mode"]
    if theme_mode == "light":
        setTheme(Theme.LIGHT)
    elif theme_mode == "dark":
        setTheme(Theme.DARK)
    else:
        setTheme(Theme.AUTO)
    
    # 应用主题色
    setThemeColor(theme_config["theme_color"])

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()

"""
剪贴板记忆管理器 - 快捷键监听模块
Ctrl+Alt+V → 弹出记忆面板（单次按下即可）
Ctrl+V     → 完全不动，正常系统粘贴
"""

import time

from PyQt5.QtCore import QThread, pyqtSignal


class HotkeyListener(QThread):
    """
    快捷键监听线程。
    只监听 Ctrl+Alt+V，不拦截任何系统按键。
    """

    show_panel = pyqtSignal()  # 弹出面板

    def __init__(self):
        super().__init__()
        self._running = False

    def run(self):
        self._running = True
        try:
            import keyboard
            # suppress=False → 不影响系统正常功能
            keyboard.add_hotkey(
                "ctrl+alt+v",
                self._on_hotkey,
                suppress=True,       # ★ 拦截按键，不让 V 字符输出到应用
            )
            while self._running:
                time.sleep(0.2)
        except ImportError:
            print("[错误] 需要安装 keyboard 库：pip install keyboard")
        except Exception as e:
            print(f"[快捷键监听错误] {e}")
            import traceback
            traceback.print_exc()

    def stop(self):
        self._running = False
        try:
            import keyboard
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

    def _on_hotkey(self):
        """用户按下 Ctrl+Shift+V → 弹出面板"""
        self.show_panel.emit()

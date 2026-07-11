"""
剪贴板记忆管理器 - 主程序入口
- 系统托盘常驻后台
- Ctrl+C        → 自动记录剪贴板内容
- Ctrl+V        → 正常系统粘贴（完全不干预）
- Ctrl+Alt+V  → 弹出记忆面板（选择后复制到剪贴板，再 Ctrl+V 粘贴）
- 开机自启
"""

import sys
import os

from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QPen, QBrush,
)

import config
from database import Database, _get_app_dir
from clipboard_monitor import (
    ClipboardMonitor,
    set_clipboard_text,
    set_clipboard_image,
    set_clipboard_file,
)
from hotkey_listener import HotkeyListener
# ★ clipboard_panel 必须在 QApplication 创建之后才能导入（加载时需要 QPixmap）


# ═══════════════════════════════════════════════════════════════
# 托盘图标生成
# ═══════════════════════════════════════════════════════════════

def create_tray_icon() -> QIcon:
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    # 绿色圆角方形背景
    p.setBrush(QColor(config.ACCENT_COLOR))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(6, 4, 52, 56, 10, 10)

    # 白色面板
    p.setBrush(QColor("white"))
    p.drawRoundedRect(14, 12, 36, 40, 6, 6)

    # 顶部夹子
    p.setBrush(QColor(config.ACCENT_COLOR))
    p.drawRoundedRect(22, 6, 20, 12, 4, 4)

    # 内容线条
    pen = QPen(QColor(config.ACCENT_COLOR), 3)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.drawLine(22, 28, 42, 28)
    p.drawLine(22, 34, 38, 34)
    p.drawLine(22, 40, 40, 40)

    p.end()
    return QIcon(pix)


# ═══════════════════════════════════════════════════════════════
# 开机自启
# ═══════════════════════════════════════════════════════════════

AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = "ClipboardMemory"


def get_autostart_path() -> str:
    """
    返回开机自启的命令行。
    - 打包成 exe 后：直接用 exe 路径
    - 开发模式：用 pythonw.exe（无控制台黑窗）+ 脚本路径
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的 exe
        return f'"{sys.executable}"'
    else:
        # 开发模式：pythonw.exe 无窗口静默运行
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        script = os.path.abspath(__file__)
        return f'"{pythonw}" "{script}"'


def enable_autostart():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ,
                          get_autostart_path())
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[自动启动] 注册失败: {e}")


def disable_autostart():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, AUTOSTART_NAME)
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[自动启动] 移除失败: {e}")


def is_autostart_enabled() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, AUTOSTART_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
# 主应用程序
# ═══════════════════════════════════════════════════════════════

class ClipboardApp:
    """剪贴板记忆管理器"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # QApplication 就绪后才导入 panel
        from clipboard_panel import ClipboardPanel

        # ── 数据库 ──
        self.db = Database()
        print(f"[初始化] 数据库: {self.db.db_path}")

        # ── 面板 ──
        self.panel = ClipboardPanel(self.db)
        self.panel.paste_record.connect(self._on_select_item)

        # ── 剪贴板监听 ──
        storage_dir = os.path.join(_get_app_dir(), config.STORAGE_DIR)
        self.monitor = ClipboardMonitor(self.db, storage_dir)
        self.monitor.new_record_added.connect(self._on_new_record)
        self.monitor.start()
        print("[初始化] 剪贴板监听已启动")

        # ── 快捷键 Ctrl+Alt+V → 弹出面板 ──
        self.hotkey = HotkeyListener()
        self.hotkey.show_panel.connect(self._show_panel)
        self.hotkey.start()
        print("[初始化] 快捷键 Ctrl+Alt+V 已就绪")

        # ── 系统托盘 ──
        self._setup_tray()

        # ── 开机自启 ──
        if not is_autostart_enabled():
            enable_autostart()
            print("[初始化] 已启用开机自启")

        self.tray.showMessage(
            "剪贴板记忆管理器",
            "已启动\nCtrl+C 复制 → 自动记忆\nCtrl+Alt+V → 打开记忆面板",
            QSystemTrayIcon.Information, 3000)
        print("[启动] 就绪")

    # ── 系统托盘 ─────────────────────────────────────────

    def _setup_tray(self):
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(create_tray_icon())
        self.tray.setToolTip("剪贴板记忆管理器\nCtrl+Alt+V 打开面板")

        menu = QMenu()
        menu.addAction("📋 显示面板  (Ctrl+Alt+V)", self._show_panel)
        menu.addSeparator()
        autostart_text = ("✅ 开机自启（已开启）" if is_autostart_enabled()
                          else "⬜ 开机自启（已关闭）")
        self.autostart_action = menu.addAction(autostart_text)
        self.autostart_action.triggered.connect(self._toggle_autostart)
        menu.addSeparator()
        menu.addAction("🗑 清空历史记录", self._confirm_clear_all)
        menu.addSeparator()
        menu.addAction("ℹ 关于", self._show_about)
        menu.addAction("❌ 退出", self._quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda r: r == QSystemTrayIcon.DoubleClick and self._show_panel())
        self.tray.show()

    # ── 面板 ─────────────────────────────────────────────

    def _show_panel(self):
        try:
            self.panel.show_panel()
        except Exception as e:
            print(f"[主程序错误] 显示面板失败: {e}")
            import traceback
            traceback.print_exc()

    def _on_new_record(self, record: dict):
        try:
            if self.panel.isVisible():
                self.panel.refresh()
        except Exception as e:
            print(f"[主程序错误] 刷新面板失败: {e}")

    def _on_select_item(self, record: dict):
        """
        用户在面板中选中了一条记录：
        1. 把内容写入系统剪贴板
        2. 关闭面板
        3. 用户自己按 Ctrl+V 粘贴
        """
        ctype = record.get("content_type", config.TYPE_TEXT)

        # 暂停监听（防止把自己写入的内容重复记录）
        self.monitor.pause()

        try:
            if ctype == config.TYPE_TEXT:
                set_clipboard_text(record.get("content", ""))
            elif ctype == config.TYPE_IMAGE:
                set_clipboard_image(record.get("image_path", ""))
            elif ctype == config.TYPE_FILE:
                set_clipboard_file(record.get("content", ""))
        except Exception as e:
            print(f"[错误] 写入剪贴板失败: {e}")

        self.monitor.resume()
        self.panel.hide_panel()

    # ── 开机自启 ─────────────────────────────────────────

    def _toggle_autostart(self):
        if is_autostart_enabled():
            disable_autostart()
            self.autostart_action.setText("⬜ 开机自启（已关闭）")
            self.tray.showMessage("剪贴板记忆管理器", "已关闭开机自启",
                                  QSystemTrayIcon.Information, 2000)
        else:
            enable_autostart()
            self.autostart_action.setText("✅ 开机自启（已开启）")
            self.tray.showMessage("剪贴板记忆管理器", "已开启开机自启",
                                  QSystemTrayIcon.Information, 2000)

    # ── 其他 ─────────────────────────────────────────────

    def _confirm_clear_all(self):
        reply = QMessageBox.question(
            None, "确认清空",
            "确定要清空所有剪贴板历史记录吗？\n"
            "此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.clear_all()
            if self.panel.isVisible():
                self.panel.refresh()
            self.tray.showMessage("剪贴板记忆管理器", "已清空",
                                  QSystemTrayIcon.Information, 2000)

    def _show_about(self):
        QMessageBox.about(
            None, "关于",
            "<h3>📋 剪贴板记忆管理器 v1.0</h3>"
            "<p>带记忆功能的剪贴板增强工具。</p>"
            "<p><b>快捷键：</b></p>"
            "<ul>"
            "<li><b>Ctrl+C</b> — 复制并自动记录</li>"
            "<li><b>Ctrl+V</b> — 正常粘贴</li>"
            "<li><b>Ctrl+Alt+V</b> — 打开记忆面板</li>"
            "</ul>"
            "<p>最多保存 100 条，保留 7 天，开机自启。</p>")

    def _quit(self):
        self.monitor.stop()
        self.hotkey.stop()
        self.tray.hide()
        self.app.quit()

    def run(self):
        sys.exit(self.app.exec_())


if __name__ == "__main__":
    ClipboardApp().run()

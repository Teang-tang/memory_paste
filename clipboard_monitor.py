"""
剪贴板记忆管理器 - 剪贴板监听模块
后台轮询 Windows 剪贴板，自动捕获文字、图片和文件路径
"""

import os
import time
import threading
import hashlib
import struct
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

import config
from database import Database

# Windows 剪贴板相关导入
try:
    import win32clipboard
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    print("[警告] pywin32 未安装，剪贴板功能将受限")

try:
    from PIL import Image, ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class ClipboardMonitor(QThread):
    """后台剪贴板轮询线程"""

    # 信号：新记录已添加，通知 UI 刷新
    new_record_added = pyqtSignal(dict)

    def __init__(self, db: Database, storage_dir: str):
        super().__init__()
        self.db = db
        self.storage_dir = storage_dir
        self._running = False
        self._pause_event = threading.Event()  # 暂停标志（Event 确保跨线程可见）
        self._last_text = ""
        self._last_image_hash = ""
        self._last_file_list = set()

        # 确保存储目录存在
        os.makedirs(self.storage_dir, exist_ok=True)

    def run(self):
        """线程主循环：轮询剪贴板"""
        self._running = True

        # 初始化：记录当前剪贴板状态，避免启动时重复记录
        self._last_text = self._get_clipboard_text() or ""
        img = self._get_clipboard_image()
        self._last_image_hash = self._hash_image(img) if img else ""

        while self._running:
            try:
                self._check_clipboard()
            except Exception as e:
                print(f"[剪贴板轮询错误] {e}")

            # 休眠
            for _ in range(config.POLLING_INTERVAL_MS // 100):
                if not self._running:
                    break
                time.sleep(0.1)

    def stop(self):
        """停止轮询"""
        self._running = False

    def pause(self):
        """暂停监听（粘贴操作时调用，防止把自身粘贴记录进去）"""
        self._pause_event.set()

    def resume(self):
        """恢复监听，并刷新"上次状态"防止记录中间的变化"""
        self._last_text = self._get_clipboard_text() or ""
        img = self._get_clipboard_image()
        self._last_image_hash = self._hash_image(img) if img else ""
        self._last_file_list = self._get_clipboard_files() or set()
        self._pause_event.clear()

    def _check_clipboard(self):
        """检查剪贴板是否有新内容"""
        if self._pause_event.is_set():
            return
        # 1. 检查图片（优先级最高，因为截图很常见）
        image = self._get_clipboard_image()
        if image:
            img_hash = self._hash_image(image)
            if img_hash and img_hash != self._last_image_hash:
                self._last_image_hash = img_hash
                self._save_image_record(image)
                return

        # 2. 检查文件（资源管理器中复制的文件）
        files = self._get_clipboard_files()
        if files and files != self._last_file_list:
            self._last_file_list = files
            for fpath in files:
                self._save_file_record(fpath)
            return
        else:
            self._last_file_list = files or set()

        # 3. 检查文字（放在最后，因为文字变化最频繁但最容易去重）
        text = self._get_clipboard_text()
        if text and text != self._last_text:
            self._last_text = text
            self._save_text_record(text)

    # ── 剪贴板读取方法 ──────────────────────────────

    def _get_clipboard_text(self) -> str | None:
        """从剪贴板读取文字"""
        if not HAS_WIN32:
            return None
        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                    return data
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            return None
        return None

    def _get_clipboard_image(self):
        """从剪贴板读取图片（返回 PIL Image 或 None）"""
        if not HAS_PIL:
            return None
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                return img
        except Exception:
            pass
        return None

    def _get_clipboard_files(self) -> set | None:
        """从剪贴板读取文件列表（资源管理器复制操作）"""
        if not HAS_WIN32:
            return None
        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
                    data = win32clipboard.GetClipboardData(win32con.CF_HDROP)
                    return set(data)
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            return None
        return None

    # ── 保存方法 ─────────────────────────────────────

    def _save_text_record(self, text: str):
        """保存文字记录"""
        text_stripped = text.strip()
        if len(text_stripped) < 1 or len(text_stripped) > 50000:
            return  # 跳过空内容和过长内容

        record_id = self.db.add_record(
            content_type=config.TYPE_TEXT,
            content=text_stripped,
            size_bytes=len(text_stripped.encode("utf-8"))
        )
        if record_id:
            self._emit_new(record_id, config.TYPE_TEXT, text_stripped[:config.PREVIEW_MAX_CHARS])

    def _save_image_record(self, image):
        """保存图片记录"""
        try:
            # 生成唯一文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            img_hash = self._hash_image(image)
            filename = f"img_{timestamp}_{img_hash[:8]}.png"
            filepath = os.path.join(self.storage_dir, filename)

            # 保存图片
            image.save(filepath, "PNG")
            size_kb = os.path.getsize(filepath)

            record_id = self.db.add_record(
                content_type=config.TYPE_IMAGE,
                content=f"[图片] {filename}",
                image_path=filepath,
                size_bytes=size_kb
            )
            if record_id:
                self._emit_new(record_id, config.TYPE_IMAGE, filepath, image_path=filepath)

        except Exception as e:
            print(f"[保存图片失败] {e}")

    def _save_file_record(self, filepath: str):
        """保存文件/文件夹路径记录"""
        path = Path(filepath)
        if not path.exists():
            return

        is_dir = path.is_dir()
        label = f"[{'文件夹' if is_dir else '文件'}] {path.name}"

        record_id = self.db.add_record(
            content_type=config.TYPE_FILE,
            content=filepath,
            size_bytes=0
        )
        if record_id:
            self._emit_new(record_id, config.TYPE_FILE, filepath)

    def _emit_new(self, record_id: int, ctype: str, content: str,
                  image_path: str = ""):
        """发送新记录信号"""
        self.new_record_added.emit({
            "id": record_id,
            "content_type": ctype,
            "content": content,
            "image_path": image_path,
            "created_at": time.time(),
            "pinned": 0,
        })

    # ── 工具方法 ─────────────────────────────────────

    @staticmethod
    def _hash_image(image) -> str:
        """计算图片哈希（用于去重）"""
        try:
            # 缩放到小尺寸后取哈希，忽略细微差异
            small = image.resize((32, 32)).convert("L")
            return hashlib.md5(small.tobytes()).hexdigest()
        except Exception:
            return ""


def get_clipboard_text_fast() -> str:
    """快速获取剪贴板文字（不抛异常）"""
    try:
        import win32clipboard
        import win32con
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        pass
    return ""


def set_clipboard_text(text: str):
    """设置剪贴板文字"""
    try:
        import win32clipboard
        import win32con
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
        win32clipboard.CloseClipboard()
    except Exception as e:
        print(f"[设置剪贴板失败] {e}")


def set_clipboard_file(filepath: str):
    """
    设置剪贴板为文件/文件夹（模拟资源管理器的 Ctrl+C 复制文件）。

    Windows CF_HDROP 格式要求一个 DROPFILES 二进制结构，
    后面跟着 UTF-16LE 编码、双 null 结尾的文件路径列表。
    """
    try:
        import win32clipboard
        from win32con import CF_HDROP

        # 1. 编码文件路径为 UTF-16LE（Windows Unicode 格式）
        path_encoded = filepath.encode("utf-16-le") + b"\x00\x00"

        # 2. 构建 DROPFILES 结构（20 字节）
        #    DWORD pFiles  = 文件列表起始偏移（即结构体大小 = 20）
        #    POINT pt      = (0, 0)  拖放坐标，粘贴操作不需要
        #    BOOL  fNC     = FALSE   不是非客户区
        #    BOOL  fWide   = TRUE    使用 Unicode 字符
        dropfiles = struct.pack(
            "<Iiiii",   # DWORD, LONG, LONG, BOOL, BOOL
            20,         # pFiles: 文件路径相对于结构体开头的偏移
            0, 0,       # pt.x, pt.y
            0,          # fNC = FALSE
            1,          # fWide = TRUE（Unicode）
        )

        # 3. 拼接：DROPFILES 结构 + 文件路径 + 结尾双 null
        data = dropfiles + path_encoded + b"\x00\x00"

        # 4. 写入剪贴板
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(CF_HDROP, data)
        win32clipboard.CloseClipboard()

    except Exception as e:
        print(f"[设置文件剪贴板失败] {e}")


def set_clipboard_image(image_path: str):
    """设置剪贴板为图片（用于从面板粘贴图片）"""
    try:
        from PyQt5.QtGui import QImage
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            print("[设置图片剪贴板失败] QApplication 未初始化")
            return

        image = QImage(image_path)
        if image.isNull():
            print(f"[设置图片剪贴板失败] 无法加载图片: {image_path}")
            return

        clipboard = app.clipboard()
        clipboard.setImage(image)
    except Exception as e:
        print(f"[设置图片剪贴板失败] {e}")

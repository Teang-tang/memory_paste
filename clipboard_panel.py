"""
剪贴板记忆管理器 - 弹出面板 UI
Ctrl+Alt+V 呼出，屏幕右上角显示
"""

import os
import time
from datetime import datetime

from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QWidget, QApplication, QDialog,
    QSizePolicy, QGraphicsDropShadowEffect,
)
from PyQt5.QtCore import (
    Qt, QTimer, pyqtSignal, QEvent,
)
from PyQt5.QtGui import (
    QFont, QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QCursor,
)

import config
from database import Database, format_relative_time


# ═══════════════════════════════════════════════════════════════
# 颜色常量（现代风格调色板）
# ═══════════════════════════════════════════════════════════════

C_PRIMARY = "#43A047"
C_PRIMARY_DARK = "#2E7D32"
C_BG = "#F4F6F8"
C_CARD_BG = "#FFFFFF"
C_CARD_HOVER = "#E8F5E9"
C_TEXT = "#263238"
C_TEXT_SECONDARY = "#90A4AE"
C_BORDER = "#E0E0E0"
C_DANGER = "#EF5350"
C_BADGE_BG = "#ECEFF1"
C_BADGE_TEXT = "#607D8B"
C_FILTER_ACTIVE = "#43A047"
C_FILTER_INACTIVE = "#E0E0E0"

PANEL_WIDTH = 440
PANEL_HEIGHT = 640
ITEM_HEIGHT = 72


# ═══════════════════════════════════════════════════════════════
# 图标（延迟初始化）
# ═══════════════════════════════════════════════════════════════

def _make_icon(char: str, bg: str, size: int = 42) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(bg))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(0, 0, size, size, 10, 10)
    p.setPen(QColor("white"))
    font = QFont("Segoe UI", size // 2, QFont.Bold)
    p.setFont(font)
    p.drawText(0, 0, size, size, Qt.AlignCenter, char)
    p.end()
    return QIcon(pix)


ICON_TEXT = None
ICON_IMAGE = None
ICON_FILE = None
ICON_FOLDER = None


def _init_icons():
    global ICON_TEXT, ICON_IMAGE, ICON_FILE, ICON_FOLDER
    if ICON_TEXT is None:
        ICON_TEXT = _make_icon("Aa", C_PRIMARY)
        ICON_IMAGE = _make_icon("IMG", "#42A5F5")
        ICON_FILE = _make_icon("DOC", "#FFA726")
        ICON_FOLDER = _make_icon("DIR", "#FFA726")


# ═══════════════════════════════════════════════════════════════
# 剪贴板条目卡片
# ═══════════════════════════════════════════════════════════════

class ClipboardItemWidget(QFrame):
    clicked = pyqtSignal(dict)
    pin_toggled = pyqtSignal(int)
    delete_requested = pyqtSignal(int)
    preview_requested = pyqtSignal(dict)

    def __init__(self, record: dict, parent=None):
        super().__init__(parent)
        _init_icons()
        self.record = record
        self._selected = False
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedHeight(ITEM_HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            ClipboardItemWidget {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 10px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # 图标
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(42, 42)
        ctype = self.record.get("content_type", config.TYPE_TEXT)
        if ctype == config.TYPE_IMAGE:
            p = self.record.get("image_path", "")
            if os.path.exists(p):
                self.icon_label.setPixmap(
                    QPixmap(p).scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.icon_label.setPixmap(ICON_IMAGE.pixmap(42, 42))
        elif ctype == config.TYPE_FILE:
            path = self.record.get("content", "")
            icon = ICON_FOLDER if os.path.isdir(path) else ICON_FILE
            self.icon_label.setPixmap(icon.pixmap(42, 42))
        else:
            self.icon_label.setPixmap(ICON_TEXT.pixmap(42, 42))
        layout.addWidget(self.icon_label)

        # 文字
        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        preview = QLabel(self._preview())
        preview.setFont(QFont("Microsoft YaHei", 11))
        preview.setStyleSheet("color: %s; border: none; background: transparent;" % C_TEXT)
        preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        text_col.addWidget(preview)

        meta = QHBoxLayout()
        meta.setSpacing(8)

        badge = QLabel(self._badge())
        badge.setFixedHeight(18)
        badge.setFont(QFont("Microsoft YaHei", 8))
        badge.setStyleSheet(
            "background: %s; color: %s; padding: 0 8px; border-radius: 9px; border: none;"
            % (C_BADGE_BG, C_BADGE_TEXT))
        meta.addWidget(badge)

        ts = self.record.get("created_at", time.time())
        time_lbl = QLabel(format_relative_time(ts))
        time_lbl.setFont(QFont("Microsoft YaHei", 9))
        time_lbl.setStyleSheet("color: %s; border: none; background: transparent;" % C_TEXT_SECONDARY)
        meta.addWidget(time_lbl)
        meta.addStretch()
        text_col.addLayout(meta)

        layout.addLayout(text_col, 1)

        # 按钮
        pinned = self.record.get("pinned", 0)
        self.pin_btn = QPushButton("📌" if pinned else "📍")
        self.pin_btn.setFixedSize(28, 28)
        self.pin_btn.setCursor(Qt.PointingHandCursor)
        self.pin_btn.setStyleSheet("border: none; background: transparent; font-size: 14px;")
        self.pin_btn.setToolTip("置顶")
        self.pin_btn.clicked.connect(lambda: self.pin_toggled.emit(self.record["id"]))
        layout.addWidget(self.pin_btn)

        self.del_btn = QPushButton("✕")
        self.del_btn.setFixedSize(28, 28)
        self.del_btn.setCursor(Qt.PointingHandCursor)
        self.del_btn.setFont(QFont("Microsoft YaHei", 11))
        self.del_btn.setStyleSheet(
            "border: none; background: transparent; color: %s; font-size: 14px;" % C_TEXT_SECONDARY)
        self.del_btn.setToolTip("删除")
        self.del_btn.clicked.connect(lambda: self.delete_requested.emit(self.record["id"]))
        layout.addWidget(self.del_btn)

        # tooltip
        full = self.record.get("content", "")
        if len(full) > config.PREVIEW_MAX_CHARS:
            self.setToolTip(full[:800])

    def _badge(self) -> str:
        t = self.record.get("content_type", "")
        if t == config.TYPE_IMAGE: return "图片"
        if t == config.TYPE_FILE:
            return "文件夹" if os.path.isdir(self.record.get("content", "")) else "文件"
        return "文字"

    def _preview(self) -> str:
        t = self.record.get("content_type", "")
        c = self.record.get("content", "")
        if t == config.TYPE_IMAGE:
            return os.path.basename(self.record.get("image_path", "图片"))
        if t == config.TYPE_FILE:
            return os.path.basename(c) if os.path.exists(c) else c
        s = c.replace("\n", " ").replace("\r", " ")
        return (s[:config.PREVIEW_MAX_CHARS] + "…") if len(s) > config.PREVIEW_MAX_CHARS else s

    def set_selected(self, sel: bool):
        self._selected = sel
        self.setStyleSheet(
            "ClipboardItemWidget { background: %s; border: 2px solid %s; border-radius: 10px; }"
            % (C_CARD_HOVER, C_PRIMARY) if sel else
            "ClipboardItemWidget { background: %s; border: 1px solid %s; border-radius: 10px; }"
            % (C_CARD_BG, C_BORDER))

    def enterEvent(self, e):
        if not self._selected:
            self.setStyleSheet(
                "ClipboardItemWidget { background: %s; border: 1px solid %s; border-radius: 10px; }"
                % (C_CARD_HOVER, C_PRIMARY))
        super().enterEvent(e)

    def leaveEvent(self, e):
        if not self._selected:
            self.setStyleSheet(
                "ClipboardItemWidget { background: %s; border: 1px solid %s; border-radius: 10px; }"
                % (C_CARD_BG, C_BORDER))
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.record.get("content_type") == config.TYPE_IMAGE:
                self.preview_requested.emit(self.record)
            else:
                self.clicked.emit(self.record)
        super().mousePressEvent(e)


# ═══════════════════════════════════════════════════════════════
# 图片预览
# ═══════════════════════════════════════════════════════════════

class ImagePreviewDialog(QDialog):
    paste_requested = pyqtSignal(dict)

    def __init__(self, rec, parent=None):
        super().__init__(parent)
        self.rec = rec
        self._ui()

    def _ui(self):
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        lo = QVBoxLayout(self)
        lo.setContentsMargins(16, 16, 16, 16)
        lo.setSpacing(12)

        pm = QPixmap(self.rec.get("image_path", ""))
        if not pm.isNull():
            sg = QApplication.primaryScreen().availableGeometry()
            mw, mh = int(sg.width() * 0.45), int(sg.height() * 0.45)
            lb = QLabel()
            lb.setPixmap(pm.scaled(mw, mh, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            lb.setAlignment(Qt.AlignCenter)
            lb.setStyleSheet("background: white; border-radius: 10px; padding: 12px;")
            lo.addWidget(lb)

        info = QLabel("保存于 " + format_relative_time(self.rec.get("created_at", 0)))
        info.setFont(QFont("Microsoft YaHei", 9))
        info.setStyleSheet("color: %s;" % C_TEXT_SECONDARY)
        info.setAlignment(Qt.AlignCenter)
        lo.addWidget(info)

        btns = QHBoxLayout()
        btns.setSpacing(10)

        b1 = QPushButton("复制到剪贴板")
        b1.setFont(QFont("Microsoft YaHei", 11))
        b1.setCursor(Qt.PointingHandCursor)
        b1.setMinimumHeight(38)
        b1.setStyleSheet(
            "QPushButton { background: %s; color: white; border: none; "
            "border-radius: 8px; padding: 8px 24px; font-weight: bold; }"
            "QPushButton:hover { background: %s; }" % (C_PRIMARY, C_PRIMARY_DARK))
        b1.clicked.connect(lambda: (self.paste_requested.emit(self.rec), self.accept()))
        btns.addWidget(b1)

        b2 = QPushButton("关闭")
        b2.setFont(QFont("Microsoft YaHei", 11))
        b2.setCursor(Qt.PointingHandCursor)
        b2.setMinimumHeight(38)
        b2.setStyleSheet(
            "QPushButton { background: %s; color: %s; border: none; "
            "border-radius: 8px; padding: 8px 24px; }"
            "QPushButton:hover { background: #CFD8DC; }" % (C_BADGE_BG, C_TEXT))
        b2.clicked.connect(self.close)
        btns.addWidget(b2)
        lo.addLayout(btns)

        self.setStyleSheet("ImagePreviewDialog { background: %s; border: 2px solid %s; "
                           "border-radius: 14px; }" % (C_BG, C_PRIMARY))
        self.adjustSize()

    def changeEvent(self, e):
        if e.type() == QEvent.ActivationChange and not self.isActiveWindow():
            self.close()
        super().changeEvent(e)


# ═══════════════════════════════════════════════════════════════
# 筛选按钮
# ═══════════════════════════════════════════════════════════════

class FilterButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(30)
        self.setFont(QFont("Microsoft YaHei", 10))

    def setChecked(self, on):
        super().setChecked(on)
        if on:
            self.setStyleSheet(
                "QPushButton { background: %s; color: white; border: none; "
                "border-radius: 15px; padding: 4px 16px; font-weight: bold; }" % C_PRIMARY)
        else:
            self.setStyleSheet(
                "QPushButton { background: %s; color: %s; border: none; "
                "border-radius: 15px; padding: 4px 16px; }"
                "QPushButton:hover { background: #BDBDBD; color: %s; }"
                % (C_FILTER_INACTIVE, C_TEXT_SECONDARY, C_TEXT))


# ═══════════════════════════════════════════════════════════════
# 主面板
# ═══════════════════════════════════════════════════════════════

class ClipboardPanel(QFrame):
    paste_record = pyqtSignal(dict)

    def __init__(self, db: Database):
        super().__init__()
        _init_icons()
        self.db = db
        self._filter = None
        self._idx = -1
        self._items: list[ClipboardItemWidget] = []
        self._keep = False
        self._ui()

    def _ui(self):
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setFixedSize(PANEL_WIDTH, PANEL_HEIGHT)
        self.setStyleSheet(
            "ClipboardPanel { background: %s; border: 1px solid %s; border-radius: 14px; }"
            % (C_BG, C_BORDER))

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

        lo = QVBoxLayout(self)
        lo.setContentsMargins(14, 14, 14, 10)
        lo.setSpacing(8)

        # 标题
        hdr = QHBoxLayout()
        ttl = QLabel("剪贴板记忆")
        ttl.setFont(QFont("Microsoft YaHei", 15, QFont.Bold))
        ttl.setStyleSheet("color: %s; border: none; background: transparent;" % C_TEXT)
        hdr.addWidget(ttl)
        hdr.addStretch()

        clr = QPushButton("清空全部")
        clr.setFont(QFont("Microsoft YaHei", 9))
        clr.setCursor(Qt.PointingHandCursor)
        clr.setFixedHeight(28)
        clr.setStyleSheet(
            "QPushButton { color: %s; background: transparent; border: 1px solid %s; "
            "border-radius: 6px; padding: 2px 12px; }"
            "QPushButton:hover { background: %s; color: white; }"
            % (C_DANGER, C_DANGER, C_DANGER))
        clr.clicked.connect(self._clear)
        hdr.addWidget(clr)
        lo.addLayout(hdr)

        # 搜索
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索剪贴板历史…")
        self.search.setFont(QFont("Microsoft YaHei", 11))
        self.search.setFixedHeight(38)
        self.search.setStyleSheet(
            "QLineEdit { background: white; border: 1px solid %s; border-radius: 10px; "
            "padding: 4px 14px; color: %s; }"
            "QLineEdit:focus { border: 2px solid %s; }"
            % (C_BORDER, C_TEXT, C_PRIMARY))
        self.search.textChanged.connect(lambda: self.refresh())
        lo.addWidget(self.search)

        # 筛选
        fr = QHBoxLayout()
        fr.setSpacing(8)
        self.ball = FilterButton("全部"); self.ball.setChecked(True)
        self.ball.clicked.connect(lambda: self._set_filter(None))
        self.btxt = FilterButton("文字")
        self.btxt.clicked.connect(lambda: self._set_filter(config.TYPE_TEXT))
        self.bimg = FilterButton("图片")
        self.bimg.clicked.connect(lambda: self._set_filter(config.TYPE_IMAGE))
        self.bfil = FilterButton("文件")
        self.bfil.clicked.connect(lambda: self._set_filter(config.TYPE_FILE))
        for b in (self.ball, self.btxt, self.bimg, self.bfil):
            fr.addWidget(b)
        fr.addStretch()
        lo.addLayout(fr)

        # 列表
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 5px; border-radius: 3px; }"
            "QScrollBar::handle:vertical { background: #BDBDBD; border-radius: 3px; min-height: 24px; }"
            "QScrollBar::handle:vertical:hover { background: %s; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            % C_PRIMARY)

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.list_lo = QVBoxLayout(self.container)
        self.list_lo.setContentsMargins(0, 0, 0, 0)
        self.list_lo.setSpacing(4)
        self.scroll.setWidget(self.container)
        lo.addWidget(self.scroll, 1)

        self.empty_lbl = QLabel("尚无剪贴板记录\n使用 Ctrl+C 复制内容即可自动保存")
        self.empty_lbl.setFont(QFont("Microsoft YaHei", 11))
        self.empty_lbl.setStyleSheet("color: %s; border: none; background: transparent;" % C_TEXT_SECONDARY)
        self.empty_lbl.setAlignment(Qt.AlignCenter)
        self.empty_lbl.setVisible(False)

        self.status_lbl = QLabel()
        self.status_lbl.setFont(QFont("Microsoft YaHei", 9))
        self.status_lbl.setStyleSheet("color: %s; border: none; background: transparent;" % C_TEXT_SECONDARY)
        self.status_lbl.setAlignment(Qt.AlignCenter)
        lo.addWidget(self.status_lbl)

    # ── 显示 ────────────────────────────────────────────

    def show_panel(self):
        try:
            self._show()
        except Exception as e:
            print("[面板] %s" % e)
            import traceback; traceback.print_exc()

    def _show(self):
        if self.isVisible():
            self.hide()
        self.refresh()
        cp = QCursor.pos()
        sc = QApplication.screenAt(cp) or QApplication.primaryScreen()
        g = sc.availableGeometry()
        self.move(g.right() - PANEL_WIDTH - 12, g.top() + 12)
        self.show(); self.raise_(); self.activateWindow()
        self.search.setFocus(); self.search.selectAll()

    def hide_panel(self):
        self.hide()

    # ── 刷新 ────────────────────────────────────────────

    def refresh(self):
        self._items.clear(); self._idx = -1

        while self.list_lo.count() > 0:
            it = self.list_lo.takeAt(0)
            w = it.widget()
            if w and w is not self.empty_lbl:
                w.deleteLater()

        q = self.search.text().strip()
        recs = self.db.get_all_records(search=q)
        if self._filter:
            recs = [r for r in recs if r.get("content_type") == self._filter]

        if not recs:
            self.empty_lbl.setVisible(True)
            self.list_lo.addWidget(self.empty_lbl)
        else:
            self.empty_lbl.setVisible(False)
            for r in recs:
                w = ClipboardItemWidget(r)
                w.clicked.connect(self._click)
                w.pin_toggled.connect(self._pin)
                w.delete_requested.connect(self._del)
                w.preview_requested.connect(self._preview)
                self._items.append(w)
                self.list_lo.addWidget(w)
        self.list_lo.addStretch()

        total = len(self.db.get_all_records())
        self.status_lbl.setText(
            "共 %d 条 · 显示 %d 条 · %d 天后自动清理"
            % (total, len(recs), config.RETENTION_DAYS))

    # ── 事件 ────────────────────────────────────────────

    def _click(self, r):    self.paste_record.emit(r)
    def _pin(self, rid):    self.db.toggle_pin(rid); self.refresh()
    def _del(self, rid):    self.db.delete_record(rid); self.refresh()

    def _preview(self, r):
        self._keep = True
        dlg = ImagePreviewDialog(r, self)
        dlg.paste_requested.connect(lambda x: self.paste_record.emit(x))
        dlg.exec_()
        self._keep = False

    def _set_filter(self, ft):
        self._filter = ft
        self.ball.setChecked(ft is None)
        self.btxt.setChecked(ft == config.TYPE_TEXT)
        self.bimg.setChecked(ft == config.TYPE_IMAGE)
        self.bfil.setChecked(ft == config.TYPE_FILE)
        self.refresh()

    def _clear(self):
        from PyQt5.QtWidgets import QMessageBox
        if QMessageBox.question(self, "确认", "清空所有剪贴板历史？",
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) == QMessageBox.Yes:
            self.db.clear_all(); self.refresh()

    # ── 键盘导航 ────────────────────────────────────────

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key_Escape:
            self.hide_panel()
        elif k in (Qt.Key_Return, Qt.Key_Enter):
            if 0 <= self._idx < len(self._items):
                self._click(self._items[self._idx].record)
        elif k == Qt.Key_Down:
            self._nav(1)
        elif k == Qt.Key_Up:
            self._nav(-1)
        elif k == Qt.Key_Delete:
            if 0 <= self._idx < len(self._items):
                self._del(self._items[self._idx].record["id"])
        elif k == Qt.Key_F and e.modifiers() == Qt.ControlModifier:
            self.search.setFocus(); self.search.selectAll()
        else:
            super().keyPressEvent(e)

    def _nav(self, d):
        if not self._items: return
        if 0 <= self._idx < len(self._items):
            self._items[self._idx].set_selected(False)
        self._idx += d
        self._idx = max(0, min(self._idx, len(self._items) - 1))
        w = self._items[self._idx]
        w.set_selected(True)
        self.scroll.ensureWidgetVisible(w)

    def changeEvent(self, e):
        if e.type() == QEvent.ActivationChange and not self.isActiveWindow() and not self._keep:
            if self.isVisible():
                self.hide()
        super().changeEvent(e)

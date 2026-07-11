"""
剪贴板记忆管理器 - 配置文件
Clipboard Memory Manager - Configuration
"""

# ── 存储 ────────────────────────────────────────────
MAX_HISTORY = 100               # 最多保存条数
RETENTION_DAYS = 7              # 保留天数（超过自动删除）
POLLING_INTERVAL_MS = 500       # 剪贴板轮询间隔（毫秒）
DOUBLE_PRESS_INTERVAL_MS = 500  # 双击 Ctrl+V 判定间隔（毫秒）

# ── 存储路径 ────────────────────────────────────────
STORAGE_DIR = "storage"         # 图片存储文件夹
DB_FILE = "clipboard.db"        # 数据库文件名

# ── UI 配色（淡绿色主题） ──────────────────────────
PRIMARY_BG = "#E8F5E9"          # 主背景淡绿
PRIMARY_DARK = "#C8E6C9"        # 深一级淡绿
ACCENT_COLOR = "#4CAF50"        # 强调绿
ACCENT_HOVER = "#388E3C"        # 悬停深绿
TEXT_PRIMARY = "#212121"        # 主文字色
TEXT_SECONDARY = "#757575"      # 次要文字色
WHITE = "#FFFFFF"               # 卡片背景白
BORDER_COLOR = "#A5D6A7"        # 边框绿
DANGER_COLOR = "#E53935"        # 删除按钮红
PIN_COLOR = "#FF9800"           # 置顶按钮橙

# ── 面板尺寸 ────────────────────────────────────────
PANEL_WIDTH = 420
PANEL_HEIGHT = 600
ITEM_MAX_HEIGHT = 80            # 每条记录最大高度
PREVIEW_MAX_CHARS = 60          # 文字预览最大字符数
IMAGE_THUMB_SIZE = 48           # 图片缩略图尺寸

# ── 内容类型 ────────────────────────────────────────
TYPE_TEXT = "text"
TYPE_IMAGE = "image"
TYPE_FILE = "file"

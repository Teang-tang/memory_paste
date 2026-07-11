# 📋 剪贴板记忆管理器

一个带**记忆功能**的 Windows 剪贴板增强工具。复制过的文字、图片、文件路径都会被自动记录，随时唤出面板重新使用。

## ✨ 功能

- 🧠 **自动记忆** — Ctrl+C 复制时自动保存文字、图片、文件路径
- ⚡ **永不丢失** — 最多保存 100 条，保留 7 天
- 🔍 **快速搜索** — 输入关键词实时筛选历史记录
- 📌 **置顶收藏** — 重要内容置顶，不会被自动清理
- 🖼 **图片预览** — 点击图片条目弹出大图预览
- 📁 **文件路径** — 复制文件/文件夹只存路径，不占额外空间
- 🎨 **简洁美观** — 淡绿色现代 UI，从屏幕右上角滑出
- 🚀 **开机自启** — 注册到 Windows 启动项，重启不丢失
- 💼 **单文件 exe** — 打包为独立程序，无需安装 Python

## 🎮 快捷键

| 按键 | 功能 |
|:--|:--|
| `Ctrl + C` | 复制内容并自动记入历史 |
| `Ctrl + V` | 正常系统粘贴（不受影响） |
| `Ctrl + Alt + V` | 弹出记忆面板，选择要粘贴的内容 |

## 📥 使用方式

### 方式一：直接运行 exe（推荐）

下载 `dist/ClipboardMemory.exe`，双击运行即可。任务栏右下角出现绿色图标表示启动成功。

> 首次运行需要**以管理员身份运行**（热键功能需要），exe 已内置 UAC 提权。

### 方式二：从源码运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行
python main.py

# 或者双击 run_silent.vbs（无命令行黑窗）
```

### 方式三：自行打包

```bash
python build_exe.py
# 输出 → dist/ClipboardMemory.exe
```

## 📂 项目结构

```
├── main.py               # 主程序入口（系统托盘 + 信号连接）
├── clipboard_panel.py    # 弹出面板 UI（搜索/筛选/预览/动画）
├── clipboard_monitor.py  # 剪贴板监听（轮询 → 自动记录）
├── hotkey_listener.py    # 全局快捷键监听
├── database.py           # SQLite 数据库（增删改查/过期清理）
├── config.py             # 配置文件（数量上限/配色/尺寸）
├── requirements.txt      # Python 依赖
├── build_exe.py          # PyInstaller 打包脚本
├── run_silent.vbs        # 静默启动脚本
└── dist/                 # 打包输出目录
    └── ClipboardMemory.exe
```

## 🛠 技术栈

- **Python 3.13**
- **PyQt5** — GUI 框架
- **keyboard** — 全局热键监听
- **pywin32** — Windows 剪贴板 API
- **Pillow** — 图片处理
- **PyInstaller** — 打包为 exe

## ⚠️ 注意事项

- 仅支持 **Windows 10/11 64位**
- 需要**管理员权限**运行（全局热键需要）
- 部分杀毒软件可能误报 PyInstaller 打包的 exe，请添加信任

## 📄 License

MIT

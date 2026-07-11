# 📋 剪贴板记忆管理器 (Memory Paste)

带**记忆功能**的 Windows 剪贴板增强工具。复制过的内容都会被自动保存，随时找回复用。

> **⚠️ 本仓库是源代码仓库。** 如果你只是想用这个软件，请直接跳到下面的 [📥 下载安装](#-下载安装) 部分，去 Releases 页面下载 exe 即可，无需安装 Python 或任何开发环境。

---

## ✨ 功能

- 🧠 **自动记忆** — Ctrl+C 复制时自动保存文字、图片、文件路径
- ⚡ **永不丢失** — 最多保存 100 条，保留 7 天
- 🔍 **快速搜索** — 输入关键词实时筛选历史记录
- 📌 **置顶收藏** — 重要内容置顶，不会被自动清理
- 🖼 **图片预览** — 点击图片条目弹出大图预览
- 📁 **文件路径** — 复制文件/文件夹只存路径，不占额外空间
- 🎨 **简洁美观** — 现代极简 UI，屏幕右上角弹出
- 🚀 **开机自启** — 自动注册启动项，重启电脑不丢失
- 💼 **单文件 exe** — 即下即用，无需安装任何依赖

---

## 📥 下载安装

> **推荐：直接下载 exe 运行，无需 Python 环境。**

### 从 GitHub Releases 下载（推荐）

1. 打开 [Releases 页面](https://github.com/Teang-tang/memory_paste/releases)
2. 找到最新版本（如 `v1.0`）
3. 下载 `ClipboardMemory.exe`
4. 右键 → **以管理员身份运行**
5. 任务栏右下角出现绿色图标 ✓ 启动成功

> 首次运行会自动注册开机自启。之后每次开机都会自动启动，不用再手动打开。

### 从源码运行（开发者）

```bash
# 1. 克隆仓库
git clone https://github.com/Teang-tang/memory_paste.git
cd memory_paste

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python main.py
```

---

## 🎮 快捷键

| 按键 | 功能 |
|:--|:--|
| `Ctrl + C` | 复制内容并自动记入历史 |
| `Ctrl + V` | 正常系统粘贴（完全不受影响） |
| `Ctrl + Alt + V` | 弹出记忆面板，选择历史内容粘贴 |

---

## 📖 使用场景

### 场景一：重复粘贴

经常需要反复粘贴同一段文字（如地址、邮箱、话术模板）？

> 复制一次 → 以后 `Ctrl+Alt+V` 选出来 → 再 `Ctrl+V` 粘贴。告别反复打字。

### 场景二：找回之前复制的内容

刚复制了一段重要文字，不小心又复制了别的东西把它覆盖了？

> `Ctrl+Alt+V` 打开面板，7 天内的复制记录全在，搜索关键词秒找回。

### 场景三：文件整理

需要把一个文件/文件夹复制到多个不同位置？

> 在资源管理器 `Ctrl+C` 复制文件 → 到目标文件夹 `Ctrl+Alt+V` 选中路径 → `Ctrl+V` 粘贴。不用反复回去找原文件。

### 场景四：截图收集

截图工具截图后（图片已在剪贴板），想保存到记忆里随时用？

> 截图后程序自动记录图片 → `Ctrl+Alt+V` 面板点图片可预览 → 复制到剪贴板即可粘贴到聊天/文档。

### 场景五：日常办公

编辑文档、写代码、做表格时频繁复制粘贴？

> 程序后台静默记录所有复制内容，需要历史记录时 `Ctrl+Alt+V` 即开即用，不打断工作流。

---

## 📂 项目结构

```
memory_paste/
├── main.py               # 主程序入口（系统托盘 + 信号连接）
├── clipboard_panel.py    # 弹出面板 UI（搜索/筛选/预览）
├── clipboard_monitor.py  # 剪贴板监听（轮询 → 自动记录）
├── hotkey_listener.py    # 全局快捷键监听
├── database.py           # SQLite 数据库（增删改查/过期清理）
├── config.py             # 配置文件（上限/配色/尺寸）
├── requirements.txt      # Python 依赖
├── build_exe.py          # PyInstaller 一键打包脚本
├── run_silent.vbs        # 静默启动（无命令行黑窗）
└── README.md
```

---

## 🛠 技术栈

| 技术 | 用途 |
|:--|:--|
| Python 3.13 | 主要语言 |
| PyQt5 | GUI 界面 |
| keyboard | 全局热键监听 |
| pywin32 | Windows 剪贴板 API |
| Pillow | 图片处理 |
| SQLite | 本地数据库 |
| PyInstaller | 打包为独立 exe |

---

## ⚠️ 注意事项

- 仅支持 **Windows 10/11 64 位**
- 需要**以管理员身份运行**（全局热键需要系统级权限）
- 杀毒软件可能误报 PyInstaller 打包的 exe，添加到信任即可
- 本仓库只包含**源代码**，exe 请在 [Releases](https://github.com/Teang-tang/memory_paste/releases) 下载

---

## 📄 License

MIT © Teang-tang

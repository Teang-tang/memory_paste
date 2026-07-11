"""
剪贴板记忆管理器 — 一键打包脚本
运行：python build_exe.py
输出：dist\ClipboardMemory.exe（单个文件，双击即用）
"""

import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("  剪贴板记忆管理器 — 打包中...")
print("=" * 50)

# 先确保 PyInstaller 已安装
try:
    import PyInstaller
except ImportError:
    print("正在安装 PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"],
                   check=True)
    print("PyInstaller 安装完成")

# PyInstaller 命令
cmd = [
    sys.executable, "-m", "PyInstaller",

    # 输出设置
    "--onefile",                       # 单个 exe 文件
    "--windowed",                      # 无命令行黑窗
    "--name", "ClipboardMemory",       # 程序名
    "--uac-admin",                     # ★ 启动时自动请求管理员权限
    "--icon", "NONE",                  # 用默认图标（我们有代码生成的托盘图标）

    # 清理旧文件
    "--clean",

    # 隐式导入（动态 import 的库需要手动声明）
    "--hidden-import", "keyboard",
    "--hidden-import", "win32clipboard",
    "--hidden-import", "win32con",
    "--hidden-import", "PIL",
    "--hidden-import", "PIL.Image",
    "--hidden-import", "PIL.ImageGrab",
    "--hidden-import", "PyQt5",
    "--hidden-import", "PyQt5.QtCore",
    "--hidden-import", "PyQt5.QtGui",
    "--hidden-import", "PyQt5.QtWidgets",
    "--hidden-import", "config",
    "--hidden-import", "database",
    "--hidden-import", "clipboard_monitor",
    "--hidden-import", "hotkey_listener",
    "--hidden-import", "clipboard_panel",

    # 入口文件
    "main.py",
]

result = subprocess.run(cmd, capture_output=False)

if result.returncode == 0:
    exe_path = os.path.abspath("dist/ClipboardMemory.exe")
    print()
    print("=" * 50)
    print("  [OK] 打包成功!")
    print(f"  文件位置：{exe_path}")
    print("=" * 50)
    print()
    print("  使用方法：")
    print(f"  1. 双击运行 → 任务栏出现绿色图标")
    print(f"  2. 程序自动注册开机自启")
    print(f"  3. 也可手动把快捷方式放到：")
    print(f"     Win+R → shell:startup → 粘贴快捷方式")
else:
    print()
    print("  [FAIL] 打包失败，请查看上方错误信息")
    sys.exit(1)

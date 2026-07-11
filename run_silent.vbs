' 剪贴板记忆管理器 - 静默启动脚本
' 双击此文件启动程序（不会弹出命令行黑窗）
' 也可以把此文件的快捷方式放到 Windows 启动文件夹中

Set objShell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
objShell.Run "pythonw.exe """ & scriptDir & "\main.py""", 0, False

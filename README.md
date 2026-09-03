# DropSpace (Omarchy Shell Plugin)

**DropSpace** 是专为 Omarchy / Hyprland 设计的可视化窗口工作区拖放插件。

类似于 macOS Mission Control 或 Windows 11 Snap 体验，在拖拽窗口时唤出屏幕顶部的各个工作区卡片，将窗口拖拽至目标工作区后释放，即可自动将窗口移入该工作区并随之切换。

## ✨ 特性

- **毫秒级响应**：基于 Omarchy Shell (Quickshell) 原生 Overlay 渲染，支持热加载。
- **无感穿透（Click-through）**：使用 `mask: Region {}` 保证拖拽手势完全不受遮挡，丝滑流畅。
- **原生主题融合**：自适应当前 Omarchy 主题背景、边框、圆角与字体规范。
- **直观状态指示**：高亮当前工作区，并显示每个工作区中容纳的窗口数量。
- **双重操作模式**：
  1. **拖拽落位**：拖拽窗口时按住 `ALT`，拖到目标卡片上方松开按键落位。
  2. **快速切换**：通过快捷键 `SUPER + D` 手动开关工作区栏。

## 🎮 使用方法

1. 用 `SUPER + 鼠标左键` 拖动任意应用窗口。
2. 拖动过程中，左手按下并**按住 `ALT` 键**（或 `SUPER + ALT`）。
3. 屏幕顶部滑出工作区 1 ~ 5 卡片栏。
4. 将窗口移到目标工作区卡片（如 Workspace 2）上方，**松开 `ALT` 键**。
5. 窗口自动移入目标工作区，桌面自动跟随切换。
6. **取消操作**：若不想移动，只需将鼠标移出顶部区域并松开 `ALT` 即可。

## 📁 目录结构

```
dropspace/
├── manifest.json            # Omarchy 插件元数据清单
├── WorkspaceDrop.qml        # Quickshell 顶部卡片栏界面实现
├── bin/
│   ├── drop-handler.py      # 落位坐标计算与 Hyprland 调度核心脚本
│   └── drop-handler.sh      # 可执行包装脚本
└── README.md
```

## 🛠️ IPC 控制

你也可以在终端或脚本中直接控制 DropSpace：

```bash
# 唤出工作区拖放栏
omarchy-shell dropspace show

# 隐藏工作区拖放栏
omarchy-shell dropspace hide

# 切换显示/隐藏
omarchy-shell dropspace toggle
```

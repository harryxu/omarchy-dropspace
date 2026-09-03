# DropSpace (Omarchy Shell Plugin)

**DropSpace** 是专为 Omarchy / Hyprland 设计的可视化窗口工作区拖放插件。

类似于 macOS Mission Control 或 Windows 11 Snap 体验：
在拖拽窗口至工作区卡片后松开鼠标，即可将窗口送入目标工作区并切换桌面。

---

## ✨ 核心亮点

- **两种灵活模式**：
  - **默认纯净模式（零后台进程）**：随时按下 `SUPER + D` 打开工作区栏，拖拽窗口释放落位。系统中 0 额外进程常驻！
  - **推顶感应模式（自适应休眠）**：可配置开启 `edge-watcher`，拖动窗口往屏幕顶部一推自动滑出卡片。
- **自适应智能休眠（Adaptive Sleep）**：
  - 光标在屏幕日常工作区域（中下部 80%+ 面积）时，守护进程**进入深度休眠**（采样频率 1 秒一次），CPU 占用真正为 **0.0000%**；
  - 只有靠近顶部边缘时才毫秒级唤醒；离开后立即恢复深度睡眠。
- **开箱即用的 CLI 管理工具**：
  - `dropspace status` 查看运行与配置状态
  - `dropspace edge-watcher enable` 一键开启推顶感应
  - `dropspace edge-watcher disable` 一键关闭推顶感应
- **零输入阻碍（Click-through）**：使用 `mask: Region {}` 保证拖拽过程丝滑流畅。

---

## 🎮 使用方法

### 默认模式：快捷键常开模式（系统 100% 纯净）
1. 随时按下 `SUPER + D`，屏幕顶部滑出工作区 1 ~ 5 卡片；
2. 用 `SUPER + 鼠标左键` 将目标窗口拖动到目标工作区卡片（如 Workspace 2）；
3. **松开鼠标左键**，窗口自动进入该工作区并跟随跳转，卡片栏自动收起！

### 可选模式：推顶自动滑出模式
如果您希望体验“不按键盘、窗口往屏幕顶部一推自动滑出卡片”的体验：
```bash
dropspace edge-watcher enable
```
开启后：
1. 用 `SUPER + 鼠标左键` 拖动窗口并推到屏幕顶部中央；
2. 工作区卡片自动感应滑下；
3. 移到目标卡片松开鼠标左键落位。

随时关闭恢复纯净模式：
```bash
dropspace edge-watcher disable
```

---

## ⚙️ 配置文件

配置文件位于 `~/.config/omarchy/dropspace.json`：
```json
{
  "edge_watcher": false,
  "top_edge_threshold": 12,
  "cancel_threshold": 180
}
```
- `edge_watcher`: `false`（默认关闭，0 进程）/ `true`（开启自适应推顶感应）。
- `top_edge_threshold`: 触发顶边缘距离（像素，默认 12）。
- `cancel_threshold`: 拉回取消判定距离（像素，默认 180）。

---

## 📁 项目结构

```
dropspace/
├── manifest.json                # Omarchy 插件元数据
├── WorkspaceDrop.qml            # Quickshell 顶部卡片栏 UI
├── config.example.json          # 默认配置模板
├── bin/
│   ├── dropspace                # 用户 CLI 控制工具 (已软链至 ~/.local/bin/dropspace)
│   ├── dropspace-autostart.sh   # 开机自检自启脚本 (仅配置开启时启动)
│   ├── edge-watcher.py          # 自适应节流边缘守护服务
│   ├── drop-handler.py          # 落位坐标计算与 Hyprland Lua 调度核心
│   └── drop-handler.sh          # 落位执行包装器
└── README.md
```

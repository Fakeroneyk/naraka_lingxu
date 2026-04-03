# 征神之路 · 灵虚界自动化战斗程序

> 自动化刷灵虚界5关流程：准备关（冰暴分支+灵诀选择）→ 3关小怪 → 商店跳过 → Boss关入口

---

## 目录

- [环境要求](#环境要求)
- [安装步骤](#安装步骤)
- [资源准备](#资源准备)
- [配置说明](#配置说明)
- [运行程序](#运行程序)
- [操作热键](#操作热键)
- [目录结构](#目录结构)
- [常见问题](#常见问题)

---

## 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | macOS（已适配 AppleScript 窗口定位） |
| Python | >= 3.9 |
| 游戏模式 | **窗口化** 运行，分辨率 1920×1080 |
| 游戏英雄 | 济沧海 |
| 武器配置 | 近战位=双刀（按键1），远程位=火炮（按键2），F技能=火球 |

---

## 安装步骤

```bash
# 1. 进入项目目录
cd naraka_lingxu

# 2. 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
```

### 依赖清单

| 包名 | 用途 |
|------|------|
| opencv-python | 截图模板匹配 |
| ultralytics | YOLOv8 目标检测（传送门/占点圈） |
| pyautogui | 键鼠模拟 |
| mss | 高性能屏幕截图 |
| numpy | 图像处理 |
| pynput | 全局热键监听 |
| PyYAML | 配置文件读取 |
| loguru | 日志 |

---

## 资源准备

运行程序前，需要准备以下截图模板和模型文件。

### 必需截图模板

将以下截图文件放入对应目录：

| 文件路径 | 说明 | 获取方式 |
|----------|------|---------|
| `assets/battleStart.png` | 战斗开始触发图：元素灵诀分支选择界面 | 游戏内截图 |
| `assets/battleEnd.png` | 战斗结束触发图：进入第5关时的UI | 游戏内截图 |
| `assets/ui/ice_branch.png` | 冰暴分支选择按钮 | 游戏内截图 |
| `assets/ui/capture_point_ui.png` | 占点模式UI标识 | 游戏内截图 |
| `assets/ui/spirit_templates/*.png` | 灵诀选择弹窗模板（至少1张） | 游戏内截图 |

### 截图方法

1. 以窗口化1920×1080运行游戏
2. 进入灵虚界到达对应UI时，使用系统截图工具截取**游戏窗口内容**
3. 裁剪出UI元素的关键区域（不要包含过多背景），保存为 PNG 格式

### YOLO 模型文件

| 文件路径 | 说明 |
|----------|------|
| `models/naraka_v1/weights/best.pt` | YOLOv8n 检测模型（4分类：紫/金/红传送门 + 占点圈） |

> 模型训练方法详见 [YOLO训练操作手册](docs/yolo_training_guide.md)

---

## 配置说明

所有配置在 `config.yaml` 中，关键配置项如下：

### 必须修改的配置

```yaml
game:
  window_title: "征神之路"       # 改为你的游戏窗口精确标题

spirit_select:
  pick5_click: [384, 594]       # 5选1时最左卡片的窗口坐标（需实测）
  pick3_click: [480, 594]       # 3选1时最左卡片的窗口坐标（需实测）
```

### 坐标实测方法

1. 窗口化1920×1080运行游戏
2. 进入灵虚界到达灵诀选择界面
3. 使用 Python 脚本获取鼠标位置：

```python
import pyautogui
import time
time.sleep(3)  # 3秒内把鼠标移到目标位置
print(pyautogui.position())
```

4. 计算窗口相对坐标：`相对坐标 = 鼠标位置 - 窗口左上角位置`

### 可选调优配置

```yaml
timing:
  screenshot_interval: 1.0        # 截图频率（默认每秒1次）
  combat_timeout: 120             # 单关战斗超时（秒）
  pre_portal_armor_wait: 5.0      # 进传送门前恢复护甲等待时长

threshold:
  template_match: 0.85            # 模板匹配置信度（降低=更宽松）
  yolo_confidence: 0.6            # YOLO检测置信度

exploration:
  rotate_step_deg: 45             # 搜敌时每次旋转角度
  walk_duration: 3.0              # 搜敌时向前行走时长
```

---

## 运行程序

```bash
cd naraka_lingxu
python main.py
```

### 运行流程

1. 程序启动后进入 **IDLE** 状态，持续截图匹配 `battleStart.png`
2. 手动操作游戏进入灵虚界，直到看到元素分支选择UI
3. 程序检测到 `battleStart.png` 后自动接管：
   - 选择冰暴分支
   - 完成3次灵诀选择
   - 自动寻找传送门并进入各关卡
   - 自动战斗/占点
   - 通关后选择灵诀奖励
   - 跳过商店
   - 进入第5关 Boss 区域触发结束钩子
4. 一轮结束后回到 IDLE 状态，等待下一轮触发

### 日志查看

- 控制台实时输出 INFO 级别日志
- 文件日志保存在 `logs/naraka_YYYY-MM-DD.log`（含 DEBUG 级别）

---

## 操作热键

| 热键 | 功能 |
|------|------|
| `F10` | 暂停/恢复程序 |
| `F11` | 停止程序并退出 |
| `Ctrl+C` | 强制中断退出 |

> 注意：pyautogui 的安全机制——将鼠标移到屏幕左上角(0,0)会触发 `FailSafeException` 紧急停止。

---

## 目录结构

```
naraka_lingxu/
├── main.py                    # 主入口
├── config.yaml                # 全局配置
├── requirements.txt           # 依赖清单
├── assets/                    # 截图模板资源
│   ├── battleStart.png
│   ├── battleEnd.png
│   ├── ui/
│   │   ├── ice_branch.png
│   │   ├── capture_point_ui.png
│   │   └── spirit_templates/
│   └── portals/               # YOLO训练用截图（可选）
├── core/                      # 核心模块
│   ├── screen.py              # 屏幕捕获与模板匹配
│   ├── input.py               # 键鼠输入模拟
│   ├── hooks.py               # 战斗钩子系统
│   └── state_machine.py       # 主状态机
├── modules/                   # 功能模块
│   ├── vision.py              # YOLO目标检测
│   ├── combat.py              # 战斗逻辑
│   ├── navigation.py          # 传送门导航
│   ├── ui_handler.py          # UI交互
│   └── capture_point.py       # 占点模式
├── models/                    # YOLO模型权重
│   └── naraka_v1/weights/best.pt
├── utils/                     # 工具
│   ├── logger.py              # 日志配置
│   └── window.py              # 游戏窗口管理
├── tests/                     # 测试代码
├── logs/                      # 运行日志（自动生成）
└── docs/                      # 文档
```

---

## 常见问题

### Q: 程序一直在 IDLE 状态不触发？
**A:** 检查 `battleStart.png` 是否正确截取，以及 `threshold.template_match` 是否过高。可尝试降低到 0.75。

### Q: 传送门找不到？
**A:** 确保 YOLO 模型已训练并放入 `models/naraka_v1/weights/best.pt`。查看日志中的 YOLO 检测结果。

### Q: 灵诀弹窗没有被识别？
**A:** 检查 `assets/ui/spirit_templates/` 目录下是否有至少1张灵诀弹窗截图。

### Q: 坐标点击偏移？
**A:** 确保游戏以窗口化1920×1080运行，并使用坐标实测方法重新校准 `spirit_select` 配置。

### Q: macOS 权限问题？
**A:** 程序需要以下 macOS 权限：
- **辅助功能**（Accessibility）：用于 pyautogui 模拟键鼠
- **屏幕录制**（Screen Recording）：用于 mss 截图

在 系统偏好设置 > 安全性与隐私 > 隐私 中授权终端/VS Code。

### Q: pyautogui 紧急停止了？
**A:** 鼠标碰到了屏幕左上角触发了 FAILSAFE。这是安全保护机制，避免脚本失控。
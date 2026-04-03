# AGENTS.md - 灵虚界自动化编码指南

## 项目概述

这是一个用于永劫无间·征神之路·灵虚界的 Python 自动化工具。通过屏幕截图、YOLO 检测、OCR 识别和输入模拟，实现 15 层地牢的循环刷图。

## 构建/运行命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行主自动化
python main.py

# 手动战斗模式（仅自动UI，战斗由玩家操作）
python main.py --manual

# 校准工具（调整灵敏度、HSV值、ROI）
python main.py --calibrate

# 实时预览检测效果
python main.py --preview

# 截图采集模板
python main.py --screenshot

# 查看历史统计
python main.py --stats
```

### 运行单个测试
本项目目前**没有测试框架**或单元测试。如果要添加测试，使用 pytest：
```bash
pytest tests/                    # 运行所有测试
pytest tests/test_file.py        # 运行单个测试文件
pytest tests/test_file.py::test_function  # 运行单个测试函数
```

## 代码风格指南

### 基本原则
- 使用 **Python 3.10+** 编写（使用 `|` 联合类型）
- 保持函数简洁短小（最好少于 100 行）
- 添加说明函数用途和参数的 docstrings
- 用户面向的文档使用中文注释，内部逻辑使用英文

### 第一性原理

**什么是从第一性原理出发思考？**

不基于类比或经验，而是从最基本的事实/规律出发构建解决方案。在本项目中体现为：

| 思维模式 | 错误做法 | 正确做法（第一性原理） |
|----------|----------|------------------------|
| 检测敌人 | "用最火的YOLO模型" | 从"敌人有哪些可识别特征"出发：血条颜色/YOLO/形状 |
| 瞄准 | "用现成的瞄准库" | 从"鼠标移动=像素位移×灵敏度"出发实现 |
| 状态管理 | "用复杂的状态机框架" | 从"有哪些游戏阶段"出发：大厅→战斗→灵诀→传送门 |
| 异常处理 | "到处 try/except" | 从"哪些环节会失败"出发：YOLO加载失败→血条兜底 |
| 配置 | "写死数值" | 从"哪些参数需要调优"出发：全部放入 config.yaml |

**核心原则：**
- 问"根本问题是什么"，而不是"别人怎么做"
- 每个模块只做一件事，且目的明确
- 先解决 80% 的基础场景，再考虑边缘情况
- 用最简单的方式实现，复杂是最后的手段

### 命名规范
| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | PascalCase | `CombatEngine`、`EnemyDetector` |
| 函数/变量 | snake_case | `def detect_enemies()`、`capture_fps` |
| 常量 | SCREAMING_SNAKE | `STATE_DEBOUNCE = 3` |
| 私有方法 | 下划线前缀 | `def _load_model(self)` |
| 数据类 | PascalCase | `@dataclass class DetectedEnemy` |

### 导入顺序
```python
# 标准库优先
import sys, os, time
from pathlib import Path
from typing import List, Optional

# 第三方库
import cv2
import numpy as np
from loguru import logger
from core.config import Config

# 本地模块（包内使用显式相对导入）
from detector.enemy_detector import EnemyDetector
from strategy.aim_controller import AimController
```

### 类型注解
始终为函数签名添加类型注解：
```python
def detect(self, frame: np.ndarray) -> List[DetectedEnemy]:
def get(self, key: str, default: Any = None) -> Any:
def setup_logger(log_level: str = "INFO") -> None:
```

### 数据类
使用 `@dataclass` 封装简单的数据容器：
```python
from dataclasses import dataclass, field

@dataclass
class DetectedEnemy:
    center_x: int
    center_y: int
    width: int
    height: int
    enemy_type: EnemyType
    confidence: float
    distance_to_center: float = field(default=0.0, repr=False)
```

### 枚举
使用 `Enum` 或 `auto()` 定义状态：
```python
from enum import Enum, auto

class CombatState(Enum):
    PATROL = auto()
    AIMING = auto()
    FIRING = auto()
    BOSS_BURST = auto()
```

### 异常处理
- 尽量少用 `try/except`，优先使用"请求宽恕而非请求许可"（EAFP）模式
- 记录错误时附带上下文：`logger.error(f"加载模型失败: {e}")`
- 主循环中需要堆栈跟踪的异常使用 `exc_info=True`
- 优雅降级：记录警告但继续执行（例如 YOLO 不可用时使用备用检测）

### 日志记录
- 使用 `loguru` 日志（导入为 `logger`）
- 日志级别：DEBUG < INFO < WARNING < ERROR
- 消息中包含上下文：`logger.info(f"进入第{stage_num}层")`
- 避免在紧密循环中过度记录（改为每 N 帧记录一次）

### 配置管理
- 所有可配置值放在 `config.yaml` 中
- 代码中使用 `Config` 类（点号访问嵌套配置）：
  ```python
  config = load_config()
  fps = config.screen.capture_fps
  sensitivity = config.aim.sensitivity_x
  ```
- 加载时验证配置（见 `core/config.py`）

### 项目结构
```
naraka_lingxu/
├── main.py                 # 入口文件
├── config.yaml             # 配置文件
├── core/
│   ├── config.py          # 配置加载
│   ├── logger.py          # 日志设置
│   ├── states.py          # 枚举定义
│   ├── combat_engine.py   # 战斗逻辑
│   └── game_flow.py       # 游戏流程控制
├── detector/              # 检测模块
│   ├── enemy_detector.py # YOLO + 血条检测
│   ├── ui_detector.py    # 模板匹配
│   └── ...
├── strategy/              # 游戏策略
│   ├── aim_controller.py
│   ├── fire_cannon.py
│   └── ...
├── capture/              # 屏幕截图
├── input/                # 键盘/鼠标输入
└── utils/                # 工具函数
```

### 代码模式

**状态机**：使用防抖处理状态转换：
```python
STATE_DEBOUNCE = 3

def _set_state(self, s: CombatState):
    if s == self.state:
        self._state_frames += 1; return
    if self._state_frames < self.STATE_DEBOUNCE: return
    self.state = s; self._state_frames = 0
```

**降级模式**：主方法失败时提供备选方案：
```python
def detect(self, frame):
    if self.yolo.is_available:
        enemies = self.yolo.detect(frame)
    if not enemies:
        enemies = self.hp_bar.detect(frame)  # 备用方案
    return enemies
```

**懒加载**：按需加载重资源：
```python
def _load_model(self):
    if self._load_attempted: return
    self._load_attempted = True
    # 实际加载逻辑...
```

### UI/屏幕坐标
- 所有坐标使用**游戏窗口像素**（非屏幕坐标）
- 使用 `ScreenCapture` 处理窗口偏移
- 鼠标坐标必须用 `window_offset` 调整

### 常见问题避免
- 紧密循环中不要使用 `time.sleep()`，改用帧间隔计时
- 不要阻塞主循环，tick() 保持在 20fps 下少于 50ms
- 退出/停止时不要忘记释放按键
- 不要硬编码数值，放入 config.yaml

### 调试方法
- 开启调试窗口：在 config.yaml 中设置 `debug.show_detection: true`
- 查看日志：`logs/lingxu_YYYY-MM-DD.log`
- 使用 `--preview` 进行实时检测可视化
- 使用 `--calibrate` 调整灵敏度/HSV 值

## 热键（运行时）
| 按键 | 功能 |
|------|------|
| F8 | 切换手动/自动战斗 |
| F9 | 暂停/恢复 |
| F10 | 退出 |
| Ctrl+C | 强制退出 |

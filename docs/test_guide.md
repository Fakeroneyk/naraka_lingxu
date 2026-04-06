# 灵虚界自动化程序 · 测试流程说明文档

> 本文档描述从单模块单点测试到全流程集成测试的完整测试策略与执行步骤。

---

## 目录

- [测试环境准备](#测试环境准备)
- [单点测试说明](#单点测试说明)
- [集成测试说明](#集成测试说明)
- [全流程端到端测试](#全流程端到端测试)
- [测试通过标准](#测试通过标准)
- [问题排查指南](#问题排查指南)

---

## 测试环境准备

```bash
cd naraka_lingxu
pip install -r requirements.txt
pip install pytest pytest-mock          # 测试框架
```

运行所有单点测试：

```bash
cd naraka_lingxu
python -m pytest tests/ -v
```

运行指定测试文件：

```bash
python -m pytest tests/test_hooks.py -v
python -m pytest tests/test_screen.py -v
```

---

## 单点测试说明

各测试文件对应的模块和测试点如下。

### tests/test_hooks.py → [`core/hooks.py`](../core/hooks.py)

| 测试用例 | 测试点 |
|---------|-------|
| `test_register_start_callback` | 注册战斗开始钩子后回调列表长度为1 |
| `test_register_end_callback` | 注册战斗结束钩子后回调列表长度为1 |
| `test_trigger_start_calls_all` | trigger_start 调用所有已注册回调 |
| `test_trigger_end_calls_all` | trigger_end 调用所有已注册回调 |
| `test_decorator_usage` | 装饰器用法正常注册 |
| `test_callback_exception_isolated` | 某回调抛异常不影响其他回调执行 |

运行命令：
```bash
python -m pytest tests/test_hooks.py -v
```

---

### tests/test_screen.py → [`core/screen.py`](../core/screen.py)

| 测试用例 | 测试点 |
|---------|-------|
| `test_find_template_success` | 模板在画面中存在时返回正确坐标 |
| `test_find_template_not_found` | 模板不存在时返回 None |
| `test_find_template_missing_file` | 模板文件不存在时返回 None 且打印警告 |
| `test_find_any_template_first_match` | 列表中第一个匹配成功时返回 |
| `test_find_any_template_no_match` | 列表全部不匹配时返回 None |
| `test_template_cache` | 同路径模板第二次不重复读磁盘 |
| `test_scale_to_relative` | 像素坐标正确缩放为1920x1080相对坐标 |

运行命令：
```bash
python -m pytest tests/test_screen.py -v
```

**注意**：该测试使用 Mock 替代真实截图，无需游戏窗口。

---

### tests/test_input.py → [`core/input.py`](../core/input.py)

| 测试用例 | 测试点 |
|---------|-------|
| `test_press_key` | press_key 调用 pyautogui.press |
| `test_hold_key` | hold_key 调用 keyDown/keyUp 并等待正确时长 |
| `test_click_relative_to_absolute` | click 正确将相对坐标转换为绝对坐标 |
| `test_switch_melee` | switch_melee 调用按键 "1" |
| `test_switch_ranged` | switch_ranged 调用按键 "2" |
| `test_sprint_forward` | sprint_forward 同时按下 W 和 Shift |
| `test_pre_portal_routine` | pre_portal_routine 按序执行: 5→等待→E |
| `test_attack_combo` | attack_combo 连击指定次数 |

运行命令：
```bash
python -m pytest tests/test_input.py -v
```

**注意**：该测试完全 Mock pyautogui，不会发出真实键鼠操作。

---

### tests/test_vision.py → [`modules/vision.py`](../modules/vision.py)

| 测试用例 | 测试点 |
|---------|-------|
| `test_load_model_missing_file` | 模型文件不存在时 load() 返回 False |
| `test_detect_portals_purple` | 模拟YOLO返回，detect_portals 过滤出紫色传送门 |
| `test_detect_portals_empty` | YOLO无结果时返回空列表 |
| `test_detect_capture_zone` | detect_capture_zone 返回最高置信度结果 |
| `test_portal_screen_position_left` | 传送门在画面左侧返回 "left" |
| `test_portal_screen_position_center` | 传送门居中返回 "center" |
| `test_portal_screen_position_right` | 传送门偏右返回 "right" |
| `test_is_portal_close_true` | bbox面积超过阈值时返回 True |
| `test_is_portal_close_false` | bbox面积不足阈值时返回 False |

运行命令：
```bash
python -m pytest tests/test_vision.py -v
```

---

### tests/test_ui_handler.py → [`modules/ui_handler.py`](../modules/ui_handler.py)

| 测试用例 | 测试点 |
|---------|-------|
| `test_load_spirit_templates_empty_dir` | 模板目录为空时返回空列表 |
| `test_detect_spirit_popup_found` | 模板列表有匹配时返回 True |
| `test_detect_spirit_popup_not_found` | 模板列表无匹配时返回 False |
| `test_click_leftmost_card_5pick` | 5选1时点击 pick5_click 坐标 |
| `test_click_leftmost_card_3pick` | 3选1时点击 pick3_click 坐标 |
| `test_select_ice_branch_template_match` | 模板匹配冰暴分支成功时触发点击 |
| `test_select_spirit_reward_success` | 等待弹窗出现后完成选择 |

运行命令：
```bash
python -m pytest tests/test_ui_handler.py -v
```

---

### tests/test_state_machine.py → [`core/state_machine.py`](../core/state_machine.py)

| 测试用例 | 测试点 |
|---------|-------|
| `test_stage_manager_advance` | advance() 使 stage +1 |
| `test_stage_manager_reset` | reset() 使 stage = 0 |
| `test_stage_manager_portal_type_purple` | stage=0,1,2 时返回 "purple" |
| `test_stage_manager_portal_type_gold` | stage=3 时返回 "gold" |
| `test_stage_manager_portal_type_red` | stage=4 时返回 "red" |
| `test_idle_triggers_start_on_match` | IDLE 状态匹配到 battleStart.png 触发 trigger_start |
| `test_state_transition_idle_to_preparation` | 匹配后状态变为 PREPARATION |
| `test_boss_entry_triggers_end` | BOSS_ENTRY 匹配 battleEnd.png 后触发 trigger_end |
| `test_boss_entry_resets_to_idle` | BOSS_ENTRY 完成后状态回到 IDLE |

运行命令：
```bash
python -m pytest tests/test_state_machine.py -v
```

---

## 集成测试说明

集成测试在不启动游戏的情况下，使用预先录制的截图序列验证各模块协作。

### 测试前准备

在 `tests/fixtures/` 目录放置以下测试截图（从游戏中截取）：

```
tests/fixtures/
├── battle_start_screen.png     # 元素分支选择界面截图
├── battle_end_screen.png       # 第5关进入时截图
├── spirit_popup_screen.png     # 灵诀弹窗截图
├── portal_purple_screen.png    # 含紫色传送门的游戏画面截图
├── portal_gold_screen.png      # 含金色传送门的游戏画面截图
└── portal_red_screen.png       # 含红色传送门的游戏画面截图
```

### 运行集成测试

```bash
python -m pytest tests/test_integration.py -v
```

### 集成测试用例说明

| 测试用例 | 描述 |
|---------|-----|
| `test_battle_start_detection` | 加载 battle_start_screen.png，验证模板匹配触发 trigger_start |
| `test_spirit_popup_detection` | 加载 spirit_popup_screen.png，验证 ui_handler 检测到弹窗 |
| `test_portal_purple_detection` | 加载 portal_purple_screen.png，验证 YOLO 检测到紫色传送门 |
| `test_preparation_phase_flow` | 模拟准备关UI序列，验证 run_preparation_phase 完整流程 |

---

## 全流程端到端测试

> ⚠️ 全流程测试需要游戏运行中。建议先完成所有单点测试后再进行。

### 阶段一：各操作验证（需游戏运行）

**目的**：验证键鼠操作实际生效。

执行步骤：

1. 启动游戏，窗口化1920×1080，进入主界面
2. 运行以下测试脚本，逐步验证每个操作：

```bash
# 测试1: 验证窗口定位
python -c "
from utils.window import GameWindow
w = GameWindow('Naraka')
ok = w.locate()
print('窗口定位:', '成功' if ok else '失败', w.region)
"

# 测试2: 验证截图
python -c "
import cv2
from utils.window import GameWindow
from core.screen import ScreenCapture
w = GameWindow('征神之路')
w.locate()
sc = ScreenCapture(w)
frame = sc.capture()
cv2.imwrite('test_capture.png', frame)
print('截图已保存到 test_capture.png（项目目录下），形状:', frame.shape)
"

# 测试3: 验证按键（请在游戏中打开聊天框后运行）
python -c "
import time
from utils.window import GameWindow
from core.input import GameInput
import yaml
cfg = yaml.safe_load(open('config.yaml'))
w = GameWindow(cfg['game']['window_title'])
w.locate()
gi = GameInput(w, cfg['keys'])
time.sleep(2)
gi.press_key('1')
print('已按下1键')
"
```

### 阶段二：UI识别验证（需进入灵虚界准备关）

**目的**：验证截图模板和坐标配置是否正确。

执行步骤：

1. 进入灵虚界，停留在元素分支选择界面
2. 运行：

```bash
python -c "
from utils.window import GameWindow
from core.screen import ScreenCapture
import yaml
cfg = yaml.safe_load(open('config.yaml'))
w = GameWindow(cfg['game']['window_title'])
w.locate()
sc = ScreenCapture(w)
pos = sc.find_template(cfg['assets']['battle_start'])
print('battleStart.png 匹配结果:', pos)
"
```

预期：输出非 None 的坐标值。

3. 到达灵诀选择界面后，验证模板列表匹配：

```bash
python -c "
from utils.window import GameWindow
from core.screen import ScreenCapture
from modules.ui_handler import UIHandler
from core.input import GameInput
import yaml
cfg = yaml.safe_load(open('config.yaml'))
w = GameWindow(cfg['game']['window_title'])
w.locate()
sc = ScreenCapture(w)
gi = GameInput(w, cfg['keys'])
ui = UIHandler(sc, gi, cfg)
result = ui.detect_spirit_popup()
print('灵诀弹窗检测:', '成功' if result else '失败（检查spirit_templates）')
"
```

### 阶段三：传送门检测验证（需进入具体关卡）

**目的**：验证 YOLO 模型能正确检测传送门。

执行步骤：

1. 进入灵虚界第1关，找到紫色传送门并站在附近
2. 运行：

```bash
python -c "
from utils.window import GameWindow
from core.screen import ScreenCapture
from modules.vision import ObjectDetector
import yaml, cv2
cfg = yaml.safe_load(open('config.yaml'))
w = GameWindow(cfg['game']['window_title'])
w.locate()
sc = ScreenCapture(w)
det = ObjectDetector(cfg['models']['detector'], cfg['threshold']['yolo_confidence'])
frame = sc.capture()
portals = det.detect_portals(frame, 'purple')
print(f'紫色传送门检测: {len(portals)} 个')
if portals:
    print(f'  最佳: 中心={portals[0].center} 置信度={portals[0].confidence:.2f}')
# 保存标注结果图
for p in portals:
    x1,y1,x2,y2 = p.bbox
    cv2.rectangle(frame, (x1,y1), (x2,y2), (128,0,255), 2)
cv2.imwrite('portal_detection.png', frame)
print('检测结果图已保存到 portal_detection.png（项目目录下）')
"
```

### 阶段四：完整5关流程测试

**目的**：验证完整的状态机流程。

执行步骤：

1. 进入游戏，手动进入灵虚界入口附近（不要开始）
2. 启动主程序：`python main.py`
3. 手动触发进入灵虚界（让程序看到 battleStart.png）
4. 观察程序日志，按以下检查清单逐项确认：

```
✅ [ ] IDLE → 检测到 battleStart.png → 触发 on_battle_start
✅ [ ] PREPARATION → 选择冰暴分支
✅ [ ] PREPARATION → 第1次灵诀选择（5选1）
✅ [ ] PREPARATION → 第2次灵诀选择（3选1）
✅ [ ] PREPARATION → 第3次灵诀选择（3选1）
✅ [ ] PORTAL_TRANSITION → 找到紫色传送门 → 护甲恢复5s → 进入第1关
✅ [ ] COMBAT_NORMAL → 战斗循环运行（日志有搜敌/攻击记录）
✅ [ ] COMBAT_NORMAL → 检测到灵诀弹窗（通关）
✅ [ ] SPIRIT_SELECT → 选择最左灵诀奖励
✅ [ ] PORTAL_TRANSITION → 找到紫色传送门 → 进入第2关
✅ [ ] （重复第2、3关）
✅ [ ] PORTAL_TRANSITION → 找到金色传送门 → 进入第4关商店
✅ [ ] SHOP_SKIP → 直接找红色传送门
✅ [ ] PORTAL_TRANSITION → 找到红色传送门 → 进入第5关
✅ [ ] BOSS_ENTRY → 检测到 battleEnd.png → 触发 on_battle_end
✅ [ ] 状态回到 IDLE
```

---

## 测试通过标准

| 测试类型 | 通过标准 |
|---------|---------|
| 单点测试 | 所有 pytest 用例 PASS，无 ERROR/FAIL |
| 集成测试 | 加载测试截图后模板/YOLO检测结果符合预期 |
| 操作验证 | 键鼠操作在游戏中实际生效，窗口定位准确 |
| UI识别 | battleStart/灵诀弹窗模板匹配成功率 > 90% |
| 传送门检测 | YOLO 对3种传送门检测置信度 > 0.6 |
| 全流程 | 5关流程检查清单全部勾选，日志无 ERROR |

---

## 问题排查指南

| 问题 | 排查步骤 |
|------|---------|
| 窗口定位失败 | 确认 `game.window_title` 与实际窗口标题一致；终端有屏幕录制权限 |
| 截图全黑 | 检查 mss 屏幕录制权限；确认游戏窗口未最小化 |
| 模板匹配失败 | 降低 `threshold.template_match` 到 0.75；检查截图是否与当前游戏UI一致 |
| YOLO 无检测结果 | 确认 best.pt 文件存在；降低 `threshold.yolo_confidence` 到 0.4 调试 |
| 灵诀弹窗不检测 | 检查 `spirit_templates/` 目录是否有截图；截图内容是否与弹窗一致 |
| 坐标点击偏移 | 重新实测灵诀坐标；确认游戏窗口未发生缩放 |
| 战斗循环卡住 | 检查 `combat_timeout` 设置；查看日志中搜敌是否在循环 |
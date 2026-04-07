"""
主状态机模块
驱动灵虚界5关完整流程: IDLE → PREPARATION → 战斗/占点循环 → BOSS_ENTRY → IDLE
"""

import time
from enum import Enum
from typing import Optional

from core.hooks import BattleHooks
from core.input import GameInput
from core.screen import ScreenCapture
from modules.capture_point import CapturePointHandler
from modules.combat import CombatHandler
from modules.navigation import Navigator
from modules.ui_handler import UIHandler
from modules.vision import ObjectDetector
from utils.logger import get_logger
from utils.window import GameWindow

log = get_logger(__name__)


class BattleState(Enum):
    """灵虚界战斗状态"""
    IDLE              = "idle"               # 等待: 持续匹配 battleStart.png
    PREPARATION       = "preparation"        # 准备关卡: 选冰暴分支 + 3次灵诀
    PORTAL_TRANSITION = "portal_transition"  # 寻找传送门并进入
    COMBAT_NORMAL     = "combat_normal"      # 小怪关卡战斗
    CAPTURE_POINT     = "capture_point"      # 占点模式
    SPIRIT_SELECT     = "spirit_select"      # 灵诀奖励选择弹窗
    SHOP_SKIP         = "shop_skip"          # 第4关商店: 跳过
    BOSS_ENTRY        = "boss_entry"         # 第5关入口, 触发结束钩子


class StageManager:
    """
    关卡管理器: 跟踪5关流程。

    stage 取值:
      0 = 准备关（选分支+灵诀）
      1-3 = 小怪关
      4 = 商店关
      5 = Boss关（进入即触发结束）
    """

    def __init__(self):
        self.stage: int = 0

    def advance(self):
        self.stage += 1
        log.info(f"关卡推进: stage={self.stage}")

    def reset(self):
        self.stage = 0
        log.info("关卡重置: stage=0")

    def is_combat_stage(self) -> bool:
        return 1 <= self.stage <= 3

    def is_shop_stage(self) -> bool:
        return self.stage == 4

    def is_boss_stage(self) -> bool:
        return self.stage == 5

    def get_portal_type(self) -> str:
        """返回当前关需要寻找的传送门类型"""
        if self.stage <= 2:
            return "purple"   # 第0→1、1→2、2→3关 是紫色传送门
        elif self.stage == 3:
            return "gold"     # 第3→4关 是金色传送门
        elif self.stage == 4:
            return "red"      # 第4→5关 是红色传送门
        return "none"


class StateMachine:
    """
    灵虚界主状态机。

    主循环:
      IDLE → 检测 battleStart.png → trigger_start → PREPARATION
      PREPARATION → 完成UI流程 → PORTAL_TRANSITION
      PORTAL_TRANSITION → 找传送门并进入 → COMBAT/CAPTURE_POINT/SHOP/BOSS
      COMBAT_NORMAL → 灵诀弹窗 → SPIRIT_SELECT → 选灵诀 → PORTAL_TRANSITION
      SHOP_SKIP → 直接找红门 → PORTAL_TRANSITION
      BOSS_ENTRY → trigger_end → IDLE
    """

    def __init__(self, hooks: BattleHooks, cfg: dict):
        self._hooks = hooks
        self._cfg = cfg
        self._state = BattleState.IDLE
        self._stage = StageManager()
        self._running = False
        self._paused = False

        # 各子模块将在 _init_modules 中初始化
        self._window: Optional[GameWindow] = None
        self._screen: Optional[ScreenCapture] = None
        self._input: Optional[GameInput] = None
        self._detector: Optional[ObjectDetector] = None
        self._navigator: Optional[Navigator] = None
        self._ui: Optional[UIHandler] = None
        self._combat: Optional[CombatHandler] = None
        self._capture: Optional[CapturePointHandler] = None

    def _init_modules(self):
        """初始化所有子模块"""
        log.info("初始化子模块...")

        # 窗口管理
        self._window = GameWindow(
            self._cfg["game"]["window_title"],
            tuple(self._cfg["game"]["resolution"]),
        )
        self._window.locate()

        # 屏幕捕获
        self._screen = ScreenCapture(
            self._window,
            template_match_threshold=self._cfg["threshold"]["template_match"],
        )

        # 输入模拟
        self._input = GameInput(
            self._window,
            keys_config=self._cfg["keys"],
            action_delay=self._cfg["timing"]["action_delay"],
        )

        # YOLO 检测器
        self._detector = ObjectDetector(
            model_path=self._cfg["models"]["detector"],
            confidence=self._cfg["threshold"]["yolo_confidence"],
        )
        self._detector.load()

        # 导航
        self._navigator = Navigator(
            self._screen, self._input, self._detector, self._cfg
        )

        # UI 处理
        self._ui = UIHandler(
            self._screen, self._input, self._cfg
        )

        # 战斗
        self._combat = CombatHandler(
            self._screen, self._input, self._ui, self._cfg
        )

        # 占点
        self._capture = CapturePointHandler(
            self._screen, self._input, self._navigator,
            self._ui, self._detector, self._cfg
        )

        log.info("子模块初始化完成")

    def run(self):
        """主循环入口"""
        self._init_modules()
        self._running = True
        interval = self._cfg["timing"]["screenshot_interval"]

        log.info("状态机启动，进入主循环")

        while self._running:
            if self._paused:
                time.sleep(0.5)
                continue

            try:
                self._tick()
            except Exception as e:
                log.error(f"状态机执行异常: {e}", exc_info=True)
                time.sleep(2.0)

            time.sleep(interval)

    def stop(self):
        """停止状态机"""
        self._running = False
        self._state = BattleState.IDLE
        self._stage.reset()
        log.info("状态机已停止")

    def pause(self):
        """暂停状态机"""
        self._paused = True
        log.info("状态机已暂停")

    def resume(self):
        """恢复状态机"""
        self._paused = False
        log.info("状态机已恢复")

    @property
    def state(self) -> BattleState:
        return self._state

    def _set_state(self, new_state: BattleState):
        log.info(f"状态转换: {self._state.value} → {new_state.value}")
        self._state = new_state

    # ─────────────── 主循环每帧逻辑 ───────────────

    def _tick(self):
        """根据当前状态执行对应逻辑"""
        handler = {
            #BattleState.IDLE: self._handle_idle,
            BattleState.IDLE: self._handle_combat,  #todo : 目前先直接进入打怪阶段
            BattleState.PREPARATION: self._handle_preparation,
            BattleState.PORTAL_TRANSITION: self._handle_portal_transition,
            BattleState.COMBAT_NORMAL: self._handle_combat,
            BattleState.CAPTURE_POINT: self._handle_capture_point,
            BattleState.SPIRIT_SELECT: self._handle_spirit_select,
            BattleState.SHOP_SKIP: self._handle_shop_skip,
            BattleState.BOSS_ENTRY: self._handle_boss_entry,
        }.get(self._state)

        if handler:
            handler()
        else:
            log.error(f"未知状态: {self._state}")

    # ─────────────── 各状态处理器 ───────────────

    def _handle_idle(self):
        """IDLE: 持续检测 battleStart.png"""
        battle_start_img = self._cfg["assets"]["battle_start"]
        pos = self._screen.find_template(battle_start_img)
        if pos:
            log.info("检测到 battleStart.png，触发战斗开始")
            self._hooks.trigger_start()
            self._stage.reset()
            self._set_state(BattleState.PREPARATION)

    def _handle_preparation(self):
        """PREPARATION: 执行准备关卡UI流程"""
        self._ui.run_preparation_phase()
        self._set_state(BattleState.PORTAL_TRANSITION)

    def _handle_portal_transition(self):
        """PORTAL_TRANSITION: 寻找并进入传送门"""
        portal_type = self._stage.get_portal_type()
        log.info(f"寻找传送门: {portal_type}（当前 stage={self._stage.stage}）")

        success = self._navigator.navigate_to_portal(portal_type)
        if not success:
            log.warning("传送门导航失败，等待重试")
            return

        # 进入传送门成功，推进关卡
        self._stage.advance()
        log.info(f"进入传送门，当前 stage={self._stage.stage}")

        # 等待加载完成
        time.sleep(3.0)

        # 根据新的关卡阶段决定下一个状态
        if self._stage.is_boss_stage():
            self._set_state(BattleState.BOSS_ENTRY)
        elif self._stage.is_shop_stage():
            self._set_state(BattleState.SHOP_SKIP)
        elif self._stage.is_combat_stage():
            # 检测是否是占点模式
            if self._detect_capture_point():
                self._set_state(BattleState.CAPTURE_POINT)
            else:
                self._set_state(BattleState.COMBAT_NORMAL)

    def _handle_combat(self):
        """COMBAT_NORMAL: 执行小怪关卡战斗循环"""
        cleared = self._combat.run_combat_loop()
        if cleared:
            # 通关，检测到灵诀弹窗
            self._set_state(BattleState.SPIRIT_SELECT)
        else:
            # 战斗超时，仍切到灵诀检测状态等待
            log.warning("战斗超时，转入灵诀等待")
            self._set_state(BattleState.SPIRIT_SELECT)

    def _handle_capture_point(self):
        """CAPTURE_POINT: 执行占点模式"""
        cleared = self._capture.run_capture_loop()
        if cleared:
            self._set_state(BattleState.SPIRIT_SELECT)
        else:
            log.warning("占点超时，转入灵诀等待")
            self._set_state(BattleState.SPIRIT_SELECT)

    def _handle_spirit_select(self):
        """SPIRIT_SELECT: 选择通关灵诀奖励后转入传送门"""
        self._ui.select_spirit_reward()
        time.sleep(0.5)
        self._set_state(BattleState.PORTAL_TRANSITION)

    def _handle_shop_skip(self):
        """SHOP_SKIP: 跳过商店，直接寻找红色传送门"""
        log.info("商店关卡，跳过购买，直接寻找红色传送门")
        # 商店关不需要战斗，stage已为4，找红色传送门（stage=4 → portal_type=red）
        self._set_state(BattleState.PORTAL_TRANSITION)

    def _handle_boss_entry(self):
        """BOSS_ENTRY: 检测 battleEnd.png 并触发结束钩子"""
        log.info("进入第5关 Boss 区域")

        # 检测 battleEnd.png
        battle_end_img = self._cfg["assets"]["battle_end"]
        # 等待一段时间让UI出现
        for _ in range(10):
            pos = self._screen.find_template(battle_end_img)
            if pos:
                log.info("检测到 battleEnd.png")
                break
            time.sleep(1.0)

        # 触发结束钩子
        self._hooks.trigger_end()

        # 重置状态
        self._stage.reset()
        self._set_state(BattleState.IDLE)
        log.info("灵虚界一轮完成，回到 IDLE")

    # ─────────────── 辅助方法 ───────────────

    def _detect_capture_point(self) -> bool:
        """
        检测当前关卡是否是占点模式。
        使用占点模式UI模板匹配。
        """
        capture_ui = self._cfg["assets"].get("capture_point_ui")
        if not capture_ui:
            return False

        frame = self._screen.capture()
        pos = self._screen.find_template(capture_ui, frame=frame)
        if pos:
            log.info("检测到占点模式UI标识")
            return True
        return False
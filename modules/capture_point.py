"""
占点模式专项模块
处理占点关卡：导航到圈内、切火炮守点、扫描射击附近敌人、防止被击退出圈。
"""

import time

from core.input import GameInput
from core.screen import ScreenCapture
from modules.navigation import Navigator
from modules.ui_handler import UIHandler
from modules.vision import ObjectDetector
from utils.logger import get_logger

log = get_logger(__name__)

# 占点战斗循环参数
RANGED_FIRE_INTERVAL = 0.4   # 远程射击间隔
IN_ZONE_CHECK_INTERVAL = 2.0 # 检测是否还在圈内的间隔（秒）
SCAN_ROTATE_DEG = 30         # 占点时小幅旋转角度（扫描周边敌人）
CAPTURE_TIMEOUT = 180.0      # 占点模式总超时（秒）


class CapturePointHandler:
    """
    占点模式战斗控制器。

    流程:
      1. 导航到占点圈中心
      2. 切换到火炮（远程），守在圈内射击
      3. 小幅旋转视角寻找附近敌人并持续射击
      4. 定期检测是否被击退出圈，若出圈则返回
      5. 检测到灵诀弹窗（通关）退出循环
    """

    def __init__(
        self,
        screen: ScreenCapture,
        game_input: GameInput,
        navigator: Navigator,
        ui_handler: UIHandler,
        detector: ObjectDetector,
        cfg: dict,
    ):
        self._screen = screen
        self._input = game_input
        self._navigator = navigator
        self._ui = ui_handler
        self._detector = detector
        self._cfg = cfg
        self._pixel_per_deg: float = cfg["exploration"]["rotate_pixel_per_deg"]
        self._repair_interval: float = cfg["combat"]["repair_check_interval"]
        self._last_repair_check: float = 0.0
        self._last_zone_check: float = 0.0

    def run_capture_loop(self) -> bool:
        """
        执行占点模式完整流程。

        Returns:
            True=通关（检测到灵诀弹窗），False=超时
        """
        log.info("======= 占点模式开始 =======")

        # ─── Step 1: 导航到占点圈 ───
        reached = self._navigator.navigate_to_capture_zone()
        if not reached:
            log.warning("未能导航到占点圈，仍尝试在当前位置守点")

        # ─── Step 2: 切换火炮，开始守点循环 ───
        self._input.switch_ranged()
        log.info("已切换火炮，开始守点射击")

        start_time = time.time()
        scan_angle = 0  # 当前扫描角度累计

        while time.time() - start_time < CAPTURE_TIMEOUT:

            # ─── 检测通关（灵诀弹窗）───
            if self._ui.detect_spirit_popup():
                log.info("占点通关！检测到灵诀弹窗")
                return True

            # ─── 定期检测武器耐久 ───
            self._check_and_repair_weapon()

            # ─── 定期检测是否还在圈内 ───
            if self._should_check_zone():
                frame = self._screen.capture()
                if not self._navigator.is_in_capture_zone(frame):
                    log.warning("已被击退出占点圈，重新返回")
                    self._input.switch_melee()   # 切近战跑回去更快
                    self._navigator.return_to_capture_zone()
                    self._input.switch_ranged()  # 回到圈内再切火炮
                    scan_angle = 0
                    continue

            # ─── 小幅旋转视角扫描周边敌人并射击 ───
            self._scan_and_shoot(scan_angle)
            scan_angle = (scan_angle + SCAN_ROTATE_DEG) % 360

            time.sleep(0.2)

        log.warning(f"占点模式超时（{CAPTURE_TIMEOUT}s）")
        return False

    def _scan_and_shoot(self, current_angle: float):
        """
        小幅旋转视角并射击。

        Args:
            current_angle: 当前扫描累计角度（用于控制旋转方向）
        """
        # 每步小幅旋转
        self._input.rotate_step(SCAN_ROTATE_DEG, self._pixel_per_deg)
        time.sleep(0.15)

        # 射击 1 发（持续扫射）
        self._input.left_click()
        time.sleep(RANGED_FIRE_INTERVAL)

    def _should_check_zone(self) -> bool:
        """判断是否到了检测圈内位置的时间"""
        now = time.time()
        if now - self._last_zone_check >= IN_ZONE_CHECK_INTERVAL:
            self._last_zone_check = now
            return True
        return False

    def _check_and_repair_weapon(self):
        """定期修复火炮耐久"""
        now = time.time()
        if now - self._last_repair_check < self._repair_interval:
            return
        self._last_repair_check = now
        log.debug("占点中定期修复火炮耐久")
        self._input.repair_weapon()
        self._input.switch_ranged()   # 修复后切回火炮
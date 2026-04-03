"""
导航模块
负责将角色导航至传送门，包含视角扫描、方向移动、靠近判定和进门前置流程。
"""

import time
from typing import Optional

import numpy as np

from core.input import GameInput
from core.screen import ScreenCapture
from modules.vision import ObjectDetector
from utils.logger import get_logger

log = get_logger(__name__)


class Navigator:
    """
    传送门导航控制器。

    流程:
      1. YOLO 检测目标传送门在画面中的位置
      2. 根据位置方向调整视角并向前移动
      3. 若画面中没有传送门，旋转视角扫描
      4. 检测到足够靠近后，执行前置流程（护甲恢复→等待→E进入）
    """

    def __init__(
        self,
        screen: ScreenCapture,
        game_input: GameInput,
        detector: ObjectDetector,
        cfg: dict,
    ):
        self._screen = screen
        self._input = game_input
        self._detector = detector
        # 配置
        self._rotate_step_deg: float = cfg["exploration"]["rotate_step_deg"]
        self._pixel_per_deg: float = cfg["exploration"]["rotate_pixel_per_deg"]
        self._walk_duration: float = cfg["exploration"]["walk_duration"]
        self._portal_timeout: float = cfg["timing"]["portal_search_timeout"]
        self._close_ratio: float = cfg["threshold"]["portal_close_ratio"]
        self._armor_wait: float = cfg["timing"]["pre_portal_armor_wait"]

    def navigate_to_portal(self, portal_type: str) -> bool:
        """
        导航到指定类型的传送门并进入。

        Args:
            portal_type: "purple" / "gold" / "red"

        Returns:
            是否成功进入（按下E后返回True，超时返回False）
        """
        log.info(f"开始导航到传送门: {portal_type}")
        start_time = time.time()

        while time.time() - start_time < self._portal_timeout:
            frame = self._screen.capture()

            # ─── 检测是否足够靠近 ───
            if self._detector.is_portal_close(frame, portal_type, self._close_ratio):
                log.info(f"传送门足够近，执行进入流程")
                self._input.pre_portal_routine(self._armor_wait)
                return True

            # ─── 检测传送门方向并调整 ───
            direction = self._detector.get_portal_screen_position(
                frame, portal_type, frame.shape[1]
            )

            if direction == "center":
                # 传送门在正前方，向前走
                log.debug("传送门正前方，前进")
                self._input.move_toward("w", 0.8)

            elif direction == "left":
                # 传送门偏左，左转视角后前进
                log.debug("传送门偏左，左转")
                self._input.rotate_step(-self._rotate_step_deg / 2, self._pixel_per_deg)
                self._input.move_toward("w", 0.5)

            elif direction == "right":
                # 传送门偏右，右转视角后前进
                log.debug("传送门偏右，右转")
                self._input.rotate_step(self._rotate_step_deg / 2, self._pixel_per_deg)
                self._input.move_toward("w", 0.5)

            else:
                # 画面中未检测到传送门，旋转扫描
                found = self._scan_for_portal(portal_type)
                if not found:
                    # 扫一圈没找到，向前探索
                    log.debug("扫描未找到传送门，向前探索")
                    self._input.sprint_forward(self._walk_duration)

            time.sleep(0.2)

        log.warning(f"导航超时: 传送门 {portal_type} 未找到（已等待 {self._portal_timeout}s）")
        return False

    def _scan_for_portal(self, portal_type: str) -> bool:
        """
        旋转视角360°扫描传送门。

        Returns:
            是否扫描到目标传送门
        """
        steps = int(360 / self._rotate_step_deg)
        log.info(f"旋转扫描传送门 ({steps} 步 × {self._rotate_step_deg}°)")

        for i in range(steps):
            frame = self._screen.capture()
            direction = self._detector.get_portal_screen_position(
                frame, portal_type, frame.shape[1]
            )
            if direction is not None:
                log.info(f"扫描找到传送门: 方向={direction}（第{i+1}步）")
                return True
            # 旋转一步
            self._input.rotate_step(self._rotate_step_deg, self._pixel_per_deg)
            time.sleep(0.3)

        return False

    def navigate_to_capture_zone(self) -> bool:
        """
        导航到占点圈中心。
        检测圈的位置，向圈中心移动直到处于圈内。

        Returns:
            是否成功到达占点圈内
        """
        log.info("开始导航到占点圈")
        start_time = time.time()
        timeout = self._portal_timeout  # 复用超时配置

        while time.time() - start_time < timeout:
            frame = self._screen.capture()
            zone = self._detector.detect_capture_zone(frame)

            if zone is None:
                # 未检测到占点圈，旋转扫描
                log.debug("未检测到占点圈，旋转扫描")
                self._input.rotate_step(self._rotate_step_deg, self._pixel_per_deg)
                time.sleep(0.3)
                continue

            # 根据圈的中心位置判断方向
            frame_w = frame.shape[1]
            frame_h = frame.shape[0]
            cx, cy = zone.center
            third = frame_w // 3

            # 判断是否已在圈内（圈的bbox足够大且居中）
            zone_w = zone.bbox[2] - zone.bbox[0]
            zone_ratio = zone.area / (frame_w * frame_h)
            if zone_ratio > 0.04:  # 占点圈面积超过4%时认为已进入圈内
                log.info("已到达占点圈内")
                return True

            if cx < third:
                log.debug("占点圈偏左，左转")
                self._input.rotate_step(-self._rotate_step_deg / 2, self._pixel_per_deg)
            elif cx > 2 * third:
                log.debug("占点圈偏右，右转")
                self._input.rotate_step(self._rotate_step_deg / 2, self._pixel_per_deg)
            else:
                log.debug("占点圈居中，前进")
                self._input.move_toward("w", 0.8)

            time.sleep(0.2)

        log.warning(f"导航到占点圈超时（{timeout}s）")
        return False

    def return_to_capture_zone(self) -> bool:
        """
        被击退出圈后返回占点圈（同 navigate_to_capture_zone）
        """
        log.info("被击退，重新返回占点圈")
        return self.navigate_to_capture_zone()

    def is_in_capture_zone(self, frame: np.ndarray) -> bool:
        """
        检测角色当前是否处于占点圈内（圈足够大且居中）
        """
        zone = self._detector.detect_capture_zone(frame)
        if zone is None:
            return False
        frame_area = frame.shape[0] * frame.shape[1]
        ratio = zone.area / frame_area
        return ratio > 0.04
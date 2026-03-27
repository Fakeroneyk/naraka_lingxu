"""传送门处理 - 识别多种传送门并按优先级交互

迭代优化:
- 多帧确认：连续2帧检测到同位置才确认（防误检）
- 渐进式走近：分段前进+复检（确保对准）
- 交互重试机制
- 面积过滤更精准
"""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from loguru import logger

from core.config import Config
from core.states import PortalType
from input.keyboard import Keyboard
from input.mouse import Mouse
from input.humanize import random_delay
from strategy.aim_controller import AimController
from utils.timer import TimeoutTimer


@dataclass
class DetectedPortal:
    """检测到的传送门"""
    portal_type: PortalType
    center_x: int
    center_y: int
    area: float


class PortalHandler:
    """传送门识别与交互"""

    def __init__(
        self, config: Config, keyboard: Keyboard,
        mouse: Mouse, aim_controller: AimController,
    ):
        self.keyboard = keyboard
        self.mouse = mouse
        self.aim = aim_controller

        self.priority = config.portal.priority
        self.search_timeout = config.portal.search_timeout
        self.key_interact = config.keybinds.interact
        self.key_forward = config.keybinds.move_forward

        self.hsv_ranges: Dict[PortalType, Tuple[np.ndarray, np.ndarray]] = {}
        portal_hsv = config.portal.hsv_ranges
        self.hsv_ranges[PortalType.SHOP] = (
            np.array(portal_hsv.shop.lower), np.array(portal_hsv.shop.upper),
        )
        self.hsv_ranges[PortalType.NORMAL] = (
            np.array(portal_hsv.normal.lower), np.array(portal_hsv.normal.upper),
        )
        self.hsv_ranges[PortalType.BOSS] = (
            np.array(portal_hsv.boss.lower), np.array(portal_hsv.boss.upper),
        )

        self._min_area = 500
        self._max_area = 200000  # 防止全屏误检
        self._last_portal: Optional[DetectedPortal] = None  # 多帧确认
        self._confirm_count = 0

        logger.info(f"传送门处理器初始化 | 优先级: {self.priority}")

    def find_all_portals(self, frame: np.ndarray) -> List[DetectedPortal]:
        portals = []
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        for portal_type, (lower, upper) in self.hsv_ranges.items():
            mask = cv2.inRange(hsv, lower, upper)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                area = cv2.contourArea(contour)
                if self._min_area < area < self._max_area:
                    M = cv2.moments(contour)
                    if M["m00"] > 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        # 排除屏幕四角UI区域
                        h, w = frame.shape[:2]
                        if cy > h * 0.85 or cy < h * 0.05:
                            continue
                        portals.append(DetectedPortal(
                            portal_type=portal_type,
                            center_x=cx, center_y=cy, area=area,
                        ))

        return portals

    def select_best_portal(self, portals: List[DetectedPortal]) -> Optional[DetectedPortal]:
        if not portals:
            return None

        for ptype_str in self.priority:
            try:
                ptype = PortalType(ptype_str)
            except ValueError:
                continue
            matches = [p for p in portals if p.portal_type == ptype]
            if matches:
                best = max(matches, key=lambda p: p.area)
                logger.info(f"选择传送门: {best.portal_type.value} ({best.center_x},{best.center_y}) 面积:{best.area:.0f}")
                return best

        return portals[0]

    def _confirm_portal(self, portal: DetectedPortal) -> bool:
        """多帧确认：同一位置连续检测到才算有效"""
        if self._last_portal is None:
            self._last_portal = portal
            self._confirm_count = 1
            return False

        # 检查是否在相近位置
        dx = abs(portal.center_x - self._last_portal.center_x)
        dy = abs(portal.center_y - self._last_portal.center_y)
        if dx < 80 and dy < 80 and portal.portal_type == self._last_portal.portal_type:
            self._confirm_count += 1
        else:
            self._confirm_count = 1

        self._last_portal = portal

        return self._confirm_count >= 2

    def interact_with_portal(self, portal: DetectedPortal) -> None:
        """分段走近+多次交互确保进入"""
        logger.info(f"走向传送门: {portal.portal_type.value}")

        # 瞄准传送门
        self.aim.aim_at_position(portal.center_x, portal.center_y)
        random_delay(200, 400)

        # 分段前进（走一段 → 交互 → 再走 → 再交互）
        for step in range(3):
            self.keyboard.hold(self.key_forward, duration=0.7)
            random_delay(100, 200)
            self.keyboard.press(self.key_interact)
            random_delay(300, 500)

        # 最后多按几次交互确保生效
        for _ in range(2):
            self.keyboard.press(self.key_interact)
            random_delay(200, 400)

        logger.info("等待传送加载...")
        time.sleep(3.0)

        # 重置确认状态
        self._last_portal = None
        self._confirm_count = 0

    def search_and_enter(self, capture_func) -> bool:
        """搜索传送门并进入"""
        timer = TimeoutTimer(self.search_timeout)
        scan_direction = 1

        while not timer.is_timeout():
            frame = capture_func()
            portals = self.find_all_portals(frame)

            if portals:
                best = self.select_best_portal(portals)
                if best and self._confirm_portal(best):
                    self.interact_with_portal(best)
                    return True

            self.mouse.move_relative(scan_direction * 60, 0)
            time.sleep(0.3)
            self.keyboard.hold(self.key_forward, duration=0.3)

            import random
            if random.random() < 0.2:
                scan_direction *= -1

        logger.warning("传送门搜索超时")
        self._last_portal = None
        self._confirm_count = 0
        return False
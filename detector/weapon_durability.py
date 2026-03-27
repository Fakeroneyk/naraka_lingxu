"""武器耐久监控 - 检测远程武器耐久度并触发修复"""

import cv2
import numpy as np
from loguru import logger

from core.config import Config
from utils.timer import IntervalTimer


class WeaponDurabilityMonitor:
    """武器耐久度监控器

    通过检测武器耐久条区域的颜色变化判断耐久状态。
    绿色=充足，黄色=中等，红色=需要修复。
    """

    # 耐久条ROI区域（1920x1080基准，右下角武器栏附近）
    # 需要根据实际游戏UI截图校准
    DEFAULT_ROI = {
        "x": 1650,
        "y": 980,
        "w": 150,
        "h": 8,
    }

    # 红色耐久条HSV范围（需要修复）
    RED_LOWER = np.array([0, 100, 100])
    RED_UPPER = np.array([10, 255, 255])
    RED_LOWER2 = np.array([170, 100, 100])
    RED_UPPER2 = np.array([180, 255, 255])

    # 黄色耐久条HSV范围（警告）
    YELLOW_LOWER = np.array([15, 100, 100])
    YELLOW_UPPER = np.array([35, 255, 255])

    def __init__(self, config: Config):
        """
        Args:
            config: 全局配置
        """
        self._roi = self.DEFAULT_ROI.copy()
        self._check_timer = IntervalTimer(config.weapon.durability_check_interval)
        self.repair_cooldown = config.weapon.repair_cooldown
        self._needs_repair = False

        # 根据分辨率缩放ROI
        res = config.screen.resolution
        scale_x = res[0] / 1920
        scale_y = res[1] / 1080
        self._roi["x"] = int(self._roi["x"] * scale_x)
        self._roi["y"] = int(self._roi["y"] * scale_y)
        self._roi["w"] = int(self._roi["w"] * scale_x)
        self._roi["h"] = int(self._roi["h"] * scale_y)

        logger.info(
            f"武器耐久监控初始化 | ROI: ({self._roi['x']}, {self._roi['y']}, "
            f"{self._roi['w']}, {self._roi['h']}) | "
            f"检查间隔: {config.weapon.durability_check_interval}秒"
        )

    def needs_repair(self, frame: np.ndarray) -> bool:
        """检查武器是否需要修复

        使用间隔计时器避免每帧都检测。

        Args:
            frame: BGR格式截屏帧

        Returns:
            True表示需要修复
        """
        if not self._check_timer.should_tick():
            return self._needs_repair

        # 裁切耐久条区域
        roi = frame[
            self._roi["y"]: self._roi["y"] + self._roi["h"],
            self._roi["x"]: self._roi["x"] + self._roi["w"],
        ]

        if roi.size == 0:
            return False

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # 检测红色像素
        red_mask1 = cv2.inRange(hsv, self.RED_LOWER, self.RED_UPPER)
        red_mask2 = cv2.inRange(hsv, self.RED_LOWER2, self.RED_UPPER2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)

        # 检测黄色像素
        yellow_mask = cv2.inRange(hsv, self.YELLOW_LOWER, self.YELLOW_UPPER)

        total_pixels = roi.shape[0] * roi.shape[1]
        red_pixels = cv2.countNonZero(red_mask)
        yellow_pixels = cv2.countNonZero(yellow_mask)

        if total_pixels == 0:
            self._needs_repair = False
            return False

        red_ratio = red_pixels / total_pixels
        yellow_ratio = yellow_pixels / total_pixels

        # 红色占比超过30%需要修复
        if red_ratio > 0.3:
            logger.warning(f"武器耐久低！红色占比: {red_ratio:.1%}")
            self._needs_repair = True
        # 黄色占比超过50%也触发修复（早修复）
        elif yellow_ratio > 0.5:
            logger.info(f"武器耐久中等，黄色占比: {yellow_ratio:.1%}")
            self._needs_repair = True
        else:
            self._needs_repair = False

        return self._needs_repair

    def set_roi(self, x: int, y: int, w: int, h: int) -> None:
        """手动设置耐久条ROI区域（用于校准）"""
        self._roi = {"x": x, "y": y, "w": w, "h": h}
        logger.info(f"耐久条ROI已更新: ({x}, {y}, {w}, {h})")
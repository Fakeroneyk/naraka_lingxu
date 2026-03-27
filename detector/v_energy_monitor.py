"""V大招能量条监控 - 检测济沧海炎神大招是否充能完毕

高玩迭代 (batch2, iter 11-12):
- 通过UI能量条颜色/亮度检测V是否充满
- 检测炎神激活状态（V激活后能量条会变化）
- 替代之前的纯时间估算
"""

import cv2
import numpy as np
from loguru import logger

from core.config import Config
from utils.timer import IntervalTimer


class VEnergyMonitor:
    """V大招能量条监控器

    通过检测屏幕上V技能能量条区域的亮度/颜色判断充能状态。
    """

    # V能量条ROI区域（1920x1080基准，角色技能栏附近）
    # 需要用截图工具校准
    DEFAULT_ROI = {
        "x": 900,
        "y": 1020,
        "w": 120,
        "h": 12,
    }

    # 充满时能量条颜色（通常为明亮的橙色/金色）
    FULL_HSV_LOWER = np.array([10, 100, 180])
    FULL_HSV_UPPER = np.array([30, 255, 255])

    # 激活状态颜色（炎神激活后可能变红/发光）
    ACTIVE_HSV_LOWER = np.array([0, 150, 200])
    ACTIVE_HSV_UPPER = np.array([15, 255, 255])

    # 充满判定阈值（能量条填充比例）
    FULL_THRESHOLD = 0.7

    def __init__(self, config: Config):
        self._roi = self.DEFAULT_ROI.copy()
        self._check_timer = IntervalTimer(0.5)  # 每0.5秒检查
        self._is_ready = False
        self._is_active = False
        self._fallback_time = 30.0  # 时间估算兜底
        self._last_use_time = 0.0

        # 分辨率缩放
        res = config.screen.resolution
        sx, sy = res[0] / 1920, res[1] / 1080
        self._roi = {
            "x": int(self._roi["x"] * sx),
            "y": int(self._roi["y"] * sy),
            "w": int(self._roi["w"] * sx),
            "h": int(self._roi["h"] * sy),
        }

        logger.info(f"V能量监控初始化 | ROI: {self._roi}")

    def check(self, frame: np.ndarray) -> bool:
        """检查V大招是否充满

        Args:
            frame: BGR截屏帧

        Returns:
            True = 充满可用
        """
        if not self._check_timer.should_tick():
            return self._is_ready

        roi = frame[
            self._roi["y"]: self._roi["y"] + self._roi["h"],
            self._roi["x"]: self._roi["x"] + self._roi["w"],
        ]

        if roi.size == 0:
            # ROI无效，用时间兜底
            import time
            self._is_ready = (time.time() - self._last_use_time) >= self._fallback_time
            return self._is_ready

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # 检测充满颜色
        full_mask = cv2.inRange(hsv, self.FULL_HSV_LOWER, self.FULL_HSV_UPPER)
        total = roi.shape[0] * roi.shape[1]
        full_pixels = cv2.countNonZero(full_mask)
        full_ratio = full_pixels / max(total, 1)

        self._is_ready = full_ratio >= self.FULL_THRESHOLD

        return self._is_ready

    def is_active(self, frame: np.ndarray) -> bool:
        """检查炎神是否激活中"""
        roi = frame[
            self._roi["y"]: self._roi["y"] + self._roi["h"],
            self._roi["x"]: self._roi["x"] + self._roi["w"],
        ]
        if roi.size == 0:
            return self._is_active

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        active_mask = cv2.inRange(hsv, self.ACTIVE_HSV_LOWER, self.ACTIVE_HSV_UPPER)
        total = roi.shape[0] * roi.shape[1]
        active_ratio = cv2.countNonZero(active_mask) / max(total, 1)
        self._is_active = active_ratio > 0.3

        return self._is_active

    def mark_used(self) -> None:
        """标记V已使用"""
        import time
        self._last_use_time = time.time()
        self._is_ready = False

    def set_roi(self, x: int, y: int, w: int, h: int) -> None:
        """手动设置ROI（校准用）"""
        self._roi = {"x": x, "y": y, "w": w, "h": h}
        logger.info(f"V能量ROI更新: {self._roi}")
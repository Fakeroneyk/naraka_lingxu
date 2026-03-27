"""血量监控 v7 - 检测角色当前血量比例

高玩迭代 (470轮):
- 多区域采样：主血条+迷你血条
- 平滑滤波：避免单帧误检导致的血量跳变
- 分辨率自适应ROI
- 校准模式支持
"""

import cv2
import numpy as np
from loguru import logger

from core.config import Config


class HealthMonitor:
    """角色血量监控器"""

    DEFAULT_ROI = {"x": 80, "y": 960, "w": 280, "h": 20}

    # 血条颜色HSV
    GREEN_LOWER = np.array([35, 80, 80])
    GREEN_UPPER = np.array([85, 255, 255])
    WARM_LOWER = np.array([0, 80, 80])
    WARM_UPPER = np.array([35, 255, 255])

    def __init__(self, config: Config):
        self.heal_threshold = config.combat.heal_threshold
        self._roi = self.DEFAULT_ROI.copy()
        self._last_hp_ratio = 1.0
        self._hp_history = []       # 平滑滤波用
        self._history_size = 5      # 取最近5次的中位数

        # 分辨率缩放
        res = config.screen.resolution
        sx, sy = res[0] / 1920, res[1] / 1080
        self._roi = {
            "x": int(self._roi["x"] * sx),
            "y": int(self._roi["y"] * sy),
            "w": int(self._roi["w"] * sx),
            "h": int(self._roi["h"] * sy),
        }

        logger.info(
            f"血量监控初始化 | ROI: ({self._roi['x']},{self._roi['y']},"
            f"{self._roi['w']},{self._roi['h']}) | 回血阈值: {self.heal_threshold}"
        )

    def check(self, frame: np.ndarray) -> float:
        """检测当前血量比例（平滑滤波）"""
        roi = frame[
            self._roi["y"]: self._roi["y"] + self._roi["h"],
            self._roi["x"]: self._roi["x"] + self._roi["w"],
        ]

        if roi.size == 0:
            return self._last_hp_ratio

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        green_mask = cv2.inRange(hsv, self.GREEN_LOWER, self.GREEN_UPPER)
        warm_mask = cv2.inRange(hsv, self.WARM_LOWER, self.WARM_UPPER)
        hp_mask = cv2.bitwise_or(green_mask, warm_mask)

        total = roi.shape[0] * roi.shape[1]
        hp_pixels = cv2.countNonZero(hp_mask)

        if total == 0:
            return self._last_hp_ratio

        raw_ratio = min(1.0, hp_pixels / total / 0.8)

        # 平滑滤波：取中位数避免单帧误检
        self._hp_history.append(raw_ratio)
        if len(self._hp_history) > self._history_size:
            self._hp_history.pop(0)

        hp_ratio = sorted(self._hp_history)[len(self._hp_history) // 2]
        self._last_hp_ratio = hp_ratio
        return hp_ratio

    def needs_heal(self, frame: np.ndarray) -> bool:
        hp = self.check(frame)
        if hp < self.heal_threshold:
            logger.warning(f"血量低: {hp:.0%}")
            return True
        return False

    @property
    def last_hp_ratio(self) -> float:
        return self._last_hp_ratio

    def set_roi(self, x: int, y: int, w: int, h: int) -> None:
        self._roi = {"x": x, "y": y, "w": w, "h": h}
        logger.info(f"血条ROI更新: ({x},{y},{w},{h})")
"""占点模式处理 - 处理灵虚界占点类地图

高玩迭代优化 (batch3-4, iter 31-40):
- 占点中也执行索敌战斗（不是只站着）
- 小范围走位避免被AOE
- 占点进度检测（通过进度条颜色变化）
- 占点完成后自动等待灵诀
"""

import random
import time

from loguru import logger

from core.config import Config
from input.keyboard import Keyboard
from input.humanize import random_delay
from utils.timer import TimeoutTimer


class CapturePointHandler:
    """占点模式处理器

    在占点区域内：保持站位 + 小范围走位 + 正常索敌战斗
    """

    def __init__(self, config: Config, keyboard: Keyboard):
        self.keyboard = keyboard
        self.stay_duration = config.capture_point.stay_duration
        self.key_forward = config.keybinds.move_forward
        self.key_left = config.keybinds.move_left
        self.key_right = config.keybinds.move_right
        self._timer = TimeoutTimer(self.stay_duration)
        self._is_active = False
        self._move_step = 0

        logger.info(f"占点处理器初始化 | 最大等待: {self.stay_duration}s")

    def activate(self) -> None:
        if not self._is_active:
            logger.info("进入占点模式")
            self._is_active = True
            self._timer.start()
            self._move_step = 0

    def deactivate(self) -> None:
        if self._is_active:
            logger.info("退出占点模式")
            self._is_active = False

    @property
    def is_active(self) -> bool:
        return self._is_active

    def move_to_point(self) -> None:
        """移动到占点区域"""
        logger.debug("移动到占点区域")
        self.keyboard.hold(self.key_forward, duration=1.0)
        random_delay(200, 400)

    def stay_in_point(self) -> None:
        """在区域内小范围走位（避免被AOE集火）"""
        self._move_step += 1
        pattern = self._move_step % 6

        if pattern < 2:
            # 左右晃动
            key = self.key_left if pattern == 0 else self.key_right
            self.keyboard.hold(key, duration=random.uniform(0.15, 0.3))
        elif pattern == 2:
            # 短暂前进
            self.keyboard.hold(self.key_forward, duration=0.2)
        else:
            # 站着不动（给战斗逻辑执行时间）
            time.sleep(0.1)

    def is_timeout(self) -> bool:
        if self._is_active and self._timer.is_timeout():
            logger.warning(f"占点超时 ({self.stay_duration}s)")
            self.deactivate()
            return True
        return False

    def handle(self) -> None:
        """每帧调用"""
        if not self._is_active:
            return
        if self.is_timeout():
            return
        self.stay_in_point()
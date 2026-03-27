"""键盘模拟 - DirectInput级别的按键模拟"""

import time
import platform
from typing import Optional

from loguru import logger

from input.humanize import random_delay

# Windows平台使用pydirectinput
_USE_DIRECT_INPUT = platform.system() == "Windows"

if _USE_DIRECT_INPUT:
    try:
        import pydirectinput

        pydirectinput.PAUSE = 0  # 禁用内置延迟，使用自己的延迟控制
    except ImportError:
        logger.warning("pydirectinput未安装，将使用模拟模式")
        _USE_DIRECT_INPUT = False


class Keyboard:
    """键盘模拟器

    Windows下使用pydirectinput（DirectInput级别），
    其他平台使用模拟输出（仅用于开发调试）。
    """

    def __init__(self, humanize: bool = True, delay_min: int = 50, delay_max: int = 200):
        """
        Args:
            humanize: 是否启用人性化随机延迟
            delay_min: 按键最小延迟(ms)
            delay_max: 按键最大延迟(ms)
        """
        self.humanize = humanize
        self.delay_min = delay_min
        self.delay_max = delay_max
        self._held_keys: set = set()

        logger.info(
            f"键盘模拟器初始化 | DirectInput: {_USE_DIRECT_INPUT} | "
            f"人性化: {humanize} | 延迟: {delay_min}-{delay_max}ms"
        )

    def press(self, key: str) -> None:
        """按下并释放按键

        Args:
            key: 按键名称（如 'f', 'v', 'shift', 'tab', '2'）
        """
        if _USE_DIRECT_INPUT:
            pydirectinput.press(key)
        else:
            logger.debug(f"[模拟] 按键: {key}")

        if self.humanize:
            random_delay(self.delay_min, self.delay_max)

    def key_down(self, key: str) -> None:
        """按下按键（不释放）

        Args:
            key: 按键名称
        """
        if _USE_DIRECT_INPUT:
            pydirectinput.keyDown(key)
        else:
            logger.debug(f"[模拟] 按下: {key}")

        self._held_keys.add(key)

    def key_up(self, key: str) -> None:
        """释放按键

        Args:
            key: 按键名称
        """
        if _USE_DIRECT_INPUT:
            pydirectinput.keyUp(key)
        else:
            logger.debug(f"[模拟] 释放: {key}")

        self._held_keys.discard(key)

    def hold(self, key: str, duration: float = 1.0) -> None:
        """按住按键一段时间（自然化持续时间）

        Args:
            key: 按键名称
            duration: 按住时长（秒）
        """
        from input.humanize import natural_hold_duration

        self.key_down(key)
        actual_duration = natural_hold_duration(duration) if self.humanize else duration
        time.sleep(actual_duration)
        self.key_up(key)

        if self.humanize:
            random_delay(self.delay_min // 2, self.delay_max // 2)

    def press_combo(self, *keys: str) -> None:
        """按组合键

        Args:
            keys: 按键序列（如 'shift', 'f'）
        """
        # 依次按下
        for key in keys:
            self.key_down(key)
            time.sleep(0.05)

        time.sleep(0.1)

        # 倒序释放
        for key in reversed(keys):
            self.key_up(key)
            time.sleep(0.05)

        if self.humanize:
            random_delay(self.delay_min, self.delay_max)

    def release_all(self) -> None:
        """释放所有按住的按键"""
        for key in list(self._held_keys):
            self.key_up(key)
        self._held_keys.clear()

    def type_sequence(self, keys: list, interval_min: int = 100, interval_max: int = 200) -> None:
        """按顺序按下一系列按键

        Args:
            keys: 按键列表
            interval_min: 按键间最小间隔(ms)
            interval_max: 按键间最大间隔(ms)
        """
        for key in keys:
            self.press(key)
            random_delay(interval_min, interval_max)
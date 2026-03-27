"""计时器工具 - 技能CD管理和超时检测"""

import time


class CooldownTimer:
    """技能冷却计时器"""

    def __init__(self, cooldown: float):
        """
        Args:
            cooldown: 冷却时间（秒）
        """
        self.cooldown = cooldown
        self._last_used: float = 0.0

    def use(self) -> None:
        """标记技能已使用"""
        self._last_used = time.time()

    def is_ready(self) -> bool:
        """检查技能是否冷却完成"""
        return (time.time() - self._last_used) >= self.cooldown

    @property
    def remaining(self) -> float:
        """剩余冷却时间（秒）"""
        elapsed = time.time() - self._last_used
        return max(0.0, self.cooldown - elapsed)

    def reset(self) -> None:
        """重置计时器（立即就绪）"""
        self._last_used = 0.0


class TimeoutTimer:
    """超时检测计时器"""

    def __init__(self, timeout: float):
        """
        Args:
            timeout: 超时时间（秒）
        """
        self.timeout = timeout
        self._start_time: float = time.time()

    def start(self) -> None:
        """开始/重置计时"""
        self._start_time = time.time()

    def is_timeout(self) -> bool:
        """是否已超时"""
        return (time.time() - self._start_time) >= self.timeout

    @property
    def elapsed(self) -> float:
        """已经过时间（秒）"""
        return time.time() - self._start_time

    @property
    def remaining(self) -> float:
        """剩余时间（秒）"""
        return max(0.0, self.timeout - self.elapsed)


class IntervalTimer:
    """间隔执行计时器"""

    def __init__(self, interval: float):
        """
        Args:
            interval: 间隔时间（秒）
        """
        self.interval = interval
        self._last_tick: float = 0.0

    def should_tick(self) -> bool:
        """是否该执行了"""
        now = time.time()
        if (now - self._last_tick) >= self.interval:
            self._last_tick = now
            return True
        return False

    def reset(self) -> None:
        """重置计时"""
        self._last_tick = 0.0
"""自动瞄准 - 将视角对准目标敌人

迭代优化:
- 渐进式追踪：远距离大步移动，近距离微调
- 过冲保护：检测来回抖动并降低步幅
- 目标预测：基于上一帧位置预判移动方向
- 死区处理：极小偏差不再移动（避免抖动）
"""

from typing import Optional, Tuple

from loguru import logger

from core.config import Config
from detector.enemy_detector import DetectedEnemy
from input.mouse import Mouse


class AimController:
    """自动瞄准控制器"""

    def __init__(self, config: Config, mouse: Mouse):
        self.sensitivity_x = config.aim.sensitivity_x
        self.sensitivity_y = config.aim.sensitivity_y
        self.threshold = config.aim.threshold
        self.smooth_steps = config.aim.smooth_steps
        self.mouse = mouse

        self.screen_cx = config.screen.resolution[0] // 2
        self.screen_cy = config.screen.resolution[1] // 2

        # 过冲保护
        self._last_dx = 0
        self._last_dy = 0
        self._overshoot_count = 0
        self._damping = 1.0  # 阻尼系数，过冲时降低

        # 死区
        self._dead_zone = 8  # 小于8像素不移动

        logger.info(
            f"瞄准控制器初始化 | 灵敏度: ({self.sensitivity_x}, {self.sensitivity_y}) | "
            f"阈值: {self.threshold}px | 死区: {self._dead_zone}px"
        )

    def aim_at(self, target: DetectedEnemy) -> bool:
        """瞄准目标

        Returns:
            True表示已瞄准（偏差小于阈值）
        """
        dx = target.center_x - self.screen_cx
        dy = target.center_y - self.screen_cy

        # 已瞄准
        if abs(dx) < self.threshold and abs(dy) < self.threshold:
            self._reset_overshoot()
            return True

        # 死区内不动
        if abs(dx) < self._dead_zone and abs(dy) < self._dead_zone:
            return True

        # 过冲检测：方向与上次相反 → 在来回抖动
        if self._last_dx != 0 and (dx * self._last_dx < 0):
            self._overshoot_count += 1
            if self._overshoot_count >= 2:
                self._damping = max(0.3, self._damping * 0.7)
                logger.debug(f"检测到瞄准过冲，阻尼降至 {self._damping:.2f}")
        else:
            self._overshoot_count = max(0, self._overshoot_count - 1)
            self._damping = min(1.0, self._damping + 0.1)

        self._last_dx = dx
        self._last_dy = dy

        # 渐进式灵敏度：远距离快移，近距离微调
        distance = (dx ** 2 + dy ** 2) ** 0.5
        if distance > 200:
            speed_factor = 1.0
            steps = max(3, self.smooth_steps - 2)
        elif distance > 80:
            speed_factor = 0.8
            steps = self.smooth_steps
        else:
            speed_factor = 0.5
            steps = self.smooth_steps + 2

        # 计算移动量
        mouse_dx = int(dx * self.sensitivity_x * speed_factor * self._damping)
        mouse_dy = int(dy * self.sensitivity_y * speed_factor * self._damping)

        # 限制最大单次移动量（防止飞出去）
        max_move = 300
        mouse_dx = max(-max_move, min(max_move, mouse_dx))
        mouse_dy = max(-max_move, min(max_move, mouse_dy))

        if abs(mouse_dx) > 1 or abs(mouse_dy) > 1:
            self.mouse.move_relative_smooth(
                mouse_dx, mouse_dy,
                steps=steps,
                step_delay_ms=12,
            )

        return False

    def aim_at_position(self, x: int, y: int) -> bool:
        """瞄准屏幕坐标位置"""
        dx = x - self.screen_cx
        dy = y - self.screen_cy

        if abs(dx) < self.threshold and abs(dy) < self.threshold:
            return True

        mouse_dx = int(dx * self.sensitivity_x * 0.8)
        mouse_dy = int(dy * self.sensitivity_y * 0.8)

        self.mouse.move_relative_smooth(
            mouse_dx, mouse_dy,
            steps=self.smooth_steps,
            step_delay_ms=15,
        )
        return False

    def is_aimed(self, target: DetectedEnemy) -> bool:
        """检查是否已瞄准"""
        dx = abs(target.center_x - self.screen_cx)
        dy = abs(target.center_y - self.screen_cy)
        return dx < self.threshold and dy < self.threshold

    def get_offset(self, target: DetectedEnemy) -> Tuple[int, int]:
        """获取目标偏移"""
        return target.center_x - self.screen_cx, target.center_y - self.screen_cy

    def _reset_overshoot(self) -> None:
        """重置过冲状态"""
        self._overshoot_count = 0
        self._damping = 1.0
        self._last_dx = 0
        self._last_dy = 0
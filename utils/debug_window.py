"""调试可视化窗口 - 显示检测结果叠加层"""

import cv2
import numpy as np
from typing import List, Optional

from core.states import CombatState, PortalType
from detector.enemy_detector import DetectedEnemy


class DebugWindow:
    """调试可视化窗口

    在截屏画面上叠加显示：
    - 敌人检测框
    - 瞄准十字线
    - 传送门检测
    - 当前状态信息
    - 血量/耐久状态
    """

    WINDOW_NAME = "灵虚界调试窗口"

    # 颜色定义 (BGR)
    COLOR_ENEMY = (0, 0, 255)      # 红
    COLOR_BOSS = (0, 0, 200)       # 深红
    COLOR_PORTAL = (255, 200, 0)   # 青
    COLOR_AIM = (0, 255, 0)        # 绿
    COLOR_TEXT = (255, 255, 255)    # 白
    COLOR_WARNING = (0, 165, 255)  # 橙

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._display_scale = 0.5  # 缩小显示

    def update(
        self,
        frame: np.ndarray,
        state: CombatState,
        enemies: Optional[List[DetectedEnemy]] = None,
        hp_ratio: float = 1.0,
        fps: float = 0.0,
    ) -> None:
        """更新调试窗口

        Args:
            frame: 当前截屏帧
            state: 当前战斗状态
            enemies: 检测到的敌人列表
            hp_ratio: 血量比例
            fps: 当前帧率
        """
        if not self.enabled:
            return

        display = frame.copy()
        h, w = display.shape[:2]

        # 绘制屏幕中心十字线
        cx, cy = w // 2, h // 2
        cv2.line(display, (cx - 20, cy), (cx + 20, cy), self.COLOR_AIM, 2)
        cv2.line(display, (cx, cy - 20), (cx, cy + 20), self.COLOR_AIM, 2)

        # 绘制敌人检测框
        if enemies:
            for enemy in enemies:
                color = (
                    self.COLOR_BOSS
                    if enemy.enemy_type.value == "enemy_boss"
                    else self.COLOR_ENEMY
                )
                x1 = enemy.center_x - enemy.width // 2
                y1 = enemy.center_y - enemy.height // 2
                x2 = enemy.center_x + enemy.width // 2
                y2 = enemy.center_y + enemy.height // 2

                cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
                label = f"{enemy.enemy_type.value} {enemy.confidence:.1%}"
                cv2.putText(
                    display, label, (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1,
                )

        # 状态信息面板
        panel_y = 30
        cv2.putText(
            display, f"State: {state.name}", (10, panel_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.COLOR_TEXT, 2,
        )
        panel_y += 30

        # 血量条
        hp_color = (0, 255, 0) if hp_ratio > 0.5 else (0, 165, 255) if hp_ratio > 0.3 else (0, 0, 255)
        cv2.rectangle(display, (10, panel_y), (210, panel_y + 20), (50, 50, 50), -1)
        cv2.rectangle(display, (10, panel_y), (10 + int(200 * hp_ratio), panel_y + 20), hp_color, -1)
        cv2.putText(
            display, f"HP: {hp_ratio:.0%}", (220, panel_y + 15),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLOR_TEXT, 1,
        )
        panel_y += 30

        # FPS
        cv2.putText(
            display, f"FPS: {fps:.1f}", (10, panel_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLOR_TEXT, 1,
        )

        # 敌人数量
        enemy_count = len(enemies) if enemies else 0
        cv2.putText(
            display, f"Enemies: {enemy_count}", (150, panel_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLOR_TEXT, 1,
        )

        # 缩小显示
        display = cv2.resize(
            display,
            (int(w * self._display_scale), int(h * self._display_scale)),
        )

        cv2.imshow(self.WINDOW_NAME, display)
        cv2.waitKey(1)

    def close(self) -> None:
        """关闭窗口"""
        cv2.destroyWindow(self.WINDOW_NAME)
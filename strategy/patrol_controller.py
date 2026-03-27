"""巡逻控制 - 无敌人时的自动移动策略

迭代优化:
- 更丰富的巡逻模式（前进/扫描/绕圈/探索）
- 智能卡死检测（只比对中心区域，排除UI变化干扰）
- 多级卡死恢复（轻度→中度→重度）
- 跳跃辅助脱困
"""

import random
import time

import cv2
import numpy as np
from loguru import logger

from core.config import Config
from input.keyboard import Keyboard
from input.mouse import Mouse
from input.humanize import random_delay
from utils.timer import TimeoutTimer


class PatrolController:
    """巡逻控制器"""

    def __init__(self, config: Config, keyboard: Keyboard, mouse: Mouse):
        self.keyboard = keyboard
        self.mouse = mouse

        self.forward_duration = config.patrol.forward_duration
        self.scan_speed = config.patrol.scan_speed
        self.stuck_timeout = config.patrol.stuck_timeout
        self.turn_min = config.patrol.turn_angle_min
        self.turn_max = config.patrol.turn_angle_max

        self.key_forward = config.keybinds.move_forward
        self.key_back = config.keybinds.move_back
        self.key_left = config.keybinds.move_left
        self.key_right = config.keybinds.move_right
        self.key_jump = getattr(config.keybinds, "jump", "space")

        self._stuck_timer = TimeoutTimer(self.stuck_timeout)
        self._last_frame_center: np.ndarray | None = None
        self._scan_direction = 1
        self._patrol_step = 0
        self._stuck_recovery_level = 0  # 0=正常, 1=轻度, 2=中度, 3=重度

        logger.info(
            f"巡逻控制器初始化 | 前进: {self.forward_duration}s | "
            f"卡死超时: {self.stuck_timeout}s"
        )

    def move(self) -> None:
        """执行一步巡逻动作（含3D地图垂直扫描）"""
        self._patrol_step += 1
        action = self._patrol_step % 9

        if action < 3:
            self._move_forward_scan()       # 前进+水平/垂直扫描
        elif action == 3:
            self._random_turn()             # 随机转向
        elif action == 4:
            self._strafe_move()             # 侧移探索
        elif action == 5:
            self._move_forward_scan()       # 继续前进扫描
        elif action == 6:
            self._look_up_scan()            # 抬头扫描屋顶敌人
        elif action == 7:
            self._move_forward_scan()
        else:
            random_delay(100, 250)          # 短暂停顿

    def _move_forward_scan(self) -> None:
        """前进并扫描视角（水平+垂直）"""
        self.keyboard.key_down(self.key_forward)

        # 水平扫描
        scan_dx = self._scan_direction * self.scan_speed * random.randint(5, 15)
        # 垂直扫描：偶尔抬头看屋顶上的怪
        scan_dy = 0
        if random.random() < 0.2:
            scan_dy = random.randint(-30, -10)  # 负值=抬头
        elif random.random() < 0.1:
            scan_dy = random.randint(10, 20)    # 正值=低头

        self.mouse.move_relative(scan_dx, scan_dy)
        time.sleep(random.uniform(0.25, 0.4))
        self.keyboard.key_up(self.key_forward)

        # 抬头后要回正视角
        if scan_dy < -15:
            time.sleep(0.1)
            self.mouse.move_relative(0, abs(scan_dy) // 2)  # 部分回正

        if random.random() < 0.25:
            self._scan_direction *= -1

    def _look_up_scan(self) -> None:
        """专门抬头扫描（检查屋顶/高处敌人）"""
        self.mouse.move_relative(0, -40)  # 抬头
        time.sleep(0.3)
        # 左右扫一圈
        self.mouse.move_relative(60, 0)
        time.sleep(0.2)
        self.mouse.move_relative(-120, 0)
        time.sleep(0.2)
        self.mouse.move_relative(60, 0)
        time.sleep(0.1)
        # 回正
        self.mouse.move_relative(0, 35)

    def _strafe_move(self) -> None:
        """侧移（探索侧方区域）"""
        side_key = self.key_left if random.random() < 0.5 else self.key_right
        self.keyboard.key_down(self.key_forward)
        self.keyboard.key_down(side_key)
        time.sleep(random.uniform(0.3, 0.6))
        self.keyboard.key_up(side_key)
        self.keyboard.key_up(self.key_forward)

    def _random_turn(self) -> None:
        """随机转向"""
        angle = random.randint(self.turn_min, self.turn_max)
        direction = random.choice([-1, 1])
        mouse_dx = int(angle * direction * 5)
        self.mouse.move_relative_smooth(mouse_dx, 0, steps=5, step_delay_ms=20)

    def is_stuck(self, current_frame: np.ndarray) -> bool:
        """智能卡死检测（只比对画面中心区域，排除UI变化）"""
        h, w = current_frame.shape[:2]
        # 只取中心区域比对（排除四角UI）
        margin_x, margin_y = w // 4, h // 4
        center_region = current_frame[margin_y:h - margin_y, margin_x:w - margin_x]

        if self._last_frame_center is None:
            self._last_frame_center = center_region.copy()
            self._stuck_timer.start()
            return False

        # 缩小后比对（更快）
        small_curr = cv2.resize(center_region, (160, 90))
        small_last = cv2.resize(self._last_frame_center, (160, 90))

        diff = cv2.absdiff(small_curr, small_last)
        mean_diff = np.mean(diff)

        self._last_frame_center = center_region.copy()

        if mean_diff < 4:
            if self._stuck_timer.is_timeout():
                logger.warning(f"卡死检测！画面差异: {mean_diff:.1f}")
                return True
        else:
            self._stuck_timer.start()
            self._stuck_recovery_level = 0

        return False

    def unstuck(self) -> None:
        """多级卡死恢复"""
        self._stuck_recovery_level += 1
        level = min(self._stuck_recovery_level, 3)
        logger.info(f"卡死恢复 Level {level}")

        self.keyboard.release_all()
        time.sleep(0.2)

        if level == 1:
            # 轻度：后退+转向
            self.keyboard.hold(self.key_back, duration=0.8)
            angle = random.randint(60, 120)
            self.mouse.move_relative_smooth(angle * random.choice([-5, 5]), 0, steps=5, step_delay_ms=20)

        elif level == 2:
            # 中度：后退+大转向+侧移
            self.keyboard.hold(self.key_back, duration=1.2)
            self.mouse.move_relative_smooth(random.choice([-600, 600]), 0, steps=8, step_delay_ms=20)
            side = random.choice([self.key_left, self.key_right])
            self.keyboard.hold(side, duration=1.0)

        else:
            # 重度：后退+180度转+跳跃前冲（翻越障碍/上平台）
            self.keyboard.hold(self.key_back, duration=1.5)
            self.mouse.move_relative_smooth(900 * random.choice([-1, 1]), 0, steps=10, step_delay_ms=20)
            # 跳跃前冲尝试翻越障碍
            self.keyboard.key_down(self.key_forward)
            self.keyboard.press(self.key_jump)
            time.sleep(0.5)
            self.keyboard.press(self.key_jump)  # 二段跳
            time.sleep(0.3)
            self.keyboard.key_up(self.key_forward)
            self.keyboard.hold(self.key_forward, duration=1.0)

        self._stuck_timer.start()
        self._last_frame_center = None
        logger.info(f"卡死恢复 Level {level} 完成")

    def reset(self) -> None:
        """重置巡逻状态"""
        self._patrol_step = 0
        self._last_frame_center = None
        self._stuck_timer.start()
        self._stuck_recovery_level = 0
        self.keyboard.release_all()
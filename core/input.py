"""
键鼠输入模拟模块
基于 pyautogui 实现游戏操作，所有坐标接受窗口相对坐标并自动转换为绝对坐标。
"""

import random
import time
from typing import Optional

import pyautogui

from utils.logger import get_logger
from utils.window import GameWindow

log = get_logger(__name__)

# pyautogui 安全设置
pyautogui.FAILSAFE = True       # 鼠标移到左上角触发异常退出
pyautogui.PAUSE = 0.05          # 每次操作后微延迟


class GameInput:
    """
    游戏键鼠操作封装。

    所有 click / move 操作接受窗口相对坐标（基于1920x1080），
    内部自动转换为屏幕绝对坐标后执行。
    """

    def __init__(self, window: GameWindow, keys_config: dict, action_delay: float = 0.3):
        self._window = window
        self._keys = keys_config
        self._delay = action_delay

    def _wait(self, duration: Optional[float] = None):
        """动作间隔等待"""
        time.sleep(duration if duration is not None else self._delay)

    # ─────────────── 基础输入 ───────────────

    def press_key(self, key: str):
        """按下并释放按键"""
        pyautogui.press(key)
        log.debug(f"按键: {key}")
        self._wait(0.1)

    def hold_key(self, key: str, duration: float):
        """长按按键指定时长"""
        pyautogui.keyDown(key)
        time.sleep(duration)
        pyautogui.keyUp(key)
        log.debug(f"长按: {key} 持续 {duration}s")

    def click(self, rx: int, ry: int):
        """
        点击窗口相对坐标位置。

        Args:
            rx: 基于1920x1080的窗口相对X坐标
            ry: 基于1920x1080的窗口相对Y坐标
        """
        abs_x, abs_y = self._window.relative_to_absolute(rx, ry)
        pyautogui.click(abs_x, abs_y)
        log.debug(f"点击: 相对({rx},{ry}) → 绝对({abs_x},{abs_y})")
        self._wait(0.15)

    def left_click(self):
        """在当前鼠标位置左键点击（攻击用）"""
        pyautogui.click()
        self._wait(0.05)

    def move_mouse_relative(self, dx: int, dy: int):
        """鼠标相对位移（用于视角旋转）"""
        pyautogui.moveRel(dx, dy, duration=0.1)

    # ─────────────── 移动 ───────────────

    def move_toward(self, direction: str, duration: float):
        """
        朝指定方向持续移动。

        Args:
            direction: 方向键名（如 "w", "a", "s", "d"）
            duration: 持续时长（秒）
        """
        key = self._keys.get(f"move_{self._direction_name(direction)}", direction)
        self.hold_key(key, duration)

    def sprint_forward(self, duration: float):
        """冲刺前进（W + Shift 同时按下）"""
        w_key = self._keys["move_forward"]
        sprint_key = self._keys["sprint"]
        pyautogui.keyDown(sprint_key)
        pyautogui.keyDown(w_key)
        time.sleep(duration)
        pyautogui.keyUp(w_key)
        pyautogui.keyUp(sprint_key)
        log.debug(f"冲刺前进 {duration}s")

    def random_walk(self, duration: float):
        """随机方向游走（搜敌用）"""
        directions = ["w", "a", "s", "d"]
        chosen = random.choice(directions)
        log.debug(f"随机游走: {chosen} {duration}s")
        self.hold_key(chosen, duration)

    # ─────────────── 视角 ───────────────

    def rotate_camera(self, delta_x: int, delta_y: int = 0):
        """
        旋转视角。

        Args:
            delta_x: 水平旋转量（正=右转，负=左转），单位像素
            delta_y: 垂直旋转量（正=下看，负=上看），单位像素
        """
        # 先将鼠标移到窗口中心，再进行相对偏移
        cx, cy = self._window.get_center()
        pyautogui.moveTo(cx, cy, duration=0.05)
        pyautogui.moveRel(delta_x, delta_y, duration=0.15)
        log.debug(f"视角旋转: dx={delta_x}, dy={delta_y}")
        self._wait(0.1)

    def rotate_step(self, degrees: float, pixel_per_deg: float):
        """
        按角度步进旋转视角。

        Args:
            degrees: 旋转角度（正=右转，负=左转）
            pixel_per_deg: 每度对应的鼠标像素位移
        """
        px = int(degrees * pixel_per_deg)
        self.rotate_camera(delta_x=px)

    # ─────────────── 游戏专用操作 ───────────────

    def lock_target(self):
        """按 ~ 键锁定最近敌人（需持近战武器）"""
        key = self._keys["lock_target"]
        self.press_key(key)
        log.info("锁定目标")
        self._wait(0.3)

    def switch_melee(self):
        """按 1 切换到双刀"""
        key = self._keys["melee_weapon"]
        self.press_key(key)
        log.info("切换近战: 双刀")
        self._wait(0.2)

    def switch_ranged(self):
        """按 2 切换到火炮"""
        key = self._keys["ranged_weapon"]
        self.press_key(key)
        log.info("切换远程: 火炮")
        self._wait(0.2)

    def interact(self):
        """按 E 交互（进传送门等）"""
        key = self._keys["interact"]
        self.press_key(key)
        log.info("交互: E")

    def use_f_skill(self):
        """按 F 使用火球技能"""
        key = self._keys["f_skill"]
        self.press_key(key)
        log.info("技能: 火球(F)")

    def repair_weapon(self):
        """按 R 修复武器（火炮耐久耗尽时）"""
        key = self._keys["repair"]
        self.press_key(key)
        log.info("修复武器: R")
        self._wait(1.0)    # 修复动画等待

    def restore_armor(self):
        """按 5 恢复护甲"""
        key = self._keys["restore_armor"]
        self.press_key(key)
        log.info("恢复护甲: 5")

    def attack_combo(self, count: int):
        """
        近战连击。

        Args:
            count: 连击次数
        """
        for i in range(count):
            self.left_click()
            self._wait(0.12)
        log.debug(f"近战连击 x{count}")

    def ranged_burst(self, count: int):
        """
        远程火炮连射。

        Args:
            count: 射击次数
        """
        for i in range(count):
            self.left_click()
            self._wait(0.3)
        log.debug(f"远程射击 x{count}")

    # ─────────────── 复合操作 ───────────────

    def pre_portal_routine(self, armor_wait: float):
        """
        进传送门前置流程：恢复护甲 → 等待 → 交互进入。

        Args:
            armor_wait: 恢复护甲后等待时长（秒）
        """
        log.info("传送门前置: 恢复护甲")
        self.restore_armor()
        log.info(f"等待 {armor_wait} 秒...")
        time.sleep(armor_wait)
        log.info("按E进入传送门")
        self.interact()
        self._wait(2.0)   # 等待加载过渡

    # ─────────────── 辅助 ───────────────

    @staticmethod
    def _direction_name(key: str) -> str:
        """将 wasd 映射为 forward/left/back/right"""
        mapping = {"w": "forward", "a": "left", "s": "back", "d": "right"}
        return mapping.get(key, key)
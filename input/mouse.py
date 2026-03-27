"""鼠标模拟 - DirectInput级别的鼠标操作"""

import time
import platform
from typing import Optional, Tuple

from loguru import logger

from input.humanize import random_delay, random_offset, bezier_curve

_USE_DIRECT_INPUT = platform.system() == "Windows"

if _USE_DIRECT_INPUT:
    try:
        import pydirectinput
        import ctypes

        # Win32 API常量
        MOUSEEVENTF_MOVE = 0x0001
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        MOUSEEVENTF_RIGHTDOWN = 0x0008
        MOUSEEVENTF_RIGHTUP = 0x0010
        MOUSEEVENTF_MIDDLEDOWN = 0x0020
        MOUSEEVENTF_MIDDLEUP = 0x0040

    except ImportError:
        logger.warning("pydirectinput未安装，将使用模拟模式")
        _USE_DIRECT_INPUT = False


class Mouse:
    """鼠标模拟器

    支持相对移动（游戏中视角控制）和绝对点击（UI操作）。
    使用Win32 mouse_event实现相对移动，兼容FPS游戏。

    坐标说明：
    - move_relative(): 相对移动，不需要坐标转换
    - click(x, y): 绝对坐标点击，如果设置了window_offset会自动转换
    - move_to(x, y): 绝对坐标移动，同上
    """

    def __init__(self, humanize: bool = True, delay_min: int = 50, delay_max: int = 200):
        self.humanize = humanize
        self.delay_min = delay_min
        self.delay_max = delay_max

        # 游戏窗口偏移（由ScreenCapture设置）
        self._window_offset_x = 0
        self._window_offset_y = 0

        logger.info(
            f"鼠标模拟器初始化 | DirectInput: {_USE_DIRECT_INPUT} | "
            f"人性化: {humanize}"
        )

    def set_window_offset(self, offset_x: int, offset_y: int) -> None:
        """设置游戏窗口偏移量

        设置后，click/move_to 等绝对坐标操作会自动加上偏移。
        """
        self._window_offset_x = offset_x
        self._window_offset_y = offset_y
        logger.debug(f"鼠标窗口偏移: ({offset_x}, {offset_y})")

    def _to_screen(self, x: int, y: int) -> tuple:
        """游戏窗口坐标 → 屏幕绝对坐标"""
        return x + self._window_offset_x, y + self._window_offset_y

    def click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """鼠标左键点击（游戏窗口坐标，自动转换为屏幕绝对坐标）

        Args:
            x: 游戏窗口内x坐标，None表示当前位置
            y: 游戏窗口内y坐标，None表示当前位置
        """
        if x is not None and y is not None:
            if self.humanize:
                x, y = random_offset(x, y, max_offset=3)
            sx, sy = self._to_screen(x, y)
            self.move_to_screen(sx, sy)

        if _USE_DIRECT_INPUT:
            pydirectinput.click()
        else:
            logger.debug(f"[模拟] 左键点击 @ ({x}, {y})")

        if self.humanize:
            random_delay(self.delay_min // 2, self.delay_max // 2)

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """鼠标右键点击"""
        if x is not None and y is not None:
            if self.humanize:
                x, y = random_offset(x, y, max_offset=3)
            self.move_to(x, y)

        if _USE_DIRECT_INPUT:
            pydirectinput.rightClick()
        else:
            logger.debug(f"[模拟] 右键点击 @ ({x}, {y})")

        if self.humanize:
            random_delay(self.delay_min // 2, self.delay_max // 2)

    def mouse_down(self, button: str = "left") -> None:
        """按下鼠标按键"""
        if _USE_DIRECT_INPUT:
            pydirectinput.mouseDown(button=button)
        else:
            logger.debug(f"[模拟] 鼠标按下: {button}")

    def mouse_up(self, button: str = "left") -> None:
        """释放鼠标按键"""
        if _USE_DIRECT_INPUT:
            pydirectinput.mouseUp(button=button)
        else:
            logger.debug(f"[模拟] 鼠标释放: {button}")

    def move_to(self, x: int, y: int) -> None:
        """移动到游戏窗口内坐标（自动加偏移）"""
        sx, sy = self._to_screen(x, y)
        self.move_to_screen(sx, sy)

    def move_to_screen(self, x: int, y: int) -> None:
        """移动到屏幕绝对坐标"""
        if _USE_DIRECT_INPUT:
            pydirectinput.moveTo(x, y)
        else:
            logger.debug(f"[模拟] 移动到: ({x}, {y})")

    def move_relative(self, dx: int, dy: int) -> None:
        """相对移动鼠标（用于游戏内视角控制）

        使用Win32 mouse_event API实现，确保游戏内可用。

        Args:
            dx: 水平偏移量（正=右，负=左）
            dy: 垂直偏移量（正=下，负=上）
        """
        if _USE_DIRECT_INPUT:
            # 使用Win32 API的mouse_event进行相对移动
            # 这比pydirectinput.moveRel更可靠
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, int(dx), int(dy), 0, 0)
        else:
            logger.debug(f"[模拟] 相对移动: ({dx}, {dy})")

    def move_relative_smooth(
        self, dx: int, dy: int, steps: int = 5, step_delay_ms: int = 15
    ) -> None:
        """平滑相对移动鼠标（模拟人类瞄准）

        将总移动量分成多步执行，每步间添加微小延迟。

        Args:
            dx: 总水平偏移量
            dy: 总垂直偏移量
            steps: 分步数
            step_delay_ms: 每步延迟(ms)
        """
        if abs(dx) < 3 and abs(dy) < 3:
            self.move_relative(dx, dy)
            return

        # 分步移动
        step_dx = dx / steps
        step_dy = dy / steps

        for i in range(steps):
            # 添加微小随机抖动
            jitter_x = 0
            jitter_y = 0
            if self.humanize and i < steps - 1:  # 最后一步不加抖动
                import random
                jitter_x = random.uniform(-0.5, 0.5)
                jitter_y = random.uniform(-0.5, 0.5)

            self.move_relative(
                int(step_dx + jitter_x),
                int(step_dy + jitter_y),
            )
            time.sleep(step_delay_ms / 1000.0)

    def click_at_smooth(self, x: int, y: int, steps: int = 10) -> None:
        """平滑移动到目标位置并点击（UI操作用）

        Args:
            x: 目标x坐标
            y: 目标y坐标
            steps: 移动插值步数
        """
        if _USE_DIRECT_INPUT:
            # 获取当前位置
            import ctypes

            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            current = (pt.x, pt.y)
        else:
            current = (0, 0)

        target = (x, y)
        if self.humanize:
            target = random_offset(x, y, max_offset=3)

        # 贝塞尔曲线移动
        points = bezier_curve(current, target, steps=steps)
        for px, py in points:
            self.move_to(px, py)
            time.sleep(0.01)

        self.click()

    def hold_click(self, duration: float = 0.5, button: str = "left") -> None:
        """按住鼠标一段时间

        Args:
            duration: 按住时长（秒）
            button: 按键（left/right）
        """
        self.mouse_down(button)
        time.sleep(duration)
        self.mouse_up(button)

        if self.humanize:
            random_delay(self.delay_min // 2, self.delay_max // 2)
"""
游戏窗口管理模块
负责定位游戏窗口位置，计算窗口相对坐标，支持 macOS 平台。
"""

import subprocess
import re
from typing import Optional, Tuple

from utils.logger import get_logger

log = get_logger(__name__)


class GameWindow:
    """
    管理游戏窗口的定位与坐标转换。

    在 macOS 下通过 AppleScript 获取窗口位置和大小。
    所有对外暴露的坐标均为窗口相对坐标，基于1920x1080分辨率。
    """

    def __init__(self, window_title: str, resolution: Tuple[int, int] = (1920, 1080)):
        self.window_title = window_title
        self.target_width, self.target_height = resolution
        self._x: int = 0
        self._y: int = 0
        self._width: int = 0
        self._height: int = 0
        self._found: bool = False

    @property
    def found(self) -> bool:
        return self._found

    @property
    def region(self) -> Tuple[int, int, int, int]:
        """返回窗口区域 (x, y, width, height) 用于截图"""
        return (self._x, self._y, self._width, self._height)

    def locate(self) -> bool:
        """
        定位游戏窗口位置。
        返回是否成功找到窗口。
        """
        try:
            result = self._get_window_bounds_macos()
            if result:
                self._x, self._y, self._width, self._height = result
                self._found = True
                log.info(
                    f"游戏窗口已定位: ({self._x}, {self._y}) "
                    f"大小: {self._width}x{self._height}"
                )
                return True
            else:
                self._found = False
                log.warning(f"未找到游戏窗口: '{self.window_title}'")
                return False
        except Exception as e:
            self._found = False
            log.error(f"定位游戏窗口异常: {e}")
            return False

    def _get_window_bounds_macos(self) -> Optional[Tuple[int, int, int, int]]:
        """
        使用 AppleScript 获取 macOS 窗口位置和大小。
        返回 (x, y, width, height) 或 None。
        """
        script = f'''
        tell application "System Events"
            set targetProcess to first process whose name contains "{self.window_title}"
            tell targetProcess
                set targetWindow to front window
                set {{x, y}} to position of targetWindow
                set {{w, h}} to size of targetWindow
                return (x as text) & "," & (y as text) & "," & (w as text) & "," & (h as text)
            end tell
        end tell
        '''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(",")
                if len(parts) == 4:
                    return tuple(int(p.strip()) for p in parts)
        except subprocess.TimeoutExpired:
            log.warning("AppleScript 获取窗口位置超时")
        except Exception as e:
            log.error(f"AppleScript 执行异常: {e}")
        return None

    def relative_to_absolute(self, rx: int, ry: int) -> Tuple[int, int]:
        """
        将窗口相对坐标转换为屏幕绝对坐标。

        Args:
            rx: 基于1920x1080的相对X坐标
            ry: 基于1920x1080的相对Y坐标

        Returns:
            (abs_x, abs_y) 屏幕绝对坐标
        """
        if not self._found:
            log.warning("窗口未定位，返回原始坐标")
            return rx, ry

        # 缩放因子：实际窗口大小 / 目标分辨率
        scale_x = self._width / self.target_width
        scale_y = self._height / self.target_height

        abs_x = self._x + int(rx * scale_x)
        abs_y = self._y + int(ry * scale_y)
        return abs_x, abs_y

    def get_center(self) -> Tuple[int, int]:
        """获取窗口中心的屏幕绝对坐标"""
        return self.relative_to_absolute(
            self.target_width // 2,
            self.target_height // 2
        )
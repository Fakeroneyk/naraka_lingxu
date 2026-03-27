"""截屏模块 v7 - 基于mss的高性能屏幕截取

关键修正：游戏窗口坐标偏移
- 截屏范围限定在游戏窗口内
- 提供窗口偏移量给其他模块做坐标换算
- 全屏/无边框/窗口化都兼容
"""

import time
import platform
from typing import Optional, Tuple

import cv2
import numpy as np

try:
    import mss
except ImportError:
    raise ImportError("请安装mss: pip install mss")

from loguru import logger

from core.config import Config


class ScreenCapture:
    """高性能屏幕截取器（支持游戏窗口定位）"""

    def __init__(self, config: Config):
        self.resolution = config.screen.resolution
        self.target_w = self.resolution[0]
        self.target_h = self.resolution[1]
        self._game_title = config.screen.game_window_title
        self._sct = mss.mss()
        self._monitor = self._sct.monitors[1]
        self._frame_count = 0
        self._fps_start = time.time()
        self._current_fps = 0.0
        self._last_frame: Optional[np.ndarray] = None

        # 游戏窗口定位
        self._game_hwnd = None
        self._window_offset_x = 0  # 游戏窗口左上角在屏幕上的x偏移
        self._window_offset_y = 0  # 游戏窗口左上角在屏幕上的y偏移
        self._window_rect = None   # (left, top, right, bottom)

        if platform.system() == "Windows":
            self._find_game_window()

        logger.info(
            f"截屏初始化 | 显示器: {self._monitor['width']}x{self._monitor['height']} | "
            f"目标: {self.target_w}x{self.target_h} | "
            f"窗口偏移: ({self._window_offset_x}, {self._window_offset_y})"
        )

    def _find_game_window(self) -> None:
        """查找游戏窗口并获取其位置"""
        try:
            import win32gui
            import win32con

            def callback(hwnd, results):
                title = win32gui.GetWindowText(hwnd)
                if self._game_title and self._game_title.lower() in title.lower():
                    if win32gui.IsWindowVisible(hwnd):
                        results.append(hwnd)

            results = []
            win32gui.EnumWindows(callback, results)

            if results:
                self._game_hwnd = results[0]
                title = win32gui.GetWindowText(self._game_hwnd)

                # 获取窗口客户区域（不含标题栏/边框）
                rect = win32gui.GetClientRect(self._game_hwnd)
                point = win32gui.ClientToScreen(self._game_hwnd, (0, 0))

                self._window_offset_x = point[0]
                self._window_offset_y = point[1]
                self._window_rect = (
                    point[0], point[1],
                    point[0] + rect[2], point[1] + rect[3],
                )

                logger.info(
                    f"游戏窗口: '{title}' | "
                    f"位置: ({self._window_offset_x}, {self._window_offset_y}) | "
                    f"大小: {rect[2]}x{rect[3]}"
                )
        except ImportError:
            logger.debug("win32gui不可用，使用全屏截取")
        except Exception as e:
            logger.debug(f"查找窗口失败: {e}")

    def refresh_window_position(self) -> None:
        """刷新游戏窗口位置（窗口可能被拖动）"""
        if self._game_hwnd is not None:
            try:
                import win32gui
                rect = win32gui.GetClientRect(self._game_hwnd)
                point = win32gui.ClientToScreen(self._game_hwnd, (0, 0))
                self._window_offset_x = point[0]
                self._window_offset_y = point[1]
                self._window_rect = (
                    point[0], point[1],
                    point[0] + rect[2], point[1] + rect[3],
                )
            except Exception:
                pass

    @property
    def window_offset(self) -> Tuple[int, int]:
        """获取游戏窗口左上角在屏幕上的偏移量

        所有UI坐标 + 此偏移 = 屏幕绝对坐标
        """
        return self._window_offset_x, self._window_offset_y

    def game_to_screen(self, game_x: int, game_y: int) -> Tuple[int, int]:
        """将游戏内坐标转换为屏幕绝对坐标

        Args:
            game_x: 游戏窗口内x坐标
            game_y: 游戏窗口内y坐标

        Returns:
            屏幕绝对坐标 (screen_x, screen_y)
        """
        return game_x + self._window_offset_x, game_y + self._window_offset_y

    def focus_game_window(self) -> bool:
        """将游戏窗口提到前台"""
        if self._game_hwnd is None:
            return False
        try:
            import win32gui
            import win32con
            win32gui.ShowWindow(self._game_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self._game_hwnd)
            # 刷新位置
            self.refresh_window_position()
            return True
        except Exception:
            return False

    def grab(self, region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """截取游戏窗口画面

        如果找到了游戏窗口，只截取窗口区域。
        否则截取全屏。
        """
        if region is not None:
            # 指定区域截取（相对于游戏窗口的坐标）
            monitor = {
                "left": region[0] + self._window_offset_x,
                "top": region[1] + self._window_offset_y,
                "width": region[2],
                "height": region[3],
            }
        elif self._window_rect is not None:
            # 截取游戏窗口区域
            monitor = {
                "left": self._window_rect[0],
                "top": self._window_rect[1],
                "width": self._window_rect[2] - self._window_rect[0],
                "height": self._window_rect[3] - self._window_rect[1],
            }
        else:
            # 全屏
            monitor = self._monitor

        try:
            screenshot = self._sct.grab(monitor)
            frame = np.array(screenshot, dtype=np.uint8)[:, :, :3]
        except Exception as e:
            logger.warning(f"截屏失败: {e}")
            if self._last_frame is not None:
                return self._last_frame
            return np.zeros((self.target_h, self.target_w, 3), dtype=np.uint8)

        h, w = frame.shape[:2]
        if w != self.target_w or h != self.target_h:
            frame = cv2.resize(frame, (self.target_w, self.target_h))

        self._last_frame = frame
        self._update_fps()
        return frame

    def save_screenshot(self, filepath: str, frame: Optional[np.ndarray] = None) -> None:
        if frame is None:
            frame = self.grab()
        cv2.imwrite(filepath, frame)
        logger.debug(f"截图: {filepath}")

    @property
    def fps(self) -> float:
        return self._current_fps

    @property
    def screen_center(self) -> Tuple[int, int]:
        """游戏窗口内的中心坐标"""
        return self.target_w // 2, self.target_h // 2

    def _update_fps(self) -> None:
        self._frame_count += 1
        elapsed = time.time() - self._fps_start
        if elapsed >= 1.0:
            self._current_fps = self._frame_count / elapsed
            self._frame_count = 0
            self._fps_start = time.time()

    def __del__(self):
        if hasattr(self, "_sct"):
            try:
                self._sct.close()
            except Exception:
                pass
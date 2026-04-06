"""
游戏窗口管理模块
负责定位游戏窗口位置，计算窗口相对坐标，支持 Windows 平台。
依赖: pywin32 (pip install pywin32)
"""

from typing import Optional, Tuple

from utils.logger import get_logger

log = get_logger(__name__)


class GameWindow:
    """
    管理游戏窗口的定位与坐标转换。

    在 Windows 下通过 win32gui 枚举窗口标题并获取客户区位置和大小。
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
        self._hwnd: Optional[int] = None

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
            result = self._get_window_bounds_windows()
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

    def _get_window_bounds_windows(self) -> Optional[Tuple[int, int, int, int]]:
        """
        使用 win32gui 获取 Windows 窗口位置和大小。

        策略：
          1. 优先查找标题完全匹配的窗口
          2. 其次查找标题包含关键字的窗口
          3. 使用客户区坐标（去除标题栏/边框）

        Returns:
            (x, y, width, height) 屏幕绝对坐标，或 None
        """
        try:
            import win32gui
            import win32con
        except ImportError:
            log.error("pywin32 未安装，请执行: pip install pywin32")
            return None

        # 候选窗口列表：(hwnd, title)
        candidates = []

        def _enum_callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return
            # 完全匹配或包含匹配
            if title == self.window_title or self.window_title in title:
                candidates.append((hwnd, title))

        win32gui.EnumWindows(_enum_callback, None)

        if not candidates:
            return None

        # 优先取完全匹配，否则取第一个包含匹配
        exact = [c for c in candidates if c[1] == self.window_title]
        hwnd, title = (exact[0] if exact else candidates[0])
        self._hwnd = hwnd
        log.debug(f"找到游戏窗口: hwnd={hwnd} title='{title}'")

        # 获取客户区在屏幕中的绝对位置
        # ClientToScreen 获取客户区左上角的屏幕坐标
        try:
            client_left, client_top = win32gui.ClientToScreen(hwnd, (0, 0))
            rect = win32gui.GetClientRect(hwnd)
            client_width = rect[2] - rect[0]
            client_height = rect[3] - rect[1]

            if client_width <= 0 or client_height <= 0:
                log.warning("客户区大小无效，尝试使用窗口矩形")
                window_rect = win32gui.GetWindowRect(hwnd)
                return (
                    window_rect[0],
                    window_rect[1],
                    window_rect[2] - window_rect[0],
                    window_rect[3] - window_rect[1],
                )

            return (client_left, client_top, client_width, client_height)

        except Exception as e:
            log.error(f"获取窗口客户区失败: {e}")
            # fallback: 使用窗口矩形
            window_rect = win32gui.GetWindowRect(hwnd)
            return (
                window_rect[0],
                window_rect[1],
                window_rect[2] - window_rect[0],
                window_rect[3] - window_rect[1],
            )

    def refresh(self) -> bool:
        """
        刷新窗口位置（游戏窗口移动后调用）
        """
        return self.locate()

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

    def bring_to_front(self):
        """将游戏窗口置于最前（确保键鼠操作有效）"""
        if self._hwnd is None:
            return
        try:
            import win32gui
            import win32con
            win32gui.ShowWindow(self._hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self._hwnd)
            log.debug("游戏窗口已置于最前")
        except Exception as e:
            log.warning(f"置前窗口失败: {e}")
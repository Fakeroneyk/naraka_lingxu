"""
屏幕捕获与模板匹配模块
基于 mss 高性能截图，opencv 模板匹配，所有坐标均为窗口相对坐标。
"""

from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import mss
import numpy as np

from utils.logger import get_logger
from utils.window import GameWindow

log = get_logger(__name__)


class ScreenCapture:
    """
    游戏窗口屏幕捕获与模板匹配。

    所有返回坐标均为基于1920x1080的窗口相对坐标。
    """

    def __init__(self, window: GameWindow, template_match_threshold: float = 0.8):
        self._window = window
        self._threshold = template_match_threshold
        self._sct = mss.mss()
        self._template_cache: dict = {}   # 模板图像缓存，避免重复读磁盘

    def capture(self) -> np.ndarray:
        """
        截取游戏窗口当前画面。

        Returns:
            BGR 格式 numpy 数组，形状 (H, W, 3)
        """
        x, y, w, h = self._window.region
        monitor = {"left": x, "top": y, "width": w, "height": h}
        sct_img = self._sct.grab(monitor)
        frame = np.array(sct_img)
        # mss 返回 BGRA，转为 BGR
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        return frame

    def find_template(
        self,
        template_path: str,
        frame: Optional[np.ndarray] = None,
        threshold: Optional[float] = None,
    ) -> Optional[Tuple[int, int]]:
        """
        在画面中寻找单个模板。

        Args:
            template_path: 模板图片路径
            frame: 截图帧（None 则自动截图）
            threshold: 匹配置信度阈值（None 则使用默认值）

        Returns:
            匹配中心的窗口相对坐标 (x, y)，未找到返回 None
        """
        thr = threshold if threshold is not None else self._threshold
        if frame is None:
            frame = self.capture()

        template = self._load_template(template_path)
        if template is None:
            return None

        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= thr:
            th, tw = template.shape[:2]
            cx = max_loc[0] + tw // 2
            cy = max_loc[1] + th // 2
            # 将截图坐标（已是窗口相对坐标）缩放回1920x1080基准
            cx_rel, cy_rel = self._scale_to_relative(cx, cy, frame.shape)
            log.debug(f"模板匹配成功: {template_path} 位置=({cx_rel},{cy_rel}) 置信度={max_val:.3f}")
            return cx_rel, cy_rel

        return None

    def find_any_template(
        self,
        template_list: List[str],
        frame: Optional[np.ndarray] = None,
        threshold: Optional[float] = None,
    ) -> Optional[Tuple[str, Tuple[int, int]]]:
        """
        在模板列表中匹配任意一个。

        Args:
            template_list: 模板路径列表
            frame: 截图帧（None 则自动截图一次后复用）
            threshold: 匹配置信度阈值

        Returns:
            (匹配到的模板路径, (cx, cy))，全未匹配返回 None
        """
        if frame is None:
            frame = self.capture()

        for tpl_path in template_list:
            pos = self.find_template(tpl_path, frame=frame, threshold=threshold)
            if pos is not None:
                return tpl_path, pos

        return None

    def _load_template(self, template_path: str) -> Optional[np.ndarray]:
        """加载模板图像（带缓存）"""
        if template_path in self._template_cache:
            return self._template_cache[template_path]

        path = Path(template_path)
        if not path.exists():
            log.warning(f"模板文件不存在: {template_path}")
            return None

        tpl = cv2.imread(str(path))
        if tpl is None:
            log.error(f"模板文件读取失败: {template_path}")
            return None

        self._template_cache[template_path] = tpl
        return tpl

    def _scale_to_relative(
        self, px: int, py: int, frame_shape: Tuple
    ) -> Tuple[int, int]:
        """
        将截图像素坐标缩放为1920x1080的相对坐标。
        如果实际窗口大小与目标分辨率不符，进行等比换算。
        """
        h, w = frame_shape[:2]
        rx = int(px * self._window.target_width / w)
        ry = int(py * self._window.target_height / h)
        return rx, ry

    def clear_cache(self):
        """清空模板缓存（模板文件更新后调用）"""
        self._template_cache.clear()
        log.debug("模板缓存已清空")
"""UI状态检测 - OpenCV模板匹配检测游戏UI状态"""

import os
from pathlib import Path
from typing import Optional, Tuple, Dict, List

import cv2
import numpy as np
from loguru import logger

from core.config import Config


class UIDetector:
    """UI状态检测器

    使用OpenCV模板匹配检测各种游戏UI面板状态，
    如灵诀选择面板、占点UI、死亡画面等。
    """

    def __init__(self, config: Config):
        """
        Args:
            config: 全局配置
        """
        self.confidence = config.detection.ui_confidence
        self._templates: Dict[str, np.ndarray] = {}
        self._template_dir = Path(__file__).parent / "templates"

        # 确保模板目录存在
        self._template_dir.mkdir(parents=True, exist_ok=True)

        # 加载所有模板图片
        self._load_templates()

        logger.info(
            f"UI检测器初始化 | 置信度: {self.confidence} | "
            f"已加载模板: {len(self._templates)} 个"
        )

    def _load_templates(self) -> None:
        """加载templates目录下的所有PNG模板图片"""
        if not self._template_dir.exists():
            logger.warning(f"模板目录不存在: {self._template_dir}")
            return

        for filepath in self._template_dir.glob("*.png"):
            name = filepath.stem  # 文件名不带扩展名
            template = cv2.imread(str(filepath), cv2.IMREAD_COLOR)
            if template is not None:
                self._templates[name] = template
                logger.debug(f"已加载模板: {name} ({template.shape})")
            else:
                logger.warning(f"无法加载模板: {filepath}")

    def match_template(
        self,
        frame: np.ndarray,
        template_name: str,
        confidence: Optional[float] = None,
    ) -> Optional[Tuple[int, int, float]]:
        """模板匹配

        Args:
            frame: BGR格式截屏帧
            template_name: 模板名称（不含.png后缀）
            confidence: 置信度阈值，None使用默认值

        Returns:
            匹配成功返回 (center_x, center_y, score)，失败返回 None
        """
        if template_name not in self._templates:
            logger.warning(f"模板不存在: {template_name}")
            return None

        template = self._templates[template_name]
        threshold = confidence or self.confidence

        # 模板匹配
        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            th, tw = template.shape[:2]
            center_x = max_loc[0] + tw // 2
            center_y = max_loc[1] + th // 2
            return center_x, center_y, max_val

        return None

    def match_template_all(
        self,
        frame: np.ndarray,
        template_name: str,
        confidence: Optional[float] = None,
    ) -> List[Tuple[int, int, float]]:
        """查找所有匹配位置

        Args:
            frame: BGR格式截屏帧
            template_name: 模板名称
            confidence: 置信度阈值

        Returns:
            所有匹配位置列表 [(center_x, center_y, score), ...]
        """
        if template_name not in self._templates:
            return []

        template = self._templates[template_name]
        threshold = confidence or self.confidence

        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)

        matches = []
        th, tw = template.shape[:2]
        for pt in zip(*locations[::-1]):
            center_x = pt[0] + tw // 2
            center_y = pt[1] + th // 2
            score = result[pt[1], pt[0]]
            matches.append((center_x, center_y, float(score)))

        # 非极大值抑制（去重）
        return self._nms(matches, distance_threshold=50)

    def is_jue_panel(self, frame: np.ndarray) -> bool:
        """检测是否出现灵诀选择面板

        Args:
            frame: BGR格式截屏帧

        Returns:
            True表示灵诀面板出现
        """
        return self.match_template(frame, "jue_panel") is not None

    def is_capture_point(self, frame: np.ndarray) -> bool:
        """检测是否在占点模式

        Args:
            frame: BGR格式截屏帧

        Returns:
            True表示占点UI出现
        """
        return self.match_template(frame, "capture_point") is not None

    def is_death_screen(self, frame: np.ndarray) -> bool:
        """检测是否死亡画面

        Args:
            frame: BGR格式截屏帧

        Returns:
            True表示死亡画面出现
        """
        return self.match_template(frame, "death_screen") is not None

    def is_loading(self, frame: np.ndarray) -> bool:
        """检测是否在加载画面

        通过检测画面亮度和变化判断。

        Args:
            frame: BGR格式截屏帧

        Returns:
            True表示在加载中
        """
        # 方案1：检测加载模板
        if self.match_template(frame, "loading") is not None:
            return True

        # 方案2：全黑/全暗画面检测
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        return mean_brightness < 20  # 非常暗的画面可能是加载中

    def add_template(self, name: str, image: np.ndarray) -> None:
        """动态添加模板

        Args:
            name: 模板名称
            image: BGR格式模板图片
        """
        self._templates[name] = image
        # 同时保存到文件
        filepath = self._template_dir / f"{name}.png"
        cv2.imwrite(str(filepath), image)
        logger.info(f"已添加模板: {name}")

    @staticmethod
    def _nms(
        matches: List[Tuple[int, int, float]],
        distance_threshold: int = 50,
    ) -> List[Tuple[int, int, float]]:
        """非极大值抑制，去除重叠的匹配结果"""
        if not matches:
            return []

        # 按score降序排序
        matches = sorted(matches, key=lambda m: m[2], reverse=True)
        kept = []

        for match in matches:
            is_duplicate = False
            for kept_match in kept:
                dx = match[0] - kept_match[0]
                dy = match[1] - kept_match[1]
                dist = (dx ** 2 + dy ** 2) ** 0.5
                if dist < distance_threshold:
                    is_duplicate = True
                    break
            if not is_duplicate:
                kept.append(match)

        return kept
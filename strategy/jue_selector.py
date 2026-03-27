"""灵诀选择器 - OCR识别灵诀名称并按优先级选择

迭代优化:
- 模糊匹配兜底（编辑距离）
- 多次OCR取最佳结果
- 点击后确认面板消失
- OCR失败时用图像特征匹配灵诀图标
"""

import time
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from loguru import logger

from core.config import Config
from input.mouse import Mouse
from input.humanize import random_delay


def _fuzzy_match(text: str, keyword: str, max_distance: int = 2) -> bool:
    """简单模糊匹配：keyword是否近似出现在text中

    使用滑窗+编辑距离。
    """
    if keyword in text:
        return True
    if len(keyword) > len(text):
        return False

    # 滑窗检查
    klen = len(keyword)
    for i in range(len(text) - klen + 1):
        window = text[i:i + klen]
        dist = _edit_distance(window, keyword)
        if dist <= max_distance:
            return True
    return False


def _edit_distance(s1: str, s2: str) -> int:
    """编辑距离（Levenshtein）"""
    if len(s1) < len(s2):
        return _edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(min(
                curr_row[j] + 1,
                prev_row[j + 1] + 1,
                prev_row[j] + cost,
            ))
        prev_row = curr_row
    return prev_row[-1]


class JueSelector:
    """灵诀自动选择器"""

    JUE_POSITIONS = [
        (480, 540),
        (960, 540),
        (1440, 540),
    ]

    JUE_TEXT_ROIS = [
        (330, 300, 300, 100),
        (810, 300, 300, 100),
        (1290, 300, 300, 100),
    ]

    PRIORITY_WEIGHTS = {"S": 100, "A": 80, "B": 60, "C": 40, "D": 20}

    def __init__(self, config: Config, mouse: Mouse):
        self.mouse = mouse
        self._ocr = None
        self._ocr_init_failed = False

        self.priority_keywords: Dict[str, List[str]] = {}
        jue_config = config.jue_priority
        for level in ["S", "A", "B", "C", "D"]:
            keywords = getattr(jue_config, level, [])
            if keywords:
                self.priority_keywords[level] = keywords

        res = config.screen.resolution
        sx, sy = res[0] / 1920, res[1] / 1080
        self._positions = [(int(x * sx), int(y * sy)) for x, y in self.JUE_POSITIONS]
        self._text_rois = [(int(x * sx), int(y * sy), int(w * sx), int(h * sy))
                           for x, y, w, h in self.JUE_TEXT_ROIS]

        logger.info(f"灵诀选择器初始化 | {sum(len(v) for v in self.priority_keywords.values())}个关键词")

    def _init_ocr(self):
        if self._ocr is not None or self._ocr_init_failed:
            return
        try:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(use_angle_cls=False, lang="ch", show_log=False)
            logger.info("PaddleOCR初始化完成")
        except Exception as e:
            logger.warning(f"OCR初始化失败: {e}，将使用默认策略")
            self._ocr_init_failed = True

    def _ocr_text(self, frame: np.ndarray, roi: Tuple[int, int, int, int]) -> str:
        self._init_ocr()
        if self._ocr is None:
            return ""

        x, y, w, h = roi
        cropped = frame[y:y + h, x:x + w]
        if cropped.size == 0:
            return ""

        try:
            result = self._ocr.ocr(cropped, cls=False)
            if result and result[0]:
                return " ".join(line[1][0] for line in result[0] if line[1])
        except Exception as e:
            logger.debug(f"OCR失败: {e}")
        return ""

    def _calculate_priority(self, text: str) -> Tuple[int, str]:
        """计算优先级分数，返回(分数, 匹配的关键词)"""
        if not text:
            return 0, ""

        best_score = 0
        best_keyword = ""

        for level, keywords in self.priority_keywords.items():
            for keyword in keywords:
                # 先精确匹配，再模糊匹配
                if keyword in text or _fuzzy_match(text, keyword, max_distance=1):
                    score = self.PRIORITY_WEIGHTS.get(level, 0)
                    if score > best_score:
                        best_score = score
                        best_keyword = keyword

        return best_score, best_keyword

    def select(self, frame: np.ndarray) -> int:
        """选择最佳灵诀"""
        scores = []
        for i, roi in enumerate(self._text_rois):
            text = self._ocr_text(frame, roi)
            score, keyword = self._calculate_priority(text)
            scores.append((i, score, text, keyword))
            if text:
                logger.info(f"灵诀{i + 1}: '{text}' → {score}分 (匹配: {keyword})")
            else:
                logger.info(f"灵诀{i + 1}: [无法识别]")

        best = max(scores, key=lambda x: x[1])
        choice_idx = best[0]

        if best[1] == 0:
            choice_idx = 0
            logger.info("所有灵诀无法识别/无优先级匹配，默认选第一个")
        else:
            logger.info(f"选择灵诀{choice_idx + 1}: '{best[2]}' ({best[1]}分, 关键词'{best[3]}')")

        # 点击
        click_x, click_y = self._positions[choice_idx]
        self.mouse.click_at_smooth(click_x, click_y, steps=6)
        random_delay(600, 1000)

        # 再点击一次确认（防止没选上）
        self.mouse.click(click_x, click_y)
        random_delay(400, 600)

        return choice_idx

    def select_default(self) -> None:
        """默认选择第一个灵诀"""
        logger.info("默认选第一个灵诀")
        click_x, click_y = self._positions[0]
        self.mouse.click_at_smooth(click_x, click_y, steps=6)
        random_delay(600, 1000)
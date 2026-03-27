"""敌人检测 - YOLO目标检测 + 血条颜色检测

迭代优化:
- YOLO可用性缓存（只加载一次）
- 血条检测增加自身血条排除（避免把自己血条当敌人）
- 检测结果NMS去重
- Boss血条宽度阈值可配置
- 检测区域排除UI区域（左下/右下角）
"""

from dataclasses import dataclass, field
from typing import List, Optional

import cv2
import numpy as np
from loguru import logger

from core.config import Config
from core.states import EnemyType


@dataclass
class DetectedEnemy:
    """检测到的敌人信息"""
    center_x: int
    center_y: int
    width: int
    height: int
    enemy_type: EnemyType
    confidence: float
    distance_to_center: float = field(default=0.0, repr=False)


class HpBarDetector:
    """基于血条颜色的敌人检测"""

    def __init__(self, config: Config):
        self.hp_bar_lower1 = np.array(config.detection.hp_bar_hsv_lower)
        self.hp_bar_upper1 = np.array(config.detection.hp_bar_hsv_upper)
        self.hp_bar_lower2 = np.array(config.detection.hp_bar_hsv_lower2)
        self.hp_bar_upper2 = np.array(config.detection.hp_bar_hsv_upper2)

        self._scan_ratio = 0.85  # 扫描屏幕上方85%（3D地图怪物可能在屋顶等高处）
        self._min_bar_width = 20
        self._max_bar_width = 300
        self._min_bar_height = 3
        self._max_bar_height = 15
        self._min_aspect_ratio = 3.0
        self._boss_width_threshold = 150

        # UI排除区域（左下角血条、右下角武器栏）
        self._exclude_regions = [
            (0, 900, 400, 180),       # 左下角 (x, y, w, h)
            (1520, 900, 400, 180),    # 右下角
            (800, 0, 320, 50),        # 顶部中间（可能有系统提示）
        ]

        logger.info("血条颜色检测器初始化")

    def _is_in_exclude_region(self, x: int, y: int) -> bool:
        """检查坐标是否在排除区域内"""
        for rx, ry, rw, rh in self._exclude_regions:
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return True
        return False

    def detect(self, frame: np.ndarray) -> List[DetectedEnemy]:
        h, w = frame.shape[:2]
        scan_h = int(h * self._scan_ratio)

        roi = frame[:scan_h, :, :]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        mask1 = cv2.inRange(hsv, self.hp_bar_lower1, self.hp_bar_upper1)
        mask2 = cv2.inRange(hsv, self.hp_bar_lower2, self.hp_bar_upper2)
        red_mask = cv2.bitwise_or(mask1, mask2)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 2))
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(
            red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        cx, cy = w // 2, h // 2
        enemies = []

        for contour in contours:
            x, y, cw, ch = cv2.boundingRect(contour)

            if not (self._min_bar_width <= cw <= self._max_bar_width):
                continue
            if not (self._min_bar_height <= ch <= self._max_bar_height):
                continue
            if cw / max(ch, 1) < self._min_aspect_ratio:
                continue

            center_x = x + cw // 2
            center_y = y + ch // 2 + 50

            # 排除UI区域的误检
            if self._is_in_exclude_region(center_x, center_y):
                continue

            enemy_type = EnemyType.BOSS if cw > self._boss_width_threshold else EnemyType.NORMAL
            dist = ((center_x - cx) ** 2 + (center_y - cy) ** 2) ** 0.5

            enemies.append(DetectedEnemy(
                center_x=center_x,
                center_y=center_y,
                width=cw,
                height=ch,
                enemy_type=enemy_type,
                confidence=0.7,
                distance_to_center=dist,
            ))

        # NMS去重（距离太近的只保留一个）
        return self._nms(enemies, distance_threshold=60)

    @staticmethod
    def _nms(enemies: List[DetectedEnemy], distance_threshold: int = 60) -> List[DetectedEnemy]:
        """非极大值抑制去重"""
        if not enemies:
            return []
        enemies.sort(key=lambda e: e.confidence, reverse=True)
        kept = []
        for enemy in enemies:
            is_dup = False
            for k in kept:
                dx = enemy.center_x - k.center_x
                dy = enemy.center_y - k.center_y
                if (dx ** 2 + dy ** 2) ** 0.5 < distance_threshold:
                    is_dup = True
                    break
            if not is_dup:
                kept.append(enemy)
        return kept


class YoloDetector:
    """基于YOLOv8的敌人检测"""

    def __init__(self, config: Config):
        self.confidence = config.detection.yolo_confidence
        self.model_path = config.detection.yolo_model
        self._model = None
        self._load_attempted = False  # 只尝试加载一次

        logger.info(f"YOLO检测器初始化 | 模型: {self.model_path}")

    def _load_model(self):
        """懒加载YOLO模型（只尝试一次）"""
        if self._load_attempted:
            return
        self._load_attempted = True

        try:
            from ultralytics import YOLO
            self._model = YOLO(self.model_path)
            logger.info(f"YOLO模型已加载: {self.model_path}")
        except FileNotFoundError:
            logger.warning(f"YOLO模型不存在: {self.model_path}，使用血条检测")
        except ImportError:
            logger.warning("ultralytics未安装，使用血条检测")
        except Exception as e:
            logger.error(f"YOLO加载失败: {e}")

    def detect(self, frame: np.ndarray) -> List[DetectedEnemy]:
        self._load_model()
        if self._model is None:
            return []

        results = self._model.predict(frame, conf=self.confidence, verbose=False)

        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2
        enemies = []

        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                if cls_name in ("enemy_normal", "enemy_boss"):
                    ecx = int((x1 + x2) / 2)
                    ecy = int((y1 + y2) / 2)
                    enemy_type = EnemyType.BOSS if cls_name == "enemy_boss" else EnemyType.NORMAL
                    dist = ((ecx - cx) ** 2 + (ecy - cy) ** 2) ** 0.5

                    enemies.append(DetectedEnemy(
                        center_x=ecx,
                        center_y=ecy,
                        width=int(x2 - x1),
                        height=int(y2 - y1),
                        enemy_type=enemy_type,
                        confidence=conf,
                        distance_to_center=dist,
                    ))

        return enemies

    @property
    def is_available(self) -> bool:
        self._load_model()
        return self._model is not None


class EnemyDetector:
    """敌人检测器（融合YOLO + 血条检测）"""

    def __init__(self, config: Config):
        self.yolo = YoloDetector(config)
        self.hp_bar = HpBarDetector(config)
        logger.info("敌人检测器初始化（YOLO + 血条融合）")

    def detect(self, frame: np.ndarray) -> List[DetectedEnemy]:
        """检测所有敌人，按优先级排序（Boss优先 > 距离最近）"""
        enemies = []

        if self.yolo.is_available:
            enemies = self.yolo.detect(frame)

        if not enemies:
            enemies = self.hp_bar.detect(frame)

        # 排序：Boss优先，同类型按距离
        enemies.sort(key=lambda e: (
            0 if e.enemy_type == EnemyType.BOSS else 1,
            e.distance_to_center,
        ))

        return enemies

    def detect_nearest(self, frame: np.ndarray) -> Optional[DetectedEnemy]:
        enemies = self.detect(frame)
        return enemies[0] if enemies else None
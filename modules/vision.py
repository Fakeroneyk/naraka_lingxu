"""
视觉识别模块
基于 YOLOv8 进行传送门和占点圈的目标检测，支持多角度鲁棒识别。

类别映射:
  0: portal_purple  (紫色传送门, 1-3关)
  1: portal_gold    (金色传送门, 第4关商店)
  2: portal_red     (红色传送门, 第5关boss)
  3: capture_zone   (占点圈)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from utils.logger import get_logger

log = get_logger(__name__)

# 类别名称常量
CLASS_PORTAL_PURPLE = "紫门"
CLASS_PORTAL_GOLD = "金门"
CLASS_PORTAL_RED = "红门"
CLASS_CAPTURE_ZONE = "站点"

# 类别ID → 名称映射
CLASS_NAMES = {
    0: CLASS_PORTAL_PURPLE,
    1: CLASS_PORTAL_GOLD,
    2: CLASS_PORTAL_RED,
    3: CLASS_CAPTURE_ZONE,
}

# 传送门类别名称 → 关卡阶段映射
PORTAL_TYPE_MAP = {
    "purple": CLASS_PORTAL_PURPLE,
    "gold": CLASS_PORTAL_GOLD,
    "red": CLASS_PORTAL_RED,
}


@dataclass
class Detection:
    """单个检测结果"""
    class_name: str          # 类别名称
    class_id: int            # 类别ID
    confidence: float        # 置信度
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2) 像素坐标
    center: Tuple[int, int]  # (cx, cy) 中心点像素坐标
    area: int                # 面积（像素²）


class ObjectDetector:
    """
    基于 YOLOv8 的统一目标检测器。
    单模型4分类检测传送门（紫/金/红）和占点圈。
    """

    def __init__(self, model_path: str, confidence: float = 0.6):
        self._model = None
        self._model_path = model_path
        self._confidence = confidence
        self._loaded = False

    def load(self) -> bool:
        """
        加载 YOLO 模型。
        延迟加载，首次调用 detect 时自动加载。

        Returns:
            是否加载成功
        """
        try:
            from ultralytics import YOLO
            path = Path(self._model_path)
            if not path.exists():
                log.warning(f"YOLO 模型文件不存在: {self._model_path}，检测功能不可用")
                return False
            self._model = YOLO(str(path))
            self._loaded = True
            log.info(f"YOLO 模型加载成功: {self._model_path}")
            return True
        except ImportError:
            log.error("ultralytics 未安装，请执行: pip install ultralytics")
            return False
        except Exception as e:
            log.error(f"YOLO 模型加载失败: {e}")
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        在帧中检测所有目标。

        Args:
            frame: BGR 格式 numpy 数组

        Returns:
            检测结果列表
        """
        if not self._loaded:
            if not self.load():
                return []

        try:
            results = self._model(frame, conf=self._confidence, verbose=False)
            #log.info(f"YOLO 检测完成: {len(results)} 结果")
            detections = []
            for r in results:
                if r.boxes is None:
                    continue
                for box in r.boxes:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    x1, y1, x2, y2 = [int(v.item()) for v in box.xyxy[0]]
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    area = (x2 - x1) * (y2 - y1)
                    cls_name = CLASS_NAMES.get(cls_id, f"unknown_{cls_id}")
                    detections.append(Detection(
                        class_name=cls_name,
                        class_id=cls_id,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        center=(cx, cy),
                        area=area,
                    ))
            return detections
        except Exception as e:
            log.error(f"YOLO 推理异常: {e}")
            return []

    def detect_portals(
        self, frame: np.ndarray, portal_type: str
    ) -> List[Detection]:
        """
        检测指定类型的传送门。

        Args:
            frame: BGR 帧
            portal_type: "purple" / "gold" / "red"

        Returns:
            匹配的传送门检测结果列表（按置信度降序）
        """
        target_class = PORTAL_TYPE_MAP.get(portal_type)
        if target_class is None:
            log.info(f"未知传送门类型: {portal_type}")
            return []

        all_detections = self.detect(frame)
        portals = [d for d in all_detections if d.class_name == target_class]
        portals.sort(key=lambda d: d.confidence, reverse=True)

        if portals:
            best = portals[0]
            log.info(
                f"检测到 {portal_type} 传送门: "
                f"中心=({best.center[0]},{best.center[1]}) "
                f"置信度={best.confidence:.2f} 面积={best.area}"
            )
        return portals

    def detect_capture_zone(self, frame: np.ndarray) -> Optional[Detection]:
        """
        检测占点圈。

        Args:
            frame: BGR 帧

        Returns:
            占点圈检测结果（置信度最高），或 None
        """
        all_detections = self.detect(frame)
        zones = [d for d in all_detections if d.class_name == CLASS_CAPTURE_ZONE]
        zones.sort(key=lambda d: d.confidence, reverse=True)

        if zones:
            best = zones[0]
            log.debug(
                f"检测到占点圈: 中心=({best.center[0]},{best.center[1]}) "
                f"置信度={best.confidence:.2f}"
            )
            return best
        return None

    def get_portal_screen_position(
        self, frame: np.ndarray, portal_type: str, frame_width: int
    ) -> Optional[str]:
        """
        判断传送门在画面中的位置方向。

        Args:
            frame: BGR 帧
            portal_type: "purple" / "gold" / "red"
            frame_width: 帧宽度

        Returns:
            "left" / "center" / "right" / None（未检测到）
        """
        portals = self.detect_portals(frame, portal_type)
        if not portals:
            log.info(f"未检测到 {portal_type} 传送门")
            return None

        cx = portals[0].center[0]
        third = frame_width // 3
        if cx < third:
            return "left"
        elif cx < 2 * third:
            return "center"
        else:
            return "right"

    def is_portal_close(
        self, frame: np.ndarray, portal_type: str, close_ratio: float
    ) -> bool:
        """
        判断传送门是否已经足够近（可以交互）。

        Args:
            frame: BGR 帧
            portal_type: 传送门类型
            close_ratio: 面积占比阈值

        Returns:
            是否够近
        """
        portals = self.detect_portals(frame, portal_type)
        if not portals:
            return False

        frame_area = frame.shape[0] * frame.shape[1]
        portal_ratio = portals[0].area / frame_area
        log.info(f"传送门面积占比: {portal_ratio:.4f} (阈值: {close_ratio})")
        return portal_ratio >= close_ratio
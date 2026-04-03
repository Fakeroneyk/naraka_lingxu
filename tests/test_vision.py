"""
单点测试: modules/vision.py
测试 ObjectDetector 的传送门/占点圈检测逻辑。
使用 Mock 替代真实 YOLO 模型。
"""

from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytest

from modules.vision import (
    ObjectDetector, Detection,
    CLASS_PORTAL_PURPLE, CLASS_PORTAL_GOLD, CLASS_PORTAL_RED, CLASS_CAPTURE_ZONE,
)


def _make_mock_yolo_result(detections_data):
    """
    构造 Mock YOLO 推理结果。

    detections_data: list of (class_id, confidence, x1, y1, x2, y2)
    """
    mock_result = MagicMock()
    boxes_list = []
    for cls_id, conf, x1, y1, x2, y2 in detections_data:
        box = MagicMock()
        box.cls = [MagicMock(item=MagicMock(return_value=cls_id))]
        box.conf = [MagicMock(item=MagicMock(return_value=conf))]
        xyxy_tensor = MagicMock()
        xyxy_tensor.__getitem__ = MagicMock(return_value=[
            MagicMock(item=MagicMock(return_value=x1)),
            MagicMock(item=MagicMock(return_value=y1)),
            MagicMock(item=MagicMock(return_value=x2)),
            MagicMock(item=MagicMock(return_value=y2)),
        ])
        box.xyxy = xyxy_tensor
        boxes_list.append(box)
    mock_result.boxes = boxes_list
    return [mock_result]


@pytest.fixture
def detector():
    """创建 ObjectDetector 并标记为已加载（跳过真实模型加载）"""
    det = ObjectDetector("fake_model.pt", confidence=0.6)
    det._loaded = True
    det._model = MagicMock()
    return det


class TestObjectDetectorLoad:

    def test_load_missing_file(self):
        """模型文件不存在时，load() 返回 False"""
        det = ObjectDetector("nonexistent/model.pt")
        result = det.load()
        assert result is False
        assert not det.is_loaded

    def test_is_loaded_default_false(self):
        """初始化后 is_loaded 为 False"""
        det = ObjectDetector("some.pt")
        assert not det.is_loaded


class TestObjectDetectorDetect:

    def test_detect_returns_detections(self, detector, fake_frame):
        """detect 返回正确的 Detection 对象列表"""
        detector._model.return_value = _make_mock_yolo_result([
            (0, 0.92, 100, 200, 300, 400),  # portal_purple
            (3, 0.85, 500, 600, 700, 800),  # capture_zone
        ])

        results = detector.detect(fake_frame)

        assert len(results) == 2
        assert results[0].class_name == CLASS_PORTAL_PURPLE
        assert results[0].confidence == 0.92
        assert results[0].center == (200, 300)
        assert results[0].area == 200 * 200
        assert results[1].class_name == CLASS_CAPTURE_ZONE

    def test_detect_empty_when_no_boxes(self, detector, fake_frame):
        """YOLO 无检测结果时返回空列表"""
        mock_result = MagicMock()
        mock_result.boxes = None
        detector._model.return_value = [mock_result]

        results = detector.detect(fake_frame)
        assert results == []


class TestPortalDetection:

    def test_detect_portals_purple(self, detector, fake_frame):
        """detect_portals("purple") 过滤出紫色传送门"""
        detector._model.return_value = _make_mock_yolo_result([
            (0, 0.90, 100, 200, 300, 400),  # portal_purple
            (1, 0.80, 500, 200, 700, 400),  # portal_gold
            (0, 0.75, 800, 200, 1000, 400), # portal_purple (置信度低)
        ])

        portals = detector.detect_portals(fake_frame, "purple")

        assert len(portals) == 2
        # 按置信度降序
        assert portals[0].confidence == 0.90
        assert portals[1].confidence == 0.75
        for p in portals:
            assert p.class_name == CLASS_PORTAL_PURPLE

    def test_detect_portals_gold(self, detector, fake_frame):
        """detect_portals("gold") 过滤出金色传送门"""
        detector._model.return_value = _make_mock_yolo_result([
            (0, 0.90, 100, 200, 300, 400),  # portal_purple
            (1, 0.85, 500, 200, 700, 400),  # portal_gold
        ])

        portals = detector.detect_portals(fake_frame, "gold")
        assert len(portals) == 1
        assert portals[0].class_name == CLASS_PORTAL_GOLD

    def test_detect_portals_red(self, detector, fake_frame):
        """detect_portals("red") 过滤出红色传送门"""
        detector._model.return_value = _make_mock_yolo_result([
            (2, 0.88, 100, 100, 400, 500),  # portal_red
        ])

        portals = detector.detect_portals(fake_frame, "red")
        assert len(portals) == 1
        assert portals[0].class_name == CLASS_PORTAL_RED

    def test_detect_portals_none_found(self, detector, fake_frame):
        """目标类型传送门不存在时返回空列表"""
        detector._model.return_value = _make_mock_yolo_result([
            (0, 0.90, 100, 200, 300, 400),  # purple
        ])

        portals = detector.detect_portals(fake_frame, "red")
        assert portals == []

    def test_detect_portals_unknown_type(self, detector, fake_frame):
        """未知传送门类型返回空列表"""
        portals = detector.detect_portals(fake_frame, "unknown")
        assert portals == []


class TestCaptureZoneDetection:

    def test_detect_capture_zone_success(self, detector, fake_frame):
        """检测到占点圈时返回最高置信度的结果"""
        detector._model.return_value = _make_mock_yolo_result([
            (3, 0.70, 400, 400, 800, 800),  # capture_zone
            (3, 0.90, 500, 500, 900, 900),  # capture_zone (更高置信度)
        ])

        zone = detector.detect_capture_zone(fake_frame)
        assert zone is not None
        assert zone.confidence == 0.90
        assert zone.class_name == CLASS_CAPTURE_ZONE

    def test_detect_capture_zone_not_found(self, detector, fake_frame):
        """无占点圈时返回 None"""
        detector._model.return_value = _make_mock_yolo_result([
            (0, 0.90, 100, 200, 300, 400),  # portal_purple only
        ])

        zone = detector.detect_capture_zone(fake_frame)
        assert zone is None


class TestPortalScreenPosition:

    def test_position_left(self, detector, fake_frame):
        """传送门在画面左侧1/3 → 返回 'left'"""
        detector._model.return_value = _make_mock_yolo_result([
            (0, 0.90, 100, 200, 300, 400),  # center_x = 200 < 640
        ])

        pos = detector.get_portal_screen_position(fake_frame, "purple", 1920)
        assert pos == "left"

    def test_position_center(self, detector, fake_frame):
        """传送门在画面中间1/3 → 返回 'center'"""
        detector._model.return_value = _make_mock_yolo_result([
            (0, 0.90, 800, 200, 1000, 400),  # center_x = 900, 640 < 900 < 1280
        ])

        pos = detector.get_portal_screen_position(fake_frame, "purple", 1920)
        assert pos == "center"

    def test_position_right(self, detector, fake_frame):
        """传送门在画面右侧1/3 → 返回 'right'"""
        detector._model.return_value = _make_mock_yolo_result([
            (0, 0.90, 1500, 200, 1800, 400),  # center_x = 1650 > 1280
        ])

        pos = detector.get_portal_screen_position(fake_frame, "purple", 1920)
        assert pos == "right"

    def test_position_none_when_not_found(self, detector, fake_frame):
        """画面中无目标传送门 → 返回 None"""
        mock_result = MagicMock()
        mock_result.boxes = None
        detector._model.return_value = [mock_result]

        pos = detector.get_portal_screen_position(fake_frame, "purple", 1920)
        assert pos is None


class TestPortalCloseness:

    def test_is_portal_close_true(self, detector, fake_frame):
        """传送门bbox面积超过阈值时返回 True"""
        # frame 面积 = 1920 * 1080 = 2073600
        # bbox (0,0,500,500) → area = 250000 → ratio ≈ 0.12 > 0.05
        detector._model.return_value = _make_mock_yolo_result([
            (0, 0.90, 0, 0, 500, 500),
        ])

        result = detector.is_portal_close(fake_frame, "purple", 0.05)
        assert result is True

    def test_is_portal_close_false(self, detector, fake_frame):
        """传送门bbox面积不足阈值时返回 False"""
        # bbox (0,0,50,50) → area = 2500 → ratio ≈ 0.0012 < 0.05
        detector._model.return_value = _make_mock_yolo_result([
            (0, 0.90, 0, 0, 50, 50),
        ])

        result = detector.is_portal_close(fake_frame, "purple", 0.05)
        assert result is False

    def test_is_portal_close_no_portal(self, detector, fake_frame):
        """没有传送门时返回 False"""
        mock_result = MagicMock()
        mock_result.boxes = None
        detector._model.return_value = [mock_result]

        result = detector.is_portal_close(fake_frame, "purple", 0.05)
        assert result is False
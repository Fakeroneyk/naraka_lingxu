"""
单点测试: core/screen.py
测试 ScreenCapture 模板匹配、缓存、坐标缩放。
所有测试均使用 Mock，无需真实游戏窗口或截图。
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from core.screen import ScreenCapture


def _make_template_in_frame(frame: np.ndarray, template: np.ndarray, x: int, y: int) -> np.ndarray:
    """将 template 嵌入 frame 的指定位置，用于构造可匹配的测试画面"""
    h, w = template.shape[:2]
    result = frame.copy()
    result[y:y+h, x:x+w] = template
    return result


class TestScreenCapture:

    def setup_method(self):
        """每个测试前创建 Mock Window 和 ScreenCapture 实例"""
        self.mock_window = MagicMock()
        self.mock_window.found = True
        self.mock_window.region = (0, 0, 1920, 1080)
        self.mock_window.target_width = 1920
        self.mock_window.target_height = 1080
        # relative_to_absolute 直接透传
        self.mock_window.relative_to_absolute.side_effect = lambda x, y: (x, y)

        self.sc = ScreenCapture(self.mock_window, template_match_threshold=0.85)

    # ─────────────── 模板匹配测试 ───────────────

    def test_find_template_success(self, tmp_path):
        """
        模板在画面中存在时，find_template 返回正确的相对坐标。
        """
        # 构造一个有颜色区块的模板
        template = np.full((50, 80, 3), (0, 255, 0), dtype=np.uint8)  # 绿色块
        tpl_path = str(tmp_path / "test_tpl.png")
        cv2.imwrite(tpl_path, template)

        # 构造含模板的帧（模板放在 (200, 300)）
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame[300:350, 200:280] = template

        result = self.sc.find_template(tpl_path, frame=frame)

        assert result is not None
        cx, cy = result
        # 模板中心约为 (200+40, 300+25) = (240, 325)，允许±5像素误差
        assert abs(cx - 240) <= 5
        assert abs(cy - 325) <= 5

    def test_find_template_not_found(self, tmp_path):
        """模板不在画面中时，find_template 返回 None"""
        # 模板：红色块
        template = np.full((50, 80, 3), (0, 0, 255), dtype=np.uint8)
        tpl_path = str(tmp_path / "red_tpl.png")
        cv2.imwrite(tpl_path, template)

        # 帧：全绿（不含模板）
        frame = np.full((1080, 1920, 3), (0, 255, 0), dtype=np.uint8)

        result = self.sc.find_template(tpl_path, frame=frame)
        assert result is None

    def test_find_template_missing_file(self):
        """模板文件不存在时，find_template 返回 None 不抛异常"""
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        result = self.sc.find_template("nonexistent/path/template.png", frame=frame)
        assert result is None

    def test_find_template_uses_provided_frame(self, tmp_path):
        """提供 frame 参数时不重新截图（mss 不被调用）"""
        template = np.full((30, 30, 3), 128, dtype=np.uint8)
        tpl_path = str(tmp_path / "gray_tpl.png")
        cv2.imwrite(tpl_path, template)

        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame[100:130, 100:130] = template

        with patch.object(self.sc, '_sct') as mock_sct:
            self.sc.find_template(tpl_path, frame=frame)
            # 不应调用 mss.grab
            mock_sct.grab.assert_not_called()

    # ─────────────── 模板列表测试 ───────────────

    def test_find_any_template_returns_first_match(self, tmp_path):
        """find_any_template 返回列表中第一个匹配的模板路径和坐标"""
        t1 = np.full((40, 60, 3), 50, dtype=np.uint8)
        t2 = np.full((40, 60, 3), 200, dtype=np.uint8)

        tpl1 = str(tmp_path / "t1.png")
        tpl2 = str(tmp_path / "t2.png")
        cv2.imwrite(tpl1, t1)
        cv2.imwrite(tpl2, t2)

        # 帧中只放 t1
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame[400:440, 300:360] = t1

        result = self.sc.find_any_template([tpl1, tpl2], frame=frame)

        assert result is not None
        matched_path, pos = result
        assert matched_path == tpl1
        assert pos is not None

    def test_find_any_template_no_match(self, tmp_path):
        """所有模板均不在画面中时，find_any_template 返回 None"""
        t1 = np.full((40, 60, 3), 200, dtype=np.uint8)
        tpl1 = str(tmp_path / "t1.png")
        cv2.imwrite(tpl1, t1)

        # 帧中不含 t1
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

        result = self.sc.find_any_template([tpl1], frame=frame)
        assert result is None

    def test_find_any_template_empty_list(self):
        """空模板列表时，find_any_template 返回 None"""
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        result = self.sc.find_any_template([], frame=frame)
        assert result is None

    # ─────────────── 模板缓存测试 ───────────────

    def test_template_cache_avoids_reload(self, tmp_path):
        """同路径模板第二次调用时直接从缓存取，不重新读磁盘"""
        template = np.full((30, 30, 3), 100, dtype=np.uint8)
        tpl_path = str(tmp_path / "cached.png")
        cv2.imwrite(tpl_path, template)

        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

        with patch('cv2.imread', wraps=cv2.imread) as mock_imread:
            self.sc.find_template(tpl_path, frame=frame)
            self.sc.find_template(tpl_path, frame=frame)
            # cv2.imread 只被调用一次（第二次走缓存）
            assert mock_imread.call_count == 1

    def test_clear_cache(self, tmp_path):
        """clear_cache 后，再次查找会重新读取模板文件"""
        template = np.full((30, 30, 3), 77, dtype=np.uint8)
        tpl_path = str(tmp_path / "clear_test.png")
        cv2.imwrite(tpl_path, template)

        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

        with patch('cv2.imread', wraps=cv2.imread) as mock_imread:
            self.sc.find_template(tpl_path, frame=frame)
            self.sc.clear_cache()
            self.sc.find_template(tpl_path, frame=frame)
            # clear_cache 后重新加载，imread 被调用2次
            assert mock_imread.call_count == 2

    # ─────────────── 坐标缩放测试 ───────────────

    def test_scale_to_relative_same_resolution(self):
        """帧与目标分辨率相同时，坐标不变"""
        frame_shape = (1080, 1920, 3)
        rx, ry = self.sc._scale_to_relative(960, 540, frame_shape)
        assert rx == 960
        assert ry == 540

    def test_scale_to_relative_half_resolution(self):
        """帧为目标分辨率一半时，坐标翻倍"""
        frame_shape = (540, 960, 3)
        rx, ry = self.sc._scale_to_relative(480, 270, frame_shape)
        assert rx == 960
        assert ry == 540

    def test_find_template_threshold_too_high(self, tmp_path):
        """使用极高阈值（1.1）时，任何匹配都失败，返回 None"""
        template = np.full((50, 80, 3), (0, 255, 0), dtype=np.uint8)
        tpl_path = str(tmp_path / "high_thr.png")
        cv2.imwrite(tpl_path, template)

        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame[300:350, 200:280] = template

        result = self.sc.find_template(tpl_path, frame=frame, threshold=1.1)
        assert result is None
"""
单点测试: modules/ui_handler.py
测试 UIHandler 灵诀选择、冰暴分支选择等 UI 交互逻辑。
"""

from unittest.mock import MagicMock, patch, call

import numpy as np
import pytest

from modules.ui_handler import UIHandler


@pytest.fixture
def mock_screen():
    screen = MagicMock()
    screen.capture.return_value = np.zeros((1080, 1920, 3), dtype=np.uint8)
    return screen


@pytest.fixture
def mock_input():
    return MagicMock()


@pytest.fixture
def ui_handler(mock_screen, mock_input, sample_config, tmp_path):
    """创建 UIHandler，spirit_templates 目录指向空的 tmp_path"""
    cfg = sample_config.copy()
    cfg["spirit_select"] = sample_config["spirit_select"].copy()
    cfg["spirit_select"]["template_dir"] = str(tmp_path)
    return UIHandler(mock_screen, mock_input, cfg)


class TestSpiritTemplateLoading:

    def test_load_empty_dir(self, ui_handler):
        """模板目录为空时，加载0个模板"""
        assert len(ui_handler._spirit_templates) == 0

    def test_load_existing_templates(self, mock_screen, mock_input, sample_config, tmp_path):
        """模板目录有 PNG 文件时，全部加载"""
        import cv2
        for i in range(3):
            tpl = np.full((30, 30, 3), i * 50, dtype=np.uint8)
            cv2.imwrite(str(tmp_path / f"spirit_{i}.png"), tpl)

        cfg = sample_config.copy()
        cfg["spirit_select"] = sample_config["spirit_select"].copy()
        cfg["spirit_select"]["template_dir"] = str(tmp_path)

        handler = UIHandler(mock_screen, mock_input, cfg)
        assert len(handler._spirit_templates) == 3


class TestSpiritPopupDetection:

    def test_detect_spirit_popup_found(self, ui_handler, mock_screen):
        """模板匹配成功时 detect_spirit_popup 返回 True"""
        # 注入一个模板
        ui_handler._spirit_templates = ["fake_template.png"]
        mock_screen.find_any_template.return_value = ("fake_template.png", (500, 500))

        result = ui_handler.detect_spirit_popup()
        assert result is True

    def test_detect_spirit_popup_not_found(self, ui_handler, mock_screen):
        """模板匹配失败时 detect_spirit_popup 返回 False"""
        ui_handler._spirit_templates = ["fake_template.png"]
        mock_screen.find_any_template.return_value = None

        result = ui_handler.detect_spirit_popup()
        assert result is False

    def test_detect_spirit_popup_no_templates(self, ui_handler):
        """没有模板文件时 detect_spirit_popup 返回 False"""
        ui_handler._spirit_templates = []
        result = ui_handler.detect_spirit_popup()
        assert result is False


class TestCardClick:

    def test_click_leftmost_card_5pick(self, ui_handler, mock_input, sample_config):
        """5选1时点击 pick5_click 配置坐标"""
        ui_handler._click_leftmost_card(is_five_pick=True)
        expected = sample_config["spirit_select"]["pick5_click"]
        mock_input.click.assert_called_once_with(expected[0], expected[1])

    def test_click_leftmost_card_3pick(self, ui_handler, mock_input, sample_config):
        """3选1时点击 pick3_click 配置坐标"""
        ui_handler._click_leftmost_card(is_five_pick=False)
        expected = sample_config["spirit_select"]["pick3_click"]
        mock_input.click.assert_called_once_with(expected[0], expected[1])


class TestIceBranch:

    def test_select_ice_branch_template_match(self, ui_handler, mock_screen, mock_input):
        """模板匹配冰暴分支成功时触发点击"""
        mock_screen.find_template.return_value = (600, 400)
        result = ui_handler.select_ice_branch()

        assert result is True
        mock_input.click.assert_called_once_with(600, 400)

    def test_select_ice_branch_template_not_found(self, ui_handler, mock_screen, mock_input):
        """模板匹配失败时返回 False，不触发点击"""
        mock_screen.find_template.return_value = None
        result = ui_handler.select_ice_branch()

        assert result is False
        mock_input.click.assert_not_called()


class TestSpiritSelect:

    def test_select_spirit_if_popup_found(self, ui_handler, mock_screen, mock_input):
        """有灵诀弹窗时立即选择并返回 True"""
        ui_handler._spirit_templates = ["t.png"]
        mock_screen.find_any_template.return_value = ("t.png", (100, 100))

        result = ui_handler.select_spirit_if_popup(is_five_pick=False)
        assert result is True
        mock_input.click.assert_called_once()

    def test_select_spirit_if_popup_not_found(self, ui_handler, mock_screen, mock_input):
        """无灵诀弹窗时返回 False，不点击"""
        ui_handler._spirit_templates = ["t.png"]
        mock_screen.find_any_template.return_value = None

        result = ui_handler.select_spirit_if_popup()
        assert result is False
        mock_input.click.assert_not_called()

    @patch("modules.ui_handler.time")
    def test_wait_and_select_spirit_success(self, mock_time, ui_handler, mock_screen, mock_input):
        """等待灵诀弹窗出现后成功选择"""
        ui_handler._spirit_templates = ["t.png"]
        # 第一次未检测到，第二次检测到
        mock_screen.find_any_template.side_effect = [None, ("t.png", (100, 100))]
        mock_time.time.side_effect = [0, 0.5, 1.0, 1.5]  # 未超时

        result = ui_handler.wait_and_select_spirit(is_five_pick=True, timeout=10.0)
        assert result is True
        mock_input.click.assert_called_once()

    @patch("modules.ui_handler.time")
    def test_wait_and_select_spirit_timeout(self, mock_time, ui_handler, mock_screen, mock_input):
        """等待超时后返回 False"""
        ui_handler._spirit_templates = ["t.png"]
        mock_screen.find_any_template.return_value = None
        # 模拟时间快速流逝超过 timeout
        mock_time.time.side_effect = [0, 100, 200]

        result = ui_handler.wait_and_select_spirit(timeout=1.0)
        assert result is False
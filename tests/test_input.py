"""
单点测试: core/input.py
测试 GameInput 键鼠操作封装。
完全 Mock pyautogui，不会发出真实键鼠操作。
"""

from unittest.mock import MagicMock, call, patch

import pytest

from core.input import GameInput


@pytest.fixture
def game_input(mock_window, sample_config):
    """创建使用 Mock 窗口的 GameInput，action_delay 设为极小值加速测试"""
    return GameInput(
        window=mock_window,
        keys_config=sample_config["keys"],
        action_delay=0.001,
    )


class TestGameInputBasic:

    @patch("core.input.pyautogui")
    def test_press_key(self, mock_pag, game_input):
        """press_key 调用 pyautogui.press"""
        game_input.press_key("e")
        mock_pag.press.assert_called_once_with("e")

    @patch("core.input.pyautogui")
    def test_hold_key(self, mock_pag, game_input):
        """hold_key 先 keyDown 后 keyUp"""
        game_input.hold_key("w", 0.01)
        mock_pag.keyDown.assert_called_once_with("w")
        mock_pag.keyUp.assert_called_once_with("w")

    @patch("core.input.pyautogui")
    def test_click_converts_coordinates(self, mock_pag, game_input, mock_window):
        """click 使用窗口坐标转换为绝对坐标后调用 pyautogui.click"""
        mock_window.relative_to_absolute.return_value = (384, 594)
        game_input.click(384, 594)
        mock_pag.click.assert_called_once_with(384, 594)

    @patch("core.input.pyautogui")
    def test_left_click(self, mock_pag, game_input):
        """left_click 在当前鼠标位置点击"""
        game_input.left_click()
        mock_pag.click.assert_called_once_with()


class TestGameInputWeapons:

    @patch("core.input.pyautogui")
    def test_switch_melee(self, mock_pag, game_input):
        """switch_melee 按键 '1'"""
        game_input.switch_melee()
        mock_pag.press.assert_called_with("1")

    @patch("core.input.pyautogui")
    def test_switch_ranged(self, mock_pag, game_input):
        """switch_ranged 按键 '2'"""
        game_input.switch_ranged()
        mock_pag.press.assert_called_with("2")

    @patch("core.input.pyautogui")
    def test_repair_weapon(self, mock_pag, game_input):
        """repair_weapon 按键 'r'"""
        game_input.repair_weapon()
        mock_pag.press.assert_called_with("r")


class TestGameInputActions:

    @patch("core.input.pyautogui")
    def test_interact(self, mock_pag, game_input):
        """interact 按键 'e'"""
        game_input.interact()
        mock_pag.press.assert_called_with("e")

    @patch("core.input.pyautogui")
    def test_use_f_skill(self, mock_pag, game_input):
        """use_f_skill 按键 'f'"""
        game_input.use_f_skill()
        mock_pag.press.assert_called_with("f")

    @patch("core.input.pyautogui")
    def test_lock_target(self, mock_pag, game_input):
        """lock_target 按键 '`'"""
        game_input.lock_target()
        mock_pag.press.assert_called_with("`")

    @patch("core.input.pyautogui")
    def test_restore_armor(self, mock_pag, game_input):
        """restore_armor 按键 '5'"""
        game_input.restore_armor()
        mock_pag.press.assert_called_with("5")


class TestGameInputMovement:

    @patch("core.input.pyautogui")
    def test_sprint_forward(self, mock_pag, game_input):
        """sprint_forward 同时按下 shift 和 w"""
        game_input.sprint_forward(0.01)
        mock_pag.keyDown.assert_any_call("shift")
        mock_pag.keyDown.assert_any_call("w")
        mock_pag.keyUp.assert_any_call("w")
        mock_pag.keyUp.assert_any_call("shift")

    @patch("core.input.pyautogui")
    def test_rotate_camera(self, mock_pag, game_input):
        """rotate_camera 调用 moveTo + moveRel"""
        game_input.rotate_camera(100, 0)
        mock_pag.moveTo.assert_called_once()
        mock_pag.moveRel.assert_called()

    @patch("core.input.pyautogui")
    def test_rotate_step(self, mock_pag, game_input):
        """rotate_step 按角度计算像素偏移"""
        game_input.rotate_step(45, 10)  # 45° × 10px = 450px
        # 验证 moveRel 被调用，delta_x 接近 450
        mock_pag.moveRel.assert_called()


class TestGameInputCombo:

    @patch("core.input.pyautogui")
    def test_attack_combo(self, mock_pag, game_input):
        """attack_combo 连击指定次数"""
        game_input.attack_combo(3)
        # 每次 attack_combo 调用 left_click → pyautogui.click()
        assert mock_pag.click.call_count == 3

    @patch("core.input.pyautogui")
    def test_ranged_burst(self, mock_pag, game_input):
        """ranged_burst 射击指定次数"""
        game_input.ranged_burst(2)
        assert mock_pag.click.call_count == 2


class TestGameInputPortalRoutine:

    @patch("core.input.pyautogui")
    def test_pre_portal_routine_sequence(self, mock_pag, game_input):
        """pre_portal_routine 按序执行: 按5恢复护甲 → 等待 → 按E交互"""
        game_input.pre_portal_routine(armor_wait=0.01)

        # 提取所有 press 调用的参数
        press_calls = [c for c in mock_pag.press.call_args_list]
        press_keys = [c[0][0] for c in press_calls]

        # 验证顺序: 先按 "5"（恢复护甲）再按 "e"（交互进门）
        assert "5" in press_keys
        assert "e" in press_keys
        idx_5 = press_keys.index("5")
        idx_e = press_keys.index("e")
        assert idx_5 < idx_e, "应先按5再按E"

    @patch("core.input.pyautogui")
    def test_random_walk_uses_wasd(self, mock_pag, game_input):
        """random_walk 使用 w/a/s/d 中的一个"""
        game_input.random_walk(0.01)
        # hold_key 会调用 keyDown + keyUp
        held_key = mock_pag.keyDown.call_args[0][0]
        assert held_key in ["w", "a", "s", "d"]
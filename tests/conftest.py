"""
pytest 共享 fixtures
提供 Mock 配置、假窗口、假截图等测试基础设施。
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# 将项目根目录加入 sys.path（tests/ 里导入 core/modules/utils 用）
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def sample_config():
    """返回一份完整的测试配置字典"""
    return {
        "game": {
            "window_title": "TestGame",
            "resolution": [1920, 1080],
        },
        "timing": {
            "screenshot_interval": 1.0,
            "action_delay": 0.01,
            "portal_search_timeout": 5,
            "combat_timeout": 10,
            "lock_attempt_interval": 0.1,
            "pre_portal_armor_wait": 0.1,
        },
        "threshold": {
            "template_match": 0.85,
            "yolo_confidence": 0.6,
            "portal_close_ratio": 0.05,
        },
        "keys": {
            "move_forward": "w",
            "move_back": "s",
            "move_left": "a",
            "move_right": "d",
            "sprint": "shift",
            "lock_target": "`",
            "interact": "e",
            "f_skill": "f",
            "melee_weapon": "1",
            "ranged_weapon": "2",
            "repair": "r",
            "restore_armor": "5",
        },
        "spirit_select": {
            "template_dir": "assets/ui/spirit_templates/",
            "pick5_click": [384, 594],
            "pick3_click": [480, 594],
        },
        "exploration": {
            "rotate_step_deg": 45,
            "rotate_pixel_per_deg": 10,
            "walk_duration": 0.1,
            "max_explore_rounds": 2,
        },
        "combat": {
            "attack_combo_count": 3,
            "ranged_burst_count": 2,
            "sprint_duration": 0.1,
            "repair_check_interval": 5,
        },
        "models": {
            "detector": "models/naraka_v1/weights/best.pt",
        },
        "assets": {
            "battle_start": "assets/battleStart.png",
            "battle_end": "assets/battleEnd.png",
            "ice_branch": "assets/ui/ice_branch.png",
            "capture_point_ui": "assets/ui/capture_point_ui.png",
        },
    }


@pytest.fixture
def fake_frame():
    """返回一个假的 1920x1080 BGR 帧"""
    return np.zeros((1080, 1920, 3), dtype=np.uint8)


@pytest.fixture
def mock_window():
    """返回一个 Mock 的 GameWindow"""
    window = MagicMock()
    window.found = True
    window.region = (0, 0, 1920, 1080)
    window.target_width = 1920
    window.target_height = 1080
    window.relative_to_absolute.side_effect = lambda x, y: (x, y)
    window.get_center.return_value = (960, 540)
    return window
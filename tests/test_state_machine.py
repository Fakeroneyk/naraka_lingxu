"""
单点测试: core/state_machine.py
测试 StageManager 关卡管理和 StateMachine 状态转换逻辑。
"""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from core.state_machine import BattleState, StageManager, StateMachine
from core.hooks import BattleHooks


# ══════════════════════════════════════
#  StageManager 测试
# ══════════════════════════════════════

class TestStageManager:

    def setup_method(self):
        self.sm = StageManager()

    def test_initial_stage_is_zero(self):
        """初始化 stage 为 0"""
        assert self.sm.stage == 0

    def test_advance(self):
        """advance 使 stage +1"""
        self.sm.advance()
        assert self.sm.stage == 1

    def test_advance_multiple(self):
        """连续 advance 正确递增"""
        for i in range(5):
            self.sm.advance()
        assert self.sm.stage == 5

    def test_reset(self):
        """reset 使 stage 回到 0"""
        self.sm.advance()
        self.sm.advance()
        self.sm.reset()
        assert self.sm.stage == 0

    # ─── 关卡类型判断 ───

    def test_is_combat_stage_1(self):
        """stage=1 是战斗关"""
        self.sm.stage = 1
        assert self.sm.is_combat_stage() is True

    def test_is_combat_stage_2(self):
        """stage=2 是战斗关"""
        self.sm.stage = 2
        assert self.sm.is_combat_stage() is True

    def test_is_combat_stage_3(self):
        """stage=3 是战斗关"""
        self.sm.stage = 3
        assert self.sm.is_combat_stage() is True

    def test_is_combat_stage_0_false(self):
        """stage=0 不是战斗关"""
        self.sm.stage = 0
        assert self.sm.is_combat_stage() is False

    def test_is_combat_stage_4_false(self):
        """stage=4 不是战斗关"""
        self.sm.stage = 4
        assert self.sm.is_combat_stage() is False

    def test_is_shop_stage(self):
        """stage=4 是商店关"""
        self.sm.stage = 4
        assert self.sm.is_shop_stage() is True

    def test_is_shop_stage_false(self):
        """stage!=4 不是商店关"""
        self.sm.stage = 3
        assert self.sm.is_shop_stage() is False

    def test_is_boss_stage(self):
        """stage=5 是 Boss 关"""
        self.sm.stage = 5
        assert self.sm.is_boss_stage() is True

    def test_is_boss_stage_false(self):
        """stage!=5 不是 Boss 关"""
        self.sm.stage = 4
        assert self.sm.is_boss_stage() is False

    # ─── 传送门类型 ───

    def test_portal_type_stage_0(self):
        """stage=0 → purple"""
        self.sm.stage = 0
        assert self.sm.get_portal_type() == "purple"

    def test_portal_type_stage_1(self):
        """stage=1 → purple"""
        self.sm.stage = 1
        assert self.sm.get_portal_type() == "purple"

    def test_portal_type_stage_2(self):
        """stage=2 → purple"""
        self.sm.stage = 2
        assert self.sm.get_portal_type() == "purple"

    def test_portal_type_stage_3(self):
        """stage=3 → gold"""
        self.sm.stage = 3
        assert self.sm.get_portal_type() == "gold"

    def test_portal_type_stage_4(self):
        """stage=4 → red"""
        self.sm.stage = 4
        assert self.sm.get_portal_type() == "red"

    def test_portal_type_stage_5(self):
        """stage=5 → none"""
        self.sm.stage = 5
        assert self.sm.get_portal_type() == "none"


# ══════════════════════════════════════
#  StateMachine 状态转换测试
# ══════════════════════════════════════

class TestStateMachineInit:

    def test_initial_state_is_idle(self, sample_config):
        """初始状态为 IDLE"""
        hooks = BattleHooks()
        sm = StateMachine(hooks=hooks, cfg=sample_config)
        assert sm.state == BattleState.IDLE


class TestStateMachineIdle:

    def test_idle_triggers_start_on_match(self, sample_config):
        """IDLE 状态匹配到 battleStart.png 时触发 trigger_start"""
        hooks = BattleHooks()
        start_called = []

        @hooks.on_battle_start
        def cb():
            start_called.append(True)

        sm = StateMachine(hooks=hooks, cfg=sample_config)
        sm._state = BattleState.IDLE

        # Mock screen
        sm._screen = MagicMock()
        sm._screen.find_template.return_value = (500, 300)  # 匹配成功

        sm._handle_idle()

        assert len(start_called) == 1

    def test_idle_to_preparation_on_match(self, sample_config):
        """匹配成功后状态变为 PREPARATION"""
        hooks = BattleHooks()
        sm = StateMachine(hooks=hooks, cfg=sample_config)
        sm._state = BattleState.IDLE
        sm._screen = MagicMock()
        sm._screen.find_template.return_value = (500, 300)

        sm._handle_idle()

        assert sm.state == BattleState.PREPARATION

    def test_idle_stays_when_no_match(self, sample_config):
        """未匹配到时保持 IDLE 状态"""
        hooks = BattleHooks()
        sm = StateMachine(hooks=hooks, cfg=sample_config)
        sm._state = BattleState.IDLE
        sm._screen = MagicMock()
        sm._screen.find_template.return_value = None

        sm._handle_idle()

        assert sm.state == BattleState.IDLE


class TestStateMachinePreparation:

    def test_preparation_calls_ui_and_transitions(self, sample_config):
        """PREPARATION 执行 UI 流程后转入 PORTAL_TRANSITION"""
        hooks = BattleHooks()
        sm = StateMachine(hooks=hooks, cfg=sample_config)
        sm._state = BattleState.PREPARATION
        sm._ui = MagicMock()
        sm._ui.run_preparation_phase.return_value = True

        sm._handle_preparation()

        sm._ui.run_preparation_phase.assert_called_once()
        assert sm.state == BattleState.PORTAL_TRANSITION


class TestStateMachineSpiritSelect:

    def test_spirit_select_transitions_to_portal(self, sample_config):
        """SPIRIT_SELECT 选择灵诀后转入 PORTAL_TRANSITION"""
        hooks = BattleHooks()
        sm = StateMachine(hooks=hooks, cfg=sample_config)
        sm._state = BattleState.SPIRIT_SELECT
        sm._ui = MagicMock()

        sm._handle_spirit_select()

        sm._ui.select_spirit_reward.assert_called_once()
        assert sm.state == BattleState.PORTAL_TRANSITION


class TestStateMachineShopSkip:

    def test_shop_skip_transitions_to_portal(self, sample_config):
        """SHOP_SKIP 直接转入 PORTAL_TRANSITION"""
        hooks = BattleHooks()
        sm = StateMachine(hooks=hooks, cfg=sample_config)
        sm._state = BattleState.SHOP_SKIP

        sm._handle_shop_skip()

        assert sm.state == BattleState.PORTAL_TRANSITION


class TestStateMachineBossEntry:

    def test_boss_entry_triggers_end(self, sample_config):
        """BOSS_ENTRY 触发 on_battle_end 钩子"""
        hooks = BattleHooks()
        end_called = []

        @hooks.on_battle_end
        def cb():
            end_called.append(True)

        sm = StateMachine(hooks=hooks, cfg=sample_config)
        sm._state = BattleState.BOSS_ENTRY
        sm._screen = MagicMock()
        sm._screen.find_template.return_value = (100, 100)
        sm._stage = StageManager()

        sm._handle_boss_entry()

        assert len(end_called) == 1

    def test_boss_entry_resets_to_idle(self, sample_config):
        """BOSS_ENTRY 完成后状态回到 IDLE，stage 重置为 0"""
        hooks = BattleHooks()
        sm = StateMachine(hooks=hooks, cfg=sample_config)
        sm._state = BattleState.BOSS_ENTRY
        sm._screen = MagicMock()
        sm._screen.find_template.return_value = (100, 100)
        sm._stage = StageManager()
        sm._stage.stage = 5

        sm._handle_boss_entry()

        assert sm.state == BattleState.IDLE
        assert sm._stage.stage == 0


class TestStateMachinePauseStop:

    def test_pause_and_resume(self, sample_config):
        """pause/resume 正确切换暂停标志"""
        hooks = BattleHooks()
        sm = StateMachine(hooks=hooks, cfg=sample_config)

        assert not sm._paused
        sm.pause()
        assert sm._paused
        sm.resume()
        assert not sm._paused

    def test_stop_resets_state(self, sample_config):
        """stop 重置状态和运行标志"""
        hooks = BattleHooks()
        sm = StateMachine(hooks=hooks, cfg=sample_config)
        sm._running = True
        sm._state = BattleState.COMBAT_NORMAL

        sm.stop()

        assert not sm._running
        assert sm.state == BattleState.IDLE
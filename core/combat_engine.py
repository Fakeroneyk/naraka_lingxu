"""战斗引擎 v9 - 纯战斗逻辑

职责：索敌/瞄准/开火/巡逻/补给
UI流程（灵诀/传送门/大厅）由game_flow统一处理
"""

import time

from loguru import logger

from core.config import Config
from core.states import CombatState, EnemyType
from capture.screen_capture import ScreenCapture
from detector.enemy_detector import EnemyDetector, DetectedEnemy
from detector.health_monitor import HealthMonitor
from detector.weapon_durability import WeaponDurabilityMonitor
from detector.v_energy_monitor import VEnergyMonitor
from input.keyboard import Keyboard
from input.mouse import Mouse
from input.humanize import random_delay
from strategy.aim_controller import AimController
from strategy.fire_cannon import FireCannonStrategy
from strategy.patrol_controller import PatrolController
from utils.debug_window import DebugWindow


class CombatEngine:
    """战斗引擎v9 — 4状态：PATROL/AIMING/FIRING/BOSS_BURST"""

    STATE_DEBOUNCE = 3

    def __init__(self, config: Config):
        self.config = config
        self.state = CombatState.PATROL
        self._state_frames = 0

        # 感知
        self.capture = ScreenCapture(config)
        self.enemy_detector = EnemyDetector(config)
        self.health_monitor = HealthMonitor(config)
        self.weapon_monitor = WeaponDurabilityMonitor(config)
        self.v_monitor = VEnergyMonitor(config)

        # 执行
        self.keyboard = Keyboard(
            humanize=config.input.humanize,
            delay_min=config.input.key_delay_min,
            delay_max=config.input.key_delay_max,
        )
        self.mouse = Mouse(
            humanize=config.input.humanize,
            delay_min=config.input.key_delay_min,
            delay_max=config.input.key_delay_max,
        )

        # 策略
        self.aim = AimController(config, self.mouse)
        self.strategy = FireCannonStrategy(config, self.keyboard, self.mouse)
        self.patrol = PatrolController(config, self.keyboard, self.mouse)

        # 调试
        self.debug_window = DebugWindow(enabled=config.debug.show_detection)

        # 窗口偏移→鼠标
        ox, oy = self.capture.window_offset
        self.mouse.set_window_offset(ox, oy)

        # 目标追踪
        self._current_target: DetectedEnemy | None = None
        self._target_lost_frames = 0

        # 统计
        self._start_time = time.time()
        self._combat_stats = {
            "stages_cleared": 0, "jue_selected": 0, "portals_entered": 0,
            "deaths": 0, "heals_used": 0, "repairs_done": 0,
            "boss_bursts": 0, "stuck_recoveries": 0,
        }

        logger.info(f"战斗引擎v9 | {config.character.name}")

    def _set_state(self, s: CombatState):
        if s == self.state:
            self._state_frames += 1; return
        if self._state_frames < self.STATE_DEBOUNCE: return
        old = self.state; self.state = s; self._state_frames = 0
        if old == CombatState.PATROL: self.keyboard.release_all()
        if s == CombatState.PATROL: self._current_target = None

    def _select_target(self, enemies):
        if self._current_target:
            for e in enemies:
                if abs(e.center_x - self._current_target.center_x) < 150 \
                   and abs(e.center_y - self._current_target.center_y) < 150:
                    old = self._current_target; self._current_target = e
                    self._target_lost_frames = 0
                    if old is not e: self.strategy.on_target_changed()
                    return e
            self._target_lost_frames += 1
            if self._target_lost_frames < 5: return self._current_target
            self._current_target = None

        bosses = [e for e in enemies if e.enemy_type == EnemyType.BOSS]
        t = bosses[0] if bosses else enemies[0]
        if self._current_target: self.strategy.on_target_changed()
        self._current_target = t; self._target_lost_frames = 0
        return t

    def tick(self):
        """战斗单帧"""
        frame = self.capture.grab()
        enemies = self.enemy_detector.detect(frame)

        self.debug_window.update(
            frame, self.state, enemies,
            hp_ratio=self.health_monitor.last_hp_ratio,
            fps=self.capture.fps,
        )

        if enemies:
            target = self._select_target(enemies)
            if self.aim.aim_at(target):
                v = self.v_monitor.check(frame)
                if target.enemy_type == EnemyType.BOSS and v:
                    self._set_state(CombatState.BOSS_BURST)
                    self.strategy.boss_burst()
                    self.v_monitor.mark_used()
                    self._combat_stats["boss_bursts"] += 1
                else:
                    self._set_state(CombatState.FIRING)
                    self.strategy.normal_fire(target)
            else:
                self._set_state(CombatState.AIMING)
        else:
            self._set_state(CombatState.PATROL)
            self._current_target = None
            if self.patrol.is_stuck(frame):
                self.patrol.unstuck()
                self._combat_stats["stuck_recoveries"] += 1
            else:
                self.patrol.move()

    def supply(self):
        """过渡补给"""
        frame = self.capture.grab()
        hp = self.health_monitor.check(frame)
        h = 0
        while hp < 0.9 and h < 5:
            self.keyboard.press(self.config.keybinds.heal)
            self._combat_stats["heals_used"] += 1
            h += 1; random_delay(800, 1200)
            frame = self.capture.grab(); hp = self.health_monitor.check(frame)
        if h: logger.info(f"回血{h}次→{hp:.0%}")

        if self.weapon_monitor.needs_repair(frame):
            self.strategy.repair_weapon()
            self._combat_stats["repairs_done"] += 1

    def reset_for_new_stage(self):
        self.patrol.reset()
        self._current_target = None; self._target_lost_frames = 0
        self.strategy.reset()
        self.state = CombatState.PATROL; self._state_frames = 0

    def stop(self):
        self.keyboard.release_all()
        self.debug_window.close()

    def _print_stats(self):
        m, s = divmod(int(time.time() - self._start_time), 60)
        logger.info("=" * 40)
        logger.info(f"运行 {m}分{s}秒")
        for k, v in self._combat_stats.items(): logger.info(f"  {k}: {v}")
        logger.info("=" * 40)
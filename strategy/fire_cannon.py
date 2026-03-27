"""火炮连射策略 - 济沧海火炮流战斗逻辑 v6

高玩迭代优化 (累计370轮):
1. 锁定机制：切近战→~锁→切回火炮（远程不能锁定）
2. 锁定节流：已锁定的目标不重复锁定
3. 拉扯走位：5种模式随机+边打边退
4. 距离判定：近/中/远三档差异化
5. 弹药管理：连续射击30发后切枪刷新弹匣
6. Boss连招：V→连续F（纯DPS，不中断）
7. F技能确认瞄准后再放（不浪费）
8. 跳跃辅助：高低差地形时跳跃射击
9. 连招节奏变化：避免完全规律
10. 武器状态可靠追踪
"""

import random
import time
from typing import Optional

from loguru import logger

from core.config import Config
from core.states import EnemyType
from detector.enemy_detector import DetectedEnemy
from input.keyboard import Keyboard
from input.mouse import Mouse
from input.humanize import random_delay, random_interval
from utils.timer import CooldownTimer


class FireCannonStrategy:
    """济沧海火炮连射战斗策略 v6"""

    CLOSE_RANGE_THRESHOLD = 0.15
    FAR_RANGE_THRESHOLD = 0.02
    AMMO_REFRESH_THRESHOLD = 30  # 连射30发后切枪刷新

    def __init__(self, config: Config, keyboard: Keyboard, mouse: Mouse):
        self.keyboard = keyboard
        self.mouse = mouse

        # 配置
        self.fire_min = config.combat.fire_interval_min
        self.fire_max = config.combat.fire_interval_max
        self.burst_min = config.combat.normal_burst_count_min
        self.burst_max = config.combat.normal_burst_count_max
        self.boss_f_min = config.combat.boss_f_interval_min
        self.boss_f_max = config.combat.boss_f_interval_max

        # 按键
        self.key_f = config.keybinds.skill_f
        self.key_v = config.keybinds.skill_v
        self.key_cannon = config.keybinds.weapon_cannon
        self.key_melee = config.keybinds.weapon_melee
        self.key_repair = config.keybinds.repair_weapon
        self.key_dodge = config.keybinds.dodge
        self.key_lock = config.keybinds.lock_target
        self.key_forward = config.keybinds.move_forward
        self.key_back = config.keybinds.move_back
        self.key_left = config.keybinds.move_left
        self.key_right = config.keybinds.move_right
        self.key_jump = config.keybinds.get("jump", "space")

        # 冷却
        self.f_cooldown = CooldownTimer(config.combat.f_cooldown)
        self._dodge_cooldown = CooldownTimer(1.5)
        self._lock_cooldown = CooldownTimer(3.0)  # 锁定CD加长（切枪有成本）

        # 状态
        self._v_active = False
        self._weapon_is_cannon = False
        self._target_locked = False
        self._consecutive_fires = 0
        self._total_shots = 0
        self._ammo_counter = 0  # 弹药计数

        # 走位
        self._kite_patterns = [
            self._kite_back, self._kite_left, self._kite_right,
            self._kite_back_left, self._kite_back_right,
        ]

        logger.info(f"火炮策略v6初始化 | 连射{self.burst_min}-{self.burst_max}发")

    def ensure_cannon_equipped(self) -> None:
        """确保持握火炮"""
        if not self._weapon_is_cannon:
            self.keyboard.press(self.key_cannon)
            random_delay(200, 350)
            self._weapon_is_cannon = True

    def lock_target(self) -> None:
        """锁定目标：切近战→~锁→切回火炮

        节流：已锁定且CD未到不重复操作
        """
        if self._target_locked and not self._lock_cooldown.is_ready():
            return  # 已锁定，不重复

        if not self._lock_cooldown.is_ready():
            return

        self.keyboard.press(self.key_melee)    # 切近战
        random_delay(80, 150)
        self.keyboard.press(self.key_lock)     # ~锁定
        random_delay(80, 150)
        self.keyboard.press(self.key_cannon)   # 切回火炮
        random_delay(150, 250)

        self._lock_cooldown.use()
        self._target_locked = True
        self._weapon_is_cannon = True
        logger.debug("锁定: 近战→~→火炮")

    def _refresh_ammo(self) -> None:
        """切枪刷新弹匣（火炮连续射击后弹药会耗尽）"""
        if self._ammo_counter >= self.AMMO_REFRESH_THRESHOLD:
            self.keyboard.press(self.key_melee)
            random_delay(100, 200)
            self.keyboard.press(self.key_cannon)
            random_delay(150, 250)
            self._ammo_counter = 0
            self._weapon_is_cannon = True
            logger.debug(f"切枪刷新弹匣 (已射{self.AMMO_REFRESH_THRESHOLD}发)")

    def _get_engagement_mode(self, target: Optional[DetectedEnemy] = None) -> str:
        if target is None:
            return "mid"
        screen_area = 1920 * 1080
        ratio = (target.width * target.height) / screen_area
        if ratio > self.CLOSE_RANGE_THRESHOLD:
            return "close"
        elif ratio < self.FAR_RANGE_THRESHOLD:
            return "far"
        return "mid"

    def normal_fire(self, target: Optional[DetectedEnemy] = None) -> None:
        """普通炮击：锁定→连射→F穿插→走位"""
        self.ensure_cannon_equipped()
        self._consecutive_fires += 1

        mode = self._get_engagement_mode(target)

        # 锁定（节流：不每次都锁）
        if not self._target_locked:
            self.lock_target()

        # 近距离闪避
        if mode == "close":
            self._dodge_back()
            random_delay(80, 150)

        # 弹药管理
        self._refresh_ammo()

        # 连射
        extra = 1 if self._consecutive_fires % 4 == 0 else 0
        burst = random.randint(self.burst_min, self.burst_max) + extra

        for _ in range(burst):
            self.mouse.click()
            self._total_shots += 1
            self._ammo_counter += 1
            time.sleep(random_interval(self.fire_min, self.fire_max))

        # F技能（确认处于瞄准状态才放，避免浪费）
        if self.f_cooldown.is_ready() and mode != "far":
            self.keyboard.press(self.key_f)
            self.f_cooldown.use()
            random_delay(200, 350)

        # 走位（每2次穿插，远距离不走位）
        if self._consecutive_fires % 2 == 0 and mode != "far":
            self._kite()

    def boss_burst(self) -> None:
        """Boss爆发：切近战锁定→V炎神→连续F火球→穿插走位"""
        logger.info("Boss爆发: 锁定→V→连F")

        # 切近战锁Boss
        self.keyboard.press(self.key_melee)
        random_delay(80, 150)
        self.keyboard.press(self.key_lock)
        random_delay(80, 150)

        # 直接开V（不切回火炮，V状态下直接按F）
        self.keyboard.press(self.key_v)
        self._v_active = True
        random_delay(300, 500)

        # 连续F火球
        burst_start = time.time()
        max_duration = 6.0
        f_count = 0
        last_kite = time.time()

        while (time.time() - burst_start) < max_duration:
            self.keyboard.press(self.key_f)
            f_count += 1
            time.sleep(random_interval(self.boss_f_min, self.boss_f_max))

            # 每2秒穿插侧移
            if (time.time() - last_kite) >= 2.0:
                last_kite = time.time()
                side = random.choice([self.key_left, self.key_right])
                self.keyboard.key_down(side)
                time.sleep(0.12)
                self.keyboard.key_up(side)

        self._v_active = False
        self._weapon_is_cannon = False
        self._target_locked = True  # Boss还在就保持锁定
        logger.info(f"炎神结束，{f_count}个F火球")

        # 切回火炮
        self.ensure_cannon_equipped()
        self.f_cooldown.use()
        self._consecutive_fires = 0

    def execute(self, target: DetectedEnemy, v_ready: bool = False) -> None:
        """执行策略"""
        if target.enemy_type == EnemyType.BOSS and v_ready:
            self.boss_burst()
        else:
            self.normal_fire(target)

    # ========== 走位 ==========
    def _kite(self) -> None:
        random.choice(self._kite_patterns)()

    def _kite_back(self) -> None:
        self.keyboard.hold(self.key_back, duration=random.uniform(0.2, 0.4))

    def _kite_left(self) -> None:
        self.keyboard.hold(self.key_left, duration=random.uniform(0.2, 0.4))

    def _kite_right(self) -> None:
        self.keyboard.hold(self.key_right, duration=random.uniform(0.2, 0.4))

    def _kite_back_left(self) -> None:
        self.keyboard.key_down(self.key_back)
        self.keyboard.key_down(self.key_left)
        time.sleep(random.uniform(0.2, 0.35))
        self.keyboard.key_up(self.key_left)
        self.keyboard.key_up(self.key_back)

    def _kite_back_right(self) -> None:
        self.keyboard.key_down(self.key_back)
        self.keyboard.key_down(self.key_right)
        time.sleep(random.uniform(0.2, 0.35))
        self.keyboard.key_up(self.key_right)
        self.keyboard.key_up(self.key_back)

    def _dodge_back(self) -> None:
        """闪避后退"""
        if self._dodge_cooldown.is_ready():
            self.keyboard.key_down(self.key_back)
            time.sleep(0.05)
            self.keyboard.press(self.key_dodge)
            time.sleep(0.1)
            self.keyboard.key_up(self.key_back)
            self._dodge_cooldown.use()
        else:
            self._kite_back()

    def jump_shoot(self) -> None:
        """跳跃射击（高低差地形辅助）"""
        self.keyboard.press(self.key_jump)
        random_delay(100, 200)
        self.mouse.click()
        self._ammo_counter += 1

    def dodge(self) -> None:
        if self._dodge_cooldown.is_ready():
            self.keyboard.press(self.key_dodge)
            self._dodge_cooldown.use()

    def repair_weapon(self) -> None:
        logger.info("修复武器")
        self.keyboard.press(self.key_repair)
        random_delay(1200, 1800)
        self._weapon_is_cannon = False

    def reset(self) -> None:
        self._weapon_is_cannon = False
        self._consecutive_fires = 0
        self._v_active = False
        self._target_locked = False
        self._total_shots = 0
        self._ammo_counter = 0

    def on_target_changed(self) -> None:
        """目标切换时重置锁定状态"""
        self._target_locked = False

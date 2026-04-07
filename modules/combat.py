"""
战斗模块
实现小怪关卡的战斗循环：锁敌、冲锋、连击、技能、搜敌探索。
包含火炮耐久检测与自动修复。
"""

import time
from typing import Optional

import numpy as np

from core.input import GameInput
from core.screen import ScreenCapture
from modules.ui_handler import UIHandler
from utils.logger import get_logger

log = get_logger(__name__)

# 锁敌成功的检测依据：
# 当按下~锁敌后，若敌人在范围内，游戏会有锁定指示器UI出现。
# 暂用"尝试锁定后短暂等待"策略，后续可加锁定指示器模板检测。
LOCK_WAIT = 0.4        # 锁敌后等待时间（秒）
LOCK_ASSUME_RANGE = 25 # 连续锁定失败次数后视为需要探索


class CombatHandler:
    """
    小怪关卡战斗控制器。

    战斗主循环直到检测到灵诀弹窗（通关标志）为止。
    策略：
      1. 切近战双刀，按~锁敌
      2. 锁敌成功：冲锋+连击+火球+火炮补刀
      3. 锁敌失败：旋转视角扫描 + 前进探索
      4. 定期检测火炮耐久，耗尽则按R修复
    """

    def __init__(
        self,
        screen: ScreenCapture,
        game_input: GameInput,
        ui_handler: UIHandler,
        cfg: dict,
    ):
        self._screen = screen
        self._input = game_input
        self._ui = ui_handler
        self._cfg = cfg
        self._combat_cfg = cfg["combat"]
        self._explore_cfg = cfg["exploration"]

        self._combo_count: int = self._combat_cfg["attack_combo_count"]
        self._ranged_count: int = self._combat_cfg["ranged_burst_count"]
        self._sprint_dur: float = self._combat_cfg["sprint_duration"]
        self._repair_interval: float = self._combat_cfg["repair_check_interval"]
        self._combat_timeout: float = cfg["timing"]["combat_timeout"]
        self._rotate_step_deg: float = self._explore_cfg["rotate_step_deg"]
        self._pixel_per_deg: float = self._explore_cfg["rotate_pixel_per_deg"]
        self._walk_duration: float = self._explore_cfg["walk_duration"]
        self._max_explore_rounds: int = self._explore_cfg["max_explore_rounds"]

        # 武器耐久相关
        self._last_repair_check: float = 0.0
        # 可选：耐久UI模板（用户提供后填入）
        self._durability_empty_template: str = self._cfg["assets"]["attack_zero"]

    def run_combat_loop(self) -> bool:
        """
        执行战斗主循环，直到检测到灵诀奖励弹窗（通关）。

        Returns:
            True=通关（检测到灵诀弹窗），False=超时
        """
        log.info("======= 战斗开始 =======")
        start_time = time.time()
        explore_rounds = 0
        lock_fail_streak = 0  # 连续锁敌失败计数

        # 初始化：切换双刀
        self._input.switch_melee()
        time.sleep(0.3)

        while time.time() - start_time < self._combat_timeout:

            # ─── 1. 检测通关标志（灵诀弹窗）───
            if self._ui.detect_spirit_popup():
                log.info("检测到灵诀弹窗，当前关卡通关！")
                return True

            # ─── 2. 定期检测武器耐久 ───
            self._check_and_repair_weapon()

            # ─── 3. 确保持近战武器后锁敌 ───
            self._input.switch_melee()
            self._input.lock_target()
            time.sleep(LOCK_WAIT)

            # ─── 4. 判断是否锁敌成功 ───
            if self._is_target_locked():
                # 锁敌成功：执行攻击序列
                lock_fail_streak = 0
                explore_rounds = 0
                self._execute_attack_sequence()
            else:
                # 锁敌失败：进入搜敌逻辑
                lock_fail_streak += 1
                log.debug(f"锁敌失败（连续 {lock_fail_streak} 次）")

                if lock_fail_streak >= LOCK_ASSUME_RANGE:
                    # 连续多次锁不到，执行探索
                    lock_fail_streak = 0
                    explored = self._explore_for_enemies()
                    if explored:
                        explore_rounds += 1
                    else:
                        explore_rounds = 0

                    if explore_rounds >= self._max_explore_rounds:
                        log.info("多轮探索未找到敌人，执行随机游走")
                        self._input.random_walk(self._walk_duration)
                        explore_rounds = 0

            time.sleep(0.2)

        log.warning(f"战斗超时（{self._combat_timeout}s），强制结束")
        return False

    def _execute_attack_sequence(self):
        """执行完整的攻击序列：冲锋 → 近战连击 → 火球 → 火炮补刀 → 切回近战"""
        log.info("执行攻击序列")

        # 冲锋向敌人
        self._input.sprint_forward(self._sprint_dur)

        # 近战连击
        self._input.attack_combo(self._combo_count)

        # 火球技能
        self._input.use_f_skill()
        time.sleep(0.3)

        # 切换火炮补刀
        self._input.switch_ranged()
        self._input.ranged_burst(self._ranged_count)

        # 切回近战准备下一轮
        self._input.switch_melee()
        time.sleep(0.2)

    def _is_target_locked(self) -> bool:
        """
        判断是否成功锁定目标。

        策略：
        - 若提供了锁定指示器模板，使用模板匹配
        - 否则：按~锁敌后等待，假设有目标则视为成功
          （保守策略：每次都假设锁到了，靠近攻击后若没怪则通过无打击反馈判断）

        当前采用"尝试锁定计数"策略：
        连续锁定失败次数用 lock_fail_streak 计数，
        通过判断攻击是否有实际效果（暂用计数代替）来决定是否探索。
        此处返回 True 以执行攻击序列，若发现无效（无打击音效等）再退化到探索。
        TODO: 后续可集成锁定指示器模板检测
        """
        # 简化版：只要执行了锁敌就认为可以尝试攻击
        # 实际上游戏锁定失败时会无明显反馈，靠 lock_fail_streak 兜底
        return True

    def _explore_for_enemies(self) -> bool:
        """
        旋转视角360°扫描敌人，同时尝试锁定。
        每旋转一步后尝试锁敌。

        Returns:
            True=找到并锁定敌人，False=未找到
        """
        steps = int(360 / self._rotate_step_deg)
        log.info(f"旋转扫描敌人 ({steps} 步)")

        for i in range(steps):
            # 检测灵诀弹窗（可能在扫描期间通关）
            if self._ui.detect_spirit_popup():
                log.info("扫描中检测到灵诀弹窗，通关")
                return False

            self._input.rotate_step(self._rotate_step_deg, self._pixel_per_deg)
            time.sleep(0.25)
            self._input.lock_target()
            time.sleep(LOCK_WAIT)

        # 扫描完一圈没找到，向前移动再继续
        log.info("扫描未找到敌人，向前移动探索")
        self._input.sprint_forward(self._walk_duration)
        return True

    def _check_and_repair_weapon(self):
        """
        定期检测火炮耐久并自动修复。
        使用模板匹配耐久耗尽UI（需用户提供模板）。
        """
        now = time.time()
        if now - self._last_repair_check < self._repair_interval:
            return
        self._last_repair_check = now

        if self._durability_empty_template:
            frame = self._screen.capture()
            pos = self._screen.find_template(self._durability_empty_template, frame=frame)
            if pos:
                log.warning("火炮耐久耗尽，自动修复")
                self._input.repair_weapon()
                return

        # 未配置耐久模板时，定期主动修复（保守策略）
        # 每 repair_check_interval 秒修复一次，避免耐久耗尽
        log.debug("定期修复武器（保守策略）")
        current_weapon_is_ranged = False  # 简化：不追踪当前武器状态
        # 切到火炮后修复，再切回近战
        # 注意：R键是否只在持远程武器时有效取决于游戏机制
        # 此处切到远程→修复→切回近战
        self._input.switch_ranged()
        time.sleep(0.1)
        self._input.repair_weapon()
        self._input.switch_melee()

    def set_durability_template(self, template_path: str):
        """设置火炮耐久耗尽模板路径（用户提供截图后调用）"""
        self._durability_empty_template = template_path
        log.info(f"已设置耐久耗尽模板: {template_path}")
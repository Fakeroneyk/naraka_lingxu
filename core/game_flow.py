"""游戏全流程控制器 v9

流程：大厅(模板匹配+点击) → 选英雄(等40s) → 战斗15层循环 → 大厅

战斗中的UI分3种处理方式：
1. 普通UI按钮（通关/确认/死亡复活）→ 模板匹配+点击
2. 灵诀面板 → 模板检测到面板后，用JueSelector的OCR+优先级选择
3. 传送门 → 不能模板匹配（3D模型），用HSV颜色检测+走近+按E
"""

import time
from typing import Optional

from loguru import logger

from core.config import Config
from core.states import PortalType
from capture.screen_capture import ScreenCapture
from detector.ui_detector import UIDetector
from input.mouse import Mouse
from input.keyboard import Keyboard
from input.humanize import random_delay
from strategy.jue_selector import JueSelector
from strategy.portal_handler import PortalHandler
from strategy.shop_handler import ShopHandler
from strategy.aim_controller import AimController


class GameFlow:
    """游戏全流程控制器 v9"""

    HERO_SELECT_WAIT = 40
    MAX_FLOORS = 15

    # 特殊模板
    TEMPLATE_SELECT_HERO = "select_hero"
    TEMPLATES_LOBBY = {"lobby", "back_to_lobby", "return_lobby"}

    # 灵诀面板模板（检测到后用JueSelector处理，不是直接点击）
    TEMPLATES_JUE = {"jue_panel", "jue_select"}

    # 普通战斗UI模板（检测到直接点击）
    TEMPLATES_BATTLE_CLICK = {
        "stage_clear", "victory", "continue", "confirm",
        "shop_buy", "shop_close", "revive", "death",
    }

    def __init__(self, config: Config, capture: ScreenCapture,
                 mouse: Mouse, keyboard: Keyboard,
                 aim_controller: AimController):
        self.config = config
        self.capture = capture
        self.mouse = mouse
        self.keyboard = keyboard
        self.ui_detector = UIDetector(config)
        self.confidence = config.detection.ui_confidence

        # 灵诀选择器（OCR+优先级）
        self.jue_selector = JueSelector(config, mouse)

        # 传送门处理器（HSV颜色检测+移动+按E）
        self.portal_handler = PortalHandler(
            config, keyboard, mouse, aim_controller
        )

        # 商店处理器（进商店门后购买）
        self.shop_handler = ShopHandler(config, keyboard, mouse)

        self._in_combat = False
        self._current_floor = 0
        self._total_runs = 0
        self._needs_portal = False  # 是否需要寻找传送门

        # 防重复点击
        self._last_clicked = ""
        self._last_click_time = 0.0
        self._click_cooldown = 2.0

        logger.info(f"流程控制器v9 | 模板: {len(self.ui_detector._templates)}")

    @property
    def in_combat(self) -> bool:
        return self._in_combat

    @property
    def needs_portal(self) -> bool:
        return self._needs_portal

    def _match_templates(self, frame, template_names=None):
        """匹配指定模板集合（None=全部）"""
        templates = template_names or self.ui_detector._templates.keys()
        for name in templates:
            if name not in self.ui_detector._templates:
                continue
            result = self.ui_detector.match_template(frame, name, self.confidence)
            if result is not None:
                cx, cy, score = result
                # 防重复
                now = time.time()
                if name == self._last_clicked and (now - self._last_click_time) < self._click_cooldown:
                    continue
                self._last_clicked = name
                self._last_click_time = now
                return (name, cx, cy, score)
        return None

    # ========== 大厅模式 ==========

    def lobby_tick(self) -> Optional[str]:
        """大厅UI：匹配所有模板+点击"""
        frame = self.capture.grab()
        match = self._match_templates(frame)
        if match is None:
            return None

        name, cx, cy, score = match
        logger.info(f"[大厅] '{name}' ({cx},{cy}) {score:.2f}")
        self.mouse.click(cx, cy)
        random_delay(500, 1000)

        if name == self.TEMPLATE_SELECT_HERO:
            logger.info(f"选英雄！等{self.HERO_SELECT_WAIT}秒...")
            for i in range(self.HERO_SELECT_WAIT, 0, -10):
                logger.info(f"  {i}秒..."); time.sleep(10)
            self._in_combat = True
            self._current_floor = 1
            self._needs_portal = False
            self._total_runs += 1
            logger.info(f"🎮 战斗开始！第{self._total_runs}轮")

        return name

    # ========== 战斗模式 ==========

    def battle_ui_check(self) -> Optional[str]:
        """战斗中检查UI

        处理3种情况：
        1. 灵诀面板 → JueSelector OCR选择（有优先级）
        2. 大厅模板 → 战斗结束
        3. 其他按钮 → 直接点击

        Returns:
            匹配到的模板名，None表示无UI（继续战斗逻辑）
        """
        frame = self.capture.grab()

        # 1. 检查灵诀面板（优先级最高，需要OCR选择）
        jue_match = self._match_templates(frame, self.TEMPLATES_JUE)
        if jue_match is not None:
            name = jue_match[0]
            logger.info(f"[战斗] 灵诀面板出现！使用OCR优先级选择")
            self.keyboard.release_all()
            self.jue_selector.select(frame)
            # 选完灵诀 → 需要找传送门
            self._needs_portal = True
            self._current_floor += 1
            logger.info(f"灵诀已选，第{self._current_floor}/{self.MAX_FLOORS}层")
            return name

        # 2. 检查大厅模板（战斗结束）
        lobby_match = self._match_templates(frame, self.TEMPLATES_LOBBY)
        if lobby_match is not None:
            name, cx, cy, _ = lobby_match
            logger.info(f"[战斗] 回到大厅: '{name}'")
            self.mouse.click(cx, cy)
            random_delay(500, 1000)
            self._in_combat = False
            self._needs_portal = False
            self._current_floor = 0
            logger.info(f"第{self._total_runs}轮结束")
            return name

        # 3. 检查其他战斗UI（通关/确认/商店等 → 直接点击）
        other_match = self._match_templates(frame, self.TEMPLATES_BATTLE_CLICK)
        if other_match is not None:
            name, cx, cy, score = other_match
            logger.info(f"[战斗] UI: '{name}' → 点击")
            self.mouse.click(cx, cy)
            random_delay(300, 800)
            return name

        return None

    def search_portal(self) -> bool:
        """寻找并进入传送门（3D模型，用HSV颜色检测）

        传送门是3D模型，不同角度形态不同，不能用模板匹配。
        使用HSV颜色检测（黄/紫/红色光效）+ 走近 + 按E交互。

        Returns:
            True表示成功进入传送门
        """
        frame = self.capture.grab()
        portals = self.portal_handler.find_all_portals(frame)

        if portals:
            best = self.portal_handler.select_best_portal(portals)
            if best:
                self.portal_handler.interact_with_portal(best)

                # 商店门：进去买补给，然后继续找下一个传送门
                from core.states import PortalType
                if best.portal_type == PortalType.SHOP:
                    logger.info("进入商店门，购买补给")
                    import time as t; t.sleep(2)
                    self.shop_handler.interact_with_shop()
                    return False  # 商店不算过关，继续找门

                # 普通门/Boss门：进入下一层
                self._needs_portal = False
                logger.info(f"进入传送门: {best.portal_type.value}")
                return True

        # 没找到 → 旋转视角扫描
        self.mouse.move_relative(60, 0)
        time.sleep(0.2)
        self.keyboard.hold(self.config.keybinds.move_forward, duration=0.5)
        return False

    def exit_combat(self) -> None:
        self._in_combat = False
        self._needs_portal = False
        self._current_floor = 0
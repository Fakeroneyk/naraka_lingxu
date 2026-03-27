"""商店处理 - 进入商店门后自动购买补给品

高玩视角关键遗漏：
商店门（黄色）进入后是一个货郎NPC界面，需要：
1. 走近货郎NPC
2. 按E交互打开商店界面
3. 购买武备匣（补充火炮弹药）
4. 购买血药（补充回血道具）
5. 关闭商店
6. 继续找下一个传送门

这不是通关奖励，而是中间补给站！
"""

import time
from typing import Optional

from loguru import logger

from core.config import Config
from input.keyboard import Keyboard
from input.mouse import Mouse
from input.humanize import random_delay


class ShopHandler:
    """商店自动购买处理器

    进入商店门后自动与货郎交互购买补给品。
    """

    # 货郎商店UI中各物品的大致点击位置（1920x1080基准）
    # 需要根据实际截图校准
    SHOP_POSITIONS = {
        "weapon_box": (600, 400),      # 武备匣位置
        "health_potion": (600, 500),    # 血药位置
        "buy_button": (800, 600),       # 购买确认按钮
        "close_button": (1300, 200),    # 关闭商店按钮
    }

    def __init__(self, config: Config, keyboard: Keyboard, mouse: Mouse):
        self.keyboard = keyboard
        self.mouse = mouse
        self.key_interact = config.keybinds.interact

        # 购买配置
        self.buy_weapon_box = True      # 是否买武备匣
        self.buy_health_potion = True   # 是否买血药
        self.weapon_box_count = 3       # 购买武备匣数量
        self.health_potion_count = 2    # 购买血药数量

        # 分辨率缩放
        res = config.screen.resolution
        self._sx = res[0] / 1920
        self._sy = res[1] / 1080

        logger.info(f"商店处理器初始化 | 武备匣×{self.weapon_box_count} 血药×{self.health_potion_count}")

    def _scaled_pos(self, key: str):
        """获取缩放后的位置"""
        x, y = self.SHOP_POSITIONS[key]
        return int(x * self._sx), int(y * self._sy)

    def interact_with_shop(self) -> None:
        """与商店NPC交互并购买补给

        调用时机：进入商店门后
        """
        logger.info("进入商店，开始自动购买...")

        # 1. 走向NPC并交互
        self.keyboard.hold("w", duration=1.5)
        random_delay(300, 500)

        # 按E打开商店（多按几次确保）
        for _ in range(3):
            self.keyboard.press(self.key_interact)
            random_delay(500, 800)

        # 等待商店UI加载
        time.sleep(1.0)

        # 2. 购买武备匣
        if self.buy_weapon_box:
            wx, wy = self._scaled_pos("weapon_box")
            for i in range(self.weapon_box_count):
                self.mouse.click(wx, wy)
                random_delay(200, 400)
                # 点击购买确认
                bx, by = self._scaled_pos("buy_button")
                self.mouse.click(bx, by)
                random_delay(300, 500)
            logger.info(f"  购买武备匣 ×{self.weapon_box_count}")

        # 3. 购买血药
        if self.buy_health_potion:
            hx, hy = self._scaled_pos("health_potion")
            for i in range(self.health_potion_count):
                self.mouse.click(hx, hy)
                random_delay(200, 400)
                bx, by = self._scaled_pos("buy_button")
                self.mouse.click(bx, by)
                random_delay(300, 500)
            logger.info(f"  购买血药 ×{self.health_potion_count}")

        # 4. 关闭商店
        cx, cy = self._scaled_pos("close_button")
        self.mouse.click(cx, cy)
        random_delay(500, 800)

        # 按ESC确保退出
        self.keyboard.press("escape")
        random_delay(500, 800)

        logger.info("商店购买完成")
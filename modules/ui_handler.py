"""
UI 交互模块
处理灵诀选择、冰暴分支选择等所有 UI 界面交互。
使用模板列表检测灵诀选择状态，使用配置坐标点击最左卡片。
"""

import glob
import time
from pathlib import Path
from typing import List, Optional, Tuple

from core.input import GameInput
from core.screen import ScreenCapture
from utils.logger import get_logger

log = get_logger(__name__)

# 灵诀选择状态最长等待时间（秒）
SPIRIT_WAIT_TIMEOUT = 20.0
# 每次检测间隔
SPIRIT_POLL_INTERVAL = 1.0


class UIHandler:
    """
    UI 界面交互处理器。

    负责:
      - 冰暴分支选择（准备阶段）
      - 5选1 / 3选1 灵诀选择
      - 通关弹窗检测（灵诀弹出即表示通关）
    """

    def __init__(
        self,
        screen: ScreenCapture,
        game_input: GameInput,
        cfg: dict,
    ):
        self._screen = screen
        self._input = game_input
        self._cfg = cfg
        self._spirit_cfg = cfg["spirit_select"]
        self._assets = cfg["assets"]

        # 动态加载 spirit_templates/ 目录下所有模板
        self._spirit_templates: List[str] = self._load_spirit_templates()
        log.info(f"已加载灵诀模板: {len(self._spirit_templates)} 张")

    def _load_spirit_templates(self) -> List[str]:
        """加载 spirit_templates 目录下所有 PNG 模板"""
        template_dir = Path(self._spirit_cfg["template_dir"])
        if not template_dir.exists():
            log.warning(f"灵诀模板目录不存在: {template_dir}，请创建并放入模板图片")
            return []
        templates = list(template_dir.glob("*.png"))
        return [str(t) for t in templates]

    # ─────────────── 分支选择 ───────────────

    def select_ice_branch(self) -> bool:
        """
        在元素分支选择界面选择冰暴分支。
        优先使用模板匹配定位冰暴分支按钮并点击，
        fallback 使用配置固定坐标。

        Returns:
            是否成功点击
        """
        log.info("开始选择冰暴分支")
        ice_template = self._assets.get("ice_branch", "assets/ui/ice_branch.png")
        frame = self._screen.capture()
        pos = self._screen.find_template(ice_template, frame=frame)

        if pos:
            log.info(f"模板匹配到冰暴分支: {pos}")
            self._input.click(*pos)
            time.sleep(0.5)
            return True

        # fallback: 模板未找到时告警，等待用户更新截图
        log.warning("未找到冰暴分支模板，跳过点击（请提供 ice_branch.png）")
        return False

    # ─────────────── 灵诀选择 ───────────────

    def wait_and_select_spirit(
        self,
        is_five_pick: bool = False,
        timeout: float = SPIRIT_WAIT_TIMEOUT,
    ) -> bool:
        """
        等待灵诀选择弹窗出现并点击最左边卡片。

        Args:
            is_five_pick: True=5选1（第一次），False=3选1（后续）
            timeout: 等待超时时间

        Returns:
            是否成功完成选择
        """
        pick_label = "5选1" if is_five_pick else "3选1"
        log.info(f"等待灵诀选择弹窗（{pick_label}）...")
        start = time.time()

        while time.time() - start < timeout:
            frame = self._screen.capture()
            if self._detect_spirit_popup(frame):
                log.info(f"检测到灵诀选择弹窗（{pick_label}），点击最左边卡片")
                self._click_leftmost_card(is_five_pick)
                time.sleep(0.5)
                return True
            time.sleep(SPIRIT_POLL_INTERVAL)

        log.warning(f"等待灵诀选择超时（{timeout}s）")
        return False

    def detect_spirit_popup(self, frame=None) -> bool:
        """
        检测当前画面中是否存在灵诀选择弹窗（供状态机外部调用）。

        Returns:
            是否出现灵诀弹窗
        """
        if frame is None:
            frame = self._screen.capture()
        return self._detect_spirit_popup(frame)

    def select_spirit_if_popup(self, is_five_pick: bool = False) -> bool:
        """
        如果当前画面有灵诀弹窗则立即选择。
        用于战斗循环中的实时检测。

        Returns:
            是否触发了选择（True=有弹窗且已点击）
        """
        frame = self._screen.capture()
        if self._detect_spirit_popup(frame):
            log.info("检测到灵诀弹窗，立即选择")
            self._click_leftmost_card(is_five_pick)
            time.sleep(0.5)
            return True
        return False

    def _detect_spirit_popup(self, frame) -> bool:
        """
        使用模板列表检测灵诀选择弹窗状态。
        任意一张模板匹配成功即视为弹窗出现。
        """
        if not self._spirit_templates:
            # 无模板时返回 False，需要用户提供模板
            return False

        result = self._screen.find_any_template(
            self._spirit_templates,
            frame=frame,
            threshold=self._cfg["threshold"]["template_match"],
        )
        return result is not None

    def _click_leftmost_card(self, is_five_pick: bool):
        """点击最左边的灵诀卡片"""
        if is_five_pick:
            rx, ry = self._spirit_cfg["pick5_click"]
        else:
            rx, ry = self._spirit_cfg["pick3_click"]
        self._input.click(rx, ry)
        log.info(f"点击灵诀卡片坐标: ({rx}, {ry})")

    # ─────────────── 准备关卡流程 ───────────────

    def run_preparation_phase(self) -> bool:
        """
        执行完整的准备关卡 UI 流程：
          1. 选择冰暴分支
          2. 第一次灵诀选择（5选1）
          3. 第二次灵诀选择（3选1）
          4. 第三次灵诀选择（3选1）

        Returns:
            是否全部完成
        """
        log.info("========== 准备关卡: 开始 ==========")

        # 1. 选择冰暴分支
        self.select_ice_branch()
        time.sleep(2)

        # 2. 第一次灵诀选择（5选1）
        ok = self.wait_and_select_spirit(is_five_pick=True)
        if not ok:
            log.warning("第一次灵诀选择失败，继续尝试")
        time.sleep(2)

        # 3. 第二次灵诀选择（3选1）
        ok = self.wait_and_select_spirit(is_five_pick=False)
        if not ok:
            log.warning("第二次灵诀选择失败，继续尝试")
        time.sleep(2)

        # 4. 第三次灵诀选择（3选1）
        ok = self.wait_and_select_spirit(is_five_pick=False)
        if not ok:
            log.warning("第三次灵诀选择失败，继续尝试")
        time.sleep(2)

        log.info("========== 准备关卡: 完成 ==========")
        return True

    def select_spirit_reward(self) -> bool:
        """
        通关后选择灵诀奖励（3选1）。
        等待弹窗并点击最左卡片。

        Returns:
            是否成功完成
        """
        log.info("等待通关灵诀奖励弹窗")
        return self.wait_and_select_spirit(is_five_pick=False, timeout=15.0)
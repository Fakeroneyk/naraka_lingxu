"""
战斗钩子系统
提供 on_battle_start / on_battle_end 装饰器注册回调，
由模板匹配触发（battleStart.png / battleEnd.png）。
"""

from typing import Callable, List

from utils.logger import get_logger

log = get_logger(__name__)


class BattleHooks:
    """
    战斗生命周期钩子管理器。

    使用装饰器注册回调函数:

        hooks = BattleHooks()

        @hooks.on_battle_start
        def my_start():
            print("战斗开始")

        @hooks.on_battle_end
        def my_end():
            print("战斗结束")

    触发:
        hooks.trigger_start()  # battleStart.png 匹配时调用
        hooks.trigger_end()    # battleEnd.png 匹配时调用
    """

    def __init__(self):
        self._start_callbacks: List[Callable] = []
        self._end_callbacks: List[Callable] = []

    def on_battle_start(self, func: Callable) -> Callable:
        """装饰器: 注册战斗开始回调"""
        self._start_callbacks.append(func)
        log.debug(f"注册战斗开始钩子: {func.__name__}")
        return func

    def on_battle_end(self, func: Callable) -> Callable:
        """装饰器: 注册战斗结束回调"""
        self._end_callbacks.append(func)
        log.debug(f"注册战斗结束钩子: {func.__name__}")
        return func

    def trigger_start(self):
        """触发所有战斗开始回调"""
        log.info(f"[HOOK] 触发战斗开始，共 {len(self._start_callbacks)} 个回调")
        for cb in self._start_callbacks:
            try:
                cb()
            except Exception as e:
                log.error(f"战斗开始钩子 {cb.__name__} 执行异常: {e}")

    def trigger_end(self):
        """触发所有战斗结束回调"""
        log.info(f"[HOOK] 触发战斗结束，共 {len(self._end_callbacks)} 个回调")
        for cb in self._end_callbacks:
            try:
                cb()
            except Exception as e:
                log.error(f"战斗结束钩子 {cb.__name__} 执行异常: {e}")

    @property
    def start_count(self) -> int:
        return len(self._start_callbacks)

    @property
    def end_count(self) -> int:
        return len(self._end_callbacks)
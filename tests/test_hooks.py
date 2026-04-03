"""
单点测试: core/hooks.py
测试 BattleHooks 钩子注册与触发机制。
"""

import pytest
from core.hooks import BattleHooks


class TestBattleHooks:

    def setup_method(self):
        """每个测试前创建新的 BattleHooks 实例"""
        self.hooks = BattleHooks()

    # ─────────────── 注册测试 ───────────────

    def test_register_start_callback(self):
        """注册1个战斗开始回调后 start_count 为1"""
        @self.hooks.on_battle_start
        def cb():
            pass
        assert self.hooks.start_count == 1

    def test_register_end_callback(self):
        """注册1个战斗结束回调后 end_count 为1"""
        @self.hooks.on_battle_end
        def cb():
            pass
        assert self.hooks.end_count == 1

    def test_register_multiple_start_callbacks(self):
        """注册多个战斗开始回调，数量正确"""
        @self.hooks.on_battle_start
        def cb1(): pass

        @self.hooks.on_battle_start
        def cb2(): pass

        assert self.hooks.start_count == 2

    def test_register_multiple_end_callbacks(self):
        """注册多个战斗结束回调，数量正确"""
        @self.hooks.on_battle_end
        def cb1(): pass

        @self.hooks.on_battle_end
        def cb2(): pass

        assert self.hooks.end_count == 2

    def test_initial_counts_are_zero(self):
        """初始状态下回调数量为0"""
        assert self.hooks.start_count == 0
        assert self.hooks.end_count == 0

    # ─────────────── 触发测试 ───────────────

    def test_trigger_start_calls_registered_callback(self):
        """trigger_start 调用已注册的战斗开始回调"""
        called = []

        @self.hooks.on_battle_start
        def cb():
            called.append(True)

        self.hooks.trigger_start()
        assert len(called) == 1

    def test_trigger_end_calls_registered_callback(self):
        """trigger_end 调用已注册的战斗结束回调"""
        called = []

        @self.hooks.on_battle_end
        def cb():
            called.append(True)

        self.hooks.trigger_end()
        assert len(called) == 1

    def test_trigger_start_calls_all_callbacks(self):
        """trigger_start 调用所有注册的回调"""
        results = []

        @self.hooks.on_battle_start
        def cb1():
            results.append("cb1")

        @self.hooks.on_battle_start
        def cb2():
            results.append("cb2")

        self.hooks.trigger_start()
        assert "cb1" in results
        assert "cb2" in results
        assert len(results) == 2

    def test_trigger_end_calls_all_callbacks(self):
        """trigger_end 调用所有注册的回调"""
        results = []

        @self.hooks.on_battle_end
        def cb1():
            results.append("cb1")

        @self.hooks.on_battle_end
        def cb2():
            results.append("cb2")

        self.hooks.trigger_end()
        assert len(results) == 2

    def test_trigger_start_does_not_call_end_callbacks(self):
        """trigger_start 不调用战斗结束回调"""
        end_called = []

        @self.hooks.on_battle_end
        def cb():
            end_called.append(True)

        self.hooks.trigger_start()
        assert len(end_called) == 0

    def test_trigger_end_does_not_call_start_callbacks(self):
        """trigger_end 不调用战斗开始回调"""
        start_called = []

        @self.hooks.on_battle_start
        def cb():
            start_called.append(True)

        self.hooks.trigger_end()
        assert len(start_called) == 0

    # ─────────────── 异常隔离测试 ───────────────

    def test_callback_exception_does_not_stop_others(self):
        """某个回调抛异常，不影响后续回调执行"""
        results = []

        @self.hooks.on_battle_start
        def bad_cb():
            raise RuntimeError("模拟异常")

        @self.hooks.on_battle_start
        def good_cb():
            results.append("good")

        # trigger_start 不应抛出异常
        self.hooks.trigger_start()

        # good_cb 仍然被调用
        assert "good" in results

    def test_decorator_returns_original_function(self):
        """装饰器应返回原函数（不改变函数对象）"""
        def my_cb():
            return "original"

        decorated = self.hooks.on_battle_start(my_cb)
        assert decorated is my_cb
        assert decorated() == "original"

    def test_trigger_with_no_callbacks(self):
        """没有注册任何回调时，trigger 不抛出异常"""
        # 不应抛出任何异常
        self.hooks.trigger_start()
        self.hooks.trigger_end()
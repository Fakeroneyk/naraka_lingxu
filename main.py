"""
征神之路 · 灵虚界自动化战斗程序
主入口: 加载配置 → 注册钩子 → 启动热键监听 → 运行状态机
"""

import sys
import threading
from pathlib import Path

import yaml
from pynput import keyboard

from core.hooks import BattleHooks
from core.state_machine import StateMachine
from utils.logger import get_logger

log = get_logger(__name__)

# 项目根目录（main.py 所在目录）
PROJECT_ROOT = Path(__file__).parent


def load_config(config_path: str = "config.yaml") -> dict:
    """加载 YAML 配置文件"""
    path = PROJECT_ROOT / config_path
    if not path.exists():
        log.error(f"配置文件不存在: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    log.info(f"配置已加载: {config_path}")
    return cfg


def setup_hotkeys(state_machine: StateMachine):
    """
    注册全局热键:
      F10 - 暂停/恢复
      F11 - 停止并退出
    """
    paused = False

    def on_press(key):
        nonlocal paused
        try:
            if key == keyboard.Key.f10:
                if not paused:
                    state_machine.pause()
                    paused = True
                    log.info("[热键] F10: 已暂停")
                else:
                    state_machine.resume()
                    paused = False
                    log.info("[热键] F10: 已恢复")
            elif key == keyboard.Key.f11:
                log.info("[热键] F11: 停止脚本")
                state_machine.stop()
                return False  # 停止监听
        except Exception as e:
            log.error(f"热键处理异常: {e}")

    listener = keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()
    log.info("全局热键已注册: F10=暂停/恢复, F11=停止")
    return listener


def main():
    log.info("=" * 50)
    log.info("征神之路 · 灵虚界自动化战斗程序")
    log.info("=" * 50)

    # ─── 加载配置 ───
    cfg = load_config()

    # ─── 创建钩子系统 ───
    hooks = BattleHooks()

    @hooks.on_battle_start
    def on_start():
        log.info("[HOOK] >>>>>> 灵虚界战斗开始 <<<<<<")

    @hooks.on_battle_end
    def on_end():
        log.info("[HOOK] >>>>>> 灵虚界战斗结束 <<<<<<")
        sm.stop()

    # ─── 创建状态机 ───
    sm = StateMachine(hooks=hooks, cfg=cfg)

    # ─── 注册热键 ───
    hotkey_listener = setup_hotkeys(sm)

    # ─── 启动 ───
    log.info("程序已启动，等待检测 battleStart.png...")
    log.info("按 F10 暂停/恢复 | 按 F11 停止退出")

    try:
        sm.run()
    except KeyboardInterrupt:
        log.info("Ctrl+C 中断，正在退出...")
        sm.stop()
    finally:
        log.info("程序退出")


if __name__ == "__main__":
    # 确保工作目录在项目根目录
    import os
    os.chdir(PROJECT_ROOT)

    main()
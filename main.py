"""灵虚界全流程自动化 v9.0

流程：大厅(模板+点击) → 选英雄(等40s) → 战斗15层
战斗中：
  - 无UI匹配时 → 索敌/瞄准/开火（combat_engine）
  - 灵诀面板 → OCR优先级选择（jue_selector）
  - 传送门 → HSV颜色检测+走近+按E（portal_handler）
  - 其他UI → 直接点击
  - 大厅模板 → 战斗结束

python main.py / --calibrate / --stats / --preview / --screenshot
"""

import sys, os, time, signal, argparse, platform
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from core.config import load_config
from core.logger import setup_logger
from core.combat_engine import CombatEngine
from core.game_flow import GameFlow
from utils.session_stats import SessionStats


def check_env():
    if platform.system() != "Windows":
        logger.warning("非Windows，按键模拟降级")
    try:
        import cv2, numpy, mss
    except ImportError as e:
        logger.error(f"缺少依赖: {e}"); return False
    for lib in ["pydirectinput", "paddleocr", "ultralytics"]:
        try: __import__(lib)
        except ImportError: logger.warning(f"{lib}未安装")
    return True


def cmd_run(manual_mode: bool = False):
    print(r"""
  ╔═══════════════════════════════════════════╗
  ║   灵虚界全流程自动化 v9.0                  ║
  ║   济沧海 | 火炮连射 | 15层循环刷图          ║
  ╠═══════════════════════════════════════════╣
  ║  F8 切换手动/自动打怪                      ║
  ║  F9 暂停  F10 退出  Ctrl+C 强制退出        ║
  ╚═══════════════════════════════════════════╝
    """)

    config = load_config()
    setup_logger(log_level=config.debug.log_level)
    if not check_env(): sys.exit(1)

    engine = CombatEngine(config)

    # GameFlow需要aim_controller来处理传送门走近
    flow = GameFlow(
        config, engine.capture, engine.mouse, engine.keyboard,
        aim_controller=engine.aim,
    )

    stats = SessionStats()
    running = True
    paused = False
    # 手动/自动打怪开关（优先命令行参数，其次配置文件）
    auto_combat = not manual_mode and getattr(config.combat, "auto_combat", True)

    def on_quit(signum=None, frame=None):
        nonlocal running; running = False
    signal.signal(signal.SIGINT, on_quit)
    signal.signal(signal.SIGTERM, on_quit)

    try:
        import keyboard as kb
        def toggle():
            nonlocal paused; paused = not paused
            logger.info("暂停" if paused else "恢复")
            if paused: engine.keyboard.release_all()
        def toggle_combat():
            nonlocal auto_combat; auto_combat = not auto_combat
            mode = "自动打怪" if auto_combat else "手动打怪(仅自动UI)"
            logger.info(f"🔄 切换: {mode}")
        kb.add_hotkey(config.hotkeys.pause_resume, toggle)
        kb.add_hotkey(config.hotkeys.quit, lambda: on_quit())
        kb.add_hotkey("f8", toggle_combat)
    except: pass

    logger.info(f"打怪模式: {'自动' if auto_combat else '手动(仅自动UI流程)'}")
    logger.info("按F8可随时切换手动/自动打怪")

    if engine.capture.focus_game_window():
        logger.info("已聚焦游戏窗口")

    for i in range(3, 0, -1):
        logger.info(f"{i}秒..."); time.sleep(1)
    logger.info("🎮 启动！模式: 大厅")

    fps = config.screen.capture_fps
    interval = 1.0 / fps

    try:
        while running:
            if paused: time.sleep(0.5); continue
            t = time.time()

            if flow.in_combat:
                # ===== 战斗模式 =====

                if flow.needs_portal:
                    # 选完灵诀 → 补给 → 找传送门
                    engine.supply()
                    found = flow.search_portal()
                    if found:
                        engine.reset_for_new_stage()
                        logger.info(f"进入第{flow._current_floor}层")
                else:
                    # 先检查战斗UI（灵诀/通关/大厅）
                    matched = flow.battle_ui_check()

                    if matched is None:
                        if auto_combat:
                            # 自动打怪：执行战斗逻辑
                            engine.tick()
                        else:
                            # 手动打怪：只检查UI，不操作战斗
                            # 玩家自己打怪，程序只处理灵诀/传送门/通关等
                            time.sleep(0.5)
                    elif not flow.in_combat:
                        engine.keyboard.release_all()
                        engine.strategy.reset()
                        logger.info("回到大厅")
            else:
                # ===== 大厅模式 =====
                matched = flow.lobby_tick()
                if not matched:
                    time.sleep(1.0)

            dt = time.time() - t
            if dt < interval: time.sleep(interval - dt)

    except Exception as e:
        logger.error(f"异常: {e}", exc_info=True)
    finally:
        engine.stop()
        engine._print_stats()
        stats.save(engine._combat_stats)
        logger.info(f"退出 | 轮次: {flow._total_runs}")


def main():
    p = argparse.ArgumentParser(description="灵虚界全流程自动化")
    p.add_argument("--calibrate", action="store_true")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--preview", action="store_true")
    p.add_argument("--screenshot", action="store_true")
    p.add_argument("--manual", action="store_true", help="手动打怪模式（只自动UI流程，战斗由玩家操作）")
    a = p.parse_args()

    if a.calibrate:
        from utils.calibration_tool import CalibrationTool; CalibrationTool().run()
    elif a.stats:
        SessionStats.print_summary()
    elif a.preview:
        from utils.calibration_tool import CalibrationTool; CalibrationTool().live_preview()
    elif a.screenshot:
        from utils.screenshot_tool import ScreenshotTool; ScreenshotTool().run()
    else:
        cmd_run(manual_mode=a.manual)

if __name__ == "__main__":
    main()
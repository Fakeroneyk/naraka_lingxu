"""校准工具 - 一键校准瞄准灵敏度和UI区域ROI

高玩迭代 v5 (270轮):
帮助用户快速校准以下参数:
1. 瞄准灵敏度 (sensitivity_x/y)
2. 血条ROI区域
3. 武器耐久ROI区域
4. V能量条ROI区域
5. HSV颜色范围（血条/传送门）

使用方法:
    python -m utils.calibration_tool
"""

import sys
import os
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from capture.screen_capture import ScreenCapture
from core.config import load_config


class CalibrationTool:
    """交互式校准工具"""

    def __init__(self):
        self.config = load_config()
        self.capture = ScreenCapture(self.config)

    def run(self):
        """主菜单"""
        while True:
            print("\n" + "=" * 50)
            print("灵虚界校准工具")
            print("=" * 50)
            print("1. 瞄准灵敏度校准")
            print("2. ROI区域校准（血条/武器/V能量）")
            print("3. HSV颜色调试（敌人血条/传送门）")
            print("4. 截图保存（采集模板素材）")
            print("5. 实时检测预览")
            print("0. 退出")
            print()

            choice = input("选择功能: ").strip()
            if choice == "1":
                self.calibrate_sensitivity()
            elif choice == "2":
                self.calibrate_roi()
            elif choice == "3":
                self.calibrate_hsv()
            elif choice == "4":
                self.take_screenshots()
            elif choice == "5":
                self.live_preview()
            elif choice == "0":
                break

    def calibrate_sensitivity(self):
        """瞄准灵敏度校准"""
        print("\n--- 瞄准灵敏度校准 ---")
        print("操作步骤:")
        print("1. 切到游戏，面对一个固定目标（训练场假人）")
        print("2. 把准星对准目标头部")
        print("3. 按回车开始测试")
        print("4. 程序会向右移动鼠标，观察游戏内转了多少角度")
        print("5. 输入你估计的角度，程序会计算灵敏度系数")
        input("\n按回车开始...")

        try:
            import pydirectinput
            import ctypes

            test_pixels = 200  # 移动200像素
            print(f"\n将向右移动鼠标 {test_pixels} 像素...")
            time.sleep(2)

            ctypes.windll.user32.mouse_event(0x0001, test_pixels, 0, 0, 0)
            time.sleep(1)

            angle_str = input("游戏内大约转了多少度? (输入数字): ").strip()
            try:
                angle = float(angle_str)
                if angle > 0:
                    # sensitivity = pixels_needed / pixels_moved * target_angle / actual_angle
                    # 简化: sensitivity ≈ desired_movement / actual_movement
                    recommended_x = test_pixels / (angle * 5)  # 粗略换算
                    print(f"\n推荐灵敏度: sensitivity_x = {recommended_x:.2f}")
                    print(f"当前值: {self.config.aim.sensitivity_x}")
                    print(f"\n请在 config.yaml 中修改:")
                    print(f"  aim:")
                    print(f"    sensitivity_x: {recommended_x:.2f}")
                    print(f"    sensitivity_y: {recommended_x * 0.75:.2f}  # 通常垂直=水平*0.75")
            except ValueError:
                print("输入无效")
        except ImportError:
            print("需要 pydirectinput 库，请在Windows上运行")

    def calibrate_roi(self):
        """ROI区域校准"""
        print("\n--- ROI区域校准 ---")
        print("将截取当前屏幕，请在弹出窗口中框选目标区域")
        print("1. 血条区域（左下角自身血条）")
        print("2. 武器耐久区域（右下角）")
        print("3. V能量条区域")

        choice = input("选择要校准的区域 (1/2/3): ").strip()
        names = {"1": "血条(health_bar)", "2": "武器耐久(weapon)", "3": "V能量(v_energy)"}
        name = names.get(choice, "未知")

        frame = self.capture.grab()
        display = cv2.resize(frame, (960, 540))

        print(f"请在窗口中框选 {name} 区域...")
        roi = cv2.selectROI(f"框选 {name}", display, fromCenter=False)
        cv2.destroyAllWindows()

        if roi[2] > 0 and roi[3] > 0:
            # 还原到1080p坐标
            x = int(roi[0] * 2)
            y = int(roi[1] * 2)
            w = int(roi[2] * 2)
            h = int(roi[3] * 2)
            print(f"\nROI坐标 (1080p): x={x}, y={y}, w={w}, h={h}")
            print(f"请在对应模块的 DEFAULT_ROI 中更新这些值")

    def calibrate_hsv(self):
        """HSV颜色调试"""
        print("\n--- HSV颜色调试 ---")
        print("截取当前屏幕，使用滑块调整HSV范围")
        print("调整到只剩目标物体时记录HSV值")
        print("按Q退出")

        frame = self.capture.grab()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        def nothing(x):
            pass

        cv2.namedWindow("HSV调试", cv2.WINDOW_NORMAL)
        cv2.createTrackbar("H_min", "HSV调试", 0, 180, nothing)
        cv2.createTrackbar("S_min", "HSV调试", 0, 255, nothing)
        cv2.createTrackbar("V_min", "HSV调试", 0, 255, nothing)
        cv2.createTrackbar("H_max", "HSV调试", 180, 180, nothing)
        cv2.createTrackbar("S_max", "HSV调试", 255, 255, nothing)
        cv2.createTrackbar("V_max", "HSV调试", 255, 255, nothing)

        while True:
            h1 = cv2.getTrackbarPos("H_min", "HSV调试")
            s1 = cv2.getTrackbarPos("S_min", "HSV调试")
            v1 = cv2.getTrackbarPos("V_min", "HSV调试")
            h2 = cv2.getTrackbarPos("H_max", "HSV调试")
            s2 = cv2.getTrackbarPos("S_max", "HSV调试")
            v2 = cv2.getTrackbarPos("V_max", "HSV调试")

            mask = cv2.inRange(hsv, np.array([h1, s1, v1]), np.array([h2, s2, v2]))
            result = cv2.bitwise_and(frame, frame, mask=mask)
            display = cv2.resize(result, (960, 540))
            cv2.imshow("HSV调试", display)

            if cv2.waitKey(30) == ord("q"):
                print(f"\n最终HSV范围: [{h1}, {s1}, {v1}] ~ [{h2}, {s2}, {v2}]")
                break

        cv2.destroyAllWindows()

    def take_screenshots(self):
        """快速截图"""
        print("\n--- 截图模式 ---")
        print("按S截图，按Q退出")

        count = 0
        save_dir = Path("screenshots")
        save_dir.mkdir(exist_ok=True)

        while True:
            frame = self.capture.grab()
            display = cv2.resize(frame, (960, 540))
            cv2.imshow("截图 (S=保存 Q=退出)", display)

            key = cv2.waitKey(50) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("s"):
                count += 1
                path = save_dir / f"cal_{int(time.time())}_{count}.png"
                cv2.imwrite(str(path), frame)
                print(f"已保存: {path}")

        cv2.destroyAllWindows()

    def live_preview(self):
        """实时检测预览"""
        print("\n--- 实时检测预览 ---")
        print("显示敌人检测+血量+状态，按Q退出")

        from detector.enemy_detector import EnemyDetector
        from detector.health_monitor import HealthMonitor

        det = EnemyDetector(self.config)
        hm = HealthMonitor(self.config)

        while True:
            frame = self.capture.grab()
            enemies = det.detect(frame)
            hp = hm.check(frame)

            # 绘制
            display = frame.copy()
            for e in enemies:
                color = (0, 0, 255) if e.enemy_type.value == "enemy_boss" else (0, 255, 0)
                x1 = e.center_x - e.width // 2
                y1 = e.center_y - e.height // 2
                cv2.rectangle(display, (x1, y1), (x1 + e.width, y1 + e.height), color, 2)
                cv2.putText(display, f"{e.enemy_type.value} {e.confidence:.0%}",
                            (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            # 中心十字
            h, w = display.shape[:2]
            cv2.line(display, (w // 2 - 20, h // 2), (w // 2 + 20, h // 2), (0, 255, 0), 2)
            cv2.line(display, (w // 2, h // 2 - 20), (w // 2, h // 2 + 20), (0, 255, 0), 2)

            # 信息
            cv2.putText(display, f"Enemies: {len(enemies)} | HP: {hp:.0%} | FPS: {self.capture.fps:.0f}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            display = cv2.resize(display, (960, 540))
            cv2.imshow("实时预览 (Q=退出)", display)

            if cv2.waitKey(50) == ord("q"):
                break

        cv2.destroyAllWindows()


def main():
    tool = CalibrationTool()
    tool.run()


if __name__ == "__main__":
    main()
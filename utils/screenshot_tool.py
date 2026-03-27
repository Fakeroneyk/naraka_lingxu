"""截图辅助工具 - 用于采集模板图片和YOLO训练数据

使用方法:
    python -m utils.screenshot_tool

功能:
    - 按 S 保存全屏截图
    - 按 R 保存选定区域截图（鼠标框选）
    - 按 Q 退出
"""

import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

# 将项目根目录加入Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from capture.screen_capture import ScreenCapture
from core.config import load_config


class ScreenshotTool:
    """截图辅助工具"""

    def __init__(self, save_dir: str = "screenshots"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        config = load_config()
        self.capture = ScreenCapture(config)
        self._count = 0

        print(f"截图工具已启动 | 保存目录: {self.save_dir}")
        print("操作说明:")
        print("  S - 保存全屏截图")
        print("  T - 保存模板（弹出窗口框选区域）")
        print("  Q - 退出")

    def run(self):
        """运行截图工具"""
        window_name = "灵虚界截图工具 (S=截图 T=框选模板 Q=退出)"

        while True:
            frame = self.capture.grab()

            # 缩小显示（方便在窗口中查看）
            display = cv2.resize(frame, (960, 540))
            cv2.imshow(window_name, display)

            key = cv2.waitKey(50) & 0xFF

            if key == ord("q"):
                break

            elif key == ord("s"):
                # 全屏截图
                self._count += 1
                filename = f"screenshot_{int(time.time())}_{self._count}.png"
                filepath = self.save_dir / filename
                cv2.imwrite(str(filepath), frame)
                print(f"✓ 截图已保存: {filepath}")

            elif key == ord("t"):
                # 框选区域截取模板
                print("请在窗口中框选模板区域...")
                roi = cv2.selectROI(window_name, display, fromCenter=False)
                if roi[2] > 0 and roi[3] > 0:
                    # 还原到原始分辨率
                    x = int(roi[0] * 2)
                    y = int(roi[1] * 2)
                    w = int(roi[2] * 2)
                    h = int(roi[3] * 2)

                    template = frame[y: y + h, x: x + w]
                    template_name = input("输入模板名称（不含.png）: ").strip()
                    if template_name:
                        # 保存到templates目录
                        template_dir = (
                            Path(__file__).parent.parent / "detector" / "templates"
                        )
                        template_dir.mkdir(parents=True, exist_ok=True)
                        filepath = template_dir / f"{template_name}.png"
                        cv2.imwrite(str(filepath), template)
                        print(f"✓ 模板已保存: {filepath} ({w}x{h})")
                        print(f"  ROI坐标: ({x}, {y}, {w}, {h})")
                    else:
                        print("✗ 取消保存")

        cv2.destroyAllWindows()
        print("截图工具已退出")


def main():
    tool = ScreenshotTool()
    tool.run()


if __name__ == "__main__":
    main()
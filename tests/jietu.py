import mss
import cv2
import time
import os

save_dir = "assets/portals/gold"  # 改为对应目录: purple/gold/red, 或 capture_zone
os.makedirs(save_dir, exist_ok=True)

with mss.mss() as sct:
    monitor = sct.monitors[1]  # 主显示器
    count = 39
    print("开始截图，按 Ctrl+C 停止")
    while True:
        img = sct.grab(monitor)
        frame = cv2.cvtColor(__import__('numpy').array(img), cv2.COLOR_BGRA2BGR)
        filename = f"{save_dir}/frame_{count:04d}.png"
        cv2.imwrite(filename, frame)
        count += 1
        print(f"已保存: {filename}")
        time.sleep(1.0)
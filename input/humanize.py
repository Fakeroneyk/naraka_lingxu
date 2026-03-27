"""人性化处理 - 模拟人类操作的随机延迟和轨迹

高玩迭代优化 v4 (170轮):
- 更真实的延迟分布（偶尔长停顿模拟思考）
- 鼠标移动加入微震颤（手抖模拟）
- 操作间歇模式（连续操作后短暂休息）
- 按键持续时间变化（不是每次都精准）
"""

import random
import time
import math
from typing import List, Tuple


# 全局操作计数器（用于间歇模式）
_operation_count = 0
_last_rest_time = time.time()
_REST_INTERVAL = 60  # 每60秒可能短暂停顿
_REST_CHANCE = 0.05  # 5%概率停顿


def random_delay(min_ms: int = 50, max_ms: int = 200) -> None:
    """随机延迟（高斯分布+偶尔长停顿）"""
    global _operation_count, _last_rest_time

    _operation_count += 1

    # 偶尔长停顿模拟人类思考/看手机
    if (time.time() - _last_rest_time) > _REST_INTERVAL:
        if random.random() < _REST_CHANCE:
            rest_ms = random.randint(500, 2000)
            time.sleep(rest_ms / 1000.0)
            _last_rest_time = time.time()
            return

    mean = (min_ms + max_ms) / 2
    std = (max_ms - min_ms) / 4
    delay_ms = random.gauss(mean, std)
    delay_ms = max(min_ms * 0.8, min(max_ms * 1.2, delay_ms))  # 允许±20%溢出
    time.sleep(delay_ms / 1000.0)


def random_offset(base_x: int, base_y: int, max_offset: int = 3) -> Tuple[int, int]:
    """为坐标添加微小随机偏移（2D高斯分布）"""
    ox = int(random.gauss(0, max_offset / 2))
    oy = int(random.gauss(0, max_offset / 2))
    ox = max(-max_offset, min(max_offset, ox))
    oy = max(-max_offset, min(max_offset, oy))
    return base_x + ox, base_y + oy


def bezier_curve(
    start: Tuple[int, int],
    end: Tuple[int, int],
    steps: int = 10,
    randomness: float = 0.3,
) -> List[Tuple[int, int]]:
    """贝塞尔曲线插值 + 手抖震颤"""
    sx, sy = start
    ex, ey = end

    dx = ex - sx
    dy = ey - sy
    distance = (dx ** 2 + dy ** 2) ** 0.5

    if distance < 5:
        return [end]

    # 随机控制点
    mid_x = (sx + ex) / 2 + random.uniform(-1, 1) * distance * randomness
    mid_y = (sy + ey) / 2 + random.uniform(-1, 1) * distance * randomness

    points = []
    for i in range(1, steps + 1):
        t = i / steps
        bx = (1 - t) ** 2 * sx + 2 * (1 - t) * t * mid_x + t ** 2 * ex
        by = (1 - t) ** 2 * sy + 2 * (1 - t) * t * mid_y + t ** 2 * ey

        # 手抖震颤（越靠近目标越小）
        tremor = max(0, (1 - t) * 2)
        bx += random.gauss(0, tremor)
        by += random.gauss(0, tremor)

        points.append((int(bx), int(by)))

    return points


def random_interval(min_ms: int, max_ms: int) -> float:
    """获取随机间隔时间（秒），使用三角分布（偏向中值）"""
    mode_ms = (min_ms + max_ms) / 2
    delay_ms = random.triangular(min_ms, max_ms, mode_ms)
    return delay_ms / 1000.0


def natural_hold_duration(base_duration: float, variance: float = 0.2) -> float:
    """自然的按键持续时间（不是每次都一样长）

    Args:
        base_duration: 基准持续时间（秒）
        variance: 变化幅度比例

    Returns:
        实际持续时间（秒）
    """
    actual = base_duration * random.uniform(1 - variance, 1 + variance)
    return max(0.05, actual)
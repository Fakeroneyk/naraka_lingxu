"""会话统计持久化 - 记录每次运行的统计数据

高玩迭代 v5 (270轮):
- JSON格式保存每次运行统计
- 历史统计汇总查看
- 效率分析（每分钟通关数等）
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from loguru import logger


class SessionStats:
    """会话统计管理器"""

    STATS_DIR = Path("stats")
    HISTORY_FILE = STATS_DIR / "history.json"

    def __init__(self):
        self.STATS_DIR.mkdir(exist_ok=True)
        self._start_time = time.time()
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def save(self, combat_stats: Dict) -> None:
        """保存本次会话统计"""
        runtime = time.time() - self._start_time
        mins = runtime / 60

        session_data = {
            "session_id": self._session_id,
            "start_time": datetime.fromtimestamp(self._start_time).isoformat(),
            "runtime_seconds": int(runtime),
            "runtime_minutes": round(mins, 1),
            **combat_stats,
            "efficiency": {
                "stages_per_minute": round(combat_stats.get("stages_cleared", 0) / max(mins, 0.1), 2),
                "deaths_per_stage": round(
                    combat_stats.get("deaths", 0) / max(combat_stats.get("stages_cleared", 1), 1), 2
                ),
            },
        }

        # 保存单次会话
        session_file = self.STATS_DIR / f"session_{self._session_id}.json"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

        # 追加到历史记录
        self._append_history(session_data)

        logger.info(f"统计已保存: {session_file}")

    def _append_history(self, session_data: Dict) -> None:
        """追加到历史统计"""
        history = []
        if self.HISTORY_FILE.exists():
            try:
                with open(self.HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []

        history.append(session_data)

        # 只保留最近100次
        if len(history) > 100:
            history = history[-100:]

        with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    @classmethod
    def print_summary(cls) -> None:
        """打印历史统计汇总"""
        if not cls.HISTORY_FILE.exists():
            print("暂无历史统计数据")
            return

        with open(cls.HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)

        if not history:
            print("暂无历史统计数据")
            return

        total_runtime = sum(s.get("runtime_minutes", 0) for s in history)
        total_stages = sum(s.get("stages_cleared", 0) for s in history)
        total_deaths = sum(s.get("deaths", 0) for s in history)
        total_jue = sum(s.get("jue_selected", 0) for s in history)
        total_heals = sum(s.get("heals_used", 0) for s in history)

        print("\n" + "=" * 50)
        print(f"历史统计汇总 ({len(history)} 次运行)")
        print("=" * 50)
        print(f"  总运行时间: {total_runtime:.0f} 分钟")
        print(f"  总通关关卡: {total_stages}")
        print(f"  总死亡次数: {total_deaths}")
        print(f"  总灵诀选择: {total_jue}")
        print(f"  总回血次数: {total_heals}")
        if total_runtime > 0:
            print(f"  平均效率: {total_stages / total_runtime:.1f} 关/分钟")
        if total_stages > 0:
            print(f"  死亡率: {total_deaths / total_stages:.1%}")
        print("=" * 50)
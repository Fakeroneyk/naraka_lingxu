"""日志模块 - 基于loguru的日志封装"""

import sys
from pathlib import Path

from loguru import logger


def setup_logger(log_level: str = "INFO", log_dir: str = "logs") -> None:
    """初始化日志配置

    Args:
        log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        log_dir: 日志文件目录
    """
    # 移除默认handler
    logger.remove()

    # 控制台输出（带颜色）
    logger.add(
        sys.stdout,
        level=log_level,
        format=(
            "<green>{time:HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # 文件输出（按天轮转）
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger.add(
        str(log_path / "lingxu_{time:YYYY-MM-DD}.log"),
        level="DEBUG",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
        rotation="1 day",
        retention="7 days",
        encoding="utf-8",
    )

    logger.info(f"日志系统初始化完成，级别: {log_level}")
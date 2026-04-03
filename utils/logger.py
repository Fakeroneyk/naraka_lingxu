"""
日志工具模块
基于 loguru 提供统一的结构化日志，支持控制台彩色输出与文件滚动记录。
"""

import sys
from pathlib import Path
from loguru import logger

# 移除默认处理器
logger.remove()

# 控制台输出（INFO 及以上，带颜色）
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
)

# 文件输出（DEBUG 及以上，滚动保存，最多保留 7 天）
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

logger.add(
    log_dir / "naraka_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
    rotation="00:00",
    retention="7 days",
    encoding="utf-8",
)


def get_logger(name: str):
    """
    获取带模块名称的 logger 实例（loguru 全局共享，name 仅用于标识）

    用法:
        from utils.logger import get_logger
        log = get_logger(__name__)
        log.info("战斗开始")
    """
    return logger.bind(name=name)
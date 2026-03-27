"""状态枚举定义 v9"""

from enum import Enum, auto


class CombatState(Enum):
    """战斗引擎内部状态"""
    PATROL = auto()
    AIMING = auto()
    FIRING = auto()
    BOSS_BURST = auto()


class GamePhase(Enum):
    """游戏全局阶段"""
    LOBBY = auto()
    LOADING = auto()
    COMBAT = auto()
    JUE_SELECT = auto()
    PORTAL_SEARCH = auto()
    SUPPLY = auto()


class PortalType(Enum):
    """传送门类型"""
    SHOP = "shop"
    NORMAL = "normal"
    BOSS = "boss"


class EnemyType(Enum):
    """敌人类型"""
    NORMAL = "enemy_normal"
    BOSS = "enemy_boss"
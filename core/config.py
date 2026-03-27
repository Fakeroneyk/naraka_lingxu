"""配置加载模块 - 从config.yaml读取全局配置

高玩迭代 v7 (470轮):
- 配置验证：检查关键参数合法性
- 默认值兜底：缺失配置项不崩溃
- 分辨率自动检测
"""

from pathlib import Path
from typing import Any

import yaml
from loguru import logger


class Config:
    """配置管理器，支持点号访问嵌套配置"""

    def __init__(self, data: dict):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, Config(value))
            elif isinstance(value, list):
                setattr(self, key, [
                    Config(item) if isinstance(item, dict) else item
                    for item in value
                ])
            else:
                setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        """安全获取配置项（缺失返回默认值）"""
        return getattr(self, key, default)

    def to_dict(self) -> dict:
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Config):
                result[key] = value.to_dict()
            elif isinstance(value, list):
                result[key] = [
                    item.to_dict() if isinstance(item, Config) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def __repr__(self) -> str:
        return f"Config({self.to_dict()})"


def _validate_config(config: Config) -> None:
    """验证关键配置参数"""
    warnings = []

    # 分辨率
    res = config.get("screen")
    if res:
        w, h = res.resolution[0], res.resolution[1]
        if w < 1280 or h < 720:
            warnings.append(f"分辨率过低 ({w}x{h})，建议1920x1080")

    # 灵敏度
    aim = config.get("aim")
    if aim:
        sx = aim.get("sensitivity_x", 0.8)
        if sx <= 0 or sx > 5:
            warnings.append(f"灵敏度sensitivity_x={sx}异常，建议0.3-2.0")

    # 按键
    kb = config.get("keybinds")
    if kb:
        required_keys = ["skill_f", "skill_v", "weapon_cannon", "move_forward",
                          "lock_target", "heal", "interact"]
        for k in required_keys:
            if not kb.get(k):
                warnings.append(f"按键 keybinds.{k} 未配置")

    for w in warnings:
        logger.warning(f"配置警告: {w}")


def load_config(config_path: str = None) -> Config:
    """加载配置文件"""
    if config_path is None:
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config.yaml"

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    config = Config(data)
    _validate_config(config)
    return config


_global_config: Config | None = None


def get_config() -> Config:
    global _global_config
    if _global_config is None:
        _global_config = load_config()
    return _global_config


def reload_config(config_path: str = None) -> Config:
    global _global_config
    _global_config = load_config(config_path)
    return _global_config
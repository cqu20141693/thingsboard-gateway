from enum import Enum


class TagQuality(Enum):
    """点位质量"""
    GOOD = "GOOD"  # 通信良好
    BAD = "BAD"  # 通信断开


class TagType(Enum):
    """点位类型"""
    TIMESERIES = "telemetry"  # 时序数据 只支持读取
    ATTRIBUTES = "attributes"  # 属性数据 支持读取，写入

"""
Watch Alarm System Module
Attention monitoring and escalating alarm system for crew watch duties
"""

from .watch_alarms import (
    WatchAlarmManager,
    AttentionMonitor,
    AlarmLevel,
    AlarmType,
    WatchStatus,
    AlarmEscalationRule,
    AlarmEvent,
    OverrideReason
)

__all__ = [
    'WatchAlarmManager',
    'AttentionMonitor',
    'AlarmLevel',
    'AlarmType',
    'WatchStatus',
    'AlarmEscalationRule',
    'AlarmEvent',
    'OverrideReason'
]
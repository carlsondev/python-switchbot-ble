'''
Python-Switchbot-BLE: A Python library for interfacing with Switchbot devices over Bluetooth Low Energy (BLE)
Copyright (C) 2023  Benjamin Carlson
'''

from dataclasses import dataclass
from enum import Enum
from typing import List
from datetime import timedelta


class DayOfWeek(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class AlarmExecType(Enum):
    REPEATED = 0
    REPEAT_N_TIMES_AT_INTERVAL = 1
    REPEAT_FOREVER_AT_INTERVAL = 2


class AlarmExecAction(Enum):
    ACTION = 0
    ON = 1
    OFF = 2


@dataclass
class AlarmInfo:

    # If false, execute once
    execute_repeatedly: bool

    # If execute_repeatedly is true, this is the list of days to execute on
    valid_days: List[DayOfWeek]

    # The time to execute at
    execution_time: timedelta

    # The type of execution that occurs
    exec_type: AlarmExecType

    # The action to execute
    exec_action: AlarmExecAction

    # For AlarmExecType.REPEAT_N_TIMES_AT_INTERVAL
    num_continuous_actions: int

    # If execute_repeatedly is true, Max 5 hours, seconds in steps of 10
    interval: timedelta

'''
Python-Switchbot-BLE: A Python library for interfacing with Switchbot devices over Bluetooth Low Energy (BLE)
Copyright (C) 2023  Benjamin Carlson
'''

from dataclasses import dataclass
from enum import Enum
from typing import List
from datetime import timedelta

import enum_tools.documentation

__all__ = ["DayOfWeek", "AlarmExecType", "AlarmExecAction", "AlarmInfo"]

enum_tools.documentation.INTERACTIVE = True

@enum_tools.documentation.document_enum
class DayOfWeek(Enum):
    '''
    The day of the week to execute an alarm on
    '''
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

@enum_tools.documentation.document_enum
class AlarmExecType(Enum):
    '''
    The type of execution that will occur
    '''
    REPEATED = 0 # doc: "Execute repeatedly"
    REPEAT_N_TIMES_AT_INTERVAL = 1 # doc: "Execute N times every interval"
    REPEAT_FOREVER_AT_INTERVAL = 2 # doc: "Execute forever every interval"

@enum_tools.documentation.document_enum
class AlarmExecAction(Enum):
    '''
    The action to execute when the alarm is triggered
    '''
    ACTION = 0 # doc: "Press"
    ON = 1  # doc: "Turn on"
    OFF = 2 # doc: "Turn off"


@dataclass
class AlarmInfo:
    '''
    The information for an alarm
    '''

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

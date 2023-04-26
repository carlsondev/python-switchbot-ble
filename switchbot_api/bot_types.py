'''
Python-Switchbot-BLE: A Python library for interfacing with Switchbot devices over Bluetooth Low Energy (BLE)
Copyright (C) 2023  Benjamin Carlson
'''

import enum


class SwitchBotCommand(enum.Enum):
    # Known Valid UUIDs
    COMM_SERVICE_UUID = "cba20d00-224d-11e6-9fb8-0002a5d5c51b"
    REQ_CHAR_UUID = "cba20002-224d-11e6-9fb8-0002a5d5c51b"
    RESP_CHAR_UUID = "cba20003-224d-11e6-9fb8-0002a5d5c51b"
    # Unknown if valid UUIDs
    SERVICE_CHANGED_CHAR_UUID = "00002a05-0000-1000-8000-00805f9b34fb"
    # Handle 0x04 and 0x19
    CLIENT_CHAR_CONFIG_UUID = "00002902-0000-1000-8000-00805f9b34fb"
    GENERIC_ATTRIB_PROFILE_UUID = "00001801-0000-1000-8000-00805f9b34fb"


class SwitchBotReqType(enum.Enum):
    COMMAND = 0x01
    GET_BASIC_INFO = 0x02
    SET_BASIC_INFO = 0x03
    SET_PASSWORD = 0x07
    GET_TIME_MGMT_INFO = 0x08
    SET_TIME_MGMT_INFO = 0x09
    EXTENDED_COMMAND = 0x0F
    CLEAR_PASSWORD = 0x17


class SwitchBotAction(enum.Enum):
    PRESS = 0x00
    ON = 0x01
    OFF = 0x02
    PUSH_STOP = 0x03
    BACK = 0x04


class SwitchBotMode(enum.Enum):
    ONE_STATE = 0x0
    ON_OFF_STATE = 0x1


class TimeManagementInfoSubCommand(enum.Enum):
    DEVICE_TIME = 0x01
    ALARM_COUNT = 0x02
    ALARM_INFO = 0x03


# Unsure on the use of this, probbaly a larger ecosystem thing
class SwitchBotGroup(enum.Enum):
    GROUP_A = 0x0
    GROUP_B = 0x1
    GROUP_C = 0x2
    GROUP_D = 0x3


# Theorhetically we only need the BOT type but just for completeness
class SwitchBotDeviceType(enum.Enum):
    BOT = 0x48
    WO_BUTTON = 0x42
    DOOR_LOCK = 0x6F
    HUB_ADD = 0x4C  # Add mode
    HUB = 0x6C
    HUB_PLUS_ADD = 0x50  # Add mode
    HUB_PLUS = 0x70
    FAN_ADD = 0x46  # Add mode
    FAN = 0x66
    METER_ADD = 0x74  # Add mode
    METER = 0x54
    MINI_ADD = 0x4D  # Add mode
    MINI = 0x6D
    CURTAIN_PAIR = 0x43  # Pair mode
    CURTAIN = 0x63
    CONTACT_SENSOR_PAIR = 0x44  # Pair mode
    CONTACT_SENSOR = 0x64
    MOTION_SENSOR_PAIR = 0x53  # Pair mode
    MOTION_SENSOR = 0x73


class SwitchBotRespStatus(enum.Enum):
    UNKNOWN = 0x00
    OK = 0x01
    ERROR = 0x02
    BUSY = 0x03
    COMM_VERSION_NOT_SUPPORTED = 0x04
    COMMAND_NOT_SUPPORTED = 0x05
    LOW_BATTERY = 0x06
    ENC_WRONG_PASSWORD = 0x07
    DEV_UNENCRYPTED = 0x08  # I don't know when this would be returned
    PASSWORD_ERROR = 0x09
    ENC_METHOD_NOT_SUPPORTED = 0x0A
    NO_NEARBY_MESH_DEVICE = 0x0B
    FAILED_NETWORK_CONNECTION = 0x0C


# Technically doesn't belong here but should be accessible everywhere
def f_bytes(data: bytearray) -> str:
    """
    Formats byte array to readable hex string

    :param data: The data to format
    :type data: bytearray
    :return: Space seperated hex string
    :rtype: str
    """
    return " ".join(hex(x) for x in data)

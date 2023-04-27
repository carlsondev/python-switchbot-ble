'''
Python-Switchbot-BLE: A Python library for interfacing with Switchbot devices over Bluetooth Low Energy (BLE)
Copyright (C) 2023  Benjamin Carlson
'''

import enum
import enum_tools.documentation

__all__ = ["SwitchBotCommand", "SwitchBotReqType", "SwitchBotAction", "SwitchBotMode", "TimeManagementInfoSubCommand", "SwitchBotGroup", "SwitchBotDeviceType", "SwitchBotRespStatus", "f_bytes"]

enum_tools.documentation.INTERACTIVE = True

@enum_tools.documentation.document_enum
class SwitchBotCommand(enum.Enum):
    '''
    Generally known UUIDS for the SwitchBot (Bot)
    '''

    # Known Valid UUIDs
    COMM_SERVICE_UUID = "cba20d00-224d-11e6-9fb8-0002a5d5c51b"
    REQ_CHAR_UUID = "cba20002-224d-11e6-9fb8-0002a5d5c51b"
    RESP_CHAR_UUID = "cba20003-224d-11e6-9fb8-0002a5d5c51b"
    # Unknown if valid UUIDs
    SERVICE_CHANGED_CHAR_UUID = "00002a05-0000-1000-8000-00805f9b34fb"
    # Handle 0x04 and 0x19
    CLIENT_CHAR_CONFIG_UUID = "00002902-0000-1000-8000-00805f9b34fb"
    GENERIC_ATTRIB_PROFILE_UUID = "00001801-0000-1000-8000-00805f9b34fb"

@enum_tools.documentation.document_enum
class SwitchBotReqType(enum.Enum):
    '''
    The type of request to send to the SwitchBot
    '''
    COMMAND = 0x01
    GET_BASIC_INFO = 0x02
    SET_BASIC_INFO = 0x03
    SET_PASSWORD = 0x07
    GET_TIME_MGMT_INFO = 0x08
    SET_TIME_MGMT_INFO = 0x09
    EXTENDED_COMMAND = 0x0F
    CLEAR_PASSWORD = 0x17

@enum_tools.documentation.document_enum
class SwitchBotAction(enum.Enum):
    '''
    The action to execute on a COMMAND request
    '''
    PRESS = 0x00 # doc: Press
    ON = 0x01 # doc: Turn on
    OFF = 0x02 # doc: Turn off
    PUSH_STOP = 0x03 # doc: Push and leave
    BACK = 0x04 # doc: Pull and leave

@enum_tools.documentation.document_enum
class SwitchBotMode(enum.Enum):
    '''
    The type of mode to enable for the SwitchBot
    '''
    ONE_STATE = 0x0 # doc: Single action state
    ON_OFF_STATE = 0x1 # doc: On/Off state

@enum_tools.documentation.document_enum
class TimeManagementInfoSubCommand(enum.Enum):
    '''
    The subcommand to send to the SwitchBot for time management
    '''
    DEVICE_TIME = 0x01
    ALARM_COUNT = 0x02
    ALARM_INFO = 0x03


# Unsure on the use of this, probbaly a larger ecosystem thing
@enum_tools.documentation.document_enum
class SwitchBotGroup(enum.Enum):
    '''
    The group that the device belongs to
    '''
    GROUP_A = 0x0
    GROUP_B = 0x1
    GROUP_C = 0x2
    GROUP_D = 0x3



@enum_tools.documentation.document_enum
class SwitchBotDeviceType(enum.Enum):
    '''
    The type of device that the SwitchBot is
    '''

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

@enum_tools.documentation.document_enum
class SwitchBotRespStatus(enum.Enum):
    '''
    The status of the response from the SwitchBot
    '''
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

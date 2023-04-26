'''
Python-Switchbot-BLE: A Python library for interfacing with Switchbot devices over Bluetooth Low Energy (BLE)
Copyright (C) 2023  Benjamin Carlson
'''

from typing import Optional, List, Dict
import zlib
from datetime import timedelta

from .bot_types import SwitchBotDeviceType, SwitchBotMode, SwitchBotGroup
from .alarm_info import AlarmInfo, AlarmExecAction, AlarmExecType, DayOfWeek


class BotInformation:
    def __init__(self, get_info_byte_array: Optional[bytearray] = None):
        """
        Initialize information class with "Get Information" bytes if present

        :param get_info_byte_array: The byte data from the Get Information request
        :type get_info_byte_array: Optional[bytearray]
        """
        # Start Device Info
        self._remaining_battery_percent = 100  # 0-100
        self._firmware_version: float = 6.3
        self._push_button_strength = 100  # 0-100

        self._sensor_adc_value = 0  # Analog Digital Converter value
        self._motor_calibration_val = 0xA1  # Motor calibration value

        self._time_number = 0  # Number of the timer?
        self._bot_act_mode = 0  # Bot action mode, TOOD: Convert to new enum
        self._hold_and_press_times = 0  # Default

        self._is_encrypted = False

        self._device_type = SwitchBotDeviceType.BOT

        self._bot_mode = SwitchBotMode.ONE_STATE  # Default

        self._is_off = True

        self._encryption_type = 0  # (0 = standard checksum, 1 = TBD)

        self._device_groups: List[SwitchBotGroup] = []

        self._current_pass_str: Optional[str] = None
        self._current_pass_checksum: Optional[bytearray] = None

        # End Device Info

        # Start time management info

        # UNIX time since epoch
        self._current_timestamp = 0

        self._alarm_count = 0

        self._alarm_infos: Dict[int, AlarmInfo] = {}
        # End time management info

        if get_info_byte_array is not None:
            self._init_from_byte_array(get_info_byte_array)

    def _init_from_byte_array(self, get_info_byte_array: bytearray):
        """
        Initialize data from "Get Information" bytes

        :param get_info_byte_array: The byte data from the Get Information request
        :type get_info_byte_array: bytearray
        """
        if len(get_info_byte_array) != 12:
            raise ValueError(
                f"Invalid byte array length ({len(get_info_byte_array)})for BotInformation"
            )

        # For 1 byte values
        int_data = [int(byte) for byte in get_info_byte_array]

        self._remaining_battery_percent = int_data[0]  # 0-100
        self._firmware_version: float = int_data[1] * 0.1  # 44 * 0.1 = 4.4 Firmware version
        self._push_button_strength = int_data[2]  # 0-100

        self._sensor_adc_value = int.from_bytes(
            get_info_byte_array[3:5], byteorder="big"
        )  # Analog Digital Converter value
        self._motor_calibration_val = int.from_bytes(
            get_info_byte_array[5:7], byteorder="big"
        )  # Motor calibration value

        self._time_number = int_data[7]  # Number of the timer?
        self._bot_act_mode = int_data[8]  # Bot action mode, TOOD: Convert to new enum
        self._hold_and_press_times = int_data[9]  # Hold-and-press times

        self.read_service_bytes(get_info_byte_array[10:12])

    def read_service_bytes(self, service_bytes: bytearray) -> None:
        """
        Update object from service bytes (either from advertisement or Get Information)

        :param service_bytes: Service byte array
        :type service_bytes: bytearray
        """
        if len(service_bytes) < 2 or len(service_bytes) > 3:
            raise ValueError(
                f"Invalid service bytes length ({len(service_bytes)})for BotInformation"
            )

        # Might be little endian for broadcasting, currently assuming big endian (from BLE requests)

        # Handle Encrypted/Device Type Byte
        enc_dev_type_byte = service_bytes[0]

        self._is_encrypted = (enc_dev_type_byte & 0x80) == 0x80  # First bit is 1 if encrypted
        device_type_int = int(enc_dev_type_byte & 0x7F)  # Last 7 bits are the device type
        try:
            self._device_type = SwitchBotDeviceType(device_type_int)
        except ValueError:
            print(f"Unknown device type: {device_type_int}")
            pass
        # End Encrypted/Device Type Byte

        # Handle Status Byte
        status_byte = service_bytes[1]

        bot_mode_int = int(
            (status_byte & 0x80) == 0x80
        )  # First bit is the bot mode (0 = one state, 1 = on/off state)
        self._bot_mode = SwitchBotMode(bot_mode_int)

        self._is_off = (
            status_byte & 0x40
        ) == 0x40  # Second bit is the current bot state (0 = on, 1 = off)

        self._encryption_type = int(
            (status_byte & 0x20) == 0x20
        )  # Third bit is the encryption type (0 = standard checksum, 1 = TBD)

        # A little bit unsure what to do with this
        has_service_data_update = (
            status_byte & 0x10
        ) == 0x10  # Fourth bit is if the service data has been updated (0 = no, 1 = yes)

        self._device_groups = [
            group for group in SwitchBotGroup if (status_byte & group.value) == group.value
        ]  # Last 4 bits are the device group membership

        # End Status Byte

        if len(service_bytes) > 2:
            update_utc_flag_bat_byte = service_bytes[2]

            does_require_utc_sync = (
                update_utc_flag_bat_byte & 0x80
            ) == 0x80  # First bit is if the device requires a UTC sync

            self._remaining_battery_percent = int(
                update_utc_flag_bat_byte & 0x7F
            )  # Last 7 bits are the remaining battery percent

    # Basic Info Properties

    @property
    def password_str(self) -> Optional[str]:

        return self._current_pass_str

    @password_str.setter
    def password_str(self, password_str: Optional[str]):
        """
        Sets the password (or clears with None) and computes the password checksum

        :param password_str: The new password string
        :type password_str: Optional[str]
        """
        if password_str is None:
            self._is_encrypted = False
            self._current_pass_str = None
            self._current_pass_checksum = None
            return

        self._current_pass_str = password_str
        self._current_pass_checksum = zlib.crc32(self._current_pass_str.encode()).to_bytes(
            4, byteorder="big"
        )

        self._is_encrypted = True

    @property
    def password_checksum(self) -> Optional[bytearray]:
        return self._current_pass_checksum

    @property
    def is_encrypted(self) -> bool:
        return self._is_encrypted

    @property
    def remaining_battery_percent(self) -> int:
        return self._remaining_battery_percent

    @property
    def firmware_version(self) -> float:
        return self._firmware_version

    @property
    def push_button_strength(self) -> int:
        return self._push_button_strength

    @property
    def sensor_adc_value(self) -> int:
        return self._sensor_adc_value

    @property
    def motor_calibration_val(self) -> int:
        return self._motor_calibration_val

    @property
    def time_number(self) -> int:
        return self._time_number

    @property
    def bot_action_mode(self) -> int:
        return self._bot_act_mode

    @property
    def hold_and_press_times(self) -> int:
        return self._hold_and_press_times

    @property
    def device_type(self) -> SwitchBotDeviceType:
        return self._device_type

    @property
    def bot_mode(self) -> SwitchBotMode:
        return self._bot_mode

    @property
    def is_off(self) -> bool:
        return self._is_off

    @property
    def encryption_type(self) -> int:
        return self._encryption_type

    @property
    def device_groups(self) -> List[SwitchBotGroup]:
        return self._device_groups

    # End Basic Info Properties

    # Start Time Management Properties

    @property
    def alarm_count(self) -> int:
        return self._alarm_count

    @alarm_count.setter
    def alarm_count(self, count: int):
        """
        Updates alarm count (and performs 0 <= n <= 4 bounds checking)

        :param count: The amount of alarms
        :type count: int
        """
        if count < 0 or count > 4:
            print(f"Invalid alarm count {count}, must be between 0 and 4!")
            raise UserWarning(f"Invalid alarm count {count}, must be between 0 and 4!")

        self._alarm_count = count

    @property
    def system_timestamp(self) -> int:
        return self._current_timestamp

    @system_timestamp.setter
    def system_timestamp(self, timestamp: int):
        """
        Updates the timestamp (and performs 0 <= t bounds checking)

        :param timestamp: SwitchBot Unix timestamp
        :type timestamp: int
        """
        if timestamp < 0:
            print(f"Invalid timestamp {timestamp}, must be greater than 0!")
            raise UserWarning(f"Invalid timestamp {timestamp}, must be greater than 0!")
        self._current_timestamp = timestamp

    @property
    def active_alarms(self) -> List[AlarmInfo]:
        return [info for _, info in self._alarm_infos.items()]

    def update_alarm(self, response_data: bytearray):
        """
        Update alarm info from fetch alarm info request

        :param response_data: response bytes
        :type response_data: bytearray
        """
        if len(response_data) != 11:
            print(
                f"Could not update alarm, invalid response data length {len(response_data)} (Must be 11)"
            )

        alarm_count = response_data[0]
        alarm_idx = response_data[1]

        exec_repeatedly = response_data[2] >> 7 == 0

        valid_days: List[DayOfWeek] = []

        for dow in DayOfWeek:
            if response_data[2] & (1 << dow.value) == 1:
                valid_days.append(dow)

        exec_time = timedelta(hours=response_data[3], minutes=response_data[4])

        exec_type = AlarmExecType(response_data[5])
        exec_action = AlarmExecAction(response_data[6])

        action_count = response_data[7]

        exec_interval = timedelta(
            hours=response_data[8], minutes=response_data[9], seconds=response_data[10]
        )

        info = AlarmInfo(
            exec_repeatedly,
            valid_days,
            exec_time,
            exec_type,
            exec_action,
            action_count,
            exec_interval,
        )

        self._alarm_count = alarm_count
        self._alarm_infos[alarm_idx] = info

'''
Python-Switchbot-BLE: A Python library for interfacing with Switchbot devices over Bluetooth Low Energy (BLE)
Copyright (C) 2023  Benjamin Carlson
'''

from bleak import BleakClient, BleakScanner, BLEDevice, BleakGATTCharacteristic
from typing import Optional, List, Union, Tuple
import asyncio
import zlib
import time
import math

from .bot_types import (
    SwitchBotReqType,
    SwitchBotCommand,
    SwitchBotRespStatus,
    SwitchBotAction,
    TimeManagementInfoSubCommand,
    SwitchBotMode,
    f_bytes,
)
from .bot_information import BotInformation
from .alarm_info import AlarmInfo

# Functionality to capture packets for
#   - Custom Mode
#   - Custom Mode with Encryption
#   - Messages between 0x01 and 0x0F


class VirtualSwitchBot:
    def __init__(
        self,
        mac_address: str,
        device: Optional[BLEDevice] = None,
        password_str: Optional[str] = None,
    ):
        """
        A SwitchBot wrapper class for sending commands to/from the physical SwitchBot

        :param mac_address: The MAC address of the SwitchBot
        :type mac_address: str
        :param device: Already found BLEDevice (avoids finding twice)
        :type device: Optional[bleak.BLEDevice]
        :param password_str: The SwitchBot's password, None if no password is set
        :type password_str: Optional[str]
        """
        self._address = mac_address

        # Used for setting up a pre-connected device, if available
        self._device = device
        self._client: Optional[BleakClient] = None

        self._info = BotInformation()

        # Used to know what request yielded which response
        self._request_response_queue: Optional[asyncio.Queue] = None

        if password_str is not None:
            self._info.password_str = password_str

    async def connect(self):
        """
        Find (if device has not been set), and connect to the SwitchBot
        """
        self._request_response_queue = asyncio.Queue()

        if self._device is None:
            self._device = await BleakScanner.find_device_by_address(self._address)
            if self._device is None:
                print(f"Device not found for MAC Address {self._address}")
                exit(1)

            print(f"Found SwitchBot {self._device.name} with specificed MAC Address ({self._device.address})")

        self._client = BleakClient(self._device)

        try:
            await self._client.connect()
        except asyncio.TimeoutError:
            raise UserWarning(f"Timeout connecting to {self._address}, try again")
        print(f"Connected to {self._address}")

        await self._client.start_notify(
            SwitchBotCommand.RESP_CHAR_UUID.value, self._notif_callback_handler
        )

        await self.fetch_basic_device_info()
        await asyncio.sleep(1)
        await self.fetch_alarm_count()
        await asyncio.sleep(1)
        await self.fetch_system_time()
        await asyncio.sleep(1)

    async def disconnect(self):
        """
        Disconnect from SwitchBot
        """
        if self._client is None:
            print("Client is not connected. Cannot disconnect.")
            return

        print(f"Disconnecting from SwitchBot ({self._address})")
        await self._client.disconnect()

    async def _notif_callback_handler(
        self, characteristic: BleakGATTCharacteristic, data: bytearray
    ):
        """

        :param characteristic: The characteristic that was originally requested
        :type characteristic: bleak.BleakGATTCharacteristic
        :param data: The data received
        :type data: bytearray
        :return:
        :rtype:
        """
        request_type: SwitchBotReqType = await self._request_response_queue.get()

        status_enum = SwitchBotRespStatus(data[0])
        response_data = data[1:]
        print(
            f"Received response for {request_type.name} with status {status_enum.name} ({status_enum.value}): {f_bytes(response_data)}"
        )

        if status_enum != SwitchBotRespStatus.OK:
            return

        if request_type == SwitchBotReqType.SET_PASSWORD:
            print(
                f"Successfully set password to {self._info.password_str}"
            )  # Current pass is new pass
            return

        if request_type == SwitchBotReqType.COMMAND:
            print(f"Successfully sent command to SwitchBot")
            return

        if request_type == SwitchBotReqType.GET_BASIC_INFO:
            curr_password = self._info.password_str
            self._info = BotInformation(response_data)
            self._info.password_str = curr_password
            print(f"Successfully retrieved basic information")
            return

        if request_type == SwitchBotReqType.GET_TIME_MGMT_INFO:
            resp_len = len(response_data)
            if resp_len == 1:
                self._info.alarm_count = response_data[0]
                print(f"Successfully retrieved alarm count ({self._info.alarm_count})")

            if resp_len == 8:
                self._info.system_timestamp = int.from_bytes(
                    response_data, byteorder="big", signed=False
                )
                print(f"Successfully recieved system time ({self._info.system_timestamp})")

            if resp_len == 11:
                print(f"Successfully recieved alarm info for index {response_data[1]}")
                self._info.update_alarm(response_data)

    async def _send_request(self, message_bytes: bytearray, request_type: SwitchBotReqType):
        """
        Send a request to the SwitchBot

        :param message_bytes: The bytes of the message to send
        :type message_bytes: bytearray
        :param request_type: The type of request to send (used for figuring out which message was received)
        :type request_type: SwitchBotReqType
        """
        if self._client is None:
            print("Client is not connected. Cannot send request.")
            return

        self._request_response_queue.put_nowait(request_type)
        await self._client.write_gatt_char(
            SwitchBotCommand.REQ_CHAR_UUID.value, message_bytes, response=True
        )

    def _check_append_pass_check(
        self, curr_payload: Union[bytearray, List[int]], preappend: bool = False
    ) -> bytearray:
        """
        (Pre)Append the password checksum to the payload if the password exists

        :param curr_payload: The payload to modify
        :type curr_payload: Union[bytearray|List[int]]
        :param preappend: Whether to preappend the checksum or not (default false)
        :type preappend: bool
        :return: Modified payload (or the same if no password)
        :rtype: bytearray
        """
        payload = curr_payload.copy()
        if isinstance(curr_payload, list):
            payload = bytearray(payload)
        if self._info.is_encrypted:
            if self._info.password_checksum is None:
                print("Cannot send encrypted message without password checksum")
                raise UserWarning("Cannot send encrypted message without password checksum")
            if preappend:
                payload = self._info.password_checksum + payload
            else:
                payload += self._info.password_checksum

        return payload

    # | B_0  |                    B_1                      |    B_2    |    B_3    | ... |    B_15    |
    # | 0x57 | v_1 v_0 enc_1 enc_0 cmd_3 cmd_2 cmd_1 cmd_0 | payload_0 | payload_1 | ... | payload_15 |
    def _build_request_msg(
        self, command_type: SwitchBotReqType, payload: bytearray, version: int = 0
    ) -> bytearray:
        """
        Builds the header and appends the payload data to build the entire data packet

        :param command_type: The type of command to send (added to the header)
        :type command_type: SwitchBotReqType
        :param payload: The payload added to the header
        :type payload: bytearray
        :param version: Version (only 0 at the moment)
        :type version: int
        :return: Final request packet bytes
        :rtype: bytearray
        """
        msg = bytearray([0x57])

        byte_1 = version << 6
        byte_1 |= (0x01 if self._info.is_encrypted else 0x00) << 4
        byte_1 |= command_type.value
        msg.append(byte_1)

        if command_type == SwitchBotReqType.SET_TIME_MGMT_INFO:
            msg.append(0x08)  # Set long press duration

        msg += payload

        return msg

    async def set_password(self, new_password: Optional[str]):
        """
        Sends a set password message or clears the password if None

        :param new_password: The new password string or None if clearing the password
        :type new_password: Optional[str]
        """
        if new_password is None:
            print("Clearing password...")
            payload = self._check_append_pass_check([])
            msg_packet = self._build_request_msg(SwitchBotReqType.CLEAR_PASSWORD, payload)
            await self._send_request(msg_packet, SwitchBotReqType.CLEAR_PASSWORD)
            self._info.password_str = None
            return

        new_pass_checksum = zlib.crc32(new_password.encode())
        new_pass_checksum_bytes = new_pass_checksum.to_bytes(4, byteorder="big")

        payload = self._check_append_pass_check([])
        if len(payload) > 0:
            print(
                f"A password is already set, attempting a password update (Old Pass Check={f_bytes(self._info.password_checksum)}, Old Pass={self._info.password_str}, New Pass={new_password})"
            )

        payload += bytes([0x01, 0x04])  # Unknown reason
        payload += new_pass_checksum_bytes

        msg_packet = self._build_request_msg(SwitchBotReqType.SET_PASSWORD, payload)

        await self._send_request(msg_packet, SwitchBotReqType.SET_PASSWORD)

        print(f"Sent password update message ({f_bytes(msg_packet)})!")

        self._info.password_str = new_password

    async def set_bot_state(self, state: SwitchBotAction):
        """
        Sends a "set state" command

        Only can send PRESS, ON, or OFF

        :param state: The action to take (PRESS, ON, and OFF)
        :type state: SwitchBotAction
        """
        if state not in [
            SwitchBotAction.PRESS,
            SwitchBotAction.ON,
            SwitchBotAction.OFF,
        ]:
            print(
                f"Cannot send state {state.name} to SwitchBot. Only PRESS, ON, and OFF are supported right now."
            )
            return

        payload = [state.value]

        payload_bytes = self._check_append_pass_check(payload, preappend=True)

        msg_packet = self._build_request_msg(SwitchBotReqType.COMMAND, payload_bytes)

        await self._send_request(msg_packet, SwitchBotReqType.COMMAND)

        print(f"Sent {state.name} message ({f_bytes(msg_packet)})!")

    async def run_action_set(self, action_set: List[Tuple[float, SwitchBotAction]]):
        """
        Run a set of actions in order (no more than 8)

        :param action_set: The set of actions to run in order with delay (seconds) between them (first ignored)
        :type action_set: List[Tuple[float, SwitchBotAction]]
        """
        actions = action_set.copy()

        # First action does not add a delay to the packet
        payload = bytearray([actions[0][1].value])

        actions = actions[1:]

        if len(actions) > 8:
            print("Cannot send more than 9 actions in a single message")
            return
        
        if self._info.is_encrypted and len(actions) > 7:
            print("Cannot send more than 8 actions in a single message when using encryption")
            return

        for delay, action in actions:
            payload.append(delay)  # 1 second delay
            payload.append(action.value)

        payload_bytes = self._check_append_pass_check(payload, preappend=True)

        msg_packet = self._build_request_msg(SwitchBotReqType.COMMAND, payload_bytes)
        await self._send_request(msg_packet, SwitchBotReqType.COMMAND)

        print(
            f"Sent {len(action_set)} actions ({f_bytes(msg_packet)})"
        )

    async def set_basic_device_info(self, bot_mode : SwitchBotMode, is_inverse : bool):
        """
        Sends a set basic device info message
        """

        act_mode_byte = 0x00
        act_mode_byte |= bot_mode.value << 4 # 4 MSB bytes = bot_mode
        act_mode_byte |= (0x01 if is_inverse else 0x00) # 4 LSB bytes = is_inverse

        payload = self._check_append_pass_check([100, act_mode_byte], preappend=True)

        msg_packet = self._build_request_msg(SwitchBotReqType.SET_BASIC_INFO, payload)
        await self._send_request(msg_packet, SwitchBotReqType.SET_BASIC_INFO)

        print(f"Sent basic device info set message ({f_bytes(msg_packet)})")


    async def fetch_basic_device_info(self):
        """
        Update internal ``info`` object with basic info (after response is received)
        """
        payload = self._check_append_pass_check([])

        msg_packet = self._build_request_msg(SwitchBotReqType.GET_BASIC_INFO, payload)
        await self._send_request(msg_packet, SwitchBotReqType.GET_BASIC_INFO)

        print(f"Sent basic device info request ({f_bytes(msg_packet)})")

    def _build_set_dev_time_mgm_info_payload(
        self,
        subcommand: TimeManagementInfoSubCommand,
        payload: bytearray,
        alarm_id: Optional[int] = None,
    ) -> bytearray:
        """
        Create set time management information payload

        :param subcommand: The type of time management information command to build
        :type subcommand: TimeManagementInfoSubCommand
        :param payload: The data for the associated subcommand
        :type payload: bytearray
        :param alarm_id: The alarm ID to set information for (TimeManagementInfoSubCommand.ALARM_INFO)
        :type alarm_id: Optional[int]
        :return: Message payload
        :rtype: bytearray
        """
        subcmd_value = subcommand.value

        if subcommand == TimeManagementInfoSubCommand.DEVICE_TIME:
            if len(payload) != 0 and len(payload) != 8:
                print(
                    f"Cannot set device time with payload length {len(payload)}, must be equal to 8!"
                )
                raise UserWarning(
                    f"Cannot set device time with payload length {len(payload)}, must be equal to 8!"
                )
        elif subcommand == TimeManagementInfoSubCommand.ALARM_COUNT:
            if len(payload) != 0 and len(payload) != 1:
                print(
                    f"Cannot set alarm count with payload length {len(payload)}, must be equal to 1!"
                )
                raise UserWarning(
                    f"Cannot set alarm count with payload length {len(payload)}, must be equal to 1!"
                )
        elif subcommand == TimeManagementInfoSubCommand.ALARM_INFO:
            if len(payload) != 0 and len(payload) != 11:
                print(
                    f"Cannot set alarm info with payload length {len(payload)}, must be equal to 11!"
                )
                raise UserWarning(
                    f"Cannot set alarm info with payload length {len(payload)}, must be equal to 11!"
                )

            if alarm_id is None:
                print("Cannot set alarm info without an alarm ID!")
                raise UserWarning("Cannot set alarm info without an alarm ID!")

            if alarm_id < 0 or alarm_id > 4:
                print(f"Cannot set alarm info with alarm ID {alarm_id}, must be between 0 and 4!")
                raise UserWarning(
                    f"Cannot set alarm info with alarm ID {alarm_id}, must be between 0 and 4!"
                )
            # Set nth task/alarm
            subcmd_value = subcmd_value | (alarm_id << 4)

        payload = bytearray([subcmd_value]) + payload
        payload = self._check_append_pass_check(payload, preappend=True)
        return payload

    async def sync_time(self):
        """
        Sync unix timestamp between current device and SwitchBot
        """
        unix_seconds = int(time.time())
        seconds_bytes = unix_seconds.to_bytes(8, byteorder="big")

        payload = self._build_set_dev_time_mgm_info_payload(
            TimeManagementInfoSubCommand.DEVICE_TIME, seconds_bytes
        )

        msg_packet = self._build_request_msg(SwitchBotReqType.SET_TIME_MGMT_INFO, payload)
        await self._send_request(msg_packet, SwitchBotReqType.SET_TIME_MGMT_INFO)

        print(f"Sent sync timer request ({f_bytes(msg_packet)})")

    async def update_alarm_count(self, alarm_count: int):
        """
        Change the amount of alarms (0 <= n <= 4)

        :param alarm_count: The number of alarms to set
        :type alarm_count: int
        """
        if alarm_count < 0 or alarm_count > 4:
            print(f"Cannot set alarm count to {alarm_count}, must be between 0 and 4!")
            raise UserWarning(f"Cannot set alarm count to {alarm_count}, must be between 0 and 4!")

        payload = self._build_set_dev_time_mgm_info_payload(
            TimeManagementInfoSubCommand.ALARM_COUNT, bytearray([alarm_count])
        )

        msg_packet = self._build_request_msg(SwitchBotReqType.SET_TIME_MGMT_INFO, payload)
        await self._send_request(msg_packet, SwitchBotReqType.SET_TIME_MGMT_INFO)

        print(f"Sent set alarm count request ({f_bytes(msg_packet)})")

    async def update_alarm_info(self, alarm_id: int, alarm_info: AlarmInfo):
        """
        Update the information for an alarm (alarm count must be set)

        :param alarm_id: The ID of the alarm to update (0 <= id < # of alarms)
        :type alarm_id: int
        :param alarm_info: The new alarm info
        :type alarm_info: AlarmInfo
        """
        payload = [self.info.alarm_count, alarm_id]

        repeat_byte = 0x00
        if alarm_info.execute_repeatedly:
            repeat_byte |= 0x1 << 7  # Set first bit

        # Bits 6-0: Sun-Monday, 1 = Valid, 0 = Invalid
        for dow in alarm_info.valid_days:
            repeat_byte |= 0x1 << dow.value  # Set nth bit

        payload.append(repeat_byte)

        exec_hours = math.floor(alarm_info.execution_time.seconds / 60 / 60)
        exec_minutes = math.floor(alarm_info.execution_time.seconds / 60) - (exec_hours * 60)

        # These may be hex hour and minute (0x10 for 10 am and 0x23 for 23 minutes),
        # its unclear from the documentation
        payload.append(exec_hours)
        payload.append(exec_minutes)

        payload.append(alarm_info.exec_type.value)

        payload.append(alarm_info.num_continuous_actions)

        interval_hours = math.floor(alarm_info.interval.seconds / 60 / 60)
        interval_minutes = math.floor(alarm_info.interval.seconds / 60) - (interval_hours * 60)
        interval_seconds = (
            alarm_info.interval.seconds - (interval_minutes * 60) - (interval_hours * 60 * 60)
        )

        if interval_hours > 5:
            print(f"Cannot set alarm interval to {interval_hours} hours, must be less than 5!")
            raise UserWarning(
                f"Cannot set alarm interval to {interval_hours} hours, must be less than 5!"
            )

        if interval_seconds % 10 != 0:
            print(
                f"Cannot set alarm interval to {interval_seconds} seconds, must be a multiple of 10!"
            )
            print("Rounding down to the nearest multiple of 10")
            interval_seconds = math.floor(interval_seconds / 10) * 10

        payload.append(interval_hours)  # Append hours
        payload.append(interval_minutes)  # Append minutes
        payload.append(interval_seconds)  # Append minutes

        payload = self._build_set_dev_time_mgm_info_payload(
            TimeManagementInfoSubCommand.ALARM_INFO, bytearray(payload), alarm_id
        )

        msg_packet = self._build_request_msg(SwitchBotReqType.SET_TIME_MGMT_INFO, payload)
        await self._send_request(msg_packet, SwitchBotReqType.SET_TIME_MGMT_INFO)

        print(f"Sent update alarm info request for alarm ID {alarm_id} ({f_bytes(msg_packet)})")

    async def fetch_system_time(self):
        """
        Fetch current unix timestamp from SwitchBot
        """
        payload = self._build_set_dev_time_mgm_info_payload(
            TimeManagementInfoSubCommand.DEVICE_TIME, bytearray()
        )

        msg_packet = self._build_request_msg(SwitchBotReqType.GET_TIME_MGMT_INFO, payload)
        await self._send_request(msg_packet, SwitchBotReqType.GET_TIME_MGMT_INFO)

        print(f"Sent fetch system time request ({f_bytes(msg_packet)})")

    async def fetch_alarm_count(self):
        """
        Fetch the number of alarms set
        """
        payload = self._build_set_dev_time_mgm_info_payload(
            TimeManagementInfoSubCommand.ALARM_COUNT, bytearray()
        )

        msg_packet = self._build_request_msg(SwitchBotReqType.GET_TIME_MGMT_INFO, payload)
        await self._send_request(msg_packet, SwitchBotReqType.GET_TIME_MGMT_INFO)

        print(f"Sent fetch alarm count request ({f_bytes(msg_packet)})")

    async def fetch_alarm_info(self, alarm_id: int):
        """
        Fetch information for alarm information
        :param alarm_id: The ID of the alarm to fetch (0 <= id < # of alarms)
        :type alarm_id: int
        """
        payload = self._build_set_dev_time_mgm_info_payload(
            TimeManagementInfoSubCommand.ALARM_INFO, bytearray(), alarm_id=alarm_id
        )

        msg_packet = self._build_request_msg(SwitchBotReqType.GET_TIME_MGMT_INFO, payload)
        await self._send_request(msg_packet, SwitchBotReqType.GET_TIME_MGMT_INFO)

        print(f"Sent fetch alarm info request for Alarm {alarm_id} ({f_bytes(msg_packet)})")

    async def set_long_press_duration(self, duration_s: int):
        """
        Set the duration of a "long press" command

        :param duration_s: Duration in seconds
        :type duration_s: int
        """
        payload = self._build_request_msg(SwitchBotReqType.EXTENDED_COMMAND, bytearray(duration_s))

        msg_packet = self._build_request_msg(SwitchBotReqType.EXTENDED_COMMAND, payload)
        await self._send_request(msg_packet, SwitchBotReqType.EXTENDED_COMMAND)

        print(
            f"Sent set long press duration request for duration {duration_s} ({f_bytes(msg_packet)})"
        )

    @property
    def mac_address(self) -> str:
        """
        Connected SwitchBot's MAC address

        :return: MAC Address
        :rtype: str
        """
        return self._address

    @property
    def info(self) -> BotInformation:
        """
        Connected SwitchBot's Information

        :return: SwitchBot Information
        :rtype: BotInformation
        """
        return self._info

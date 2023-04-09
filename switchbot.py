from bleak import BleakClient, BleakScanner
from typing import Optional, List, Union
import asyncio
import enum
import zlib
import time
import math

from bot_types import SwitchBotReqType, SwitchBotCommand, SwitchBotRespStatus, SwitchBotAction, TimeManagementInfoSubCommand, f_bytes
from bot_information import BotInformation
from alarm_info import AlarmInfo

# Functionality to capture packets for
#   - Custom Mode
#   - Custom Mode with Encryption
#   - Messages between 0x01 and 0x0F

class VirtualSwitchBot():

    def __init__(self, mac_address : str, password_str : Optional[str] = None):

        self._address = mac_address
        self._client : Optional[BleakClient] = None

        self._info = BotInformation()

        # Used to know what request yielded which response
        self._request_response_queue : Optional[asyncio.Queue] = None

        if password_str is not None:
            self._info.password_str = password_str

    async def connect(self):

        self._request_response_queue = asyncio.Queue()

        device = await BleakScanner.find_device_by_address(self._address)
        if device is None:
            print(f"Device not found for MAC Address {self._address}")
            exit(1)

        print(f"Found SwitchBot: {device.name} ({device.address})")


        self._client = BleakClient(device, disconnected_callback=lambda _: asyncio.run_coroutine_threadsafe(self.disconnect_callback_handler(), asyncio.get_event_loop()))

        await self._client.connect()

        print(f"Connected to {self._address}")

        await self._client.start_notify(SwitchBotCommand.RESP_CHAR_UUID.value, self._notif_callback_handler)

        await self.update_basic_device_info()
        await asyncio.sleep(1)
        await self.fetch_alarm_count()
        await asyncio.sleep(1)
        await self.fetch_system_time()
        await asyncio.sleep(1)

    async def disconnect(self):
        if self._client is None:
            print("Client is not connected. Cannot disconnect.")
            return
        await self._client.disconnect()

    async def _notif_callback_handler(self, characteristic, data):

        request_type : SwitchBotReqType = await self._request_response_queue.get()

        status_enum = SwitchBotRespStatus(data[0])
        response_data = data[1:]
        print(f"Recieved response for {request_type.name} with status {status_enum.name} ({status_enum.value}): {f_bytes(response_data)}")

        if status_enum != SwitchBotRespStatus.OK:
            return
        
        if request_type == SwitchBotReqType.SET_PASSWORD:
            print(f"Successfully set password to {self._info.password_str}") # Current pass is new pass
            return
        
        if request_type == SwitchBotReqType.COMMAND:
            print(f"Successfully sent command to SwitchBot")
            if len(response_data) > 1:
                self._info.read_service_bytes(response_data)
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
                    self._info.system_timestamp = int.from_bytes(response_data, byteorder='big', signed=False)
                    print(f"Successfully recieved system time ({self._info.system_timestamp})")
                    
            if resp_len == 11:
                    print(f"Successfully recieved alarm info for index {response_data[1]}")
                    self._info.update_alarm(response_data)


    async def disconnect_callback_handler(self):
        print("Disconnecting from SwitchBot...")

        # Used for case when called externally
        if self._client is not None and self._client.is_connected:
            self._client.disconnect()


    async def _send_request(self, message_bytes : bytearray, request_type : SwitchBotReqType):
        if self._client is None:
            print("Client is not connected. Cannot send request.")
            return
        
        self._request_response_queue.put_nowait(request_type)
        await self._client.write_gatt_char(SwitchBotCommand.REQ_CHAR_UUID.value, message_bytes, response=True)

    def _check_append_pass_check(self, curr_payload : Union[bytearray, List[int]], preappend : bool = False) -> bytearray:
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
    def _build_request_msg(self, command_type : SwitchBotReqType, payload : bytearray, version : int = 0) -> bytearray:
        msg = bytearray([0x57])

        byte_1 = version << 6
        byte_1 |= (0x01 if self._info.is_encrypted else 0x00) << 4
        byte_1 |= command_type.value
        msg.append(byte_1)

        if command_type == SwitchBotReqType.SET_TIME_MGMT_INFO:
            msg.append(0x08) # Set long press duration

        msg += payload

        return msg


    async def set_password(self, new_password : Optional[str]):


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
            print(f"A password is already set, attempting a password update (Old Pass Check={f_bytes(self._info.password_checksum)}, Old Pass={self._info.password_str}, New Pass={new_password})")

        payload += bytes([0x01, 0x04]) # Unknown reason
        payload += new_pass_checksum_bytes

        msg_packet = self._build_request_msg(SwitchBotReqType.SET_PASSWORD, payload)

        await self._send_request(msg_packet, SwitchBotReqType.SET_PASSWORD)

        print(f"Sent password update message ({f_bytes(msg_packet)})!")

        self._info.password_str = new_password

    # Single state action
    async def set_bot_state(self, state : SwitchBotAction):

        if state not in [SwitchBotAction.PRESS, SwitchBotAction.ON, SwitchBotAction.OFF]:
            print(f"Cannot send state {state.name} to SwitchBot. Only PRESS, ON, and OFF are supported right now.")
            return
        
        payload = [state.value]
        if state == SwitchBotAction.PRESS:
            payload = []

        payload_bytes = self._check_append_pass_check(payload, preappend=True)

        msg_packet = self._build_request_msg(SwitchBotReqType.COMMAND, payload_bytes)

        await self._send_request(msg_packet, SwitchBotReqType.COMMAND)

        print(f"Sent {state.name} message ({f_bytes(msg_packet)})!")


    # NOTE: Not working. Once I have a better idea on how things have changed since the docs were written, I'll revisit this
    async def run_action_set(self, action_set : List[SwitchBotAction]):

        actions = action_set.copy()
        payload = bytearray([actions[0].value])

        actions = actions[1:]

        if len(actions) > 7:
            print("Cannot send more than 8 actions in a single message")
            return

        for action in actions:
            payload.append(1) # 1 second delay
            payload.append(action.value)

        payload_bytes = self._check_append_pass_check(payload)

        msg_packet = self._build_request_msg(SwitchBotReqType.COMMAND, payload_bytes)
        await self._send_request(msg_packet, SwitchBotReqType.COMMAND)

        print(f"Sent {len(action_set)} actions with a 1 second delay between them ({f_bytes(msg_packet)})")


    async def update_basic_device_info(self):
        
        payload = self._check_append_pass_check([])

        msg_packet = self._build_request_msg(SwitchBotReqType.GET_BASIC_INFO, payload)
        await self._send_request(msg_packet, SwitchBotReqType.GET_BASIC_INFO)

        print(f"Sent basic device info request ({f_bytes(msg_packet)})")


    def _build_set_dev_time_mgm_info_payload(self, subcommand : TimeManagementInfoSubCommand, payload : bytearray, alarm_id : Optional[int] = None) -> bytearray:

        subcmd_value = subcommand.value

        if subcommand == TimeManagementInfoSubCommand.DEVICE_TIME:
            if len(payload) != 0 and len(payload) != 8:
                print(f"Cannot set device time with payload length {len(payload)}, must be equal to 8!")
                raise UserWarning(f"Cannot set device time with payload length {len(payload)}, must be equal to 8!")
        elif subcommand == TimeManagementInfoSubCommand.ALARM_COUNT:
            if len(payload) != 0 and  len(payload) != 1:
                print(f"Cannot set alarm count with payload length {len(payload)}, must be equal to 1!")
                raise UserWarning(f"Cannot set alarm count with payload length {len(payload)}, must be equal to 1!")
        elif subcommand == TimeManagementInfoSubCommand.ALARM_INFO:
            if len(payload) != 0 and len(payload) != 11:
                print(f"Cannot set alarm info with payload length {len(payload)}, must be equal to 11!")
                raise UserWarning(f"Cannot set alarm info with payload length {len(payload)}, must be equal to 11!")
            
            if alarm_id is None:
                print("Cannot set alarm info without an alarm ID!")
                raise UserWarning("Cannot set alarm info without an alarm ID!")
            
            if alarm_id < 0 or alarm_id > 4:
                print(f"Cannot set alarm info with alarm ID {alarm_id}, must be between 0 and 4!")
                raise UserWarning(f"Cannot set alarm info with alarm ID {alarm_id}, must be between 0 and 4!")
            # Set nth task/alarm
            subcmd_value = subcmd_value | (alarm_id << 4)

        payload = bytearray([subcmd_value]) + payload
        payload = self._check_append_pass_check(payload, preappend=True)
        return payload

    async def sync_time(self):

        unix_seconds = int(time.time())
        seconds_bytes = unix_seconds.to_bytes(8, byteorder="big")

        payload = self._build_set_dev_time_mgm_info_payload(TimeManagementInfoSubCommand.DEVICE_TIME, seconds_bytes)

        msg_packet = self._build_request_msg(SwitchBotReqType.SET_TIME_MGMT_INFO, payload)
        await self._send_request(msg_packet, SwitchBotReqType.SET_TIME_MGMT_INFO)

        print(f"Sent sync timer request ({f_bytes(msg_packet)})")

    async def update_alarm_count(self, alarm_count : int):
        if alarm_count < 0 or alarm_count > 4:
            print(f"Cannot set alarm count to {alarm_count}, must be between 0 and 4!")
            raise UserWarning(f"Cannot set alarm count to {alarm_count}, must be between 0 and 4!")
        
        payload = self._build_set_dev_time_mgm_info_payload(TimeManagementInfoSubCommand.ALARM_COUNT, bytearray([alarm_count]))

        msg_packet = self._build_request_msg(SwitchBotReqType.SET_TIME_MGMT_INFO, payload)
        await self._send_request(msg_packet, SwitchBotReqType.SET_TIME_MGMT_INFO)

        print(f"Sent set alarm count request ({f_bytes(msg_packet)})")

    async def update_alarm_info(self, alarm_id : int, alarm_info : AlarmInfo):
        payload = [self.info.alarm_count, alarm_id]

        repeat_byte = 0x00
        if alarm_info.execute_repeatedly:
            repeat_byte |= (0x1 << 7) # Set first bit
        
        # Bits 6-0: Sun-Monday, 1 = Valid, 0 = Invalid
        for dow in alarm_info.valid_days:
            repeat_byte |= (0x1 << dow.value) # Set nth bit

        payload.append(repeat_byte)

        
        exec_hours = math.floor(alarm_info.execution_time.seconds / 60 / 60)
        exec_minutes = math.floor(alarm_info.execution_time.seconds / 60) - (exec_hours * 60)
        
        # These may be hex hour and minute (0x10 for 10 am and 0x23 for 23 minutes), its unclear from the documentation
        payload.append(exec_hours)
        payload.append(exec_minutes)

        payload.append(alarm_info.exec_type.value)

        payload.append(alarm_info.num_continuous_actions)


        
        interval_hours = math.floor(alarm_info.interval.seconds / 60 / 60)
        interval_minutes = math.floor(alarm_info.interval.seconds / 60) - (interval_hours * 60)
        interval_seconds = alarm_info.interval.seconds - (interval_minutes * 60) - (interval_hours * 60 * 60)

        if interval_hours > 5:
            print(f"Cannot set alarm interval to {interval_hours} hours, must be less than 5!")
            raise UserWarning(f"Cannot set alarm interval to {interval_hours} hours, must be less than 5!")

        if interval_seconds % 10 != 0:
            print(f"Cannot set alarm interval to {interval_seconds} seconds, must be a multiple of 10!")
            print("Rounding down to the nearest multiple of 10")
            interval_seconds = math.floor(interval_seconds / 10) * 10

        

        payload.append(interval_hours) # Append hours
        payload.append(interval_minutes) # Append minutes
        payload.append(interval_seconds) # Append minutes

        payload = self._build_set_dev_time_mgm_info_payload(TimeManagementInfoSubCommand.ALARM_INFO, bytearray(payload), alarm_id)

        msg_packet = self._build_request_msg(SwitchBotReqType.SET_TIME_MGMT_INFO, payload)
        await self._send_request(msg_packet, SwitchBotReqType.SET_TIME_MGMT_INFO)

        print(f"Sent update alarm info request for alarm ID {alarm_id} ({f_bytes(msg_packet)})")

    
    async def fetch_system_time(self):

        payload = self._build_set_dev_time_mgm_info_payload(TimeManagementInfoSubCommand.DEVICE_TIME, bytearray())

        msg_packet = self._build_request_msg(SwitchBotReqType.GET_TIME_MGMT_INFO, payload)
        await self._send_request(msg_packet, SwitchBotReqType.GET_TIME_MGMT_INFO)

        print(f"Sent fetch system time request ({f_bytes(msg_packet)})")

    async def fetch_alarm_count(self):

        payload = self._build_set_dev_time_mgm_info_payload(TimeManagementInfoSubCommand.ALARM_COUNT, bytearray())
        
        msg_packet = self._build_request_msg(SwitchBotReqType.GET_TIME_MGMT_INFO, payload)
        await self._send_request(msg_packet, SwitchBotReqType.GET_TIME_MGMT_INFO)

        print(f"Sent fetch alarm count request ({f_bytes(msg_packet)})")

    async def fetch_alarm_info(self, alarm_id : int):

        payload = self._build_set_dev_time_mgm_info_payload(TimeManagementInfoSubCommand.ALARM_INFO, bytearray(), alarm_id=alarm_id)
        
        msg_packet = self._build_request_msg(SwitchBotReqType.GET_TIME_MGMT_INFO, payload)
        await self._send_request(msg_packet, SwitchBotReqType.GET_TIME_MGMT_INFO)

        print(f"Sent fetch alarm info request for Alarm {alarm_id} ({f_bytes(msg_packet)})")

        
    async def set_long_press_duration(self, duration_s : int):
        payload = self._build_request_msg(SwitchBotReqType.EXTENDED_COMMAND, bytearray(duration_s))

        msg_packet = self._build_request_msg(SwitchBotReqType.EXTENDED_COMMAND, payload)
        await self._send_request(msg_packet, SwitchBotReqType.EXTENDED_COMMAND)

        print(f"Sent set long press duration request for duration {duration_s} ({f_bytes(msg_packet)})")



    @property
    def info(self) -> BotInformation:
        return self._info



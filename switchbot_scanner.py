from bleak import BleakScanner, BLEDevice, AdvertisementData
from typing import List, Dict, Tuple, AsyncIterator, Optional
from bot_types import SwitchBotCommand, f_bytes
from switchbot import VirtualSwitchBot
import asyncio
from collections import deque

class SwitchBotScanner:

    UNKNOWN_SERVICE_DATA_UUID = "00000d00-0000-1000-8000-00805f9b34fb"
    NORDIC_MANUFACTUER_ID = 0x59
    NORDIC_COMPANY_ID = 0x59

    @classmethod
    async def scan(cls, bot_count : int) -> AsyncIterator[VirtualSwitchBot]:

        def _filter_device_adv(device : BLEDevice, adv : AdvertisementData) -> Tuple[bool, Optional[bytes]]:
            man_data = adv.manufacturer_data.get(cls.NORDIC_COMPANY_ID)
            if man_data is None:
                return False, None

            service_data = adv.service_data.get(cls.UNKNOWN_SERVICE_DATA_UUID)
            if service_data is None:
                return False, None

            mac_addr = device.address
            # I am not sure if this is only for SwitchBot or is a general pattern
            mac_bytes = bytearray(int(x, base=16) for x in mac_addr.split(":"))
            if mac_bytes != man_data:
                return False, None

            print(f"Found SwitchBot: {device.name} ({mac_addr})")
            print(f"  - RSSI: {adv.rssi}")

            return True, service_data


        async with BleakScanner() as scanner:

            bots_found = 0

            while True:
                await asyncio.sleep(1.0)
                data = scanner.discovered_devices_and_advertisement_data
                for _, (device, advertisement) in data.items():
                    is_switchbot, service_data = _filter_device_adv(device, advertisement)
                    if is_switchbot:
                        bots_found += 1
                        switch_bot = VirtualSwitchBot(device.address, device=device)
                        switch_bot.info.read_service_bytes(service_data)
                        yield switch_bot
                    if bots_found >= bot_count:
                        print(f"Found {bots_found} SwitchBots, stopping scanner...")
                        return
from bleak import BleakScanner, BLEDevice, AdvertisementData
from typing import List, Dict, Tuple
from bot_types import SwitchBotCommand, f_bytes
from switchbot import VirtualSwitchBot

class SwitchBotScanner:

    UNKNOWN_SERVICE_DATA_UUID = "00000d00-0000-1000-8000-00805f9b34fb"
    NORDIC_MANUFACTUER_ID = 0x59
    NORDIC_COMPANY_ID = 0x59

    @classmethod
    async def scan(cls, timeout : float = 5) -> List[VirtualSwitchBot]:
        scanner = BleakScanner(service_uuids=[SwitchBotCommand.COMM_SERVICE_UUID.value])
        device_info :  Dict[str, Tuple[BLEDevice, AdvertisementData]] = await scanner.discover(timeout, return_adv=True)

        found_switchbots : List[VirtualSwitchBot] = []

        for mac, (device, adv) in device_info.items():

            man_data = adv.manufacturer_data.get(cls.NORDIC_COMPANY_ID)
            if man_data is None:
                continue
            
            service_data = adv.service_data.get(cls.UNKNOWN_SERVICE_DATA_UUID)
            if service_data is None:
                continue

            # I am not sure if this is only for SwitchBot or is a general pattern
            mac_bytes = bytearray(int(x, base=16) for x in mac.split(":"))
            if mac_bytes != man_data:
                continue

            print(f"Found SwitchBot: {device.name} ({device.address})")
            print(f"  - RSSI: {adv.rssi}")
            
            switch_bot = VirtualSwitchBot(mac)
            switch_bot.info.read_service_bytes(service_data)

            found_switchbots.append(switch_bot)

        print(f"Found {len(found_switchbots)} SwitchBots.")
        return found_switchbots

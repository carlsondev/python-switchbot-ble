'''
Python-Switchbot-BLE: A Python library for interfacing with Switchbot devices over Bluetooth Low Energy (BLE)
Copyright (C) 2023  Benjamin Carlson
'''


from bleak import BleakScanner, BLEDevice, AdvertisementData
from typing import Tuple, Optional, List
import asyncio

from .switchbot import VirtualSwitchBot


class SwitchBotScanner:
    # Service UUID
    UNKNOWN_SERVICE_DATA_UUID = "00000d00-0000-1000-8000-00805f9b34fb"
    # Manufacturer ID for Nordic Semiconductors
    NORDIC_MANUFACTURER_ID = 0x59


    def __init__(self, bot_count : int = 1) -> None:
        self._bot_count = bot_count
        self._found_mac_addrs : List[str] = []

    def _filter_device_adv(
        self, device: BLEDevice, adv: AdvertisementData
    ) -> Tuple[bool, Optional[bytearray]]:
        """
        Determines if device is a SwitchBot or not

        :param device: Device object
        :type device: BLEDevice
        :param adv: Device advertisement data
        :type adv: AdvertisementData
        :return: Whether the device is a SwitchBot and if so, the associated service data
        :rtype: Tuple[bool, Optional[bytes]]
        """
        man_data = adv.manufacturer_data.get(self.NORDIC_MANUFACTURER_ID)
        if man_data is None:
            return False, None

        service_data = adv.service_data.get(self.UNKNOWN_SERVICE_DATA_UUID)
        if service_data is None:
            return False, None

        mac_addr = device.address
        # I am not sure if this is only for SwitchBot or is a general pattern
        mac_bytes = bytearray(int(x, base=16) for x in mac_addr.split(":"))
        if mac_bytes != man_data:
            return False, None

        print(f"Found SwitchBot: {device.name} ({mac_addr})")
        print(f"  - RSSI: {adv.rssi}")

        return True, bytearray(service_data)
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        """
        Scans for ``bot_count`` SwitchBots before exiting

        :return: The VirtualSwitchBot found
        :rtype: AsyncIterator[VirtualSwitchBot]
        """
        async with BleakScanner() as scanner:

            bots_found = 0

            while True:

                if bots_found >= self._bot_count:
                    print(f"Found {bots_found} SwitchBots, stopping scanner...")
                    raise StopAsyncIteration

                await asyncio.sleep(1.0)
                data = scanner.discovered_devices_and_advertisement_data
                for _, (dis_device, dis_advertisement) in data.items():

                    bot_address = dis_device.address
                    # Ignore if we already found this device
                    if bot_address in self._found_mac_addrs:
                        continue

                    is_switchbot, dev_service_data = self._filter_device_adv(
                        dis_device, dis_advertisement
                    )

                    if is_switchbot:
                        
                        self._found_mac_addrs.append(bot_address)

                        bots_found += 1
                        switch_bot = VirtualSwitchBot(bot_address)
                        switch_bot.info.read_service_bytes(dev_service_data)

                        return switch_bot
                    
    # Alias for easy use
    next_bot = __anext__
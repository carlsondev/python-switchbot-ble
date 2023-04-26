from bleak import BleakScanner, BLEDevice, AdvertisementData
from typing import Tuple, AsyncIterator, Optional
import asyncio

from .switchbot import VirtualSwitchBot


class SwitchBotScanner:
    # Service UUID
    UNKNOWN_SERVICE_DATA_UUID = "00000d00-0000-1000-8000-00805f9b34fb"
    # Manufacturer ID for Nordic Semiconductors
    NORDIC_MANUFACTURER_ID = 0x59

    @classmethod
    def _filter_device_adv(
        cls, device: BLEDevice, adv: AdvertisementData
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
        man_data = adv.manufacturer_data.get(cls.NORDIC_MANUFACTURER_ID)
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

        return True, bytearray(service_data)

    @classmethod
    async def scan(cls, bot_count: int) -> AsyncIterator[VirtualSwitchBot]:
        """
        Scans for ``bot_count`` SwitchBots before exiting

        :param bot_count: The amount of SwitchBots to discover before exiting
        :type bot_count: int
        :return: The VirtualSwitchBot found
        :rtype: AsyncIterator[VirtualSwitchBot]
        """
        async with BleakScanner() as scanner:

            bots_found = 0

            while True:
                await asyncio.sleep(1.0)
                data = scanner.discovered_devices_and_advertisement_data
                for _, (dis_device, dis_advertisement) in data.items():
                    is_switchbot, dev_service_data = cls._filter_device_adv(
                        dis_device, dis_advertisement
                    )

                    if is_switchbot:
                        bots_found += 1
                        switch_bot = VirtualSwitchBot(dis_device.address, device=dis_device)
                        switch_bot.info.read_service_bytes(dev_service_data)
                        yield switch_bot

                    if bots_found >= bot_count:
                        print(f"Found {bots_found} SwitchBots, stopping scanner...")
                        return

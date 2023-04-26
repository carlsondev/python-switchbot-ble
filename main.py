import asyncio
from typing import Optional

from switchbot_api import VirtualSwitchBot
from switchbot_api import SwitchBotScanner
from switchbot_api.bot_types import SwitchBotAction


class SwitchBotMITM:
    def __init__(self) -> None:
        self._virt_switchbot: Optional[VirtualSwitchBot] = None

    async def start(self):
        try:

            async for switchbot in SwitchBotScanner.scan(1):
                print(f"Found SwitchBot: {switchbot.mac_address}")
                self._virt_switchbot = switchbot
                self._virt_switchbot.info.password_str = "1235"
                break

            await asyncio.sleep(5)
            print("Connecting...")
            await self._virt_switchbot.connect()
            await self._virt_switchbot.set_bot_state(SwitchBotAction.ON)
            await asyncio.sleep(5)
            await self._virt_switchbot.set_bot_state(SwitchBotAction.OFF)
            await asyncio.sleep(5)
            await self._virt_switchbot.set_password(None)
            await asyncio.sleep(5)
            await self._virt_switchbot.fetch_alarm_info(alarm_id=0)
            await asyncio.sleep(5)
            await self._virt_switchbot.set_password("1235")
            await asyncio.sleep(5)
            await self._virt_switchbot.disconnect()

        except KeyboardInterrupt:
            if self._virt_switchbot is not None:
                await self._virt_switchbot.disconnect_callback_handler()
            print("Exiting...")


if __name__ == "__main__":
    bot = SwitchBotMITM()
    asyncio.run(bot.start())

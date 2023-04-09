import asyncio
from typing import Optional

from switchbot import VirtualSwitchBot
from switchbot_scanner import SwitchBotScanner
from bot_types import SwitchBotAction

class SwitchBotMITM():


    def __init__(self) -> None:
        self._virt_switchbot : Optional[VirtualSwitchBot] = None


    async def start(self):
        try:

            found_switchbots = await SwitchBotScanner.scan(3)

            if len(found_switchbots) == 0:
                print("No SwitchBots found.")
                return
            
            self._virt_switchbot = found_switchbots[0]
            self._virt_switchbot.info.password_str = "1235"

            await self._virt_switchbot.connect()
            await self._virt_switchbot.set_bot_state(SwitchBotAction.ON)
            await asyncio.sleep(5)
            await self._virt_switchbot.set_bot_state(SwitchBotAction.OFF)
            await asyncio.sleep(5)
            await self._virt_switchbot.set_password(None)
            await asyncio.sleep(5)
            await self._virt_switchbot.fetch_alarm_info(0)
            await asyncio.sleep(5)
            # await self._virt_switchbot.set_password("1235")
            # await asyncio.sleep(5)
            await self._virt_switchbot.disconnect()


        except KeyboardInterrupt:
            if self._virt_switchbot is not None:
                self._virt_switchbot.disconnect_callback_handler(None)
            print("Exiting...")
if __name__ == "__main__":
    bot = SwitchBotMITM()
    asyncio.run(bot.start())
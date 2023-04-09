import asyncio


from switchbot import VirtualSwitchBot
from bot_types import SwitchBotAction

ben_switchbot_mac = "F6:9A:4E:9C:3F:3B"

class SwitchBotMITM():


    def __init__(self, address : str) -> None:
        self._switchbot_mac = address
        self._virt_switchbot = VirtualSwitchBot(address, "1235")


    async def start(self):
        try:
            await self._virt_switchbot.connect()
            await self._virt_switchbot.set_bot_state(SwitchBotAction.ON)
            await asyncio.sleep(5)
            await self._virt_switchbot.set_bot_state(SwitchBotAction.OFF)
            await asyncio.sleep(5)
            # await self._virt_switchbot.set_password("1235")
            # await asyncio.sleep(5)
            await self._virt_switchbot.set_password(None)
            await asyncio.sleep(5)
            await self._virt_switchbot.disconnect()


        except KeyboardInterrupt:
            self._virt_switchbot.disconnect_callback_handler(None)
            print("Exiting...")
if __name__ == "__main__":
    bot = SwitchBotMITM(ben_switchbot_mac)
    asyncio.run(bot.start())
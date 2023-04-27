import asyncio

from switchbot_api import SwitchBotScanner
from switchbot_api.bot_types import SwitchBotAction

async def start():

        # Apply the same ON/OFF pattern to two unique SwitchBots
        async for switchbot in SwitchBotScanner(bot_count=2):
            print("Connecting...")
            await switchbot.connect()
            await asyncio.sleep(5)

            # Set the SwitchBot to ON
            await switchbot.set_bot_state(SwitchBotAction.ON)
            await asyncio.sleep(5)

            # Set the SwitchBot to OFF
            await switchbot.set_bot_state(SwitchBotAction.OFF)
            await asyncio.sleep(5)

            # Disconnect from the switchbot
            await switchbot.disconnect()
            

if __name__ == "__main__":
    asyncio.run(start())

import asyncio
from typing import Optional

from switchbot_api import VirtualSwitchBot
from switchbot_api import SwitchBotScanner
from switchbot_api.bot_types import SwitchBotAction


async def start():
    virtual_bot: Optional[VirtualSwitchBot] = None

    # Get the first SwitchBot found
    async for switchbot in SwitchBotScanner(bot_count=1):
        print(f"Found SwitchBot: {switchbot.mac_address}")
        virtual_bot = switchbot
        break

    print("Connecting...")
    await virtual_bot.connect()

    # Set the SwitchBot to ON
    await virtual_bot.set_bot_state(SwitchBotAction.ON)

    # Sleep is necsessary to allow the SwitchBot to physcially change state
    await asyncio.sleep(5)

    # Set the SwitchBot to OFF
    await virtual_bot.set_bot_state(SwitchBotAction.OFF)
    await asyncio.sleep(5)

    # Disconnect from the switchbot
    await virtual_bot.disconnect()

if __name__ == "__main__":
    asyncio.run(start())

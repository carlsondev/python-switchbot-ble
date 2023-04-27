import asyncio

from switchbot_api import SwitchBotScanner
from switchbot_api.bot_types import SwitchBotAction


async def start():
    
    # An alternative way of getting the first SwitchBot found
    virtual_bot = await SwitchBotScanner(bot_count=1).next_bot()
    print(f"Found SwitchBot: {virtual_bot.mac_address}")

    # Set the current password for the switchbot
    virtual_bot.info.password_str = "1234"

    print("Connecting...")
    await virtual_bot.connect()

    # Set the SwitchBot to ON
    await virtual_bot.set_bot_state(SwitchBotAction.ON)
    await asyncio.sleep(5)

    # Update the password for the switchbot
    await virtual_bot.set_password("4321")

    # Set the SwitchBot to OFF
    await virtual_bot.set_bot_state(SwitchBotAction.OFF)
    await asyncio.sleep(5)

    # Remove the password for the switchbot
    await virtual_bot.set_password(None)

    # Disconnect from the switchbot
    await virtual_bot.disconnect()

if __name__ == "__main__":
    asyncio.run(start())
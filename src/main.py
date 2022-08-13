import asyncio

from clan_battle_data import update_clanbattledata
from client import bot
from send_clanbattle_videos import notify_videos
from setup_channel import setup_channel

loop = asyncio.get_event_loop()
task3 = loop.create_task(update_clanbattledata())
task2 = loop.create_task(notify_videos())
task1 = loop.create_task(bot._ready())

gathered = asyncio.gather(task1, task2, task3, loop=loop)
loop.run_until_complete(gathered)

import asyncio
from datetime import datetime
from typing import List, Tuple

from setting import BASE_URL, JST
from util import get_from_web_api


class ClanBattleData:
    boss_names: List[str] = []
    hp: List[List[int]] = []
    boudaries: List[Tuple[int]] = []
    icon: List[str] = []
    start_time: datetime = datetime.now()
    end_time: datetime = datetime.now()
    next_start: datetime = datetime.now()

    @staticmethod
    def get_hp(lap: int, boss_index: int) -> int:
        for i, (lap_from, lap_to) in enumerate(ClanBattleData.boudaries):
            if lap_from <= lap <= lap_to or (lap_from <= lap and lap_to == -1):
                return ClanBattleData.hp[i][boss_index]
        return ClanBattleData.hp[-1][boss_index]


async def get_clan_battle_data() -> None:
    clan_battle_abstract = await get_from_web_api(BASE_URL + "clanbattles/latest")
    hp_list = []
    boundaries = []
    icons = []
    for i, map in enumerate(clan_battle_abstract["maps"]):
        hp_list_in_level = []
        for id in map["boss_ids"]:
            await asyncio.sleep(0.5)
            boss_data = await get_from_web_api(BASE_URL + f"enemies/{id}")
            hp_list_in_level.append(int(boss_data["parameter"]["hp"] // 10000))
            if i == 0:
                icons.append(boss_data["unit"]["icon"])
        hp_list.append(hp_list_in_level)
        boundaries.append((map["lap_from"], map["lap_to"]))
    ClanBattleData.boss_names = clan_battle_abstract["maps"][0]["boss_names"]
    ClanBattleData.hp = hp_list
    ClanBattleData.boudaries = boundaries
    ClanBattleData.icon = icons
    ClanBattleData.start_time = datetime.strptime(clan_battle_abstract["start_time"], "%Y/%m/%d %H:%M:%S").astimezone(
        JST
    )
    ClanBattleData.end_time = datetime.strptime(clan_battle_abstract["end_time"], "%Y/%m/%d %H:%M:%S").astimezone(JST)
    ClanBattleData.next_start = datetime.strptime(clan_battle_abstract["interval_end"], "%Y/%m/%d %H:%M:%S").astimezone(
        JST
    )


async def update_clanbattledata():
    while True:
        if datetime.now(JST).strftime("%H:%M") == "12:00" or not ClanBattleData.boss_names:
            await get_clan_battle_data()
        await asyncio.sleep(60)

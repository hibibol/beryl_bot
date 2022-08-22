import asyncio

import interactions

from clan_battle_data import ClanBattleData
from client import bot
from seach_videos import search_videos
from sql_util import (delete_channel_data, get_all_channel_data,
                      get_old_video_data, register_video_data)


def check_contain_words(words: list, txt: str):
    """
    words にある単語がtxtに含まれているかどうかをチェックする
    """
    for word in words:
        if word in txt:
            return True
    return False


def get_level(title: str, description: str):
    """
    動画のタイトルもしくは説明から段階数を取ってくる
    """
    keywords_list = [
        ["5段", "５段", "五段", "5週", "５週", "五週"],
        ["4段", "４段", "四段", "4週", "４週", "四週"],
        ["3段", "３段", "三段", "3週", "３週", "三週"],
        ["2段", "２段", "二段", "2週", "２週", "二週"],
        ["1段", "１段", "一段", "1週", "１週", "一週"],
    ]
    for text in (title, description):
        for i, keywords in enumerate(keywords_list):
            if check_contain_words(keywords, text):
                return str(5 - i)
    return ""


def create_embed(item, level: str):
    """埋め込みメッセージを作成する
    引数:
        search_resouce: youtube data api の検索結果のitem
        level: 段階数
    返り値:
        動画を知らせる用の埋め込みメッセージ
    """
    DEFAULT_YOUTUBE_URL = "https://www.youtube.com/watch?v="
    # 動画の説明がめちゃめちゃ長い場合には切り取って表示する
    description = item["snippet"]["description"]
    if len(description) > 550:
        description = description[:500] + "..."

    COLOR_DICT = {"1": 0xEC784D, "2": 0xB8B8DC, "3": 0xFDFBAE, "4": 0xBE81F4, "5": 0x641B20}

    if len(level) == 0:
        embed_color = 0xEB8D7E
    else:
        embed_color = COLOR_DICT[level]

    embed = interactions.Embed(
        title=item["snippet"]["title"],
        description=description,
        url=f"{DEFAULT_YOUTUBE_URL}{item['id']['videoId']}",
        color=embed_color,
        author=interactions.EmbedAuthor(name=item["snippet"]["channelTitle"]),
        image=interactions.EmbedImageStruct(url=item["snippet"]["thumbnails"]["high"]["url"]),
    )
    return embed


async def send_embed_messages(boss_index: int, embed: interactions.Embed):
    for _, category_id, channel_ids in get_all_channel_data():
        try:
            channel = await interactions.get(bot, interactions.Channel, object_id=channel_ids[boss_index])
            await channel.send(embeds=embed)
        except Exception as e:
            print(e, flash=True)
            print(f"delete channel, category_id = {category_id}", flash=True)
            delete_channel_data(category_id)
        await asyncio.sleep(1)


class SearchBossIndex:
    index = 0


async def notify_videos():
    while True:
        await asyncio.sleep(30 * 60)

        boss_names = ClanBattleData.boss_names
        next_boss_index = (SearchBossIndex.index + 1) % 5
        target_bosses = [
            (SearchBossIndex.index, boss_names[SearchBossIndex.index]),
            (next_boss_index, boss_names[next_boss_index]),
        ]
        q = f"{target_bosses[0][1]} OR {target_bosses[1][1]}"

        items = search_videos(q)

        for item in items:
            for boss_index, boss_name in target_bosses:
                if boss_name not in item["snippet"]["title"]:
                    continue
                videoid = item["id"]["videoId"]
                old_video_ids = get_old_video_data(boss_name)
                if videoid in old_video_ids:
                    continue
                level = get_level(item["snippet"]["title"], item["snippet"]["description"])
                embed = create_embed(item, level)
                await send_embed_messages(boss_index, embed)
                register_video_data((boss_name, videoid))

        SearchBossIndex.index = (SearchBossIndex.index + 2) % 5

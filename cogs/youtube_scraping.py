from discord.ext import tasks,commands 
from discord import Forbidden,HTTPException
import json
from bs4 import BeautifulSoup
from urllib import request
from urllib import parse
# import aiohttp
from asyncio import sleep

from copy import copy


class  Youtube_Scraping(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.old_href_dict = {}
        self.default_url = "https://www.youtube.com"
        self.youtube_scraping.start()


    #htmlを取ってきて，動画のhref linkのリストを取り出す
    async def fetch_href_list(self,url):
        # async with aiohttp.ClientSession() as client:
        #     async with client.get(url) as resp:
        #         assert resp.status == 200
        #         html = resp.text
        html = request.urlopen(url)
        # soup = BeautifulSoup(html, "html.parser")
        soup = BeautifulSoup(html, "html.parser")
        movie_list = soup.find_all("a",class_="yt-uix-tile-link yt-ui-ellipsis yt-ui-ellipsis-2 yt-uix-sessionlink spf-link")
        return [movie["href"] for movie in movie_list]

    @tasks.loop(minutes=5)
    async def youtube_scraping(self):

        with open("jsons/search_words.json","r") as f:
            word_list = json.load(f)["WORDS"]
        with open("jsons/channels.json","r") as f:
            channel_dict = json.load(f)
        tmp_channel_dict = copy(channel_dict)
        for i,word in enumerate(word_list):
            search_url = f"https://www.youtube.com/results?search_query={parse.quote(word)}&sp=CAI%253D"
            href_list = await self.fetch_href_list(search_url)
            if not word in self.old_href_dict:
                self.old_href_dict[word] = href_list
            else:
                for href in href_list:
                    if not href in self.old_href_dict[word]:
                        self.old_href_dict[word].append(href)
                        print(word,href)
                        for channel_id in channel_dict[str(i+1)]:
                            channel = self.bot.get_channel(channel_id)
                            if channel:
                                try:
                                    await channel.send(self.default_url+href)
                                    print("success at ",channel.guild.name)
                                except Forbidden:
                                    tmp_channel_dict[str(i+1)].remove(channel_id)
                                    print("delete channel at ",channel.guild.name)
                                except:
                                    print("raise error",flush=True)
                            else:
                                tmp_channel_dict[str(i+1)].remove(channel_id)
                                print("delete channel id:",channel_id,flush=True)

            with open("jsons/channels.json","w") as f:
                json.dump(tmp_channel_dict,f,ensure_ascii=False, indent=4)
            await sleep(1)


# Bot本体側からコグを読み込む際に呼び出される関数。
def setup(bot):
    bot.add_cog(Youtube_Scraping(bot)) # TestCogにBotを渡してインスタンス化し、Botにコグとして登録する。

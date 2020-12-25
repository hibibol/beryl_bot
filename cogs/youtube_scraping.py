import datetime

import discord
from discord.ext import tasks, commands
from discord import Forbidden, Embed
import json
import aiohttp
from asyncio import sleep

from copy import copy

import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import apiclient


default_youtube_url = "https://www.youtube.com/watch?v="
FILTER_SETTING_FILE = "jsons/level.json"
CONFIG_FILE = "jsons/config.json"

class Youtube_Scraping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("jsons/old_dict.json", "r") as f:
            self.old_id_dict = json.load(f)
        # self.old_id_dict = {}
        self.ss_service, self.drive_service = self.init_drive()
        self.youtube = self.init_youtube()
        self.search_boss_number = 0
        self.start_time = datetime.datetime.now().isoformat() + "Z"

        self.notify_movies.start()

    def init_drive(self):
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            SCOPES = ['https://www.googleapis.com/auth/drive']
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    './jsons/credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        return build('sheets', 'v4', credentials=creds), build('drive', 'v3', credentials=creds)
    
    def init_youtube(self):
        with open(CONFIG_FILE) as f:
            api_key = json.load(f)["GOOGLE"]
        
        return apiclient.discovery.build('youtube', 'v3', developerKey=api_key)

    # todo 非同期にする
    def search_movies(self, q: str):
        """
        YouTube Data APIを用いて動画をupload dateの順で検索した結果を返す
        引数
            q:検索word
        返り値
            items (検索リソース)
        """
        search_response = self.youtube.search().list(
            part="snippet",
            q=q,
            order="date",
            type="video",
            publishedAfter=self.start_time
        ).execute()
        return search_response["items"]
    
    async def get_battle_info(self, youtube_url):
        """Prilogを使って編成とダメージ，TLを取ってくる
        返り値 total_damage, chars, tl
        """
        with open("jsons/config.json") as f:
            PRILOG_TOKEN = json.load(f)["PRILOG_TOKEN"]

        api_url = f"https://prilog.jp/rest/analyze?Url={youtube_url}&Token={PRILOG_TOKEN}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as r:
                try:
                    data = await r.json()
                except Exception:
                    return "", [], ""

        # 正常な場合
        if data["status"] == 200 or data["status"] == 301:
            if data["result"]['total_damage']:
                total_damage = data["result"]['total_damage']
            else:
                total_damage = ""

            if data["result"]["timeline"]:
                tl = data["result"]["timeline_txt"]
                chars = list(set([ub.split()[1] for ub in data["result"]["timeline"]]))
            else:
                tl = ""
                chars = []
            
            return total_damage, chars, tl

        else:
            return "", [], ""

    def make_embed_message(self, search_resouce, total_damage: str = "", chars: list = [], level: str = ""):
        """埋め込みメッセージを作成する
        引数
            search_resouce: youtube data api の検索結果のitem
            status; Prirog api のresponseのstatus
            total_damage: 合計ダメージ
            chars: 編成キャラのリスト
            level: 段階数
        返り値
            動画を知らせる用の埋め込みメッセージ
        """

        color_dict = {
            "1": discord.Colour.from_rgb(236, 120, 77),
            "2": discord.Colour.from_rgb(184, 184, 220),
            "3": discord.Colour.from_rgb(253, 251, 174),
            "4": discord.Colour.from_rgb(190, 129, 244),
            "5": discord.Colour.from_rgb(100, 27, 32)
        }

        if len(level) == 0:
            embed_color = 0xeb8d7e
        else:
            embed_color = color_dict[level]

        # 動画の説明がめちゃめちゃ長い場合には切り取って表示する
        description = search_resouce["snippet"]["description"]
        if len(description) > 250:
            description = description[:200] + "..."

        embed = Embed(
            title=search_resouce["snippet"]["title"],
            description=description,
            url=f"{default_youtube_url}{search_resouce['id']['videoId']}",
            color=embed_color
        )
        embed.set_author(name=search_resouce["snippet"]["channelTitle"])
        embed.set_thumbnail(url=search_resouce["snippet"]["thumbnails"]["default"]["url"])
        if len(level) > 0:
            embed.add_field(name="段階数", value=level)
        if len(total_damage) > 0:
            embed.add_field(name="合計ダメージ", value=total_damage)
        if len(chars) > 1:
            embed.add_field(name="編成", value="\n".join(chars))

        return embed

    def append_value_gss(self, boss: str, level: str, total_damage: str, chars: list, title: str, youtube_url: str, tl: str):
        """引数のデータをスプレッドシートに登録する
        引数:
            boss シート名を参照するときに必要なボスの場所 (ex. ボス1, ボス2 ...)
            ...
            省略
        """
        sheet_name = boss

        tmp_chars = copy(chars)
        while len(tmp_chars) < 5:
            tmp_chars.append("")
        
        append_object = [level, total_damage] + tmp_chars + [title, youtube_url, tl]
        value_range_body = {"values": [append_object]}
        with open(CONFIG_FILE) as f:
            spreadsheetId = json.load(f)["spreadsheetId"]

        self.ss_service.spreadsheets().values().append(
            spreadsheetId=spreadsheetId,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            body=value_range_body
        ).execute()

        with open("jsons/sheet_properties.json") as f:
            sheetId = json.load(f)[sheet_name]

        # 行のサイズを整えて，段階数でsortする
        batch_update_spreadsheet_request_body = {
            "requests": [
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheetId,
                            "dimension": "ROWS",
                            "startIndex": 1
                        },
                        "fields": "pixelSize",
                        "properties": {
                            "pixelSize": 40
                        }
                    }
                },
                {
                    "sortRange": {
                        "range": {
                            "sheetId": sheetId,
                            "startRowIndex": 1
                        },
                        "sortSpecs": [
                            {
                                "sortOrder": "DESCENDING",
                                "dimensionIndex": 0
                            }
                        ]
                    }
                }
            ]
        }
        self.ss_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheetId,
            body=batch_update_spreadsheet_request_body
        ).execute()

    def check_contain_words(self, words: list, txt: str):
        """
        words にある単語がtxtに含まれているかどうかをチェックする
        """
        for word in words:
            if word in txt:
                return True
        return False

    def get_level(self, title: str, description: str):
        """
        動画のタイトルもしくは説明から段階数を取ってくる
        """
        keywords_list = [
            ["5段", "５段", "五段", "5週", "５週", "五週"],
            ["4段", "４段", "四段", "4週", "４週", "四週"],
            ["3段", "３段", "三段", "3週", "３週", "三週"],
            ["2段", "２段", "二段", "2週", "２週", "二週"],
            ["1段", "１段", "一段", "1週", "１週", "一週"]
        ]
        for text in (title, description):
            for i, keywords in enumerate(keywords_list):
                if self.check_contain_words(keywords, text):
                    return str(5-i)
        return ""

    @commands.command()
    @commands.is_owner()
    async def test_search(self, ctx, q: str):
        """
        テスト用コマンド

        youtubeから検索して出てきた動画をdiscordに送信し，spreadsheetの更新を行う
        """

        search_resouces = self.search_movies(q)
        for search_resouce in search_resouces:
            youtube_url = f"{default_youtube_url}{search_resouce['id']['videoId']}"

            total_damage, chars, tl = await self.get_battle_info(youtube_url)
            level = self.get_level(search_resouce["snippet"]["title"], search_resouce["snippet"]["description"])
            self.append_value_gss("ボス5", level, total_damage, chars, search_resouce["snippet"]["title"], youtube_url, tl)
            embed = self.make_embed_message(search_resouce, total_damage, chars, level)
            try:
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(e)
                print(embed)

    # TODO非同期にする
    @commands.command()
    @commands.is_owner()
    async def create_gss(self, ctx, month):
        """凸動画収集用のシートを新規作成する．"""
        await ctx.send("新規スプレッドシートの作成を開始します")

        try:
            spreadsheet_body = {
                "properties": {
                    "title": f"{month} クラバト凸動画収集シート"
                }
            }
            new_ss = self.ss_service.spreadsheets().create(body=spreadsheet_body).execute()

            # 作ったシートを公開用のフォルダに移動する
            spreadsheetId = new_ss["spreadsheetId"]
            folderId = "1spCbnI2hnpPSUKwqpEzAJ2jkfc5WEc0p"
            file = self.drive_service.files().get(fileId=spreadsheetId, fields='parents').execute()
            previous_parents = ",".join(file.get('parents'))
            self.drive_service.files().update(
                fileId=spreadsheetId,
                addParents=folderId,
                removeParents=previous_parents
            ).execute()

            template_spreadsheetId = "1s-yj2E7cJc1YX8H7y889m8xbYe1ddviai5aMNFdCyL0"
            template_sheetId = 1661547396

            sheet_list = ["ボス1", "ボス2", "ボス3", "ボス4", "ボス5"]
            sheet_properties = {}
            for sheet_name in sheet_list:

                copy_sheet_to_another_spreadsheet_request_body = {
                    'destination_spreadsheet_id': spreadsheetId
                }
                newsheet = self.ss_service.spreadsheets().sheets().copyTo(
                    spreadsheetId=template_spreadsheetId,
                    sheetId=template_sheetId,
                    body=copy_sheet_to_another_spreadsheet_request_body
                ).execute()
                batch_update_spreadsheet_request_body = {
                    "requests": [{
                        "updateSheetProperties": {
                            "properties": {
                                "sheetId": newsheet["sheetId"],
                                "title": sheet_name
                            },
                            "fields": "title"
                        }}
                    ]
                }
                sheet_properties[sheet_name] = newsheet["sheetId"]
                self.ss_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheetId,
                    body=batch_update_spreadsheet_request_body
                ).execute()
            
            # 作成するときに出来たデフォルトのシートを削除する
            default_sheetId = [sheet["properties"]["sheetId"] for sheet in new_ss["sheets"] if sheet["properties"]["title"] == "Sheet1"][0]
            batch_update_spreadsheet_request_body = {
                "requests": [{
                    "deleteSheet": {
                        "sheetId": default_sheetId
                    }
                }
                ]
            }
            self.ss_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheetId,
                body=batch_update_spreadsheet_request_body
            ).execute()

            # spreadsheetId をconfigに登録する
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            config["spreadsheetId"] = spreadsheetId
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            with open("jsons/sheet_properties.json", "w") as f:
                json.dump(sheet_properties, f, ensure_ascii=False, indent=4)
            await ctx.send(f"スプレッドシートの作成が完了しました\n{new_ss['spreadsheetUrl']}")
        
        except Exception as e:
            await ctx.send(f"```\n{e}\n```")
    
    async def set_level(self, channel: discord.TextChannel, level_number: int) -> None:
        """
        フィルタ設定を保存する
        """
        with open(FILTER_SETTING_FILE, "r") as f:
            setting_dict = json.load(f)
        
        setting_dict[str(channel.guild.id)] = level_number
        
        with open(FILTER_SETTING_FILE, "w") as f:
            json.dump(setting_dict, f, ensure_ascii=False, indent=4)
        
        return await channel.send(f"{level_number}段階目以上の動画を送信します")
            
    @commands.command(aliases=["スプシ", "スプレッドシート", "gss", "ss"])
    async def show_gss(self, ctx):
        """現在使用しているスプレッドシートを表示する"""

        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        await ctx.send(f"https://docs.google.com/spreadsheets/d/{config['spreadsheetId']}")

    @commands.command()
    async def archives(self, ctx):
        """過去のクラバト動画のスプシを保存しているフォルダを表示"""
        await ctx.send("https://drive.google.com/drive/folders/1spCbnI2hnpPSUKwqpEzAJ2jkfc5WEc0p?usp=sharing")

    @commands.command(name="level")
    async def _level(self, ctx, level_number: int):
        """ベリルちゃんがdiscordに投稿する動画の段階数フィルタを設定する
        設定はサーバー単位で反映
        設定した段階数以上と段階数が不明な動画のみを投稿する

        引数
        -------------
        level_number: 制限する段階数
        """
        await self.set_level(ctx.channel, level_number)

    @commands.command()
    @commands.is_owner()
    async def reset_level(self, ctx):
        """段階数フィルタを初期化する
        """
        pass
    
    @commands.Cog.listener('on_message')
    async def _level_on_message(self, message: discord.Message):
        """段階数フィルター設定 Botからの入力を受け付ける用"""
        if message.author.bot:
            arg_list = message.content.split()
            if len(arg_list) != 2:
                return
            if arg_list[0] == "b.level" and arg_list[1].isdecimal():
                await self.set_level(message.channel, int(arg_list[1]))

    @tasks.loop(minutes=15)
    async def notify_movies(self):
        """
        定期的にyoutubeを検索して新しく出てきた動画を設定した動画に送信する
        """
        if not self.bot.is_ready():
            print("bot is not ready", flush=True)
            return 

        print("start search", flush=True)
        with open("jsons/search_words.json", "r") as f:
            search_dict = json.load(f)
        query_list = search_dict["WORDS"]
        name_list = search_dict["NAMES"]

        with open("jsons/channels.json", "r") as f:
            channel_dict = json.load(f)
        invalid_channel_dict = {"1": [], "2": [], "3": [], "4": [], "5": []}

        q = f"{query_list[self.search_boss_number]} OR {query_list[(self.search_boss_number+1)%5]}"
        tmp_boss_name_list = [name_list[(self.search_boss_number)], name_list[(self.search_boss_number + 1) % 5]]

        for i, boss_name in enumerate(tmp_boss_name_list):
            if boss_name not in self.old_id_dict.keys():
                self.old_id_dict[boss_name] = []
        
        print(datetime.datetime.now(), q, flush=True)

        items = self.search_movies(q)

        await sleep(5*60)  # プリログの安定化のために5分待ってからプリログに投げる

        for search_resouce in items:
            for i, boss_name in enumerate(tmp_boss_name_list):
                if boss_name in search_resouce["snippet"]["title"]:
                    
                    if search_resouce['id']["videoId"] in self.old_id_dict[boss_name]:
                        continue
                    
                    self.old_id_dict[boss_name].append(search_resouce['id']["videoId"])
                    
                    for remove_word in search_dict[f"REMOVE{str(i+1)}"]:
                        if remove_word in search_resouce["snippet"]["title"]:
                            continue
                    
                    boss_number = (self.search_boss_number + i) % 5 + 1
                    sheet_name = f"ボス{str(boss_number)}"
                    channel_dict_key = str(boss_number)

                    youtube_url = f"{default_youtube_url}{search_resouce['id']['videoId']}"
                    total_damage, chars, tl = await self.get_battle_info(youtube_url)
                    level = self.get_level(search_resouce["snippet"]["title"], search_resouce["snippet"]["description"])
                    try:
                        self.append_value_gss(sheet_name, level, total_damage, chars, search_resouce["snippet"]["title"], youtube_url, tl)
                    except Exception as e:
                        print(e, flush=True)
                        print(sheet_name, level, total_damage, chars, search_resouce["snippet"]["title"], youtube_url, tl, flush=True)
                    embed = self.make_embed_message(search_resouce, total_damage, chars, level)

                    with open(FILTER_SETTING_FILE, "r") as f:
                        filter_setting = json.load(f)

                    for channel_id in channel_dict[channel_dict_key]:
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            flag = False
                            if len(level) > 0:
                                if str(channel.guild.id) not in filter_setting.keys() or int(level) >= filter_setting[str(channel.guild.id)]:
                                    flag = True
                            else:
                                flag = True
                            if flag:
                                try:
                                    await channel.send(embed=embed)
                                    print("sent to ", channel.guild.name, flush=True)
                                    await sleep(0.4)
                                except Forbidden:
                                    invalid_channel_dict[channel_dict_key].append(channel_id)
                                    print("channel deleted: ", channel.guild.name, flush=True)
                                except Exception as e:
                                    print("raise error: ", e, flush=True)
                        else:
                            invalid_channel_dict[channel_dict_key].append(channel_id)
                            print("Invalid Id :", channel_id, flush=True)
        
        self.search_boss_number = (self.search_boss_number + 2) % 5

        #  channes.jsonからinvalid_channelを削除
        with open("jsons/channels.json", "r") as f:
            tmp_channel_dict = json.load(f)

        for key in tmp_channel_dict.keys():
            for channel_id in invalid_channel_dict[key]:
                if channel_id in tmp_channel_dict[key]:
                    tmp_channel_dict[key].remove(channel_id)
        
        with open("jsons/channels.json", "w") as f:
            json.dump(tmp_channel_dict, f, ensure_ascii=False, indent=4)

        with open("jsons/old_dict.json", "w") as f:
            json.dump(self.old_id_dict, f, ensure_ascii=False, indent=4)

        print("end search", flush=True)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(
                error,
                (
                    commands.MissingRequiredArgument,
                    commands.BadArgument,
                    commands.ArgumentParsingError,
                    commands.TooManyArguments
                )
        ):
            await ctx.send_help(ctx.command)
        else:
            print(error, flush=True)


# Bot本体側からコグを読み込む際に呼び出される関数。
def setup(bot):
    bot.add_cog(Youtube_Scraping(bot))

from discord.ext import tasks,commands 
from discord import Forbidden,HTTPException, Embed
import json
# from bs4 import BeautifulSoup
from urllib import request
from urllib import parse
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

class  Youtube_Scraping(commands.Cog):
    def __init__(self,bot):
        self.bot = bot
        self.old_href_dict = {}
        self.default_url = "https://www.youtube.com"
        # self.youtube_scraping.start()
        self.ss_service, self.drive_service = self.init_drive()
        self.youtube = self.init_youtube()


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
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    './jsons/credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        return  build('sheets', 'v4', credentials=creds), build('drive', 'v3', credentials=creds)
    
    def init_youtube(self):
        with open("jsons/config.json") as f:
            api_key = json.load(f)["GOOGLE"]
        
        return apiclient.discovery.build('youtube', 'v3', developerKey=api_key)

    #todo 非同期にする
    def search_movies(self, q):
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
            type="video"
        ).execute()
        return search_response["items"]
    
    async def get_battle_info(self, youtube_url):
        """Prilogを使って編成とダメージ，TLを取ってくる
        返り値 total_damage, chars, tl
        """
        api_url = f"https://prilog.jp/rest/analyze?Url={youtube_url}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as r:
                try:
                    data = await r.json()
                except:
                    return  "", [], ""

        #正常な場合
        if data["status"] == 0:
            if data["result"]['total_damage']:
                total_damage = data["result"]['total_damage'].split()[1]
            else:
                total_damage = ""

            if  data["result"]["timeline"]:
                tl =data["result"]["timeline_txt"]
                chars = list(set([ub.split()[1] for ub in  data["result"]["timeline"]]))
            else:
                tl = ""
                chars = []
            
            return total_damage, chars, tl

        else:
            return "", [], ""

    def make_embed_message(self, search_resouce, total_damage:str = "", chars:list = [], level:str = ""):
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

        # 動画の説明がめちゃめちゃ長い場合には切り取って表示する
        description = search_resouce["snippet"]["description"]
        if len(description) > 250:
            description = description[:200] + "..."

        embed = Embed(
            title=search_resouce["snippet"]["title"],
            description=description,
            url=f"{default_youtube_url}{search_resouce['id']['videoId']}",
            color=0xeb8d7e
            )
        embed.set_author(name=search_resouce["snippet"]["channelTitle"])
        embed.set_thumbnail(url=search_resouce["snippet"]["thumbnails"]["default"]["url"])
        if len(level) > 0:
            embed.add_field(name="段階数",value=level)
        if len(total_damage) > 0:
            embed.add_field(name="合計ダメージ", value=total_damage)
        if len(chars) > 1:
            embed.add_field(name="編成", value="\n".join(chars))

        # if len(level) == 0 and len(total_damage) ==  0 and len(chars) == 0:
            # embed.add_field(name="解析ミス", value="適切に解析を行うことが出来ませんでした")

        return embed

    def append_value_gss(self, boss: str, level:str, total_damage:str,  chars:list, title:str, youtube_url:str, tl:str):
        """引数のデータをスプレッドシートに登録する
        引数:
            boss シート名を参照するときに必要なボスの場所 (ex. ボス1, ボス2 ...)
            ...
            省略
        """

        analysis_success = len(level)>0 and len(total_damage) > 0 and len(chars) > 0

        sheet_name = boss
        if not analysis_success:
            sheet_name += "(解析ミス)"

        tmp_chars = copy(chars)
        while len(tmp_chars) < 5:
            tmp_chars.append("")
        
        append_object = [level, total_damage] + tmp_chars + [title, youtube_url, tl]
        value_range_body = {"values": [append_object]}
        with open("jsons/config.json") as f:
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
        batch_update_spreadsheet_request_body={
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
                    "pixelSize": 30
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
    

    def check_contain_words(self, words:list, txt:str):
        """
        words にある単語がtxtに含まれているかどうかをチェックする
        """
        for word in words:
            if word in txt:
                return True
        return False

    def get_level(self, title:str, description:str):
        """
        動画のタイトルもしくは説明から段階数を取ってくる
        """

        ex_words = ["EX","4段","４段","四段","4週","４週","四週"]
        vh_words = ["VH","3段","３段","三段","3週","３週","三週"]
        h_words = ["H","2段","２段","二段","2週","２週","二週"]
        n_words = ["N","1段","１段","一段","1週","１週","一週"]

        if self.check_contain_words(ex_words,title) or self.check_contain_words(ex_words,description):
            return "4"
        elif self.check_contain_words(vh_words,title) or self.check_contain_words(vh_words,description):
            return "3"
        elif self.check_contain_words(h_words,title) or self.check_contain_words(h_words,description):
            return "2"
        elif self.check_contain_words(n_words,title) or self.check_contain_words(n_words,description):
            return "1"

        return ""

    @commands.command()
    @commands.is_owner()
    async def test_search(self, ctx, q:str):
        """
        テスト用コマンド

        youtubeから検索して出てきた動画をdiscordに送信し，spreadsheetの更新を行う
        """

        search_resouces = self.search_movies(q)
        for search_resouce in search_resouces:
            youtube_url = f"{default_youtube_url}{search_resouce['id']['videoId']}"

            total_damage, chars, tl = await self.get_battle_info(youtube_url)
            level = self.get_level(search_resouce["snippet"]["title"],search_resouce["snippet"]["description"])
            self.append_value_gss("ボス5", level, total_damage, chars, search_resouce["snippet"]["title"], youtube_url, tl)
            embed = self.make_embed_message(search_resouce, total_damage, chars, level)
            try:
                await ctx.send(embed=embed)
            except:
                print(embed)


    # TODO非同期にする
    @commands.command()
    @commands.is_owner()
    async def create_gss(self,ctx,month):
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
            file = self.drive_service.files().get(fileId=spreadsheetId,fields='parents').execute()
            previous_parents = ",".join(file.get('parents'))
            self.drive_service.files().update(
                fileId=spreadsheetId,
                addParents=folderId,
                removeParents=previous_parents
            ).execute()

            template_spreadsheetId = "1s-yj2E7cJc1YX8H7y889m8xbYe1ddviai5aMNFdCyL0"
            template_sheetId = 1661547396

            sheet_list = ["ボス1","ボス2","ボス3","ボス4","ボス5","ボス1(解析ミス)","ボス2(解析ミス)","ボス3(解析ミス)","ボス4(解析ミス)","ボス5(解析ミス)"]
            sheet_properties={}
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
                    "requests":[{
                        "updateSheetProperties":{
                            "properties":{
                                "sheetId":newsheet["sheetId"],
                                "title": sheet_name
                            },
                            "fields":"title"
                        }}
                    ]
                }
                sheet_properties[sheet_name] = newsheet["sheetId"]
                self.ss_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheetId,
                    body=batch_update_spreadsheet_request_body
                ).execute()
            
            # 作成するときに出来たデフォルトのシートを削除する
            default_sheetId = [sheet["properties"]["sheetId"] for sheet in  new_ss["sheets"] if sheet["properties"]["title"] == "Sheet1" ][0]
            batch_update_spreadsheet_request_body = {
                "requests":[{
                    "deleteSheet": {
                    "sheetId":default_sheetId
                }
                }
                ]
            }
            self.ss_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheetId,
                body=batch_update_spreadsheet_request_body
            ).execute()

            # spreadsheetId をconfigに登録する
            with open("jsons/config.json","r") as f:
                config = json.load(f)
            config["spreadsheetId"] = spreadsheetId
            with open("jsons/config.json","w") as f:
                json.dump(config,f,ensure_ascii=False, indent=4)
            with open("jsons/sheet_properties.json","w") as f:
                json.dump(sheet_properties,f,ensure_ascii=False, indent=4)
            await ctx.send(f"スプレッドシートの作成が完了しました\n{new_ss['spreadsheetUrl']}")
        
        except Exception as e:
            await ctx.send(f"```\n{e}\n```")            
            
    @commands.command(aliases = ["スプシ","スプレッドシート","gss","ss"])
    async def show_gss(self, ctx):
        """現在使用しているスプレッドシートを表示する"""

        with open("jsons/config.json","r") as f:
            config = json.load(f)
        await ctx.send(f"https://docs.google.com/spreadsheets/d/{config['spreadsheetId']}")

    


    # @tasks.loop(minutes=5)
    # async def youtube_scraping(self):

    #     with open("jsons/search_words.json","r") as f:
    #         word_list = json.load(f)["WORDS"]
    #     with open("jsons/channels.json","r") as f:
    #         channel_dict = json.load(f)
    #     tmp_channel_dict = copy(channel_dict)
    #     for i,word in enumerate(word_list):
    #         search_url = f"https://www.youtube.com/results?search_query={parse.quote(word)}&sp=CAI%253D"
    #         href_list = await self.fetch_href_list(search_url)
    #         if not word in self.old_href_dict:
    #             self.old_href_dict[word] = href_list
    #         else:
    #             for href in href_list:
    #                 if not href in self.old_href_dict[word]:
    #                     self.old_href_dict[word].append(href)
    #                     print(word,href)
    #                     for channel_id in channel_dict[str(i+1)]:
    #                         channel = self.bot.get_channel(channel_id)
    #                         if channel:
    #                             try:
    #                                 await channel.send(self.default_url+href)
    #                                 print("success at ",channel.guild.name)
    #                             except Forbidden:
    #                                 tmp_channel_dict[str(i+1)].remove(channel_id)
    #                                 print("delete channel at ",channel.guild.name)
    #                             except:
    #                                 print("raise error",flush=True)
    #                         else:
    #                             tmp_channel_dict[str(i+1)].remove(channel_id)
    #                             print("delete channel id:",channel_id,flush=True)

    #         with open("jsons/channels.json","w") as f:
    #             json.dump(tmp_channel_dict,f,ensure_ascii=False, indent=4)
    #         await sleep(1)


# Bot本体側からコグを読み込む際に呼び出される関数。
def setup(bot):
    bot.add_cog(Youtube_Scraping(bot)) # TestCogにBotを渡してインスタンス化し、Botにコグとして登録する。

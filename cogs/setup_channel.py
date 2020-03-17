from discord.ext import commands # Bot Commands Frameworkのインポート
from discord import Forbidden
import json
from discord import Client

# コグとして用いるクラスを定義。
class SetupChannel(commands.Cog):

    # TestCogクラスのコンストラクタ。Botを受取り、インスタンス変数として保持。
    def __init__(self, bot):
        self.bot = bot

    # コマンドの作成。コマンドはcommandデコレータで必ず修飾する。
    @commands.command(aliases=["setup","SetupChannel"])
    async def setup_channel(self, ctx):
        guild = ctx.message.guild
        if guild:
            await ctx.send("セットアップを開始します")
            try:
                category = await guild.create_category_channel("凸動画")
                channel1 = await category.create_text_channel("ボス1")
                channel2 = await category.create_text_channel("ボス2")
                channel3 = await category.create_text_channel("ボス3")
                channel4 = await category.create_text_channel("ボス4")
                channel5 = await category.create_text_channel("ボス5")
            except Forbidden:
                return await ctx.send(f"権限がないためチャンネル作成が出来ませんでした．\nこのBotにチャンネル管理の権限を与えてください．")
            
            #jsonに作成したチャンネルを登録
            with open("jsons/channels.json","r") as f:
                channels = json.load(f)

            channels["1"].append(channel1.id)
            channels["2"].append(channel2.id)
            channels["3"].append(channel3.id)
            channels["4"].append(channel4.id)
            channels["5"].append(channel5.id)

            with open("jsons/channels.json","w") as f:
                json.dump(channels,f,ensure_ascii=False, indent=4)

            return await ctx.send(f"セットアップを完了しました\n今後は <#{channel1.id}><#{channel2.id}><#{channel3.id}><#{channel4.id}><#{channel5.id}> に動画を送信します")

    @commands.command()
    async def confirm_channel(self,ctx):
        channels = [
        670182036417282080,
        674876777381888020,
        674885549357662226,
        674886040317591552,
        674886414151843853,
        674913868870320138,
        674946200130158592,
        674948041492660233,
        675299749825478666,
        675349070587494400,
        676336133046796321,
        676970049545830401,
        677034315288150037,
        677162608926785546,
        677162831019245578,
        677760075691196426,
        678497293057392642,
        678513935317467147,
        680317485031096330,
        680320513188692032,
        680629587495223307,
        680667965473292288,
        680688375371399186,
        680710341726175257,
        680717589433155596,
        680768658275827775,
        680772709214715933,
        680773340549480468,
        680778206613471264,
        680969677958414391,
        680982292860239872,
        680989700689100865,
        680997148413657148,
        681045319034994908,
        681047608839372800,
        681198326032367631,
        681370598982549541,
        681812933432573952,
        681816681433006103,
        681829553534271511
        ]
        for channel_id in channels:
            try:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    print(channel_id, channel.guild.name)
                else:
                    print(channel_id,"チャンネルを取得できませんでした")
            except:
                print(channel_id,"エラーが発生しました")

            
            

                
 
# Bot本体側からコグを読み込む際に呼び出される関数。
def setup(bot):
    bot.add_cog(SetupChannel(bot)) # TestCogにBotを渡してインスタンス化し、Botにコグとして登録する。
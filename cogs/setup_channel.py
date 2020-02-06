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

            
            

                
 
# Bot本体側からコグを読み込む際に呼び出される関数。
def setup(bot):
    bot.add_cog(SetupChannel(bot)) # TestCogにBotを渡してインスタンス化し、Botにコグとして登録する。
import interactions
from client import bot
from sql_util import register_channel_data


@bot.command(name="setup", description="チャンネルのセットアップをします")
async def setup_channel(ctx: interactions.ComponentContext):
    guild = ctx.guild
    if not guild:
        return await ctx.send("サーバー内で実行してください")
    try:
        category = await guild.create_channel("クラバト動画", type=interactions.ChannelType.GUILD_CATEGORY)
        channels: list[interactions.Channel] = []
        for i in range(1, 6):
            channel = await guild.create_channel(
                f"ボス{i}",
                type=interactions.ChannelType.GUILD_TEXT,
                parent_id=category.id,
            )
            channels.append(channel)
    except interactions.error.LibraryException as e:
        return await ctx.send(f"チャンネルの作成に失敗しました\n{e.code}: {e.lookup(e.code)}")

    params = (
        int(ctx.guild_id),
        int(category.id),
        *[int(channel.id) for channel in channels],
    )
    register_channel_data(params)

    await ctx.send("チャンネルのセットアップが完了しました")

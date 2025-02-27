import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

bot = commands.Bot()
#debug_guilds=[879288794560471050]
load_dotenv()
TOKEN = os.getenv('TOKEN')
print(TOKEN)

path = "./cogs"


@bot.event
async def on_application_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.respond(error)
        await bot.get_partial_messageable(1009731664412426240).send(error)#traceback.format_exc())
    elif isinstance(error, commands.MissingPermissions):
        await ctx.respond(content="BOT管理者限定コマンドです", ephemeral=True)
    else:
        raise error

@bot.event
async def on_ready():
    print(f"Bot名:{bot.user} On ready!!")
    await bot.change_presence(activity=discord.Game(name=f"厳選 Impactをプレイ中 / {len(bot.guilds)}サーバーで稼働中",))

async def guildsCount():
    await bot.change_presence(activity=discord.Game(name=f"厳選 Impactをプレイ中 / {len(bot.guilds)}サーバーで稼働中",))

bot.load_extension('cogs.genshin', store=False)
bot.load_extension('cogs.wish', store=False)
bot.load_extension('cogs.genbot', store=False)
bot.load_extension('cogs.uidlist', store=False)

bot.run(TOKEN)

from http import server
import discord
from discord.ui import Select,View,Button
from discord.ext import commands,tasks
from discord import Option, SlashCommandGroup
import aiohttp
from lib.yamlutil import yaml
import lib.getStat as getStat
import lib.picture as getPicture
from typing import List

charactersYaml = yaml(path='characters.yaml')
characters = charactersYaml.load_yaml()
genshinJpYaml = yaml(path='genshinJp.yaml')
genshinJp = genshinJpYaml.load_yaml()
uidListYaml = yaml(path='uidList.yaml')
uidList = uidListYaml.load_yaml()
l: list[discord.SelectOption] = []

class TicTacToeButton(discord.ui.Button["TicTacToe"]):
    def __init__(self, label: str, uid: str, dict, data):
        super().__init__(style=discord.ButtonStyle.secondary, label=label)
        self.dict = dict
        self.uid = uid
        self.data = data

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TicTacToe = self.view

        await interaction.response.edit_message(content="```読み込み中...（10秒ほどかかります）```", embed=None, view=None)
        self.style = discord.ButtonStyle.success
        #ラベル（名前）からIDを割り出す
        #多分「名前：iD」ってなってるはず
        id = self.dict[self.label]
        print(f"\n実行者:{interaction.user.name}\n鯖名:{interaction.guild.name}\nget - キャラ詳細")
        for child in self.view.children:
            child.style = discord.ButtonStyle.gray
        #await interaction.response.edit_message(content=content, embed=await getStat.get(self.uid, id), view=TicTacToe(self.data,self.uid))
        embed = discord.Embed( 
                                title=f"{self.label}",
                                color=0x1e90ff, 
                                )
        embed.set_image(url=f"attachment://{str(self.dict[self.label])}.png") 
        getImage = await getStat.getCharacterImage(self.uid, id, interaction)
        if type(getImage) is discord.embeds.Embed:
            await interaction.edit_original_message(content=None, embed=getImage)
            return
        file = discord.File(getImage, filename=f"{str(self.dict[self.label])}.png")
        await interaction.edit_original_message(content=None, file=file, embed=embed, view=TicTacToe(self.data,self.uid))

class TicTacToe(discord.ui.View):
    children: List[TicTacToeButton]

    def __init__(self, data, uid):
        super().__init__(timeout=300, disable_on_timeout=True)
        names = []
        dict = {}
        #入ってきたidを名前にしてリスト化
        for id in data:
            id = str(id)
            name = genshinJp[characters[str(id)]["NameId"]]
            names.append(name)
            dict.update({name: id})
        #名前をラベル、ついでにdictとuidも送り付ける
        for v in names:
            self.add_item(TicTacToeButton(v,uid,dict,data))

#モーダルを表示させるボタン
class UidModalButton(discord.ui.Button):
    def __init__(self,ctx):
        super().__init__(label="UIDからステータスを検索",style=discord.ButtonStyle.green)
        self.ctx = ctx
 
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(UidModal(self.ctx))

#UIDを聞くモーダル
class UidModal(discord.ui.Modal):
    def __init__(self,ctx):
        super().__init__(title="UIDを入力してください。",timeout=300,)
        self.ctx = ctx
        
        self.uid = discord.ui.InputText(
            label="UID",
            style=discord.InputTextStyle.short,
            min_length=9,
            max_length=9,
            placeholder="000000000",
            required=True,
        )
        self.add_item(self.uid)

    async def callback(self, interaction: discord.Interaction) -> None:
        uid = self.uid.value
        ctx = self.ctx
        if uid == "000000000":
            await interaction.response.edit_message(f"エラー：UIDを入力してください。",view=None)
        try:
            #指定したUIDが非公開だった場合
            if uidList[ctx.guild.id][uid]["isPablic"] == "False":
                #かつ、コマンドの送信者がそのUIDの保有者じゃなかった場合
                if uidList[ctx.guild.id][uid]["user"] != ctx.author.name:
                    await interaction.response.edit_message(content="このUIDは表示できません。",view=None)
                    return
        except:
            #エラーということはそのUIDがないということなので適当にプリントしてパス
            print(ctx.author.name)

        await interaction.response.edit_message(content="アカウント情報読み込み中...",view=None)  
        url = f"https://enka.network/u/{uid}/__data.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                resp = await response.json()
                resalt = []
        embed = await GenshinCog.getApi(self,uid,resp)
        await interaction.edit_original_message(content="キャラ情報読み込み中...")  
        if resp == {}:
            await interaction.edit_original_message(content="エラー：入力されたものが存在するUIDではありません")

        await interaction.edit_original_message(content="画像を生成中...")  
        hoge = discord.File(await getPicture.getProfile(uid,resp), f"{uid}.png")
        try:
            for id in resp["playerInfo"]["showAvatarInfoList"]:
                resalt.append(id["avatarId"])
            await interaction.edit_original_message(content="ボタンを生成中...")  
            await interaction.edit_original_message(content=None,embed=embed,view=TicTacToe(resalt,uid), file=hoge)
        except:
            embed.add_field(name="エラー",value="キャラ情報を一切取得できませんでした。原神の設定を確認してください。")
            await interaction.edit_original_message(content=None,embed=embed,file=hoge)

#UIDを表示させるボタン
class UidButton(discord.ui.Button):
    def __init__(self,ctx,uid):
        super().__init__(label="登録されたUIDを使う",style=discord.ButtonStyle.green)
        self.ctx = ctx
        self.uid = uid

    async def callback(self, interaction: discord.Interaction):
        ctx = self.ctx
        uid = self.uid
        try:
            #指定したUIDが非公開だった場合
            if uidList[ctx.guild.id][uid]["isPablic"] == "False":
                #かつ、コマンドの送信者がそのUIDの保有者じゃなかった場合
                if uidList[ctx.guild.id][uid]["user"] != ctx.author.name:
                    await interaction.response.edit_message(content="このUIDは表示できません。", ephemeral=True )
                    return
        except:
            #エラーということはそのUIDがないということなので適当にプリントしてパス
            print(ctx.author.name)

        await interaction.response.edit_message(content="アカウント情報読み込み中...",view=None)  
        url = f"https://enka.network/u/{uid}/__data.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                resp = await response.json()
                resalt = []
        embed = await GenshinCog.getApi(self,uid,resp)
        await interaction.edit_original_message(content="キャラ情報読み込み中...") 
        if resp == {}:
            await interaction.edit_original_message(content="エラー：入力されたものが存在するUIDではありません")
        await interaction.edit_original_message(content="画像を生成中...")  
        hoge = discord.File(await getPicture.getProfile(uid,resp), f"{uid}.png")
        try:
            for id in resp["playerInfo"]["showAvatarInfoList"]:
                resalt.append(id["avatarId"])
            await interaction.edit_original_message(content="ボタンを生成中...")  
            await interaction.edit_original_message(content=None,embed=embed,view=TicTacToe(resalt,uid), file=hoge)
        except:
            embed.add_field(name="エラー",value="キャラ情報を一切取得できませんでした。原神の設定を確認してください。")
            await interaction.edit_original_message(content=None,embed=embed,file=hoge)

async def getProfile(ctx,uid,interaction):
    await interaction.response.edit_message(content="アカウント情報読み込み中...",view=None)  
    url = f"https://enka.network/u/{uid}/__data.json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            resp = await response.json()
            resalt = []
    embed = await GenshinCog.getApi(uid,resp)
    await interaction.edit_original_message(content="キャラ情報読み込み中...")  
    try: 
        for id in resp["playerInfo"]["showAvatarInfoList"]:
            resalt.append(id["avatarId"])
    except:
        print("genshinstat - 誰も見ることができない")
    await interaction.edit_original_message(content="画像を生成中...")  
    hoge = discord.File(await getPicture.getProfile(uid,resp), f"{uid}.png")
    await interaction.edit_original_message(content="ボタンを生成中...")  
    await interaction.edit_original_message(content=None,embed=embed,view=TicTacToe(resalt,uid), file=hoge)

class GenshinCog(commands.Cog):

    def __init__(self, bot):
        print('genshin初期化')
        self.bot = bot

    async def getApi(self,uid,resp):
        try:
            embed = discord.Embed( 
                                title=f"{resp['playerInfo']['nickname']}",
                                color=0x1e90ff, 
                                description=f"uid: {uid}", 
                                url=f"https://enka.network/u/{uid}/__data.json"
                                )
            embed.set_image(url=f"attachment://{uid}.png")                     
            return embed
        except:
            embed = discord.Embed( 
                    title=f"エラーが発生しました。APIを確認してからもう一度お試しください。\n{f'https://enka.network/u/{uid}/__data.json'}",
                    color=0x1e90ff, 
                    url=f"https://enka.network/u/{uid}/__data.json"
                    )
            return embed

    genshin = SlashCommandGroup('genshinstat', 'test')

    @genshin.command(name="get", description="【自分だけが確認できる】UIDからキャラ情報を取得します")
    async def genshin_get(
            self,
            ctx: discord.ApplicationContext,
    ):
        uidListYaml = yaml(path='uidList.yaml')
        uidList = uidListYaml.load_yaml()
        view = View(timeout=300, disable_on_timeout=True)
        uid = None
        print(f"\n実行者:{ctx.author.name}\n鯖名:{ctx.guild.name}\nget - キャラ情報取得")
        # もしuserに当てはまるUIDが無ければ終了
        try:
            for k,v in uidList[ctx.guild.id].items():
                if v["user"] == ctx.author.name:
                    uid = k
                    view.add_item(UidButton(ctx,uid))
                    view.add_item(UidModalButton(ctx))
                    await ctx.respond(content="UIDが登録されていますが、UIDを指定しますか？",view=view,ephemeral=True)
                    return
        except:
            uid = None
        if uid == None:
            view.add_item(UidModalButton(ctx))
            await ctx.respond(content="UIDが登録されていません。```/uidlist control```で登録すると、UIDをいちいち入力する必要がないので便利です。\n下のボタンから、登録せずに確認できます。",view=view,ephemeral=True)
            return

def setup(bot):
    bot.add_cog(GenshinCog(bot))
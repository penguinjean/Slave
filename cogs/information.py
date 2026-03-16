import discord
from discord.ext import commands

class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_data = {
            "welcome": {
                "name": "Slave",
                "greeting": "서버에 초대해 주셔서 감사합니다!\n",
                "summary": "즐거운 서버 활동을 돕기 위한 주요 명령어들을 안내해 드립니다.\n",
                },
        }

        self.credit_data = {
            "credit": {
                "bot_name": "Slave",
                "developer": "penguinjean0421",
                "illustrator": "aram",
                "supporter": "목대 겜소과 친목 디코",
            },
        }

    async def send_welcome_help(self, channel: discord.abc.Messageable, name: str, prefix: str = None):
        data = self.help_data.get(name) or self.help_data["welcome"]
        if prefix is None:
            prefix = self.bot.command_prefix
            if isinstance(prefix, list):
                prefix = prefix[0]

        embed = discord.Embed(
            title=f"👋 {data['name']} 입니다.",
            description=f"{data['greeting']}{data['summary']}",
            color=0x007acc
        )

        embed.add_field(name="🆔 접두사(Prefix)", value=f"`{prefix}`", inline=False)
        embed.add_field(
            name="📖 도움말 명령어",
            value=f"`{prefix}help` / `{prefix}help 관리자`",
            inline=True
        )
        embed.add_field(
            name="✨ 유틸리티", 
            value=(
                f"`{prefix}choose` : 제시된 후보군중 하나를 선택합니다.\n",
                f"`{prefix}menu` : 메뉴를 추천해줍니다.\n",
                f"`{prefix}kill` : 랜덤으로 마인크래프트 다잉 메세지를 출력합니다."
                ),
            inline=True
        )
        embed.add_field(
            name="🎮 게임 전적 조회",
            value=(
                f"`{prefix}lol 국가 닉네임#태그 : 리그오브레전드 전적을 조회 합니다.`\n",
                f"`{prefix}pubg 플랫폼 닉네임` : 배틀그라운드 전적을 조회합니다."
                ),
            inline=True
        )
        embed.add_field(
            name="⚙️ 서버 관리",
            value=f"상세 명령어는 `{prefix}help 관리자`를 참고하세요.",
            inline=False
        )

        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(
            text=f"상세 도움말은 {prefix}help를 입력하세요.",
            icon_url=self.bot.user.display_avatar.url
        )
        await channel.send(embed=embed)

    async def send_admin_help(self, ctx: commands.Context, prefix: str):
        embed = discord.Embed(
            title="🛠️ 서버 관리자 명령어 가이드",
            description="서버 관리 권한이 있는 멤버만 사용 가능한 명령어입니다.",
            color=0x5d2b90
        )
        embed.add_field(
            name="🔇 음성 제재",
            value=(
                f"`{prefix}mute [유저] (시간)` : 마이크 차단\n"
                f"`{prefix}unmute [유저]` : 마이크 해제\n"
                f"`{prefix}vckick [유저] (사유)` : 음성 채널 강제 퇴장"
            ),
            inline=False
        )
        embed.add_field(
            name="🔨 서버 제재",
            value=(
                f"`{prefix}timeout [유저] [시간] (사유)` : 타임아웃\n"
                f"`{prefix}kick [유저] (사유)` : 서버 추방\n"
                f"`{prefix}ban [유저] (사유)` : 서버 차단\n"
                f"`{prefix}unban [ID/닉네임]` : 차단 해제"
            ),
            inline=False
        )
        embed.add_field(
            name="⚙️ 시스템 설정",
            value=(
                f"`{prefix}set [log/punish/bot/ticket] [#채널]` : 채널 설정\n"
                f"`{prefix}reset [log/punish/bot/ticket]` : 설정 해제\n"
                f"`{prefix}reset all` : 모든 설정 초기화"
            ),
            inline=False
        )
        embed.add_field(
            name="🎫 티켓 시스템",
            value=(
                f"`{prefix}open` : 티켓 열기\n"
                f"`{prefix}close` : 티켓 닫기 버튼 전송\n"
                f"`{prefix}answer` : 답변을 임베드로 전송"
                ), 
                inline=False,
        )

        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(
            text="시간 단위: s(초), m(분), h(시간), d(일) | 예: 10m, 1d",
            icon_url=self.bot.user.display_avatar.url
        )
        await ctx.send(embed=embed)

    async def send_credit(self, ctx: commands.Context, name: str):
        data = self.credit_data[name]
        embed = discord.Embed(
            title=f"Thanks for using {data['bot_name']}",
            description=f"{data['bot_name']}를 함께 만들어주신 분들입니다.",
            color=0x5d2b90
        )
        embed.add_field(
            name="👤 Developer",
            value=f"[@{data['developer']}](https://github.com/{data['developer']})",
            inline=True
        )
        embed.add_field(name="🎨 Illustrator", value=f"@{data['illustrator']}", inline=True)
        embed.add_field(name="🤝 Supporter", value=data['supporter'], inline=False)
        embed.add_field(
            name="🔗 Source Code",
            value=f"[GitHub Repository](https://github.com/{data['developer']}/{data['bot_name']})",
            inline=False
        )
        embed.add_field(name="📧 Contact", value=f"`{data['developer']}@gmail.com`", inline=False)

        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"© 2026 {data['developer']} All rights reserved.")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        system_cog = self.bot.get_cog('System')
        channel = None
        if system_cog:
            channel = system_cog.get_log_channel(guild)
        if not channel:
            channel = guild.system_channel
        if channel and channel.permissions_for(guild.me).send_messages:
            await self.send_welcome_help(channel, "welcome")

    @commands.command(name="help", aliases=["도움말", "guide"])
    async def help_command(self, ctx: commands.Context, category: str = None):
        admin_keywords = ["관리자", "어드민", "admin", "management", "administrator"]
        if category and category.lower() in admin_keywords:
            return await self.send_admin_help(ctx, ctx.prefix)
        await self.send_welcome_help(ctx.channel, "welcome", ctx.prefix)

    @commands.command(name="credit", aliases=["크레딧"])
    async def credit(self, ctx: commands.Context):
        await self.send_credit(ctx, "credit")

async def setup(bot: commands.Bot):
    await bot.add_cog(Information(bot))
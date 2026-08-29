import json
import os
import discord
from discord import app_commands
from discord.ext import commands

class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        base_path = os.path.dirname(os.path.abspath(__file__))
        self.slave_file = os.path.join(base_path, "..", "data/slave_data.json")
        with open(self.slave_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.help_data = data['help']
            self.credit_data = data['credit']

    async def send_welcome_help(self, channel: discord.abc.Messageable):
        data = self.help_data

        embed = discord.Embed(
            title=f"👋 {data['name']} 입니다.",
            description=f"{data['greeting']}{data['summary']}",
            color=0x007acc
        )

        embed.add_field(name="🆔 명령어 방식", value="`슬래시(/) 명령어 기반`", inline=False)
        embed.add_field(
            name="📖 도움말 명령어",
            value="`/help`",
            inline=True
        )
        embed.add_field(
            name="✨ 유틸리티", 
            value=(
                "`/choose` : 제시된 후보군 중 하나를 선택합니다.\n"
                "`/menu` : 메뉴를 추천해줍니다.\n"
                "`/kill` : 랜덤으로 마인크래프트 다잉 메시지를 출력합니다."
            ),
            inline=True
        )
        embed.add_field(
            name="🎮 게임 전적 조회",
            value=(
                "`/lol` : 리그오브레전드 전적을 조회합니다.\n"
                "`/pubg` : 배틀그라운드 전적을 조회합니다."
            ),
            inline=True
        )
        embed.add_field(
            name="⚙️ 서버 관리",
            value="상세 명령어는 `/help 카테고리:관리자`를 참고하세요.",
            inline=False
        )

        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="상세 도움말은 /help를 입력하세요.", icon_url=self.bot.user.display_avatar.url)
        await channel.send(embed=embed)

    async def send_admin_help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛠️ 서버 관리자 명령어 가이드",
            description="서버 관리 권한이 있는 멤버만 사용 가능한 명령어입니다.",
            color=0x5d2b90
        )
        embed.add_field(
            name="🔇 음성 제재",
            value=(
                "`/mute [유저] (시간)` : 마이크 차단\n"
                "`/unmute [유저]` : 마이크 해제\n"
                "`/vckick [유저] (사유)` : 음성 채널 강제 퇴장"
            ),
            inline=False
        )
        embed.add_field(
            name="🔨 서버 제재",
            value=(
                "`/timeout [유저] [시간] (사유)` : 타임아웃\n"
                "`/kick [유저] (사유)` : 서버 추방\n"
                "`/ban [유저] (사유)` : 서버 차단\n"
                "`/unban [ID/닉네임]` : 차단 해제"
            ),
            inline=False
        )
        embed.add_field(
            name="⚙️ 시스템 설정",
            value=(
                "`/set log [server/punish/ticket] [#채널]` : 로그 채널 설정\n"
                "`/set command [bot/ticket] [#채널]` : 명령어 채널 설정\n"
                "`/reset log [server/punish/ticket]` : 로그 채널 초기화\n"
                "`/reset command [bot/ticket]` : 명령어 채널 초기화\n"
                "`/reset all` : 모든 설정 초기화"
            ),
            inline=False
        )
        embed.add_field(
            name="🎫 티켓 시스템",
            value=(
                "`/open` : 티켓 열기\n"
                "`/close` : 티켓 닫기 버튼 전송\n"
                "`/answer` : 답변을 임베드로 전송"
            ), 
            inline=False,
        )

        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="시간 단위: s(초), m(분), h(시간), d(일) | 예: 10m, 1d", icon_url=self.bot.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def send_credit(self, interaction: discord.Interaction):
        data = self.credit_data
        embed = discord.Embed(
            title=f"Thanks for using {data['bot_name']}",
            description=f"{data['bot_name']}를 함께 만들어주신 분들입니다.",
            color=0x5d2b90
        )
        embed.add_field(
            name="👤 Developer",
            value=f"[@{data['developer']}](https://github.com/{data['developer']})",
            inline=False
        )
        embed.add_field(name="🎨 Illustrator", value=f"@{data['illustrator']}", inline=False)
        embed.add_field(name="🤝 Supporter", value=data['supporter'], inline=False)
        embed.add_field(name="🔗 Source Code", value=f"[GitHub Repository](https://github.com/{data['repository']})", inline=False)
        embed.add_field(name="📧 Contact", value=f"`{data['contact']}`", inline=False)

        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"© 2026 {data['developer']} All rights reserved.")
        await interaction.response.send_message(embed=embed)

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

    @app_commands.command(name="help", description="봇의 사용법과 명령어 가이드를 확인합니다.")
    @app_commands.choices(category=[
        app_commands.Choice(name="일반 도움말", value="general"),
        app_commands.Choice(name="관리자 가이드", value="admin")
    ])
    @app_commands.describe(category="조회할 도움말의 카테고리를 선택하세요.")
    async def help_command(self, interaction: discord.Interaction, category: str = "general"):
        if category == "admin":
            return await self.send_admin_help(interaction)
        
        embed = discord.Embed(
            title=f"👋 {self.help_data['name']} 입니다.",
            description=f"{self.help_data['greeting']}{self.help_data['summary']}",
            color=0x007acc
        )
        embed.add_field(name="🆔 명령어 방식", value="`슬래시(/) 명령어 기반`", inline=False)
        embed.add_field(name="📖 도움말", value="`/help`", inline=True)
        embed.add_field(name="✨ 유틸리티", value="`/choose`, `/menu`, `/kill`", inline=True)
        embed.add_field(name="🎮 전적 조회", value="`/lol`, `/pubg`", inline=True)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="상세 도움말은 /help를 입력하세요.", icon_url=self.bot.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="credit", description="봇 개발에 도움을 주신 분들입니다.")
    async def credit(self, interaction: discord.Interaction):
        await self.send_credit(interaction)

async def setup(bot: commands.Bot):
    await bot.add_cog(Information(bot))
from datetime import datetime

import discord
from discord.ext import commands

class Logger(commands.Cog):
    def __init__(self, bot):
            self.bot = bot

    def get_log_channel(self, guild, type="general"):
        settings = self.bot.get_cog('Settings')
        if not settings: return guild.system_channel
        data = settings.get_server_data(guild)
        if type == "punish":
            chn_id = data.get("punish_log_channel_id") or data.get("log_channel_id")
        else:
            chn_id = data.get("log_channel_id")
            
        return self.bot.get_channel(chn_id) if chn_id else guild.system_channel

    async def send_log(self, guild, embed, type="general"):
        log_channel = self.get_log_channel(guild, type)
        if log_channel and log_channel.permissions_for(guild.me).send_messages:
            if not embed.timestamp: embed.timestamp = datetime.now()
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        embed = discord.Embed(
            title="📥 멤버 입장",
            description=f"{member.mention} **{member}** 님이 입장했습니다.",
            color=0x2ECC71
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"ID: {member.id} | 총 멤버: {member.guild.member_count}명")
        await self.send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        embed = discord.Embed(
            title="📤 멤버 퇴장",
            description=f"**{member}** 님이 서버를 떠났습니다.",
            color=0xE74C3C
        )
        embed.set_footer(text=f"ID: {member.id} | 남은 멤버: {member.guild.member_count}명")
        await self.send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content:
            return
        embed = discord.Embed(title="📝 메시지 수정됨", url=after.jump_url, color=0xF1C40F)
        embed.set_author(name=f"{before.author}", icon_url=before.author.display_avatar.url)
        embed.add_field(name="수정 전", value=f"```{before.content or '내용 없음'}```", inline=False)
        embed.add_field(name="수정 후", value=f"```{after.content or '내용 없음'}```", inline=False)
        await self.send_log(before.guild, embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        embed = discord.Embed(title="🗑️ 메시지 삭제됨", color=0xE74C3C)
        embed.description = (
            f"**작성자:** {message.author.mention}\n"
            f"**채널:** {message.channel.mention}\n"
            f"**내용:** ```{message.content or '내용 없음'}```"
        )
        await self.send_log(message.guild, embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel == after.channel:
            return
        user_info = f"{member.mention} **({member.id})**"
        
        if not before.channel:
            desc, color = f"🔊 {user_info} 님이 **{after.channel.name}** 입장", 0x2ECC71
        elif not after.channel:
            desc, color = f"🔇 {user_info} 님이 **{before.channel.name}** 퇴장", 0x95A5A6
        else:
            desc, color = f"🔄 {user_info}: **{before.channel.name}** ➡ **{after.channel.name}**", 0xF1C40F
            
        await self.send_log(member.guild, discord.Embed(description=desc, color=color))

async def setup(bot):
    await bot.add_cog(Logger(bot))
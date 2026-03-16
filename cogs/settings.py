import json
import os

import discord
from discord.ext import commands

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(base_path, "..", "config.json")
        self.server_configs = {}
        self.load_config()

    def load_config(self):
        """설정 파일(JSON)을 로드합니다."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.server_configs = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.server_configs = {}
        else:
            self.server_configs = {}

    def save_config(self):
        """현재 설정을 파일에 저장합니다."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.server_configs, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"파일 저장 중 오류 발생: {e}")

    def get_server_data(self, guild):
        """서버별 데이터 구조를 반환하며, 없을 경우 초기화합니다."""
        gid = str(guild.id)

        if gid not in self.server_configs:
            self.server_configs[gid] = {
                "server_name": guild.name,
                "owner_id": guild.owner_id,
                "owner_name": str(guild.owner),
                "log_channel_id": None,
                "punish_log_channel_id": None,
                "command_channel_id": None,
                "ticket_panel_channel_id": None,
                "ticket_panel_msg_id": None,
                "ticket_count": 0
            }
        else:
            keys = ["ticket_panel_channel_id", "ticket_panel_msg_id", "ticket_count"]
            for key in keys:
                if key not in self.server_configs[gid]:
                    self.server_configs[gid][key] = 0 if "count" in key else None
            self.server_configs[gid]["server_name"] = guild.name

        self.save_config()
        return self.server_configs[gid]

    @commands.command(name="set")
    @commands.has_permissions(administrator=True)
    async def set_command(self, ctx, target: str = None, channel: discord.TextChannel = None):
        """서버의 각종 로그 및 티켓 채널을 설정합니다."""
        key_map = {
            "log": "log_channel_id",
            "bot": "command_channel_id",
            "punish": "punish_log_channel_id",
            "ticket": "ticket_panel_channel_id"
        }

        if not target or target.lower() not in key_map:
            embed = discord.Embed(
                description=f"❓ 사용법: `{ctx.prefix}set [log/punish/bot/ticket] [#채널]`",
                color=0x95A5A6
            )
            return await ctx.send(embed=embed)

        target = target.lower()
        target_channel = channel or ctx.channel
        gid = str(ctx.guild.id)
        self.get_server_data(ctx.guild)

        self.server_configs[gid][key_map[target]] = target_channel.id
        embed = discord.Embed(
            description=f"✅ **{target.upper()}** 채널이 {target_channel.mention}로 설정되었습니다.",
            color=0x2ECC71
        )

        if target == "ticket":
            ticket_cog = self.bot.get_cog('Ticket')
            if ticket_cog:
                panel_msg = await ticket_cog.send_ticket_panel(target_channel)
                if panel_msg:
                    self.server_configs[gid]["ticket_panel_channel_id"] = target_channel.id
                    self.server_configs[gid]["ticket_panel_msg_id"] = panel_msg.id
                    embed = discord.Embed(
                        description=f"✅ 티켓 패널이 {target_channel.mention}에 생성되었습니다.",
                        color=0x2ECC71
                    )
                else:
                    embed = discord.Embed(description="❌ 티켓 메시지 생성에 실패했습니다.", color=0xE74C3C)
                    return await ctx.send(embed=embed)
            else:
                embed = discord.Embed(description="❌ Ticket Cog가 로드되지 않았습니다.", color=0xE74C3C)
                return await ctx.send(embed=embed)

        self.save_config()
        await ctx.send(embed=embed)

    @commands.command(name="reset")
    @commands.has_permissions(administrator=True)
    async def reset_command(self, ctx, target: str = None):
        """서버 설정을 초기화하거나 특정 채널 설정을 제거합니다."""
        gid = str(ctx.guild.id)
        key_map = {
            "log": "log_channel_id",
            "bot": "command_channel_id",
            "punish": "punish_log_channel_id",
            "ticket": "ticket_panel_channel_id"
        }

        if target == "all":
            await self.delete_ticket_panel(ctx.guild)
            self.server_configs.pop(gid, None)
            embed = discord.Embed(description="✅ 모든 설정이 초기화되었습니다.", color=0xE74C3C)
        elif target and target.lower() in key_map:
            target = target.lower()
            if target == "ticket":
                await self.delete_ticket_panel(ctx.guild)

            if gid in self.server_configs:
                self.server_configs[gid][key_map[target]] = None
                if target == "ticket":
                    self.server_configs[gid]["ticket_panel_msg_id"] = None
                embed = discord.Embed(
                    description=f"✅ **{target.upper()}** 설정 및 패널이 제거되었습니다.",
                    color=0x95A5A6
                )
            else:
                embed = discord.Embed(description="❌ 설정된 데이터가 없습니다.", color=0xE74C3C)
        else:
            embed = discord.Embed(
                description=f"❓ 사용법: `{ctx.prefix}reset [log/punish/bot/ticket/all]`",
                color=0x95A5A6
            )

        self.save_config()
        await ctx.send(embed=embed)

    async def delete_ticket_panel(self, guild):
        """저장된 티켓 패널 메시지를 물리적으로 삭제합니다."""
        gid = str(guild.id)
        config = self.server_configs.get(gid)
        if not config:
            return

        msg_id = config.get("ticket_panel_msg_id")
        chn_id = config.get("ticket_panel_channel_id")

        if msg_id and chn_id:
            channel = self.bot.get_channel(chn_id)
            if not channel:
                try:
                    channel = await self.bot.fetch_channel(chn_id)
                except Exception:
                    return

            try:
                msg = await channel.fetch_message(msg_id)
                await msg.delete()
            except discord.NotFound:
                pass
            except Exception as e:
                print(f"패널 삭제 오류: {e}")


async def setup(bot):
    await bot.add_cog(Settings(bot))
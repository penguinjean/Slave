import json
import os
import random
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.dying_file = os.path.join(base_path, "..", "data/dying_data.json")
        with open(self.dying_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.monsters = data['kill_command']['monsters']
            self.death_messages = data['kill_command']['death_messages']

        self.menu_file = os.path.join(base_path, "..", "data/menu_data.json")
        with open(self.menu_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.menu_list = data['menu_command']['menu_list']
            self.time_data = data['menu_command']['time_data']

    @app_commands.command(name="choose", description="여러 선택지 중 하나를 무작위로 골라줍니다.")
    @app_commands.describe(options="선택지들을 띄어쓰기로 구분하여 입력해주세요 (예: 짜장면 짬뽕 탕수육)")
    async def choose(self, interaction: discord.Interaction, options: str):
        option_list = [opt.strip() for opt in options.split() if opt.strip()]

        if len(option_list) < 2:
            embed = discord.Embed(
                title="❓ 선택지가 부족함",
                description="최소 2개 이상의 선택지를 띄어쓰기로 구분하여 입력해주세요.\n예: `/choose 짜장면 짬뽕 탕수육`",
                color=0xE74C3C
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
            
        select = random.choice(option_list)

        embed = discord.Embed(
            title="🤔 제 선택은요...",
            description=f"작성하신 **{len(option_list)}개**의 선택지 중에서 골라봤어요!",
            color=0x2ECC71
        )
        embed.add_field(name="📋 후보 목록", value=f"`{'`, `'.join(option_list)}`", inline=False)
        embed.add_field(name="✨ 최종 결정", value=f"🎉 **{select}**", inline=False)
        embed.set_footer(text=f"요청자: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="menu", description="머먹을지 Slave가 추천해줍니다.")
    @app_commands.describe(category="추천받고 싶은 카테고리 (선택사항)")
    async def recommend_menu(self, interaction: discord.Interaction, category: Optional[str] = None):
        target_list = None
        display_category = category

        if category:
            if category in self.time_data:
                target_list = self.time_data[category]
            elif category in self.menu_list:
                target_list = self.menu_list[category]

        if not target_list:
            combined_menus = []
            for m in self.menu_list.values():
                combined_menus.extend(m)
            for t in self.time_data.values():
                combined_menus.extend(t)
            target_list = list(set(combined_menus))
            display_category = "전체 메뉴"
            
        food = random.choice(target_list)
        embed = discord.Embed(
            title="🍴 메뉴 추천 시스템",
            description=f"{interaction.user.mention}님, **{display_category}** 카테고리에서 골라봤어요!",
            color=0xF1C40F
        )
        embed.add_field(name="오늘의 추천", value=f"✨ **{food}**", inline=False)
        embed.set_footer(text="팁: 메뉴 카테고리를 정하면, 더 정확한 결과를 얻을수 있어요")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="kill", description="대상 또는 본인의 사망 사유를 보여줍니다.")
    @app_commands.describe(target="사망 대상 (유저를 지목하거나 자유로운 텍스트 입력 가능)")
    async def kill_reason(self, interaction: discord.Interaction, target: Optional[str] = None):
        if target is None:
            target_name = interaction.user.display_name
            target_is_author = True
        else:
            if target.startswith("<@") and target.endswith(">"):
                clean_id = target.strip("<@!>")
                member = interaction.guild.get_member(int(clean_id)) if clean_id.isdigit() else None
                target_name = member.display_name if member else target
                target_is_author = (member == interaction.user)
            else:
                target_name = target
                target_is_author = (target == interaction.user.name or target == interaction.user.display_name)

        chosen_msg = random.choice(self.death_messages)

        if "{attacker}" in chosen_msg:
            embed_color = 0xff0000
            if target is None or target_is_author:
                attacker_name = f"[**{random.choice(self.monsters)}**]"
            else:
                possible_attackers = [
                    f"[**{random.choice(self.monsters)}**]",
                    f"[**{interaction.user.display_name}**]"
                ]
                attacker_name = random.choice(possible_attackers)
            
            full_message = chosen_msg.format(attacker=attacker_name)
        else:
            embed_color = 0x36393F
            full_message = chosen_msg

        embed = discord.Embed(
            description=f"[**{target_name}**]이(가) {full_message}",
            color=embed_color
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
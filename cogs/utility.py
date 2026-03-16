import json
import os
import random
from typing import Union
import discord
from discord.ext import commands

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        base_path = os.path.dirname(os.path.abspath(__file__))
        self.data_file = os.path.join(base_path, "..", "utility_data.json")

        with open(self.data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

            self.monsters = data['kill_command']['monsters']
            self.death_messages = data['kill_command']['death_messages']

            self.menu_list = data['menu_command']['menu_list']
            self.time_data = data['menu_command']['time_data']

    @commands.command(name="choose", aliases=["선택", "골라줘"])
    async def choose(self, ctx: commands.Context, *options: str):
        prefix = ctx.prefix
        if len(options) < 2:
            embed = discord.Embed(
                title="❓ 선택지가 부족함",
                description=f"최소 2개 이상의 선택지를 입력합시다.\n예: `{prefix}choose 짜장면 짬뽕 탕수육`",
                color=0xE74C3C
            )
            return await ctx.send(embed=embed)
            
        select = random.choice(options)

        embed = discord.Embed(
            title="🤔 제 선택은요...",
            description=f"작성하신 **{len(options)}개**의 선택지 중에서 골라봤어요!",
            color=0x2ECC71
        )
        embed.add_field(name="📋 후보 목록", value=f"`{'`, `'.join(options)}`", inline=False)
        embed.add_field(name="✨ 최종 결정", value=f"🎉 **{select}**", inline=False)
        embed.set_footer(
            text=f"요청자: {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url
        )
        await ctx.send(embed=embed)

    @commands.command(name="menu", aliases=["메뉴", "메뉴추천", "뭐먹지", "머먹지"])
    async def recommend_menu(self, ctx: commands.Context, category: str = None):
        prefix = ctx.prefix
        target_list = None
        display_category = ""

        if category in self.time_data:
            target_list = self.time_data[category]
            display_category = category
        elif category in self.menu_list:
            target_list = self.menu_list[category]
            display_category = category

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
            description=f"{ctx.author.mention}님, **{display_category}** 카테고리에서 골라봤어요!",
            color=0xF1C40F
        )
        embed.add_field(name="오늘의 추천", value=f"✨ **{food}**", inline=False)
        embed.set_footer(
            text=f"팁: {prefix}뭐먹지 [아침/점심/한식/중식/일식 등]을 입력해 보세요!"
        )
        await ctx.send(embed=embed)

    @commands.command(name="kill")
    async def kill_reason(self, ctx, *, target_input: Union[discord.Member, str] = None):
        if target_input is None:
            target_name=ctx.author.display_name
        else:
            if isinstance(target_input, discord.Member):
                target_name=target_input.display_name
            else:
                target_name=target_input

        chosen_msg = random.choice(self.death_messages)

        if "{attacker}" in chosen_msg:
            embed_color = 0xff0000
            if target_input is None or target_input == ctx.author:
                attacker_name=f"[**{random.choice(self.monsters)}**]"
            else:
                possible_attackers = [
                    f"[**{random.choice(self.monsters)}**]",
                    f"[**{ctx.author.display_name}**]"
                ]
                attacker_name = random.choice(possible_attackers)
            
            full_message=chosen_msg.format(attacker=attacker_name)
        else:
            embed_color=0x36393F
            full_message=chosen_msg

        embed=discord.Embed(
            description=f"[**{target_name}**]이(가) {full_message}",
            color=embed_color
        )
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
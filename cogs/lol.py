import os
import re
import time
import json
from urllib.parse import quote

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

class LOLStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("RIOT_API_KEY")
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.cache_file = os.path.join(base_path, "..", "data/tracking.json")

        self.platform_alias = {
            'kr': 'kr', 'jp': 'jp1', 'na': 'na1', 'euw': 'euw1', 'eune': 'eun1',
            'br': 'br1', 'lan': 'la1', 'las': 'la2', 'tr': 'tr1', 'ru': 'ru',
            'oc': 'oc1', 'ph': 'ph2', 'sg': 'sg2', 'th': 'th2', 'vn': 'vn2'
        }

        self.region_map = {
            'kr': 'asia', 'jp1': 'asia',
            'na1': 'americas', 'br1': 'americas', 'la1': 'americas', 'la2': 'americas',
            'euw1': 'europe', 'eun1': 'europe', 'tr1': 'europe', 'ru': 'europe',
            'oc1': 'sea', 'ph2': 'sea', 'sg2': 'sea', 'th2': 'sea', 'vn2': 'sea'
        }

        if not os.path.exists(self.cache_file):
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump({}, f)

    async def fetch_riot_data(self, platform, name, tag):
        routing = self.region_map.get(platform, 'asia')
        headers = {"X-Riot-Token": self.api_key}
        async with aiohttp.ClientSession() as session:
            acc_url = (
                f"https://{routing}.api.riotgames.com/riot/account/v1/"
                f"accounts/by-riot-id/{quote(name)}/{quote(tag)}"
            )
            async with session.get(acc_url, headers=headers) as resp:
                if resp.status != 200:
                    return None
                acc_data = await resp.json()
                puuid = acc_data['puuid']

            sum_url = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
            async with session.get(sum_url, headers=headers) as resp:
                if resp.status != 200:
                    return None
                sum_data = await resp.json()
                profile_icon = sum_data.get('profileIconId', 1)
                level = sum_data.get('summonerLevel', 0)

            league_url = f"https://{platform}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
            async with session.get(league_url, headers=headers) as resp:
                if resp.status != 200:
                    return None
                league_data = await resp.json()

            res = {
                "level": level, "icon": profile_icon,
                "solo": {"tier": "Unranked", "lp": 0, "w": 0, "l": 0},
                "flex": {"tier": "Unranked", "lp": 0, "w": 0, "l": 0},
                "total_w": 0, "total_l": 0
            }

            for entry in league_data:
                q_type = entry['queueType']
                info = {
                    "tier": f"{entry['tier']} {entry['rank']}",
                    "lp": entry['leaguePoints'],
                    "w": entry['wins'],
                    "l": entry['losses']
                }
                if q_type == 'RANKED_SOLO_5x5':
                    res['solo'] = info
                elif q_type == 'RANKED_FLEX_SR':
                    res['flex'] = info
                res['total_w'] += entry['wins']
                res['total_l'] += entry['losses']

            return res

    
    @app_commands.command(name="lol", description="리그 오브 레전드(LoL) 전적을 조회합니다.")
    @app_commands.choices(platform=[
            app_commands.Choice(name="KR (한국)", value="kr"),
            app_commands.Choice(name="NA (북미)", value="na"),
            app_commands.Choice(name="JP (일본)", value="jp"),
            app_commands.Choice(name="EUW (서유럽)", value="euw"),
            app_commands.Choice(name="EUNE (북동유럽)", value="eune"),
        ])
    @app_commands.describe(
            riot_id="라이엇 ID (예: Hide on bush#KR1)",
            platform="서버 지역 (기본값: KR)",
            force_update="캐시를 무시하고 강제 갱신 여부"
        )
    async def lol_stats(self, interaction: discord.Interaction, riot_id: str, platform: str = "kr", force_update: bool = False):
        # 3초 제한 방지를 위한 응답 지연 처리
        await interaction.response.defer()
    
        if "#" not in riot_id:
                embed = discord.Embed(description="💡 예시: `Hide on bush#KR1`처럼 태그(#)를 포함하여 입력해주세요.", color=0xE74C3C)
                return await interaction.followup.send(embed=embed, ephemeral=True)
    
        game_name, tag_line = riot_id.rsplit("#", 1)
        game_name = game_name.strip()
        tag_line = tag_line.strip()
    
        platform_code = self.platform_alias.get(platform.lower(), platform.lower())
        if platform_code not in self.region_map:
            valid_list = ", ".join(self.platform_alias.keys())
            embed = discord.Embed(description=f"❌ 알 수 없는 지역입니다.\n지원: `{valid_list}`", color=0xE74C3C)
            return await interaction.followup.send(embed=embed, ephemeral=True)
    
        cache_key = f"lol {platform_code}:{riot_id}"
        
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}

        current_time = time.time()
        data, level, icon, footer = None, None, None, ""

        if not force_update and cache_key in cache:
            entry = cache[cache_key]
            if current_time - entry.get('timestamp', 0) < 1500:
                data = entry.get('data')
                level = entry.get('level')
                icon = entry.get('icon')
                footer = "캐시 데이터 사용 중"

        if data is None:
            try:
                raw_res = await self.fetch_riot_data(platform_code, game_name, tag_line)
                if not raw_res: 
                    raise Exception("No Data")

                level = raw_res.pop("level")
                icon = raw_res.pop("icon")
                data = raw_res
                
            except Exception:
                embed = discord.Embed(
                    description=f"❌ **{riot_id}** 소환사를 찾을 수 없습니다. (이름 및 태그 확인)",
                    color=0xE74C3C
                )
                return await interaction.followup.send(embed=embed, ephemeral=True)

            cache[cache_key] = {
                "timestamp": current_time,
                "region": platform_code,
                "riotid": riot_id,
                "level": level,
                "icon": icon,
                "data": data
            }
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=4)
            footer = "실시간 데이터 업데이트 완료"

        if level is None or icon is None:
            embed = discord.Embed(
                description="❌ 데이터를 처리하는 중 오류가 발생했습니다.",
                color=0xE74C3C
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)
        
        opgg_region = re.sub(r'\d+', '', platform_code)
        encoded_id = quote(riot_id.replace('#', '-'))
        opgg_url = f"https://www.op.gg/summoners/{opgg_region}/{encoded_id}"

        title = f"🎮 [{platform_code.upper()}] {riot_id} (Lv.{level})"
        embed = discord.Embed(title=title, color=0x1ABC9C)
        embed.set_thumbnail(url=f"https://ddragon.leagueoflegends.com/cdn/14.6.1/img/profileicon/{icon}.png")

        s = data['solo']
        s_total = s['w'] + s['l']
        s_wr = round(s['w'] / s_total * 100, 1) if s_total > 0 else 0
        embed.add_field(
            name="🏆 솔로 랭크",
            value=f"**{s['tier']}**\n{s['lp']} LP\n{s['w']}승 {s['l']}패 ({s_wr}%)",
            inline=True
        )

        f = data['flex']
        f_total = f['w'] + f['l']
        f_wr = round(f['w'] / f_total * 100, 1) if f_total > 0 else 0
        embed.add_field(
            name="⚔️ 자유 랭크",
            value=f"**{f['tier']}**\n{f['lp']} LP\n{f['w']}승 {f['l']}패 ({f_wr}%)",
            inline=True
        )

        embed.add_field(name="🔗 자세한 전적 (OP.GG)", value=f"[전적 보러가기]({opgg_url})", inline=False)
        embed.set_footer(text=footer)
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LOLStats(bot))
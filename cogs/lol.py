import os
import re
import time
import json
from urllib.parse import quote

import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

class LOLStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("RIOT_API_KEY")
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.cache_file = os.path.join(base_path, "..", "tracking.json")

        # 1. 사용자 입력 -> 라이엇 정식 플랫폼 코드 변환 사전
        self.platform_alias = {
            'kr': 'kr', 'jp': 'jp1', 'na': 'na1', 'euw': 'euw1', 'eune': 'eun1',
            'br': 'br1', 'lan': 'la1', 'las': 'la2', 'tr': 'tr1', 'ru': 'ru',
            'oc': 'oc1', 'ph': 'ph2', 'sg': 'sg2', 'th': 'th2', 'vn': 'vn2'
        }

        # 2. 정식 플랫폼 코드 -> 대륙 라우팅 매핑
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

            # 2. Summoner-V4: 아이콘 및 레벨 정보
            sum_url = f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
            async with session.get(sum_url, headers=headers) as resp:
                if resp.status != 200:
                    return None
                sum_data = await resp.json()
                profile_icon = sum_data.get('profileIconId', 1)
                level = sum_data.get('summonerLevel', 0)

            # 3. League-V4: 랭크 정보
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

    @commands.command(name="lol")
    async def lol_stats(self, ctx, region_or_id: str, *, args: str = None):
        """
        사용법 1: !lol Hide on bush#KR1 (KR 서버)
        사용법 2: !lol na Doublelift#NA1 (해외 서버)
        """
        # 1. 지역 입력 여부 판단
        if "#" in region_or_id:
            region_input = "kr"
            riot_id_raw = f"{region_or_id} {args if args else ''}".strip()
        else:
            region_input = region_or_id
            riot_id_raw = args if args else ""

        platform = self.platform_alias.get(region_input.lower(), region_input.lower())
        if platform not in self.region_map:
            valid_list = ", ".join(self.platform_alias.keys())
            embed = discord.Embed(
                description=f"❌ 알 수 없는 지역입니다.\n지원: `{valid_list}`",
                color=0xE74C3C
            )
            return await ctx.send(embed=embed)

        force_update = "갱신" in riot_id_raw
        riot_id = riot_id_raw.replace("갱신", "").strip()
        if "#" not in riot_id:
            embed = discord.Embed(
                description="💡 예시: `!lol Hide on bush#KR1` 또는 `!lol na Doublelift#NA1`",
                color=0x95A5A6
            )
            return await ctx.send(embed=embed)
            
        cache_key = f"lol {platform}:{riot_id}"
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}
        current_time = time.time()
        data = None
        level = None
        icon = None
        footer = ""

        if not force_update and cache_key in cache:
            entry = cache[cache_key]
            if current_time - entry.get('timestamp', 0) < 1500:
                data = entry.get('data')
                level = entry.get('level')
                icon = entry.get('icon')
                footer = "캐시 데이터 사용 중"

        if data is None:
            async with ctx.typing():
                try:
                    name, tag = riot_id.rsplit("#", 1)
                    raw_res = await self.fetch_riot_data(platform, name, tag)
                    if not raw_res: raise Exception("No Data")

                    level = raw_res.pop("level")
                    icon = raw_res.pop("icon")
                    data = raw_res
                    
                except Exception as e:
                    embed = discord.Embed(
                        description="❌ 소환사를 찾을 수 없습니다. (이름#태그 확인)",
                        color=0xE74C3C
                        )
                    return await ctx.send(embed=embed)

            cache[cache_key] = {
                "timestamp": current_time,
                "region": platform,
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
            return await ctx.send(embed=embed)
        
        opgg_region = re.sub(r'\d+', '', platform)
        encoded_id = quote(riot_id.replace('#', '-'))
        opgg_url = f"https://www.op.gg/summoners/{opgg_region}/{encoded_id}"

        title = f"🎮 [{platform.upper()}] {riot_id} (Lv.{level})"
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
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LOLStats(bot))
import os
import time
import json
from urllib.parse import quote

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

class ERStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("ER_API_KEY")
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.cache_file = os.path.join(base_path, "..", "data/tracking.json")

        if not os.path.exists(self.cache_file):
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump({}, f)

    async def fetch_er_data(self, nickname: str, server: str = None):
        headers = {
            "x-api-key": self.api_key,
            "accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            user_url = f"https://open-api.bser.io/v1/user/nickname?query={quote(nickname)}"
            async with session.get(user_url, headers=headers) as resp:
                if resp.status != 200:
                    return None
                user_data = await resp.json()
                
                if user_data.get("code") != 200 or not user_data.get("user"):
                    return None
                
                raw_users = user_data["user"]
                if isinstance(raw_users, dict):
                    raw_users = [raw_users]

                # 만약 서버를 지정하지 않았는데 검색 결과가 2명 이상(동명이인 또는 복수 결과)인 경우
                if server is None and len(raw_users) > 1:
                    return "AMBIGUOUS" # 판별 불가 상태 반환

                target_user = None
                if server:
                    for u in raw_users:
                        user_server = u.get("serverName", "").lower()
                        if server.lower() in user_server:
                            target_user = u
                            break
                    if not target_user:
                        target_user = raw_users[0]
                else:
                    target_user = raw_users[0]

                user_num = target_user["userNum"]
                name = target_user["nickname"]

            stat_url = f"https://open-api.bser.io/v1/user/stats/{user_num}/0" 
            async with session.get(stat_url, headers=headers) as resp:
                if resp.status != 200:
                    rank_data = []
                else:
                    stat_json = await resp.json()
                    rank_data = stat_json.get("userStats", [])

            res = {
                "nickname": name,
                "user_num": user_num,
                "server": server.upper() if server else "UNKNOWN",
                "squad": {"tier": "Unranked", "mmr": 0, "rank": 0},
            }

            for entry in rank_data:
                matching_team_mode = entry.get("matchingTeamMode")
                tier_name = entry.get("tierName", "Unranked")
                division = entry.get("rank", 0)
                mmr = entry.get("mmr", 0)
                
                info = {
                    "tier": tier_name if tier_name else "Unranked",
                    "mmr": mmr,
                    "rank": division
                }
                
                if matching_team_mode == 3:
                    res["squad"] = info

            return res

    @app_commands.command(name="er", description="이터널 리턴 유저 전적 정보를 조회합니다.")
    @app_commands.choices(server=[
            app_commands.Choice(name="KR (한국)", value="kr"),
            app_commands.Choice(name="NA (북미)", value="na"),
            app_commands.Choice(name="EU (유럽)", value="eu"),
            app_commands.Choice(name="SA (남미)", value="sa"),
        ])
    @app_commands.describe(nickname="조회할 유저 닉네임", server="게임 서버 지역 (선택 사항)", force_update="캐시 강제 갱신 여부")
    async def er_stats(self, interaction: discord.Interaction, nickname: str, server: str = None, force_update: bool = False):
        await interaction.response.defer()

        server_key = server.lower() if server else "default"
        cache_key = f"er {server_key} - {nickname.lower()}"
        
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}

        current_time = time.time()
        data, footer = None, ""

        if not force_update and cache_key in cache:
            entry = cache[cache_key]
            if current_time - entry.get('timestamp', 0) < 1500:
                data = entry.get('data')
                footer = "캐시 데이터 사용 중"

        if data is None:
            try:
                data = await self.fetch_er_data(nickname, server)
                
                if data == "AMBIGUOUS":
                    embed = discord.Embed(description=f"⚠️ **{nickname}** 닉네임을 가진 유저가 여러 서버에 존재합니다.\n정확한 조회를 위해 **서버(리전)를 선택하여** 다시 명령어를 입력해주세요.\n\n💡 예시: `/이터널리턴 닉네임:{nickname} server:kr`", color=0x808080)
                    return await interaction.followup.send(embed=embed, ephemeral=True)
                
                if not data: 
                    raise Exception("No Data")
            except Exception:
                embed = discord.Embed(description=f"❌ **{nickname}** 유저를 찾을 수 없습니다.", color=0x3498DB)
                return await interaction.followup.send(embed=embed, ephemeral=True)

            cache[cache_key] = {
                "timestamp": current_time,
                "server": server,
                "nickname": nickname,
                "data": data
            }
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=4)
            footer = "실시간 데이터 업데이트 완료"

        encoded_name = quote(data['nickname'])

        embed = discord.Embed(title=f"이터널 리턴 전적: {data['nickname']}", description=f"유저 번호: `{data['user_num']}` | 서버: `{data['server']}`", color=0x808080)

        sq = data['squad']
        embed.add_field(name="⚔️ 스쿼드 랭크", value=f"**{sq['tier']}**\nMMR: {sq['mmr']} (순위: {sq['rank']}위)", inline=False)
        embed.set_footer(text=footer)
        embed.add_field(name="🔗 자세한 전적 (DAK.GG)", value=f"[전적 보러가기](https://dak.gg/er/profile/{encoded_name})", inline=False)
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ERStats(bot))
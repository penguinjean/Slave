import json
import os
import time
import aiohttp

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

class PUBGStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("PUBG_API_KEY")
        self.base_url = "https://api.pubg.com/shards"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/vnd.api+json"
        }
        self.current_season = None
        self.main_color = 0xF1C40F
        
        base_path = os.path.dirname(os.path.abspath(__file__))
        self.cache_file = os.path.join(base_path, "..", "data/tracking.json")

        # 봇 시작 시 시즌 정보 로드 및 루프 시작
        self.bot.loop.create_task(self.load_current_season())

    async def load_current_season(self):
        """API를 통해 현재 활성화된 시즌 ID를 자동으로 가져옵니다."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/steam/seasons"
                async with session.get(url, headers=self.headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        seasons = data.get('data', [])
                        for season in seasons:
                            if season['attributes'].get('isCurrentSeason'):
                                self.current_season = season['id']
                                print(f"✅ PUBG 현재 시즌 로드 완료: {self.current_season}")
                                return
        except Exception as e:
            print(f"❌ 시즌 정보를 가져오는 중 오류 발생: {e}")

    def save_tracking(self, platform, nickname, stats_content, mode, is_ranked):
        """플랫폼:닉네임 키 안에 모드별 데이터를 누적하여 저장합니다."""
        data = {}
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                data = {}

        player_key = f"pubg {platform}:{nickname}"

        if player_key not in data:
            data[player_key] = {
                "nickname": nickname,
                "platform": platform,
                "data": {},
                "timestamp": time.time()
            }

        if is_ranked:
            mode_type = f"ranked-{mode}"
        else : mode_type = mode
        data[player_key]["data"][mode_type] = stats_content
        data[player_key]["timestamp"] = time.time() 

        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    async def fetch_pubg_data(self, platform, target_nick, mode, is_ranked):
        """API 호출 및 데이터 계산을 담당하는 로직"""
        async with aiohttp.ClientSession() as session:
            player_url = f"{self.base_url}/{platform}/players?filter[playerNames]={target_nick}"
            async with session.get(player_url, headers=self.headers) as resp:
                if resp.status != 200:
                    return None, "player_not_found"
                player_data = await resp.json()
                player_id = player_data['data'][0]['id']

            if is_ranked:
                if not self.current_season:
                    return None, "season_not_loaded"
                stats_url = f"{self.base_url}/{platform}/players/{player_id}/seasons/{self.current_season}/ranked"
            else:
                stats_url = f"{self.base_url}/{platform}/players/{player_id}/seasons/lifetime"

            async with session.get(stats_url, headers=self.headers) as resp:
                if resp.status != 200:
                    return None, "api_error"
                stats_data = await resp.json()

            search_mode = mode
            stats_root = stats_data['data']['attributes']
            mode_stats = stats_root['rankedGameModeStats'] if is_ranked else stats_root['gameModeStats']
            game_stats = mode_stats.get(search_mode, {})

            if not game_stats or game_stats.get('roundsPlayed', 0) == 0:
                return None, "no_data"

            rounds = game_stats.get('roundsPlayed', 0)
            wins = game_stats.get('wins', 0)
            kills = game_stats.get('kills', 0)
            damage = game_stats.get('damageDealt', 0)
            top10s = game_stats.get('top10s', 0)
            
            deaths = rounds - wins
            processed_data = {
                "nickname": target_nick,
                "platform": platform,
                "mode_key": search_mode,
                "rounds": rounds,
                "kd": round(kills / deaths, 2) if deaths > 0 else kills,
                "adr": int(damage / rounds) if rounds > 0 else 0,
                "win_rate": round((wins / rounds) * 100, 1) if rounds > 0 else 0,
                "top10_rate": round((top10s / rounds) * 100, 1) if rounds > 0 else 0,
                "tier": game_stats.get('currentTier', {}).get('tier', 'Unranked') if is_ranked else "Normal",
                "sub_tier": game_stats.get('currentTier', {}).get('subTier', '') if is_ranked else "",
                "point": game_stats.get('currentRankPoint', 0) if is_ranked else 0
            }
            return processed_data, None

    @app_commands.command(name="pubg", description="배틀그라운드 전적을 조회합니다.")
    @app_commands.choices(platform=[
    app_commands.Choice(name="Steam", value="steam"),
    app_commands.Choice(name="Kakao", value="kakao"),
    app_commands.Choice(name="PSN", value="psn"),
    app_commands.Choice(name="Xbox", value="xbox")
    ])
    @app_commands.choices(mode=[
        app_commands.Choice(name="스쿼드 (일반)", value="squad"),
        app_commands.Choice(name="듀오 (일반)", value="duo"),
        app_commands.Choice(name="솔로 (일반)", value="solo"),
        app_commands.Choice(name="경쟁전 (스쿼드)", value="ranked_squad"),
    ])
    async def pubg_stats(self, interaction: discord.Interaction, nickname: str, platform: str = "steam",  mode: str = "squad"):
        await interaction.response.defer(ephemeral=False)

        is_ranked = "ranked_" in mode
        actual_mode = mode.replace("ranked_", "")
        stats, error = await self.fetch_pubg_data(platform, nickname, actual_mode, is_ranked)

        if error:
            error_msgs = {
                "player_not_found": f"❌ **{nickname}**님을 찾을 수 없습니다.",
                "season_not_loaded": "⚠️ 시즌 정보를 로드 중입니다.",
                "api_error": "❌ API 응답 오류가 발생했습니다.",
                "no_data": f"**{nickname}**님의 {actual_mode} 데이터가 없습니다."
            }
            return await interaction.followup.send(error_msgs.get(error, "⚠️ 오류 발생"), ephemeral=True)

        stats_content = {
            "adr": stats['adr'],
            "kd": stats['kd'],
            "win_rate": f"{stats['win_rate']}%",
            "top10": f"{stats['top10_rate']}%",
            "rounds": stats['rounds'],
            "tier": stats['tier'],
            "sub_tier": stats['sub_tier'],
            "point": stats['point']
        }

        self.save_tracking(platform, stats['nickname'], stats_content, stats['mode_key'], is_ranked)

        embed = discord.Embed(title=f"PUBG 전적: {stats['nickname']}", color=self.main_color)
        if is_ranked:
            embed.add_field(name="티어", value=f"**{stats['tier']} {stats['sub_tier']}** ({stats['point']}pt)", inline=False)

        embed.add_field(name="모드", value=f"{stats['mode_key'].upper()} {'(경쟁)' if is_ranked else ''}", inline=True)
        embed.add_field(name="판수", value=f"{stats['rounds']}회", inline=True)
        embed.add_field(name="K/D", value=f"**{stats['kd']}**", inline=True)
        embed.add_field(name="평균 딜량(ADR)", value=f"{stats['adr']}", inline=True)
        embed.add_field(name="승률 / Top10", value=f"{stats['win_rate']}% / {stats['top10_rate']}%", inline=True)
        
        dak_url = f"https://dak.gg/pubg/profile/{platform}/{stats['nickname']}"
        embed.add_field(name="🔗 상세 전적", value=f"[DAK.GG 바로가기]({dak_url})", inline=False)
        embed.set_footer(text=f"{platform.upper()} / {'Ranked' if is_ranked else 'Normal'}")
        
        return await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PUBGStats(bot))
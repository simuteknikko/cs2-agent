import requests
import os
import json
from datetime import datetime, timedelta
from collections import defaultdict

# ==========================================
# SECURE KEY RETRIEVAL
# This line grabs the key from GitHub Secrets automatically
PANDASCORE_KEY = os.environ["PANDASCORE_KEY"]
# ==========================================

# Configuration
HEADERS = {"Authorization": f"Bearer {PANDASCORE_KEY}"}
MATCH_HISTORY_DEPTH = 30

def get_upcoming_matches():
    """Fetches CS2 matches for the next 24 hours."""
    now = datetime.utcnow()
    tomorrow = now + timedelta(hours=24)
    range_str = f"{now.strftime('%Y-%m-%dT%H:%M:%SZ')},{tomorrow.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    url = f"https://api.pandascore.co/csgo/matches/upcoming?sort=begin_at&range[begin_at]={range_str}"
    
    try:
        return requests.get(url, headers=HEADERS).json()
    except Exception as e:
        print(f"Error fetching matches: {e}")
        return []

def analyze_team_history(team_id, opponent_id):
    """Fetches history and calculates Map Stats + H2H."""
    if not team_id: return None

    url = f"https://api.pandascore.co/csgo/teams/{team_id}/matches?per_page={MATCH_HISTORY_DEPTH}&finished=true&sort=-begin_at"
    try:
        history = requests.get(url, headers=HEADERS).json()
    except:
        return None

    stats = {
        "last_5": [],
        "map_stats": defaultdict(lambda: {"wins": 0, "played": 0}),
        "h2h_wins": 0,
        "h2h_played": 0
    }

    for i, match in enumerate(history):
        # 1. Recent Form
        if i < 5:
            res = "W" if match['winner_id'] == team_id else "L"
            # Handle missing opponent data safely
            opp_name = "Unknown"
            if len(match['opponents']) > 1:
                opp_name = match['opponents'][0]['opponent']['name'] if match['opponents'][0]['opponent']['id'] != team_id else match['opponents'][1]['opponent']['name']
            
            score = "?"
            if match.get('results') and len(match['results']) > 1:
                score = f"{match['results'][0]['score']}-{match['results'][1]['score']}"
            
            stats["last_5"].append(f"{res} vs {opp_name} ({score})")

        # 2. Head-to-Head
        is_h2h = any(opp['opponent']['id'] == opponent_id for opp in match['opponents'])
        if is_h2h:
            stats['h2h_played'] += 1
            if match['winner_id'] == team_id:
                stats['h2h_wins'] += 1

        # 3. Map Stats
        if 'games' in match:
            for game in match['games']:
                if game.get('finished') and game.get('winner') and game.get('map'):
                    map_name = game['map']['name']
                    stats['map_stats'][map_name]['played'] += 1
                    if game['winner']['id'] == team_id:
                        stats['map_stats'][map_name]['wins'] += 1

    return stats

def format_map_stats(map_stats):
    output = []
    for m, data in map_stats.items():
        if data['played'] > 0:
            win_rate = (data['wins'] / data['played']) * 100
            output.append(f"{m}: {win_rate:.0f}% ({data['wins']}/{data['played']})")
    return ", ".join(output) if output else "No recent map data"

def run_miner():
    matches = get_upcoming_matches()
    
    report = f"🧠 DAILY CS2 INTELLIGENCE PACK - {datetime.now().strftime('%Y-%m-%d')}\n"
    report += "INSTRUCTIONS: Analyze Map Pools and H2H to find value bets.\n\n"

    if not matches:
        report += "No matches found for the next 24 hours."
    else:
        for m in matches:
            if len(m['opponents']) != 2: continue
            t1 = m['opponents'][0]['opponent']
            t2 = m['opponents'][1]['opponent']
            
            if not t1 or not t2: continue

            print(f"Analyzing {t1['name']} vs {t2['name']}...")

            t1_stats = analyze_team_history(t1['id'], t2['id'])
            t2_stats = analyze_team_history(t2['id'], t1['id'])

            if not t1_stats or not t2_stats: continue

            report += f"⚔️ MATCH: {t1['name']} vs {t2['name']}\n"
            report += f"🏆 League: {m['league']['name']} (Best of {m['number_of_games']})\n"
            
            # Team A
            report += f"\n📊 TEAM A: {t1['name']}\n"
            report += f"   • Last 5: {' | '.join(t1_stats['last_5'])}\n"
            report += f"   • H2H vs {t2['name']}: Won {t1_stats['h2h_wins']} of {t1_stats['h2h_played']}\n"
            report += f"   • MAP POOL (Last 30): {format_map_stats(t1_stats['map_stats'])}\n"

            # Team B
            report += f"\n📊 TEAM B: {t2['name']}\n"
            report += f"   • Last 5: {' | '.join(t2_stats['last_5'])}\n"
            report += f"   • H2H vs {t1['name']}: Won {t2_stats['h2h_wins']} of {t2_stats['h2h_played']}\n"
            report += f"   • MAP POOL (Last 30): {format_map_stats(t2_stats['map_stats'])}\n"

            report += "\n💰 ODDS: [ENTER ODDS HERE]\n"
            report += "="*40 + "\n\n"

    print(report)

if __name__ == "__main__":
    run_miner()
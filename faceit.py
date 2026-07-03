import os
import time
import logging
import httpx
from urllib.parse import quote

DEFAULTS = {
    "INTERVAL": "120",
}

REQUIRED = ("FACEIT_API_KEY", "FACEIT_NICKNAME", "DISCORD_BOT_TOKEN", "APP_ID", "USER_ID")


def cfg(key: str) -> str:
    val = os.environ.get(key, DEFAULTS.get(key))
    if not val:
        raise RuntimeError(f"Missing environment variable {key} (see README)")
    return val


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("faceit-widget")

FACEIT_BASE = "https://open.faceit.com/data/v4"
DISCORD_BASE = "https://discord.com/api/v9"

MAPS_RAW_BASE = "https://raw.githubusercontent.com/ghostcap-gaming/cs2-map-images/main/cs2"
LEVELS_CDN_BASE = "https://raw.githubusercontent.com/evansvl/faceit-levels/main"

LEVEL_CEIL = {1: 500, 2: 750, 3: 900, 4: 1050, 5: 1200,
              6: 1350, 7: 1530, 8: 1750, 9: 2000}

CALIB_TOTAL = 10

SEASON_START = 1776816000


def square(url: str, size: int = 512) -> str:
    return f"https://wsrv.nl/?url={quote(url, safe='')}&w={size}&h={size}&fit=cover&output=png"


def map_widget_image(url: str, size: int = 512) -> str:
    size_factor = size / 512
    top_strip = max(0, round(17 * size_factor ** 0.678))
    strip_h = size - top_strip
    inner = (f"https://wsrv.nl/?url={quote(url, safe='')}"
             f"&w={size}&h={strip_h}&fit=cover&a=focal&fpx=0.5&fpy=0&output=png")
    return (f"https://wsrv.nl/?url={quote(inner, safe='')}"
            f"&w={size}&h={size}&fit=contain&a=bottom&cbg=transparent&output=png")


def fetch_faceit_data(client: httpx.Client) -> dict:
    headers = {"Authorization": f"Bearer {cfg('FACEIT_API_KEY')}"}
    nick = cfg("FACEIT_NICKNAME")

    p_req = client.get(f"{FACEIT_BASE}/players", params={"nickname": nick}, headers=headers)
    p_req.raise_for_status()
    p_data = p_req.json()

    player_id = p_data["player_id"]
    cs2_games = p_data.get("games", {}).get("cs2", {})
    current_elo = int(cs2_games.get("faceit_elo", 0))
    skill_level = int(cs2_games.get("skill_level", 0))

    h_req = client.get(
        f"{FACEIT_BASE}/players/{player_id}/history",
        params={"game": "cs2", "limit": 100},
        headers=headers,
    )
    h_req.raise_for_status()
    items = h_req.json().get("items", [])

    season_matches = sum(1 for it in items if int(it.get("finished_at", 0)) >= SEASON_START)
    calibrating = season_matches < CALIB_TOTAL

    raw_map_name = "unknown"
    kda_text = "—"
    elo_change = "0"
    if items:
        match_id = items[0].get("match_id")
        m_req = client.get(f"{FACEIT_BASE}/matches/{match_id}/stats", headers=headers)
        if m_req.status_code == 200:
            round0 = m_req.json().get("rounds", [{}])[0]
            raw_map_name = round0.get("round_stats", {}).get("Map", "unknown").lower()
            for team in round0.get("teams", []):
                for p in team.get("players", []):
                    if p.get("player_id") == player_id:
                        stats = p.get("player_stats", {})
                        kda_text = (
                            f"{stats.get('Kills', '0')}/"
                            f"{stats.get('Deaths', '0')}/"
                            f"{stats.get('Assists', '0')}"
                        )
                        elo_change = "+25" if stats.get("Result", "0") == "1" else "-25"

    if raw_map_name != "unknown":
        raw_url = f"{MAPS_RAW_BASE}/{raw_map_name}.png"
        display = raw_map_name[3:] if raw_map_name.startswith("de_") else raw_map_name
        clean_map_name = display.capitalize()
    else:
        raw_url = f"{MAPS_RAW_BASE}/de_dust2.png"
        clean_map_name = "Unknown"
    map_img_url = map_widget_image(raw_url)

    if calibrating:
        level_value = 0
        level_label = "Calibration"
        bar_current = season_matches
        bar_max = CALIB_TOTAL
        left = CALIB_TOTAL - season_matches
        sub_2 = f"Play {left} more matches to get your Skill Level"
        sub_3 = f"Season placements: {season_matches}/{CALIB_TOTAL}"
    elif skill_level >= 10:
        level_value = 10
        level_label = "Level 10"
        bar_current = current_elo
        bar_max = current_elo
        sub_2 = "Max level reached"
        sub_3 = f"Current Elo: {current_elo}"
    else:
        level_value = skill_level
        level_label = f"Level {skill_level}"
        bar_current = current_elo
        bar_max = LEVEL_CEIL.get(skill_level, 2000)
        sub_2 = f"{bar_max + 1 - current_elo} Elo from Level {skill_level + 1}"
        sub_3 = f"Current Elo: {current_elo}"

    level_image = square(f"{LEVELS_CDN_BASE}/skill_level_{level_value}.png")

    status = "Calibration in progress" if calibrating else f"Current Elo: {current_elo}"

    return {
        "status": status,
        "map_name": clean_map_name,
        "kda": kda_text,
        "elo_change": elo_change,
        "sub_1": level_label,
        "sub_2": sub_2,
        "sub_3": sub_3,
        "bar_current": bar_current,
        "bar_max": bar_max,
        "map_image": map_img_url,
        "level_image": level_image,
    }


def build_payload(data: dict) -> dict:
    dynamic = [
        {"type": 1, "name": "map_name",    "value": data["map_name"]},
        {"type": 1, "name": "kda",         "value": data["kda"]},
        {"type": 1, "name": "elo_change",  "value": data["elo_change"]},
        {"type": 1, "name": "sub_1",       "value": data["sub_1"]},
        {"type": 1, "name": "sub_2",       "value": data["sub_2"]},
        {"type": 1, "name": "sub_3",       "value": data["sub_3"]},
        {"type": 1, "name": "status",      "value": data["status"]},
        {"type": 2, "name": "current",     "value": int(data["bar_current"])},
        {"type": 2, "name": "max",         "value": int(data["bar_max"])},
        {"type": 3, "name": "map_image",   "value": {"url": data["map_image"]}},
        {"type": 3, "name": "level_image", "value": {"url": data["level_image"]}},
    ]
    return {"username": cfg("FACEIT_NICKNAME"), "data": {"dynamic": dynamic}}


def push_to_discord(client: httpx.Client, payload: dict) -> None:
    url = f"{DISCORD_BASE}/applications/{cfg('APP_ID')}/users/{cfg('USER_ID')}/identities/0/profile"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bot {cfg('DISCORD_BOT_TOKEN')}",
    }
    resp = client.patch(url, headers=headers, json=payload)

    if resp.status_code == 429:
        retry_after = resp.json().get("retry_after", 5)
        time.sleep(retry_after + 0.5)
        resp = client.patch(url, headers=headers, json=payload)

    if resp.status_code >= 400:
        log.error("Discord %s: %s", resp.status_code, resp.text)

    resp.raise_for_status()
    log.info("Faceit widget updated successfully")


def main():
    interval = int(cfg("INTERVAL"))
    with httpx.Client(timeout=20) as client:
        while True:
            try:
                data = fetch_faceit_data(client)
                payload = build_payload(data)
                push_to_discord(client, payload)
            except Exception as e:
                log.error("Error in loop: %r", e)
            time.sleep(interval)


if __name__ == "__main__":
    main()

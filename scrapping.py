import os
import random
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID_KEY")
CLIENT_SECRET = os.getenv("CLIENT_SECRET_KEY")

GAME_NAMES = ["World of Warcraft", "Path of Exile 2", "Gothic 1 Remake"]
TWITCHTRACKER_CHANNEL_SUMMARY_URL = "https://twitchtracker.com/api/channels/summary/{username}"

TWITCHTRACKER_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Referer": "https://twitchtracker.com/",
}


def get_twitch_token(client_id, client_secret):
    auth_url = "https://id.twitch.tv/oauth2/token"
    auth_params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }
    response = requests.post(auth_url, params=auth_params, timeout=15)
    response.raise_for_status()
    return response.json()["access_token"]


def get_game_info(client_id, token, game_names):
    url = "https://api.twitch.tv/helix/games"
    headers = {
        "Client-Id": client_id,
        "Authorization": f"Bearer {token}",
    }
    params = [("name", name) for name in game_names]
    response = requests.get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    games_data = response.json().get("data", [])

    info_dict = {}
    for game in games_data:
        box_art = game["box_art_url"].replace("{width}", "150").replace("{height}", "200")
        info_dict[game["name"]] = {"id": game["id"], "box_art": box_art}

    return info_dict


def get_live_streams(client_id, token, game_id):
    url = "https://api.twitch.tv/helix/streams"
    headers = {
        "Client-Id": client_id,
        "Authorization": f"Bearer {token}",
    }
    params = {"game_id": game_id, "first": 100}
    response = requests.get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    return response.json().get("data", [])


def get_users_data(client_id, token, user_ids):
    url = "https://api.twitch.tv/helix/users"
    headers = {
        "Client-Id": client_id,
        "Authorization": f"Bearer {token}",
    }
    params = [("id", str(uid)) for uid in user_ids]
    response = requests.get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    return response.json().get("data", [])


def extract_metric(payload, aliases):
    if isinstance(payload, dict):
        normalized_payload = {
            str(key).lower().replace(" ", "_").replace("-", "_"): value
            for key, value in payload.items()
        }

        for alias in aliases:
            normalized_alias = alias.lower().replace(" ", "_").replace("-", "_")
            if normalized_alias in normalized_payload:
                return normalized_payload[normalized_alias]

        for value in payload.values():
            nested_value = extract_metric(value, aliases)
            if nested_value is not None:
                return nested_value

    if isinstance(payload, list):
        for item in payload:
            nested_value = extract_metric(item, aliases)
            if nested_value is not None:
                return nested_value

    return None


def clean_metric(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return str(int(value)) if float(value).is_integer() else str(value)

    text = str(value).strip().replace(",", "")
    return text or None


def get_twitchtracker_summary(username, session, max_retries=3):
    url = TWITCHTRACKER_CHANNEL_SUMMARY_URL.format(username=username.lower())

    for attempt in range(max_retries):
        wait_seconds = 8 * (attempt + 1)

        try:
            response = session.get(url, timeout=12)

            if response.status_code == 404:
                return {}

            if response.status_code in (403, 429, 503):
                print(f"      [LIMIT] TwitchTracker returned {response.status_code}. Waiting {wait_seconds}s.")
                time.sleep(wait_seconds)
                continue

            response.raise_for_status()
            data = response.json()

            return {
                "avg_viewers_30d": clean_metric(
                    extract_metric(
                        data,
                        [
                            "avg_viewers",
                            "average_viewers",
                            "average_viewers_30d",
                            "viewers_avg",
                        ],
                    )
                ),
                "followers_gained_30d": clean_metric(
                    extract_metric(
                        data,
                        [
                            "followers_gained",
                            "followers_gained_30d",
                            "followers",
                        ],
                    )
                ),
            }
        except requests.RequestException as exc:
            print(f"      [RETRY] Connection error: {exc}. Waiting {wait_seconds}s.")
            time.sleep(wait_seconds)
        except ValueError:
            print("      [WARN] TwitchTracker returned a non-JSON response.")
            return {}

    return {}


def scrape_channel_summary(username, session):
    try:
        return get_twitchtracker_summary(username, session)
    except Exception as exc:
        print(f"      [WARN] Could not fetch channel summary: {exc}")
        return {}


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Missing CLIENT_ID_KEY or CLIENT_SECRET_KEY in .env")
        return

    print("1. Authorizing Twitch API...")
    token = get_twitch_token(CLIENT_ID, CLIENT_SECRET)

    print("\n2. Fetching official game IDs and box art...")
    games_info = get_game_info(CLIENT_ID, token, GAME_NAMES)

    if not games_info:
        print("No configured games were found in Twitch API.")
        return

    all_streams = []

    print("\n3. Fetching live streams...")
    for game_name, info in games_info.items():
        game_id = info["id"]
        box_art = info["box_art"]

        print(f"--- Scanning: {game_name} (ID: {game_id}) ---")
        streams_data = get_live_streams(CLIENT_ID, token, game_id)

        if not streams_data:
            print("  -> No active streams right now.")
            continue

        for stream in streams_data:
            stream["game_box_art_url"] = box_art

        all_streams.extend(streams_data)
        print(f"  -> Collected {len(streams_data)} streams.")

    df_streams = pd.DataFrame(all_streams)
    if df_streams.empty:
        print("Stopping. No data was collected.")
        return

    user_ids = df_streams["user_id"].tolist()
    print(f"\n4. Fetching avatars for {len(user_ids)} creators...")

    users_data = []
    for i in range(0, len(user_ids), 100):
        chunk = user_ids[i:i + 100]
        users_data.extend(get_users_data(CLIENT_ID, token, chunk))

    if users_data:
        df_users = pd.DataFrame(users_data)[["id", "profile_image_url"]]
    else:
        df_users = pd.DataFrame(columns=["id", "profile_image_url"])

    df = df_streams.merge(df_users, left_on="user_id", right_on="id", how="left")

    now = datetime.now(timezone.utc)
    df["started_at"] = pd.to_datetime(df["started_at"])
    df["uptime_minutes"] = ((now - df["started_at"]).dt.total_seconds() / 60).round()

    total_streamers = len(df)
    print(f"\n5. Fetching TwitchTracker 30-day summaries for {total_streamers} creators...")

    tracker_session = requests.Session()
    tracker_session.headers.update(TWITCHTRACKER_HEADERS)
    df["avg_viewers_30d"] = "No data"
    df["followers_gained_30d"] = "No data"

    df = df.sort_values("viewer_count", ascending=False).reset_index(drop=True)
    summary_cache = {}

    for index, row in df.iterrows():
        username = row["user_name"]
        game = row["game_name"]

        print(f"  [{index + 1}/{total_streamers}] [{game}] {username} ...", end=" ")
        cache_key = username.lower()
        if cache_key not in summary_cache:
            summary_cache[cache_key] = scrape_channel_summary(username, tracker_session)

        summary = summary_cache[cache_key]
        avg_viewers = summary.get("avg_viewers_30d")
        followers_gained = summary.get("followers_gained_30d")

        if avg_viewers is not None:
            df.at[index, "avg_viewers_30d"] = str(avg_viewers)
        if followers_gained is not None:
            df.at[index, "followers_gained_30d"] = str(followers_gained)

        if avg_viewers is not None or followers_gained is not None:
            print(f"OK (avg: {avg_viewers or '-'}, followers +: {followers_gained or '-'})")
        else:
            print("No data/skipped")

        time.sleep(random.uniform(2.5, 5.5))

    os.makedirs("data", exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"data/{today_str}.csv"
    df.to_csv(filename, index=False)
    print(f"\nDone. Saved combined dataset to: {filename}")


if __name__ == "__main__":
    main()

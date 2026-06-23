import datetime
import json
import os
import time
import uuid

import httpx
from dotenv import load_dotenv

load_dotenv()

POE_CONTACT = os.getenv("POE_CONTACT")
if not POE_CONTACT:
    raise RuntimeError("POE_CONTACT environment variable is not set (check your .env file)")
USER_AGENT = f"gradient-boost-evaluator/0.1 (contact: {POE_CONTACT})"
POESESSID = os.getenv("POESESSID")
if not POESESSID:
    raise RuntimeError("POESESSID environment variable is not set (check your .env file)")
COOKIES = {"POESESSID": POESESSID}
BASE_URL = "https://www.pathofexile.com"
LEAGUE = "Runes%20of%20Aldur"

MIN_DELAY_SECONDS = 0.05
FETCH_BATCH_SIZE = 10
MAX_TRACKED_IDS = 400
TRACKED_IDS_TRIM_SIZE = 280
SAVE_THRESHOLD = 300

DATA_DIR = './Data/Raw'

def calculate_delay_from_headers(headers: dict) -> float:
    """Calculate required delay based on rate limit headers. Returns delay in seconds."""
    max_delay = MIN_DELAY_SECONDS

    rules = [headers.get("x-rate-limit-account"), headers.get("x-rate-limit-ip")]
    states = [headers.get("x-rate-limit-account-state"), headers.get("x-rate-limit-ip-state")]

    for rule, state in zip(rules, states):
        if not rule or not state:
            continue

        # Parse all rate limit tiers (format: "limit:window:penalty,limit:window:penalty,...")
        rule_tiers = rule.split(",")
        state_tiers = state.split(",")

        for rule_tier, state_tier in zip(rule_tiers, state_tiers):
            limit, window, penalty = map(int, rule_tier.split(":"))
            used, _, current_penalty = map(int, state_tier.split(":"))

            # If we're in penalty, wait for the penalty duration
            if current_penalty > 0:
                max_delay = max(max_delay, current_penalty)
                continue

            # Calculate delay to stay under the limit
            # If approaching the limit, spread remaining requests over the window
            remaining_requests = limit - used
            if remaining_requests <= 1:
                max_delay = max(max_delay, window)
            elif remaining_requests <= limit * 0.2:  # Under 20% capacity
                # Be more conservative when running low on quota
                delay_per_request = window / remaining_requests
                max_delay = max(max_delay, delay_per_request)

    return max(max_delay, MIN_DELAY_SECONDS)


def get_elements(data: list, batch_size: int):
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]

SEARCH_QUERY = {
    "query": {
        "filters": {
            "trade_filters": {"filters": {"indexed": {"option": "1hour"}}}
            #"type_filters" : {"filters": {"category": {"option": "weapon.bow"}, "rarity": {"option": "nonunique"}}}
        }
    },
    "sort": {"indexed": "asc"}
}


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    search_url = f"{BASE_URL}/api/trade2/search/poe2/{LEAGUE}"
    fetch_url = f"{BASE_URL}/api/trade2/fetch"

    data_from_requests = {"data": []}
    ids_track = []

    client_config = {
        "http2": True,
        "timeout": 20,
        "headers": {"User-Agent": USER_AGENT, "Accept": "application/json"},
        "cookies": COOKIES
    }

    with httpx.Client(**client_config) as session:
        next_request_time = datetime.datetime.now()

        while True:
            now = datetime.datetime.now()
            if next_request_time > now:
                seconds_to_wait = (next_request_time - now).total_seconds()
                print(f"Has to wait {seconds_to_wait:.1f}s before doing another search...")
                time.sleep(seconds_to_wait)

            print("Searching for recent items...")
            search_result = session.post(search_url, json=SEARCH_QUERY)
            delay = calculate_delay_from_headers(dict(search_result.headers))
            next_request_time = datetime.datetime.now() + datetime.timedelta(seconds=delay)
            search_json = search_result.json()

            all_ids = search_json['result']
            new_ids = list(set(all_ids) - set(ids_track))
            if len(all_ids) != len(new_ids):
                print(f"Fetching only {len(new_ids)} out of {len(all_ids)} due to duplicates...")

            for ids in get_elements(new_ids, FETCH_BATCH_SIZE):
                ids_string = ",".join(ids)
                now = datetime.datetime.now()
                if next_request_time > now:
                    seconds_to_wait = (next_request_time - now).total_seconds()
                    print(f"Has to wait {seconds_to_wait:.1f}s before doing another fetch...")
                    time.sleep(seconds_to_wait)

                print(f"Fetching {len(ids)} items...")
                fetch_result = session.get(f"{fetch_url}/{ids_string}", params={"query": search_json['id']})
                delay = calculate_delay_from_headers(dict(fetch_result.headers))
                next_request_time = datetime.datetime.now() + datetime.timedelta(seconds=delay)
                fetch_json = fetch_result.json()
                data_from_requests["data"].extend(fetch_json['result'])
                ids_track.extend(str(d['id']) for d in fetch_json['result'])

            if len(ids_track) > MAX_TRACKED_IDS:
                ids_track = ids_track[TRACKED_IDS_TRIM_SIZE:]

            if len(data_from_requests['data']) >= SAVE_THRESHOLD:
                filename = os.path.join(DATA_DIR, f'random-data-{uuid.uuid4()}.json')
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data_from_requests, f, ensure_ascii=False, indent=4)
                data_from_requests = {"data": []}


if __name__ == "__main__":
    main()
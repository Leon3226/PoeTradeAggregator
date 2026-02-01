import datetime
import json
import os
import time
import uuid

import httpx

USER_AGENT = "gradient-boost-evaluator/0.1 (contact: REDACTED_CONTACT)"
COOKIES = {"POESESSID": "REDACTED_POESESSID"}
BASE_URL = "https://www.pathofexile.com"
LEAGUE = "Fate%20of%20the%20Vaal"

SEARCH_DELAY_SECONDS = 8
FETCH_DELAY_SECONDS = 1
FETCH_BATCH_SIZE = 10
MAX_TRACKED_IDS = 400
TRACKED_IDS_TRIM_SIZE = 280
SAVE_THRESHOLD = 300

DATA_DIR = './Data/Raw'

def respect_limits(headers: dict):
    rules = [headers.get("x-rate-limit-account"), headers.get("x-rate-limit-ip")]
    states = [headers.get("x-rate-limit-account-state"), headers.get("x-rate-limit-ip-state")]

    for rule, state in zip(rules, states):
        if not rule or not state:
            continue
        limit, window, _ = map(int, rule.split(",")[0].split(":"))
        used, _, _ = map(int, state.split(",")[0].split(":"))
        if used >= limit - 1:
            time.sleep(window)


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
        search_delay = datetime.datetime.now()
        fetch_delay = datetime.datetime.now()

        while True:
            now = datetime.datetime.now()
            if search_delay > now:
                seconds_to_wait = (search_delay - now).total_seconds()
                print(f"Has to wait {seconds_to_wait:.1f}s before doing another search...")
                time.sleep(seconds_to_wait)

            print("Searching for recent items...")
            search_result = session.post(search_url, json=SEARCH_QUERY)
            search_json = search_result.json()
            search_delay = datetime.datetime.now() + datetime.timedelta(seconds=SEARCH_DELAY_SECONDS)

            all_ids = search_json['result']
            new_ids = list(set(all_ids) - set(ids_track))
            if len(all_ids) != len(new_ids):
                print(f"Fetching only {len(new_ids)} out of {len(all_ids)} due to duplicates...")

            for ids in get_elements(new_ids, FETCH_BATCH_SIZE):
                ids_string = ",".join(ids)
                now = datetime.datetime.now()
                if fetch_delay > now:
                    seconds_to_wait = (fetch_delay - now).total_seconds()
                    print(f"Has to wait {seconds_to_wait:.1f}s before doing another fetch...")
                    time.sleep(seconds_to_wait)

                print(f"Fetching {len(ids)} items...")
                fetch_result = session.get(f"{fetch_url}/{ids_string}", params={"query": search_json['id']})
                fetch_delay = datetime.datetime.now() + datetime.timedelta(seconds=FETCH_DELAY_SECONDS)
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
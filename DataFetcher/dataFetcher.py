import httpx, time, datetime, numpy as np, json, uuid, os

UA = "gradient-boost-evaluator/0.1 (contact: REDACTED_CONTACT)"
COOKIES = {"POESESSID": "REDACTED_POESESSID"}  # or use Authorization: Bearer xyz
BASE = "https://www.pathofexile.com"
LEAGUE = "Rise%20of%20the%20Abyssal"  # example PoE2 league name

os.chdir('./Data/Raw')

def respect_limits(h):
    # Example: X-Rate-Limit-Client: 20:5:60   X-Rate-Limit-Client-State: 3:5:10
    rules = [h.get("x-rate-limit-account"), h.get("x-rate-limit-ip")]
    states = [h.get("x-rate-limit-account-state"), h.get("x-rate-limit-ip-state")]
    if not rule or not state:    
        return
    limit, window, _ = map(int, rule.split(",")[0].split(":"))
    used, _, _ = map(int, state.split(",")[0].split(":"))
    if used >= limit - 1:
        time.sleep(window)

def getElements(data, n):
    for i in range(0, len(data), n):
        yield data[i:i+n]

query = {
  "query": 
  {
            "filters" : 
            { 
                "trade_filters": {"filters": {"indexed": {"option": "1hour"}}},
                #"type_filters" : {"filters": {"category": {"option": "weapon.bow"}, "rarity": {"option": "nonunique"}}}
            }
   },
  "sort": {"indexed":"asc"}
}

searchUrl = f"{BASE}/api/trade2/search/poe2/{LEAGUE}"
fetchUrl = f"{BASE}/api/trade2/fetch"

dataFromRequests = {"data": []}
idsTrack = []

with httpx.Client(http2=True, timeout=20, headers={"User-Agent": UA, "Accept": "application/json"}, cookies=COOKIES) as s:
    searchDelay = datetime.datetime.now()
    fetchDelay = datetime.datetime.now()

    while True:
        if searchDelay > datetime.datetime.now():
            secondsToWait = (searchDelay - datetime.datetime.now()).total_seconds();
            print(f"Has to wait {secondsToWait} before doing another search...")
            time.sleep(secondsToWait)

        print("Searching for recent items...")
        searchResult = s.post(searchUrl, json=query)
        searchJson = searchResult.json()
        searchDelay = datetime.datetime.now() + datetime.timedelta(0,8)
        allIds = searchJson['result']
        newIds = list(set(allIds) - set(idsTrack))
        if len(allIds) != len(newIds):
            print(f"Fetching only {len(newIds)} out of {len(allIds)} due to duplicates...")
        for ids in getElements(newIds,10):
            idsString = ",".join(ids)
            dtn = datetime.datetime.now()
            if fetchDelay > dtn:
                diff = fetchDelay - dtn
                secondsToWait = (fetchDelay - datetime.datetime.now()).total_seconds();
                print(f"Has to wait {secondsToWait} before doing another fetch...")
                time.sleep(secondsToWait)

            print(f"Fetching {len(ids)} items...")
            fetchResult = s.get(f"{fetchUrl}/{idsString}", params={"query": searchJson['id']})
            fetchDelay = datetime.datetime.now() + datetime.timedelta(0,1)
            fetchJson = fetchResult.json()
            dataFromRequests["data"].extend(fetchJson['result'])
            idsTrack.extend([str(d['id']) for d in fetchJson['result']])

        if len(idsTrack) > 400:
            idsTrack = idsTrack[280:]

        if len(dataFromRequests['data']) >= 300:
            with open(f'random-data-{uuid.uuid4()}.json', 'w', encoding='utf-8') as f:
                json.dump(dataFromRequests, f, ensure_ascii=False, indent=4)
            dataFromRequests = {"data": []}
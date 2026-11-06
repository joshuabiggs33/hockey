import os, csv, time, requests
from datetime import datetime, timezone, timedelta

KEY = os.environ.get("ODDSPAPI_KEY")
BASE = "https://api.oddspapi.io/v4"
used = 0

def get(path, **params):
    global used
    params["apiKey"] = KEY
    r = requests.get(BASE + path, params=params, timeout=60)
    used += 1
    time.sleep(10)
    return r

def names_from(fixture_id):
    r = get("/odds", fixtureId=fixture_id, bookmakers="pinnacle")
    print(f"  /odds HTTP {r.status_code}")
    if r.status_code != 200:
        print("  ", r.text[:200])
        return {}
    data = r.json()
    names = {}
    book = data.get("bookmakerOdds", {}).get("pinnacle", {})
    for m in book.get("markets", {}).values():
        for out in m.get("outcomes", {}).values():
            for pid, p in out.get("players", {}).items():
                if pid != "0" and isinstance(p, dict) and p.get("playerName"):
                    names[pid] = p["playerName"]
    return names

saved = set()
with open("data/raw/props.csv", newline="") as f:
    for row in csv.DictReader(f):
        saved.add(row["playerId"])
print("Distinct player IDs in the saved data:", len(saved))

if not KEY:
    print("No API key found.")
else:
    now = datetime.now(timezone.utc)
    day = now.date()
    r = get("/fixtures", sportId=15, **{"from": str(day - timedelta(days=1)), "to": str(day + timedelta(days=2))})
    print("Fixtures HTTP", r.status_code)
    games = [f for f in r.json() if f.get("tournamentName") == "NHL" and f.get("hasOdds")]
    games.sort(key=lambda f: f["startTime"])
    upcoming = [f for f in games if f["startTime"] > now.strftime("%Y-%m-%dT%H:%M")]
    print(f"NHL games with odds: {len(games)}, upcoming: {len(upcoming)}")
    pick = upcoming[0] if upcoming else (games[0] if games else None)
    if pick:
        print(f"\nTest 1, upcoming game: {pick['participant1Name']} vs {pick['participant2Name']} ({pick['startTime']})")
        names = names_from(pick["fixtureId"])
        print(f"  Players with names: {len(names)}")
        print("  Examples:", list(names.items())[:5])
        print(f"  IDs also found in your saved data: {len(set(names) & saved)}")

    with open("data/raw/games_log.csv", newline="") as f:
        first = next(csv.DictReader(f))
    print(f"\nTest 2, finished game: {first['home']} vs {first['away']} ({first['date']})")
    old = names_from(first["fixtureId"])
    print(f"  Players with names: {len(old)}")
    print(f"  IDs also found in your saved data: {len(set(old) & saved)}")
    print(f"\nRequests used in this test: {used}")

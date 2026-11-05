import os, time, requests
from collections import Counter

KEY = os.environ.get("ODDSPAPI_KEY")
BASE = "https://api.oddspapi.io/v4"
BOOKS = "pinnacle,draftkings,fanduel"
PROPS = {"15124": "Goals (anytime)", "15118": "Assists 0.5", "15130": "Points 0.5"}
used = 0

def get(path, **params):
    global used
    params["apiKey"] = KEY
    r = requests.get(BASE + path, params=params, timeout=60)
    used += 1
    time.sleep(1.5)
    return r

def look(label, start, end):
    print(f"\n===== {label}: {start} to {end} =====")
    r = get("/fixtures", sportId=15, **{"from": start, "to": end})
    print(f"HTTP {r.status_code}")
    if r.status_code != 200:
        print(r.text[:300])
        return None
    data = r.json()
    if not isinstance(data, list):
        print("Unexpected response:", str(data)[:300])
        return None
    print(f"Total ice hockey fixtures returned: {len(data)}")
    if data:
        print("Fields available:", sorted(data[0].keys()))
    names = Counter(f.get("tournamentName") for f in data)
    print("Leagues found:", dict(names.most_common(8)))
    nhl = [f for f in data if f.get("tournamentName") == "NHL"]
    with_odds = [f for f in nhl if f.get("hasOdds")]
    print(f"NHL games: {len(nhl)} (flagged as having odds: {len(with_odds)})")
    return nhl[0] if nhl else None

def check_game(g):
    print(f"\nChecking: {g['participant1Name']} vs {g['participant2Name']} ({g['startTime']})")
    r = get("/historical-odds", fixtureId=g["fixtureId"], bookmakers=BOOKS)
    print(f"Historical odds: HTTP {r.status_code}")
    if r.status_code != 200:
        print(r.text[:300])
        return
    books = r.json().get("bookmakers", {})
    if not books:
        print("  No bookmaker data returned")
    for name, book in books.items():
        markets = book.get("markets", {})
        print(f"  {name}: {len(markets)} markets")
        for mid, label in PROPS.items():
            m = markets.get(mid)
            if not m:
                print(f"    {label}: not found")
                continue
            players, snaps = set(), 0
            for out in m.get("outcomes", {}).values():
                for pid, series in out.get("players", {}).items():
                    players.add(pid)
                    if isinstance(series, list):
                        snaps += len(series)
            print(f"    {label}: FOUND - {len(players)} players, {snaps} price snapshots")

if not KEY:
    print("No API key found. Check the secret name ODDSPAPI_KEY.")
else:
    look("THIS WEEK (control)", "2026-11-05", "2026-11-12")
    for label, start, end in [("RECENT", "2026-10-20", "2026-10-29"),
                              ("LAST SEASON", "2025-11-10", "2025-11-19")]:
        game = look(label, start, end)
        if game:
            check_game(game)
    print(f"\nRequests used in this test: {used}")

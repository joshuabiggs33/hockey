import os, time, requests

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

def find_game(start, end):
    r = get("/fixtures", sportId=15, **{"from": start, "to": end})
    print(f"Fixtures {start} to {end}: HTTP {r.status_code}")
    if r.status_code != 200:
        print(r.text[:300])
        return None
    data = r.json()
    if not isinstance(data, list):
        print(str(data)[:300])
        return None
    games = [f for f in data if f.get("tournamentName") == "NHL" and f.get("hasOdds")]
    print(f"  NHL games with odds found: {len(games)}")
    return games[0] if games else None

def check_game(g):
    print(f"\nGame: {g['participant1Name']} vs {g['participant2Name']} ({g['startTime']})")
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
    for label, start, end in [("RECENT", "2026-10-20", "2026-10-29"),
                              ("LAST SEASON", "2025-11-10", "2025-11-19")]:
        print(f"\n===== {label} =====")
        game = find_game(start, end)
        if game:
            check_game(game)
    print(f"\nRequests used in this test: {used}")

import os, time, requests

KEY = os.environ.get("ODDSPAPI_KEY")
BASE = "https://api.oddspapi.io/v4"
BOOKS = "pinnacle,draftkings,fanduel"
PROPS = {"15124": "Goals", "152401": "GoalsAlt", "15118": "Assists",
         "152376": "AssistsAlt", "15130": "Points", "152386": "PointsAlt"}
used = 0

def get(path, **params):
    global used
    params["apiKey"] = KEY
    for attempt in range(2):
        r = requests.get(BASE + path, params=params, timeout=60)
        used += 1
        time.sleep(10)
        if r.status_code != 429:
            break
        print("  (rate limited, waiting 30s and trying once more)")
        time.sleep(30)
    return r

def check_game(g):
    print(f"  Game: {g['participant1Name']} vs {g['participant2Name']} ({g['startTime'][:10]})")
    r = get("/historical-odds", fixtureId=g["fixtureId"], bookmakers=BOOKS)
    if r.status_code != 200:
        print(f"  -> HTTP {r.status_code}: {r.text[:120]}")
        return
    books = r.json().get("bookmakers", {})
    if not books:
        print("  -> no bookmaker data")
    for name, book in books.items():
        markets = book.get("markets", {})
        parts = []
        for mid, label in PROPS.items():
            m = markets.get(mid)
            n = 0
            if m:
                ids = set()
                for out in m.get("outcomes", {}).values():
                    ids.update(out.get("players", {}).keys())
                n = len(ids)
            parts.append(f"{label}={n}")
        print(f"  -> {name}: " + ", ".join(parts))

def window(label, start, end, pick):
    print(f"\n===== {label}: {start} to {end} =====")
    r = get("/fixtures", sportId=15, **{"from": start, "to": end})
    print(f"  Fixtures: HTTP {r.status_code}")
    if r.status_code != 200:
        print(r.text[:200])
        return
    data = r.json()
    nhl = [f for f in data if f.get("tournamentName") == "NHL"] if isinstance(data, list) else []
    print(f"  NHL games found: {len(nhl)}")
    if nhl:
        check_game(nhl[min(pick, len(nhl) - 1)])

if not KEY:
    print("No API key found. Check the secret name ODDSPAPI_KEY.")
else:
    window("FEB 2026", "2026-02-10", "2026-02-19", 5)
    window("JAN 2026", "2026-01-10", "2026-01-19", 5)
    window("DEC 2025", "2025-12-10", "2025-12-19", 0)
    window("NOV 2025", "2025-11-15", "2025-11-24", 0)
    print(f"\nRequests used in this test: {used}")

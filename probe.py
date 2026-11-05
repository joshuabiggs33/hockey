import os, time, requests

KEY = os.environ.get("ODDSPAPI_KEY")
BASE = "https://api.oddspapi.io/v4"
BOOKS = "pinnacle,draftkings,fanduel"
PROPS = {"15124": "Goals", "15118": "Assists", "15130": "Points"}
used = 0

def get(path, **params):
    global used
    params["apiKey"] = KEY
    r = requests.get(BASE + path, params=params, timeout=60)
    used += 1
    time.sleep(1.5)
    return r

def catalog():
    print("\n===== MARKET CATALOG: goal, assist and points markets =====")
    r = get("/markets", sportId=15)
    print(f"HTTP {r.status_code}")
    if r.status_code != 200:
        print(r.text[:300])
        return
    rows = [m for m in r.json() if m.get("sportId") == 15]
    words = ("scorer", "assist", "to score", "points")
    hits = [m for m in rows if any(w in m.get("marketName", "").lower() for w in words)]
    for m in hits[:30]:
        print(f"  {m['marketId']}: {m['marketName']} (hcap={m.get('handicap')})")
    print(f"  ({len(hits)} matching markets in total)")

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

def window(label, start, end):
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
        check_game(nhl[len(nhl) // 2])

if not KEY:
    print("No API key found. Check the secret name ODDSPAPI_KEY.")
else:
    catalog()
    for label, start, end in [("APR 2026", "2026-04-10", "2026-04-19"),
                              ("JAN 2026", "2026-01-10", "2026-01-19"),
                              ("DEC 2025", "2025-12-10", "2025-12-19"),
                              ("NOV 2025", "2025-11-15", "2025-11-24")]:
        window(label, start, end)
    print(f"\nRequests used in this test: {used}")

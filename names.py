import os, csv, time, requests
from datetime import datetime, timezone, timedelta

KEY = os.environ.get("ODDSPAPI_KEY")
MAX_GAMES = int(os.environ.get("MAX_GAMES") or 12)
BASE = "https://api.oddspapi.io/v4"
OUT = "data/raw/players.csv"
PROPS = "data/raw/props.csv"
used = 0

def get(path, **params):
    global used
    params["apiKey"] = KEY
    r = None
    for attempt in range(2):
        r = requests.get(BASE + path, params=params, timeout=60)
        used += 1
        time.sleep(10)
        if r.status_code != 429:
            break
        print("  (rate limited, waiting 30s and trying once more)")
        time.sleep(30)
    return r

if not KEY:
    print("No API key found.")
    raise SystemExit

os.makedirs("data/raw", exist_ok=True)
known = {}
if os.path.exists(OUT):
    with open(OUT, newline="") as f:
        for row in csv.DictReader(f):
            known[row["playerId"]] = row["playerName"]
print("Names already known:", len(known))

now = datetime.now(timezone.utc)
day = now.date()
r = get("/fixtures", sportId=15, **{"from": str(day), "to": str(day + timedelta(days=2))})
print("Fixtures HTTP", r.status_code)
data = r.json() if r.status_code == 200 else []
cut = now.strftime("%Y-%m-%dT%H:%M")
upcoming = [f for f in data if f.get("tournamentName") == "NHL"
            and f.get("hasOdds") and f["startTime"] > cut]
upcoming.sort(key=lambda f: f["startTime"])
print(f"Upcoming NHL games with odds: {len(upcoming)}. Using up to {MAX_GAMES}.")

added = 0
for g in upcoming[:MAX_GAMES]:
    label = f"{g['participant1Name']} vs {g['participant2Name']}"
    r = get("/odds", fixtureId=g["fixtureId"], bookmakers="pinnacle,draftkings,fanduel")
    if r.status_code != 200:
        print(f"  STOPPING at {label}: HTTP {r.status_code} {r.text[:120]}")
        break
    found = 0
    for book in r.json().get("bookmakerOdds", {}).values():
        for m in book.get("markets", {}).values():
            for out in m.get("outcomes", {}).values():
                for pid, p in out.get("players", {}).items():
                    if pid != "0" and isinstance(p, dict) and p.get("playerName"):
                        if pid not in known:
                            known[pid] = p["playerName"]
                            added += 1
                            found += 1
    print(f"  {label}: {found} new names")

with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["playerId", "playerName"])
    for pid, name in sorted(known.items()):
        w.writerow([pid, name])

saved = set()
if os.path.exists(PROPS):
    with open(PROPS, newline="") as f:
        for row in csv.DictReader(f):
            saved.add(row["playerId"])
covered = len(saved & set(known))
print(f"\nAdded {added} names. Total known: {len(known)}.")
print(f"Player IDs in your odds data with a name: {covered} of {len(saved)}")
print(f"Requests used in this run: {used}")

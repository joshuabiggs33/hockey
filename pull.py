import os, csv, time, requests
from datetime import datetime, timedelta, timezone

KEY = os.environ.get("ODDSPAPI_KEY")
MAX_GAMES = int(os.environ.get("MAX_GAMES") or 50)
BASE = "https://api.oddspapi.io/v4"
BOOKS = "pinnacle,draftkings,fanduel"
MARKETS = {"15124", "152401", "15118", "152376", "15130", "152386"}
OUT = "data/raw"
ROWS = OUT + "/props.csv"
LOG = OUT + "/games_log.csv"
WINDOWS = [("2026-10-27", "2026-11-04"), ("2026-10-17", "2026-10-26"), ("2026-10-07", "2026-10-16")]
used = 0
shown_shape = False

def parse(ts):
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None

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

def extract(g, data):
    global shown_shape
    start = parse(g["startTime"])
    t3 = start - timedelta(hours=3)
    rows = []
    for book, b in data.get("bookmakers", {}).items():
        for mid, m in b.get("markets", {}).items():
            if mid not in MARKETS:
                continue
            for oid, out in m.get("outcomes", {}).items():
                for pid, series in out.get("players", {}).items():
                    if not isinstance(series, list) or not series:
                        continue
                    if not shown_shape:
                        print("  Example snapshot fields:", sorted(series[0].keys()))
                        shown_shape = True
                    snaps = []
                    for s in series:
                        t = parse(s.get("createdAt", ""))
                        if t is None or s.get("price") is None:
                            continue
                        snaps.append((t, s["price"], s.get("playerName")))
                    snaps.sort(key=lambda x: x[0])
                    before3 = [x for x in snaps if x[0] <= t3]
                    beforeS = [x for x in snaps if x[0] <= start]
                    name = next((x[2] for x in snaps if x[2]), "")
                    rows.append([
                        g["fixtureId"], g["startTime"][:10],
                        g["participant1Name"], g["participant2Name"],
                        book, mid, oid, pid, name,
                        before3[-1][1] if before3 else "",
                        beforeS[-1][1] if beforeS else "",
                        len(snaps),
                    ])
    return rows

if not KEY:
    print("No API key found. Check the secret name ODDSPAPI_KEY.")
    raise SystemExit

os.makedirs(OUT, exist_ok=True)
done = set()
if os.path.exists(LOG):
    with open(LOG, newline="") as f:
        done = {r["fixtureId"] for r in csv.DictReader(f)}
print(f"Games already finished in earlier runs: {len(done)}")

cutoff = datetime.now(timezone.utc) - timedelta(hours=5)
candidates = []
for start, end in WINDOWS:
    r = get("/fixtures", sportId=15, **{"from": start, "to": end})
    print(f"Fixtures {start} to {end}: HTTP {r.status_code}")
    if r.status_code != 200:
        print(r.text[:200])
        continue
    data = r.json()
    if not isinstance(data, list):
        continue
    for f in data:
        if f.get("tournamentName") != "NHL" or f["fixtureId"] in done:
            continue
        st = parse(f["startTime"])
        if st and st < cutoff:
            candidates.append(f)

candidates.sort(key=lambda f: f["startTime"], reverse=True)
batch = candidates[:MAX_GAMES]
print(f"Games left to pull: {len(candidates)}. This run: {len(batch)}")

new_rows = not os.path.exists(ROWS)
new_log = not os.path.exists(LOG)
pf = open(ROWS, "a", newline="")
lf = open(LOG, "a", newline="")
pw, lw = csv.writer(pf), csv.writer(lf)
if new_rows:
    pw.writerow(["fixtureId", "date", "home", "away", "book", "marketId", "outcomeId",
                 "playerId", "playerName", "price_3h_before", "price_close", "snapshots"])
if new_log:
    lw.writerow(["fixtureId", "date", "home", "away", "status", "rows"])

total_rows, ok, nodata = 0, 0, 0
for g in batch:
    r = get("/historical-odds", fixtureId=g["fixtureId"], bookmakers=BOOKS)
    label = f"{g['participant1Name']} vs {g['participant2Name']} ({g['startTime'][:10]})"
    if r.status_code == 200:
        rows = extract(g, r.json())
        pw.writerows(rows)
        lw.writerow([g["fixtureId"], g["startTime"][:10], g["participant1Name"],
                     g["participant2Name"], "ok", len(rows)])
        total_rows += len(rows)
        ok += 1
        print(f"  OK  {label}: {len(rows)} rows")
    elif r.status_code == 404:
        lw.writerow([g["fixtureId"], g["startTime"][:10], g["participant1Name"],
                     g["participant2Name"], "no_data", 0])
        nodata += 1
        print(f"  none {label}")
    else:
        print(f"  STOPPING at {label}: HTTP {r.status_code} {r.text[:150]}")
        break
    pf.flush()
    lf.flush()

pf.close()
lf.close()
print(f"\nSaved {total_rows} rows from {ok} games ({nodata} games had no data).")
print(f"Requests used in this run: {used}")

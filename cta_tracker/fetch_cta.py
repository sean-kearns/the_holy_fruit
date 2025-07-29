
#!/usr/bin/env python3
import os
import logging
import requests
from datetime import datetime, timezone 
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from dateutil import parser as date_parser

# ───── Load environment variables from parent .env ─────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(BASE_DIR, os.pardir))
load_dotenv(os.path.join(PARENT_DIR, ".env"))

CTA_API_KEY = os.getenv("CTA_API_KEY")
STOP_ID     = os.getenv("STOP_ID")

if not CTA_API_KEY or not STOP_ID:
    raise RuntimeError("Missing CTA_API_KEY or STOP_ID in .env")

# ───── Configure logging ─────
LOG_FILE = os.path.join(BASE_DIR, "fetch_cta.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# ───── Fetch function ─────

def get_cta_train_times(api_key, stop_id):
    url = "http://lapi.transitchicago.com/api/1.0/ttarrivals.aspx"
    params = {
        "key": api_key,
        "mapid": stop_id,
        "outputType": "JSON"
    }
    logging.info(f"Requesting {url} with {params}")
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("ctatt", {})
    arrivals = data.get("eta", [])
    times = []
    local_tz = ZoneInfo("America/Chicago")
    now_local = datetime.now(local_tz)
    for arrival in arrivals:
        arr_time_str = arrival.get("arrT")
        arr_dt = date_parser.parse(arr_time_str)
        # If arr_dt is naive, assume UTC or local timezone
        if arr_dt.tzinfo is None:
            arr_dt = arr_dt.replace(tzinfo=local_tz)
        delta = arr_dt - now_local
        total_seconds = int(delta.total_seconds())
        if total_seconds < 0:
            total_seconds = 0
        mins, secs = divmod(total_seconds, 60)
        times.append({
            "route":          arrival.get("rt"),
            "destination":    arrival.get("destNm"),
            "arrival_time":   arr_dt.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            "minutes_away":   mins,
            "seconds_away":   secs,
            "time_remaining": f"{mins}m {secs}s"
        })
    logging.info(f"Fetched {len(times)} arrival entries")
    return times

# ───── HTML writer with styling ─────

def write_html(train_times, refresh_interval=2):
    local_tz = ZoneInfo("America/Chicago")
    now_local = datetime.now(local_tz).strftime("%Y-%m-%d %H:%M:%S %Z")
    rows = "\n".join(
        f"<tr>"
        f"<td>{t['route']}</td>"
        f"<td>{t['destination']}</td>"
        f"<td>{t['arrival_time']}</td>"
        f"<td>{t['time_remaining']}</td>"
        f"</tr>"
        for t in train_times
    ) or "<tr><td colspan=4>No data</td></tr>"

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
    <meta http-equiv=\"refresh\" content=\"{refresh_interval}\"> <!-- auto-refresh every {refresh_interval}s -->
  <title>Chicago Brown Line Stop</title>
  <style>
    body {{ background-color: #3e2723; color: #d7ccc8; font-family: sans-serif; margin: 0; padding: 1rem; }}
    h1 {{ color: #ffcc80; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
    th, td {{ padding: 0.5rem; border: 1px solid #5d4037; text-align: left; }}
    th {{ background-color: #5d4037; color: #ffe0b2; }}
    tr:nth-child(even) {{ background-color: #4e342e; }}
  </style>
</head>
<body>
  <h1>Chicago Brown Line - Stop {STOP_ID}</h1>
  <p>Last updated: {now_local}</p>
  <table>
    <thead>
      <tr>
        <th>Route</th><th>Destination</th><th>ETA</th><th>Time Remaining</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</body>
</html>
"""
    www_dir = os.path.join(BASE_DIR, "www")
    os.makedirs(www_dir, exist_ok=True)
    out_path = os.path.join(www_dir, "index.html")
    with open(out_path, "w") as f:
        f.write(html)
    logging.info(f"Wrote {len(train_times)} rows to {out_path}")

# ───── Entrypoint ─────
if __name__ == "__main__":
    trains = get_cta_train_times(CTA_API_KEY, STOP_ID)
    write_html(trains)





# Rocket Watch PCC — LancerHacks 2026 (theme: SPACE!)
# Built at the event, 2026-10-30, by Ahmed's team with AI assistance (allowed per event rules).
# Data: Launch Library 2 API by The Space Devs (free). We save the answer to a file
# and only ask again every 10 minutes, because the API limits how often you may call it.

import json
import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import streamlit as st

# ----- settings -------------------------------------------------------------
API_URL = "https://ll.thespacedevs.com/2.2.0/launch/upcoming/?limit=10&location__ids=11"
CACHE_FILE = Path(__file__).parent / "launches.json"
PREV_API_URL = "https://ll.thespacedevs.com/2.2.0/launch/previous/?limit=4&location__ids=11"
PREV_CACHE_FILE = Path(__file__).parent / "previous_launches.json"
CACHE_MINUTES = 10          # how long we trust the saved file before asking again
PACIFIC = ZoneInfo("America/Los_Angeles")

# Vandenberg Space Force Base, seen from Pasadena City College:
# computed with the standard compass-bearing formula -> 287 degrees = west-northwest, 235 km away.
LOOK_DIRECTION = "West-northwest (compass 287°)"
DISTANCE_KM = 235

st.set_page_config(page_title="Rocket Watch PCC", page_icon="🚀", layout="centered")

# ----- look & feel ----------------------------------------------------------
# A starfield drawn in pure CSS (no image file, nothing to license).
# The team may later swap in a NASA photo (public domain, credit NASA).
st.markdown("""
<style>
.stApp {
  background:
    radial-gradient(1.5px 1.5px at 25px 35px,  #ffffff, transparent),
    radial-gradient(1px   1px   at 120px 90px, #cfd8ff, transparent),
    radial-gradient(1.5px 1.5px at 210px 160px,#ffffff, transparent),
    radial-gradient(1px   1px   at 60px 140px, #9fb4ff, transparent),
    radial-gradient(1px   1px   at 170px 40px, #ffffff, transparent),
    linear-gradient(180deg, #04060f 0%, #0b1030 55%, #1a1448 100%);
  background-size: 250px 250px, 250px 250px, 250px 250px, 250px 250px, 250px 250px, 100% 100%;
}
h1 {
  background: linear-gradient(90deg, #7dd3fc, #c084fc);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.countdown {
  font-family: 'Courier New', monospace;
  font-size: 72px;
  font-weight: bold;
  text-align: center;
  color: #7dd3fc;
  text-shadow: 0 0 18px rgba(125, 211, 252, 0.6);
  margin: 0.2em 0;
}
.countdown-label {
  text-align: center;
  color: #9fb4ff;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  font-size: 14px;
}
#MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ----- data -----------------------------------------------------------------
def get_launches():
    """Return the list of upcoming Vandenberg launches.

    1. If the saved file is younger than CACHE_MINUTES, use it (be nice to the API).
    2. Otherwise ask the API once and save the answer.
    3. If the internet fails, fall back to the saved file so the demo never dies.
    """
    now = datetime.datetime.now(datetime.timezone.utc)

    if CACHE_FILE.exists():
        saved = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        fetched_at = datetime.datetime.fromisoformat(saved["fetched_at"])
        age_minutes = (now - fetched_at).total_seconds() / 60
        if age_minutes < CACHE_MINUTES:
            return saved["results"], fetched_at

    try:
        answer = requests.get(API_URL, timeout=10)
        answer.raise_for_status()
        results = answer.json()["results"]
        CACHE_FILE.write_text(
            json.dumps({"fetched_at": now.isoformat(), "results": results}, indent=2),
            encoding="utf-8",
        )
        return results, now
    except Exception:
        # No internet or API said no — use whatever we saved last time.
        if CACHE_FILE.exists():
            saved = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            return saved["results"], datetime.datetime.fromisoformat(saved["fetched_at"])
        return [], now


def get_previous_launches():
    """Return the last few Vandenberg launches (our proof the tracker works).

    Same manners as get_launches(): trust the saved file for CACHE_MINUTES,
    ask the API once when it is stale, and fall back to the file if the
    internet fails so the demo never dies.
    """
    now = datetime.datetime.now(datetime.timezone.utc)

    if PREV_CACHE_FILE.exists():
        saved = json.loads(PREV_CACHE_FILE.read_text(encoding="utf-8"))
        fetched_at = datetime.datetime.fromisoformat(saved["fetched_at"])
        age_minutes = (now - fetched_at).total_seconds() / 60
        if age_minutes < CACHE_MINUTES:
            return saved["results"]

    try:
        answer = requests.get(PREV_API_URL, timeout=10)
        answer.raise_for_status()
        results = answer.json()["results"]
        PREV_CACHE_FILE.write_text(
            json.dumps({"fetched_at": now.isoformat(), "results": results}, indent=2),
            encoding="utf-8",
        )
        return results
    except Exception:
        if PREV_CACHE_FILE.exists():
            saved = json.loads(PREV_CACHE_FILE.read_text(encoding="utf-8"))
            return saved["results"]
        return []


def launch_time(launch):
    """The launch's planned time as a Python datetime (UTC)."""
    return datetime.datetime.fromisoformat(launch["net"].replace("Z", "+00:00"))


# ----- page -----------------------------------------------------------------
st.title("🚀 Rocket Watch PCC")
st.caption("Real rockets launch 235 km from this campus. This page tells you when and where to look.")

launches, fetched_at = get_launches()

if not launches:
    st.error("No launch data yet — check the wifi and reload once.")
    st.stop()

# Launches come sorted by time; the first one still in the future is "next".
now_utc = datetime.datetime.now(datetime.timezone.utc)
future = [l for l in launches if launch_time(l) > now_utc]

if not future:
    st.warning("No upcoming launches listed right now at Vandenberg.")
    st.stop()

next_launch = future[0]
t_launch = launch_time(next_launch)
t_local = t_launch.astimezone(PACIFIC)


# The countdown lives in a "fragment": Streamlit re-runs just this part every second,
# so the numbers tick live without reloading the whole page.
@st.fragment(run_every=1)
def countdown():
    remaining = launch_time(next_launch) - datetime.datetime.now(datetime.timezone.utc)
    total = int(remaining.total_seconds())
    if total <= 0:
        st.success("LIFTOFF window reached! 🎉 Look west-northwest!")
        return
    hours, rest = divmod(total, 3600)
    minutes, seconds = divmod(rest, 60)
    st.markdown("<div class='countdown-label'>T-minus</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='countdown'>{hours:02d} : {minutes:02d} : {seconds:02d}</div>",
        unsafe_allow_html=True,
    )


st.header(next_launch["name"])
st.write(f"**Launch time:** {t_local.strftime('%A %B %d, %I:%M:%S %p')} Pacific")
countdown()

col1, col2, col3 = st.columns(3)
col1.metric("Where to look from PCC", "WNW ↖")
col2.metric("Compass bearing", "287°")
col3.metric("Distance", f"{DISTANCE_KM} km")

st.write(
    "🌙 Night launches from Vandenberg are often visible across Southern California, "
    "weather permitting — look for a bright moving light climbing from the "
    "west-northwest horizon in the minutes after liftoff."
)

st.info(
    "Launch times change often — this page re-checks the schedule every "
    f"{CACHE_MINUTES} minutes. Data: Launch Library 2 API by The Space Devs."
)

# ----- the rest of the schedule ---------------------------------------------
st.subheader("Upcoming Vandenberg launches")
for launch in future[1:6]:
    t = launch_time(launch).astimezone(PACIFIC)
    st.write(f"• **{t.strftime('%b %d, %I:%M %p')}** — {launch['name']}")

# ----- proof it works: launches we already tracked ----------------------------
st.subheader("Recent launches — proof it works")
st.caption("The same tracker, pointed backwards: the last real launches from Vandenberg.")
for launch in get_previous_launches():
    t = launch_time(launch).astimezone(PACIFIC)
    status = launch.get("status", {}).get("name", "Unknown")
    badge = "✅" if "success" in status.lower() else "⚠️"
    st.write(f"{badge} **{t.strftime('%b %d, %I:%M %p')}** — {launch['name']} — {status}")

st.caption(
    f"Schedule last refreshed {fetched_at.astimezone(PACIFIC).strftime('%I:%M %p')} Pacific. "
    "Built during LancerHacks 2026 with AI assistance (allowed by event rules)."
)

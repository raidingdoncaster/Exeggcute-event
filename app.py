from flask import Flask, request, render_template
import urllib.parse
import requests
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

def fetch_event_details(event_link: str):
    """
    Uses the campfire-tools.topi.wtf API to fetch event details.
    Works with cmpf.re short links, UUIDs, or full Campfire URLs.
    """
    api_url = "https://campfire-tools.topi.wtf/api/events"
    resp = requests.get(api_url, params={"events": event_link}, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if not data:
        raise ValueError("No event data returned from API")

    event = data[0]

    # Title/description
    title = event.get("campfire_live_event_name") or event.get("name", "Campfire Event")
    description = event.get("name", "")

    # Location (API doesn’t always give full address, fallback to event URL)
    location = event.get("url", "")

    # Time (API gives ISO8601 start time, but no explicit end time)
    start_str = event.get("time")
    if not start_str:
        raise ValueError("No time data in API response")

    start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))

    # Assume events last 1 hour if no explicit end time
    end = start + timedelta(hours=1)

    # Convert to Europe/London timezone
    tz = pytz.timezone("Europe/London")
    dt_start = start.astimezone(tz)
    dt_end = end.astimezone(tz)

    return title, description, location, dt_start, dt_end

def build_gcal_link(title, description, location, dt_start, dt_end):
    def format_dt(dt: datetime) -> str:
        utc = dt.astimezone(pytz.utc)
        return utc.strftime("%Y%m%dT%H%M%SZ")

    params = {
        "action": "TEMPLATE",
        "text": title,
        "details": description,
        "location": location,
        "dates": f"{format_dt(dt_start)}/{format_dt(dt_end)}",
    }
    return "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode(params)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        if not url:
            return render_template("index.html", error="Please provide a Campfire link.")
        try:
            title, description, location, start_dt, end_dt = fetch_event_details(url)
            gcal_link = build_gcal_link(title, description or url, location, start_dt, end_dt)
            return render_template(
                "result.html",
                title=title,
                start=start_dt.strftime("%a %d %b %Y, %H:%M"),
                end=end_dt.strftime("%a %d %b %Y, %H:%M"),
                location=location,
                description=description,
                link=gcal_link,
            )
        except Exception as exc:
            return render_template("index.html", error=f"Couldn’t process link: {exc}")
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

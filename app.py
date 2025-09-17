from flask import Flask, request, render_template, redirect, url_for
import urllib.parse
import requests
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# -----------------------------
# Single Event Converter
# -----------------------------
def fetch_event_details(event_link: str):
    api_url = "https://campfire-tools.topi.wtf/api/events"
    resp = requests.get(api_url, params={"events": event_link}, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if not data:
        raise ValueError("No event data returned from API")

    event = data[0]

    title = event.get("campfire_live_event_name") or event.get("name", "Campfire Event")
    description = event.get("name", "")
    location = event.get("url", "")

    start_str = event.get("time")
    if not start_str:
        raise ValueError("No time data in API response")

    start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
    end = start + timedelta(hours=1)

    tz = pytz.timezone("Europe/London")
    dt_start = start.astimezone(tz)
    dt_end = end.astimezone(tz)

    return title, description, location, dt_start, dt_end, event


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
            title, description, location, start_dt, end_dt, event = fetch_event_details(url)
            gcal_link = build_gcal_link(title, description or url, location, start_dt, end_dt)

            # 🔑 If user ticked "See all club events", redirect to pinboard
            if request.form.get("view_club"):
                club_id = event.get("club_id")
                if club_id:
                    return redirect(url_for("club_events", club_id=club_id))
                else:
                    return render_template("index.html", error="Could not find club ID for this event.")

            # Otherwise show single event result
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


# -----------------------------
# Club Events Pinboard
# -----------------------------
@app.route("/club/<club_id>")
def club_events(club_id):
    try:
        api_url = f"https://campfire-tools.topi.wtf/api/clubs/{club_id}/events"
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
        events = resp.json()

        events.sort(key=lambda e: e.get("time", ""))

        tz = pytz.timezone("Europe/London")
        for e in events:
            if e.get("time"):
                dt = datetime.fromisoformat(e["time"].replace("Z", "+00:00")).astimezone(tz)
                e["time_fmt"] = dt.strftime("%a %d %b %Y, %H:%M")
            else:
                e["time_fmt"] = "Unknown time"

        return render_template("club_events.html", events=events, club_id=club_id)

    except Exception as exc:
        return f"Error fetching events: {exc}", 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

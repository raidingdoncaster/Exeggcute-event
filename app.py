from flask import Flask, request, render_template, redirect, url_for
import requests
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        club_id = request.form.get("club_id", "").strip()
        if not club_id:
            return render_template("index.html", error="Please provide a Club ID.")
        return redirect(url_for("club_events", club_id=club_id))
    return render_template("index.html")


@app.route("/club/<club_id>")
def club_events(club_id):
    try:
        api_url = f"https://campfire-tools.topi.wtf/api/clubs/{club_id}/events"
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
        events = resp.json()

        # Sort by time
        events.sort(key=lambda e: e.get("time", ""))

        # Format times + Google Calendar links
        tz = pytz.timezone("Europe/London")
        for e in events:
            if e.get("time"):
                start = datetime.fromisoformat(e["time"].replace("Z", "+00:00")).astimezone(tz)
                end = start + timedelta(hours=1)

                e["time_fmt"] = start.strftime("%a %d %b %Y, %H:%M")

                # Google Calendar link
                start_utc = start.astimezone(pytz.utc).strftime("%Y%m%dT%H%M%SZ")
                end_utc = end.astimezone(pytz.utc).strftime("%Y%m%dT%H%M%SZ")
                e["gcal_link"] = (
                    "https://calendar.google.com/calendar/render?"
                    f"action=TEMPLATE&text={e.get('campfire_live_event_name') or e.get('name')}"
                    f"&details={e.get('name','')}"
                    f"&location={e.get('url','')}"
                    f"&dates={start_utc}/{end_utc}"
                )
            else:
                e["time_fmt"] = "Unknown time"
                e["gcal_link"] = None

        return render_template("club_events.html", events=events, club_id=club_id)

    except Exception as exc:
        return f"Error fetching events: {exc}", 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

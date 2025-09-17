from flask import Flask, request, render_template
import urllib.parse
import requests
from datetime import datetime
import pytz

app = Flask(__name__)

def fetch_event_details(cmpf_url: str):
    # 1. Follow redirect to get the long URL
    resp = requests.get(cmpf_url, allow_redirects=True, timeout=10)
    resp.raise_for_status()
    final_url = resp.url  # e.g. https://niantic-social.nianticlabs.com/public/meetup/<UUID>

    # 2. Extract UUID
    if "/meetup/" not in final_url:
        raise ValueError("Not a valid Campfire meetup link")
    uuid = final_url.split("/meetup/")[-1]

    # 3. Hit Niantic’s API (public JSON)
    api_url = f"https://niantic-social.nianticlabs.com/api/meetup/{uuid}"
    api_resp = requests.get(api_url, timeout=10)
    api_resp.raise_for_status()
    data = api_resp.json()

    # 4. Extract fields
    title = data.get("title", "Campfire Event")
    description = data.get("description", "")
    location = data.get("location", {}).get("name", "")
    start_str = data.get("startTime")  # ISO8601 e.g. "2025-09-17T09:00:00Z"
    end_str = data.get("endTime")

    # Parse times into datetime
    tz = pytz.timezone("Europe/London")
    dt_start = datetime.fromisoformat(start_str.replace("Z", "+00:00")).astimezone(tz)
    dt_end = datetime.fromisoformat(end_str.replace("Z", "+00:00")).astimezone(tz)

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
            gcal_link = build_gcal_link(title, description, location, start_dt, end_dt)
            return render_template(
                "result.html",
                title=title,
                start=start_dt,
                end=end_dt,
                location=location,
                description=description,
                link=gcal_link,
            )
        except Exception as exc:
            return render_template("index.html", error=f"Couldn’t process link: {exc}")
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

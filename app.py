from flask import Flask, render_template, request
import requests
from urllib.parse import urlparse
from datetime import datetime
import pytz

app = Flask(__name__)

def extract_event_id(url: str) -> str:
    """
    Extract the event identifier from a Campfire or cmpf.re link.
    For cmpf.re, we just return the short token — the API import step will handle it.
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    # If it's a Campfire meetup link, extract the UUID
    if "meetup" in path:
        return path.split("/")[-1]

    # Otherwise return the token (cmpf.re shortlink, etc.)
    return path

@app.route("/", methods=["GET", "POST"])
def index():
    event_data = None
    error = None

    if request.method == "POST":
        url = request.form.get("url")
        try:
            event_id = extract_event_id(url)

            # Step 1: Import the event into Topi's system
            import_url = "https://campfire-tools.topi.wtf/api/events"
            resp_import = requests.post(import_url, json=[event_id], timeout=10)
            if resp_import.status_code not in (200, 204):
                raise Exception(f"Import failed with status {resp_import.status_code}")

            # Step 2: Fetch the event details
            api_url = f"https://campfire-tools.topi.wtf/api/events?events={event_id}"
            resp = requests.get(api_url, timeout=10)
            resp.raise_for_status()
            events = resp.json()

            if events:
                event = events[0]

                # Count attendees
                going_count = sum(
                    1 for m in event.get("members", [])
                    if m.get("rsvp_status") in ["ACCEPTED", "CHECKED_IN"]
                )

                # Format time
                start_str = event.get("time")
                dt_fmt = "Unknown time"
                if start_str:
                    tz = pytz.timezone("Europe/London")
                    dt = datetime.fromisoformat(start_str.replace("Z", "+00:00")).astimezone(tz)
                    dt_fmt = dt.strftime("%a %d %b %Y, %H:%M")

                # Build description
                description = event.get("campfire_live_event_name", "")
                if event.get("name") and event.get("name") != description:
                    description += f" — {event.get('name')}"
                description += f"\n\n🙋 Going: {going_count}"

                # Event photo (if available)
                photo_url = event.get("image") or ""

                # Package event data for template
                event_data = {
                    "title": event.get("name"),
                    "time_fmt": dt_fmt,
                    "location": event.get("location", "Unknown location"),
                    "description": description.strip(),
                    "going": going_count,
                    "photo": photo_url,
                    "url": event.get("url"),
                    "live_event": event.get("campfire_live_event_name", "N/A"),
                }
            else:
                error = "No event data found."

        except Exception as e:
            error = f"Couldn't process link: {str(e)}"

    return render_template("index.html", event=event_data, error=error)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

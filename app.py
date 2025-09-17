from flask import Flask, render_template, request
import requests
from urllib.parse import urlparse

app = Flask(__name__)

def extract_event_id(url: str) -> str:
    """
    Extract the event ID from a Campfire or cmpf.re URL.
    Works with shortlinks like https://cmpf.re/XXXXXX or
    full Campfire links like https://campfire.nianticlabs.com/discover/meetup/<id>.
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    # If the path looks like meetup/<uuid>
    if "meetup" in path:
        return path.split("/")[-1]

    # Otherwise assume it's already the short ID (cmpf.re redirects)
    return path

@app.route("/", methods=["GET", "POST"])
def index():
    event_data = None
    error = None

    if request.method == "POST":
        url = request.form.get("url")
        try:
            event_id = extract_event_id(url)
            api_url = f"https://campfire-tools.topi.wtf/api/events?events={event_id}"
            resp = requests.get(api_url)
            resp.raise_for_status()
            events = resp.json()

            if events:
                event = events[0]

                # Count RSVP’d attendees (Accepted or Checked-in)
                going_count = sum(
                    1 for m in event.get("members", [])
                    if m.get("rsvp_status") in ["ACCEPTED", "CHECKED_IN"]
                )

                # Prepare data for the template
                event_data = {
                    "title": event.get("name"),
                    "time": event.get("time"),
                    "url": event.get("url"),
                    "live_event": event.get("campfire_live_event_name", "N/A"),
                    "going": going_count,
                    "location": event.get("location", "Unknown location"),
                }
            else:
                error = "No event data found."

        except Exception as e:
            error = f"Couldn't process link: {str(e)}"

    return render_template("index.html", event=event_data, error=error)

if __name__ == "__main__":
    app.run(debug=True)

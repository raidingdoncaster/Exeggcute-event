from flask import Flask, render_template, request
import requests
import re

app = Flask(__name__)

API_BASE = "https://campfire-tools.topi.wtf/api/events"

def extract_event_id(url):
    """
    Resolve cmpf.re short links and extract the UUID event ID
    from a Campfire URL.
    """
    try:
        # Follow redirects if it's a cmpf.re short link
        resp = requests.get(url, allow_redirects=True, timeout=10)
        final_url = resp.url
    except Exception as e:
        raise ValueError(f"Failed to resolve link: {e}")

    # Match UUID in the final Campfire URL
    match = re.search(r"([0-9a-fA-F-]{36})", final_url)
    if not match:
        raise ValueError("Could not extract event ID from link")
    
    return match.group(1)

@app.route("/", methods=["GET", "POST"])
def index():
    event_data = None
    error = None

    if request.method == "POST":
        link = request.form.get("link", "").strip()
        if not link:
            error = "Please provide a link."
        else:
            try:
                # Get the UUID
                event_id = extract_event_id(link)

                # Query the API
                api_url = f"{API_BASE}?events={event_id}"
                resp = requests.get(api_url, timeout=10)
                resp.raise_for_status()

                data = resp.json()
                if not data:
                    error = "No event data found."
                else:
                    # Grab the first event object
                    event_data = data[0]

            except Exception as e:
                error = f"Couldn't process link: {e}"

    return render_template("index.html", event=event_data, error=error)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

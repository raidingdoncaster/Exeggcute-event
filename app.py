from flask import Flask, request, render_template
import urllib.parse
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import pytz

app = Flask(__name__)

def extract_event_details(page_html: str):
    soup = BeautifulSoup(page_html, "html.parser")

    # ---- Title ----
    title_tag = soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else "Campfire Event"

    # ---- Description (optional) ----
    description = ""
    if title_tag:
        desc_tag = title_tag.find_next("p")
        if desc_tag:
            description = desc_tag.get_text(strip=True)

    html = str(soup)

    # ---- Extract time/date ----
    # Looks like: Sep 17, 2025 10:00 AM – 11:00 AM
    time_match = re.search(r"([A-Z][a-z]{2} \d{1,2}, \d{4} \d{1,2}:\d{2} [AP]M)\s*[–-]\s*(\d{1,2}:\d{2} [AP]M)", html)
    if not time_match:
        raise ValueError("Could not parse date/time from page")

    start_str = time_match.group(1)       # "Sep 17, 2025 10:00 AM"
    end_time_str = time_match.group(2)    # "11:00 AM"
    date_str = " ".join(start_str.split()[0:3])  # "Sep 17, 2025"

    dt_start = datetime.strptime(start_str, "%b %d, %Y %I:%M %p")
    dt_end = datetime.strptime(f"{date_str} {end_time_str}", "%b %d, %Y %I:%M %p")

    tz = pytz.timezone("Europe/London")
    dt_start = tz.localize(dt_start)
    dt_end = tz.localize(dt_end)

    # ---- Location ----
    location = ""
    for div in soup.find_all("div"):
        text = div.get_text(" ", strip=True)
        if "," in text and "United" in text:
            location = text
            break

    return title, location, description, dt_start, dt_end

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
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            title, location, description, start_dt, end_dt = extract_event_details(resp.text)
            gcal_link = build_gcal_link(title, description or url, location, start_dt, end_dt)
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

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
    title_tag = soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else "Campfire Event"
    description = ""
    desc_tag = title_tag.find_next("p") if title_tag else None
    if desc_tag:
        description = desc_tag.get_text(strip=True)

    html = str(soup)
    date_match = re.search(r"Start:\s*([A-Z][a-z]{2}\s\d{1,2},\s\d{4})\s*(\d{1,2}:\d{2}\s[AP]M)", html)
    time_range_match = re.search(r"(\d{1,2}:\d{2}\s[AP]M)\s*[–-]\s*(\d{1,2}:\d{2}\s[AP]M)", html)
    if not date_match or not time_range_match:
        raise ValueError("Could not parse date/time from page")

    date_str = date_match.group(1)
    start_time_str = time_range_match.group(1)
    end_time_str = time_range_match.group(2)

    dt_start = datetime.strptime(f"{date_str} {start_time_str}", "%b %d, %Y %I:%M %p")
    dt_end = datetime.strptime(f"{date_str} {end_time_str}", "%b %d, %Y %I:%M %p")
    tz = pytz.timezone("Europe/London")
    dt_start = tz.localize(dt_start)
    dt_end = tz.localize(dt_end)

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
            return render_template("result.html",
                                   title=title,
                                   start=start_dt,
                                   end=end_dt,
                                   location=location,
                                   description=description,
                                   link=gcal_link)
        except Exception as exc:
            return render_template("index.html", error=f"Error: {exc}")
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

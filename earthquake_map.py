"""
Interactive Earthquake Map
---------------------------
Fetches recent earthquake data from the USGS (US Geological Survey) API
and plots it on an interactive map using folium. Marker size and color
scale with earthquake magnitude. Open the resulting HTML file in any
web browser to explore it.
"""

# --- Imports ---------------------------------------------------------------
# 'requests' lets us make HTTP calls to the USGS API and get data back.
import requests

# 'folium' builds interactive Leaflet.js maps and saves them as HTML.
import folium

# 'datetime' helps us compute date ranges (e.g. "the last 30 days")
# without the user having to type exact dates every time.
from datetime import date, timedelta, datetime, timezone

# 'os' lets us build a file path that's always next to this script,
# regardless of what folder you happen to run it from.
import os


# --- 1. CONFIGURATION: the date range filter --------------------------------
# This is the "simple date range filter" - just edit these two lines to
# change which earthquakes get pulled in. Dates must be "YYYY-MM-DD".
#
# By default we compute "today" and "30 days ago" automatically, so the
# script always shows a rolling recent window without you having to edit it.
END_DATE = date.today()
START_DATE = END_DATE - timedelta(days=30)

# Only fetch earthquakes at or above this magnitude, to avoid the map being
# cluttered with thousands of tiny, barely-felt tremors. Lower this to see
# more (smaller) earthquakes, raise it to see only the big ones.
MIN_MAGNITUDE = 2.5


# --- 2. FETCHING DATA FROM THE USGS API -------------------------------------
def fetch_earthquakes(start_date, end_date, min_magnitude):
    """
    Calls the USGS Earthquake API and returns the raw earthquake data
    as a Python dictionary (parsed from JSON).

    The API endpoint below is a "GeoJSON feed" - it returns geographic
    data (coordinates) plus properties (magnitude, place, time, etc.)
    for every earthquake matching our search filters.
    """
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"

    # 'params' is a dictionary of query-string filters. The 'requests'
    # library automatically turns this into "?format=geojson&starttime=...".
    params = {
        "format": "geojson",
        "starttime": start_date.isoformat(),   # e.g. "2026-06-28"
        "endtime": end_date.isoformat(),
        "minmagnitude": min_magnitude,
        "orderby": "time",
    }

    response = requests.get(url, params=params, timeout=30)

    # If the API returned an error status code (like 404 or 500), this
    # raises an exception instead of silently continuing with bad data.
    response.raise_for_status()

    # .json() parses the response body's JSON text into Python
    # dictionaries and lists we can work with directly.
    return response.json()


# --- 3. STYLING HELPERS: color and size based on magnitude -----------------
def magnitude_to_color(magnitude):
    """
    Returns a color name based on how strong the earthquake was.
    This gives a quick visual cue: green = minor, red = major.
    """
    if magnitude < 3:
        return "green"
    elif magnitude < 4:
        return "yellow"
    elif magnitude < 5:
        return "orange"
    else:
        return "red"


def magnitude_to_radius(magnitude):
    """
    Returns a marker radius (in pixels) that scales with magnitude,
    so bigger earthquakes appear as bigger circles on the map.

    We use max(magnitude, 0) to guard against any negative magnitude
    values (which can occur for very tiny seismic events) so the
    radius never comes out negative or zero.
    """
    return max(magnitude, 0) * 4 + 3


# --- 4. BUILDING THE MAP -----------------------------------------------------
def build_map(earthquake_data):
    """
    Takes the parsed USGS GeoJSON data and returns a folium Map object
    with one circle marker per earthquake.
    """
    features = earthquake_data["features"]

    # Center the map on the first earthquake if we have any results,
    # otherwise fall back to a default world-ish view (0, 0).
    if features:
        first_coords = features[0]["geometry"]["coordinates"]
        start_location = [first_coords[1], first_coords[0]]  # [lat, lon]
    else:
        start_location = [0, 0]

    earthquake_map = folium.Map(location=start_location, zoom_start=2, tiles="OpenStreetMap")

    for feature in features:
        # GeoJSON coordinates are ordered [longitude, latitude, depth_km].
        longitude, latitude, depth_km = feature["geometry"]["coordinates"]

        properties = feature["properties"]
        magnitude = properties["mag"]
        place = properties["place"]

        # USGS gives time as milliseconds since the Unix epoch. Convert
        # to a readable date/time string for the popup.
        event_time = datetime.fromtimestamp(properties["time"] / 1000, tz=timezone.utc)
        time_str = event_time.strftime("%Y-%m-%d %H:%M UTC")

        # Skip any earthquake missing a magnitude value (rare, but the
        # API occasionally has null magnitudes for unreviewed events).
        if magnitude is None:
            continue

        popup_text = (
            f"<b>{place}</b><br>"
            f"Magnitude: {magnitude}<br>"
            f"Depth: {depth_km} km<br>"
            f"Time: {time_str}"
        )

        folium.CircleMarker(
            location=[latitude, longitude],
            radius=magnitude_to_radius(magnitude),
            color=magnitude_to_color(magnitude),
            fill=True,
            fill_color=magnitude_to_color(magnitude),
            fill_opacity=0.7,
            popup=folium.Popup(popup_text, max_width=250),
            tooltip=f"M{magnitude} - {place}",
        ).add_to(earthquake_map)

    return earthquake_map


# --- 5. MAIN PROGRAM ---------------------------------------------------------
def main():
    print(f"Fetching earthquakes from {START_DATE} to {END_DATE} "
          f"(min magnitude {MIN_MAGNITUDE})...")

    data = fetch_earthquakes(START_DATE, END_DATE, MIN_MAGNITUDE)
    quake_count = len(data["features"])
    print(f"Found {quake_count} earthquakes.")

    earthquake_map = build_map(data)

    # Save next to this script file rather than the current working
    # directory, so it lands in a predictable place no matter where
    # you launch the script from.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "earthquake_map.html")
    earthquake_map.save(output_file)
    print(f"Map saved to {output_file}. Open it in your browser to explore!")


# This check ensures main() only runs when the script is executed directly
# (e.g. `python earthquake_map.py`), not if it were imported elsewhere.
if __name__ == "__main__":
    main()

import folium
import pandas as pd
import json
import random
import requests
from geopy.geocoders import Nominatim

# ---------------------------------------------------------
# LOAD TREE DATA
# ---------------------------------------------------------
with open("db/trees.json", "r", encoding="utf-8") as f:
    data = json.load(f)

df = pd.DataFrame(data)

linz_center = (48.3069, 14.2858)

# ---------------------------------------------------------
# HOME ADDRESS INPUT
# ---------------------------------------------------------
address = input("Enter your home address: ")

geolocator = Nominatim(user_agent="linz_tree_map")
location = geolocator.geocode(address)

if location is None:
    print("Address not found.")
    exit()

home = (location.latitude, location.longitude)
print(f"Home location: {home}")

# ---------------------------------------------------------
# TARGET DISTANCE
# ---------------------------------------------------------
target_distance_km = float(input("Enter desired total route distance in km: "))
tolerance = 2 # ±2 km allowed

# ---------------------------------------------------------
# OSRM WALKING ROUTE FUNCTION
# ---------------------------------------------------------
def osrm_route(pointA, pointB):
    url = (
        f"https://router.project-osrm.org/route/v1/foot/"
        f"{pointA[1]},{pointA[0]};{pointB[1]},{pointB[0]}"
        f"?overview=full&geometries=geojson"
    )

    r = requests.get(url)
    data = r.json()

    if "routes" not in data:
        print("OSRM error:", data)
        return None, None

    route = data["routes"][0]
    distance_km = route["distance"] / 1000.0
    geometry = route["geometry"]["coordinates"]

    polyline = [(latlon[1], latlon[0]) for latlon in geometry]

    return distance_km, polyline

# ---------------------------------------------------------
# TRY RANDOM ROUTES UNTIL DISTANCE MATCHES
# ---------------------------------------------------------
max_attempts = 200
best_route = None
best_distance = None
best_polylines = None

for _ in range(max_attempts):
    selected = df.sample(3)
    tree_points = [(row["lat"], row["lon"]) for _, row in selected.iterrows()]

    total_dist = 0
    polylines = []

    # Home → Tree1
    d1, p1 = osrm_route(home, tree_points[0])
    if d1 is None: continue

    # Tree1 → Tree2
    d2, p2 = osrm_route(tree_points[0], tree_points[1])
    if d2 is None: continue

    # Tree2 → Tree3
    d3, p3 = osrm_route(tree_points[1], tree_points[2])
    if d3 is None: continue

    # Tree3 → Home
    d4, p4 = osrm_route(tree_points[2], home)
    if d4 is None: continue

    total_dist = d1 + d2 + d3 + d4
    polylines = [p1, p2, p3, p4]

    if abs(total_dist - target_distance_km) <= tolerance:
        best_route = tree_points
        best_distance = total_dist
        best_polylines = polylines
        break

if best_route is None:
    print("Could not find a route within the desired distance range.")
    exit()

print(f"Route found! Total walking distance: {best_distance:.2f} km")

# ---------------------------------------------------------
# CREATE MAP
# ---------------------------------------------------------
m = folium.Map(location=linz_center, zoom_start=13, tiles="CartoDB Positron")

# Add all tree markers
for _, row in df.iterrows():
    folium.CircleMarker(
        location=(row["lat"], row["lon"]),
        radius=4,
        color="green",
        fill=True,
        fill_opacity=0.7,
        tooltip=row["NameDeutsch"]
    ).add_to(m)

# Home marker
folium.Marker(
    location=home,
    popup=f"Home<br>Total route: {best_distance:.2f} km",
    icon=folium.Icon(color="red", icon="home")
).add_to(m)

# Numbered tree markers
for i, pt in enumerate(best_route):
    folium.Marker(
        location=pt,
        popup=f"Tree {i+1}",
        icon=folium.DivIcon(
            html=f"""
                <div style="
                    background-color:#1E90FF;
                    color:white;
                    border-radius:50%;
                    width:24px;
                    height:24px;
                    text-align:center;
                    line-height:24px;
                    font-size:14px;
                    font-weight:bold;">
                    {i+1}
                </div>
            """
        )
    ).add_to(m)

# Draw OSRM polylines
for poly in best_polylines:
    folium.PolyLine(
        locations=poly,
        color="purple",
        weight=5,
        opacity=0.9
    ).add_to(m)

# Save map
m.save("linz_trees_route_street.html")
print("Map saved as linz_trees_route_street.html")
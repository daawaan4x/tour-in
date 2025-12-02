import L from "leaflet";
import "leaflet/dist/leaflet.css";

// MAP SETUP
const map = L.map("map").setView([18.194343, 120.6911117], 10);

L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap",
}).addTo(map);

// GEOAPIFY API KEY
const API_KEY = "86018fe289554e6a810811b58eaf0a13";

// AUTOCOMPLETE FOR DESTINATIONS
import { GeocoderAutocomplete } from "@geoapify/geocoder-autocomplete";
import "@geoapify/geocoder-autocomplete/styles/minimal.css";

const destAuto = new GeocoderAutocomplete(
  document.getElementById("autocomplete-dest")!,
  API_KEY,
  {
    placeholder: "Add destination",
    lang: "en",
    limit: 5,
    filter: {
      place:
        "51b65426295a295e405923591868d23d3240f00101f901e8f516000000000092030c496c6f636f73204e6f727465",
    },
  }
);

// DATA STORAGE
let startCoords: any = null;
let destinations: any[] = [];

let startMarker: L.Marker | null = null;
let routeLine: L.Polyline | null = null;
let destMarkers: L.Marker[] = [];

// ======= CLICK MAP TO SET START LOCATION =======
map.on("click", (e: any) => {
  startCoords = {
    lat: e.latlng.lat,
    lon: e.latlng.lng,
  };

  if (startMarker) map.removeLayer(startMarker);

  startMarker = L.marker([startCoords.lat, startCoords.lon]).addTo(map);

  planRoute();
});

// ======= DESTINATION AUTO-ADD AND LIST WITH REMOVE BUTTON =======
destAuto.on("select", (loc: any) => {
  const lat = loc.properties.lat;
  const lon = loc.properties.lon;

  const dest = {
    lat,
    lon,
    name: loc.properties.formatted,
  };

  destinations.push(dest);

  // Marker
  const marker = L.marker([dest.lat, dest.lon])
    .addTo(map)
    .bindPopup(dest.name)
    .openPopup();

  destMarkers.push(marker);

  // Update list with remove button
  const list = document.getElementById("destination-list")!;
  const li = document.createElement("li");
  li.textContent = dest.name;

  const removeBtn = document.createElement("button");
  removeBtn.textContent = "Remove";
  removeBtn.style.marginLeft = "8px";
  removeBtn.onclick = () => {
    map.removeLayer(marker); // remove marker
    destinations = destinations.filter((d) => d !== dest); // remove from array
    li.remove(); // remove from list
    planRoute(); // redraw route after removal
  };

  li.appendChild(removeBtn);
  list.appendChild(li);

  planRoute();
});

// ======= DRAW ROUTE =======
function drawRoute(coords: number[][]) {
  const points = coords.map((c) => L.latLng(c[1], c[0])); // lat, lon
  if (routeLine) map.removeLayer(routeLine);
  routeLine = L.polyline(points, { weight: 5 }).addTo(map);
  map.fitBounds(routeLine.getBounds());
}

// ======= SEND DATA TO FLASK =======
async function planRoute() {
  if (!startCoords) return drawRoute([]);
  if (destinations.length === 0) return drawRoute([]);

  const response = await fetch("http://localhost:5000/api/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      start: startCoords,
      destinations: destinations,
    }),
  });

  const data = await response.json();
  drawRoute(data.route);
}

// EXPOSE FUNCTION TO HTML
(window as any).planRoute = planRoute;

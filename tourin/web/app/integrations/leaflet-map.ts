import L from "leaflet";
import markerIcon2xUrl from "leaflet/dist/images/marker-icon-2x.png";
import markerIconUrl from "leaflet/dist/images/marker-icon.png";
import markerShadowUrl from "leaflet/dist/images/marker-shadow.png";

import { deriveDisplayDestinations } from "../state/selectors";
import type { AppState, PlaceRef } from "../state/types";
import { renderMarkerHtml } from "../ui/marker";

let didConfigureDefaultIcon = false;

function configureLeafletDefaultIcons(): void {
  if (didConfigureDefaultIcon) {
    return;
  }

  delete (L.Icon.Default.prototype as { _getIconUrl?: unknown })._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: markerIcon2xUrl,
    iconUrl: markerIconUrl,
    shadowUrl: markerShadowUrl,
  });
  didConfigureDefaultIcon = true;
}

function createPopupContent(place: PlaceRef): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "map-popup";

  const title = document.createElement("p");
  title.className = "title";
  title.textContent = place.name;
  wrapper.appendChild(title);

  if (place.municipality) {
    const meta = document.createElement("p");
    meta.className = "meta";
    meta.textContent = place.municipality;
    wrapper.appendChild(meta);
  }

  return wrapper;
}

interface CreateMarkerIconOptions {
  html: string;
}

function createMarkerIcon({ html }: CreateMarkerIconOptions): L.DivIcon {
  return L.divIcon({
    className: "tour-marker",
    html,
    iconSize: [40, 40],
    iconAnchor: [20, 39],
  });
}

export interface LeafletMapAdapter {
  sync(state: AppState): void;
  destroy(): void;
}

interface CreateLeafletMapAdapterOptions {
  mapElementId: string;
  onMapClick(lat: number, lon: number): void;
  onDestinationClick(destinationId: string): void;
  traceStrackApiKey: string;
}

export function createLeafletMapAdapter(
  options: CreateLeafletMapAdapterOptions,
): LeafletMapAdapter {
  configureLeafletDefaultIcons();

  const map = L.map(options.mapElementId).setView([18.194343, 120.6911117], 10);

  //L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  L.tileLayer(
    `https://tile.tracestrack.com/_/{z}/{x}/{y}.webp?key=${options.traceStrackApiKey}`,
    {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap",
    },
  ).addTo(map);

  map.on("click", (event: L.LeafletMouseEvent) => {
    options.onMapClick(event.latlng.lat, event.latlng.lng);
  });

  let startMarker: L.Marker | null = null;
  let routeLine: L.Polyline | null = null;
  let destinationLayer = L.layerGroup().addTo(map);
  let lastRouteSignature = "";
  let lastFocusedDestinationId: string | null = null;

  const buildDestinationMarkerMap = (
    destinations: PlaceRef[],
    focusedDestinationId: string | null,
    isPlanning: boolean,
  ): Map<string, L.Marker> => {
    destinationLayer.remove();
    destinationLayer = L.layerGroup().addTo(map);
    const markerMap = new Map<string, L.Marker>();

    destinations.forEach((destination, index) => {
      const marker = L.marker([destination.lat, destination.lon], {
        icon: createMarkerIcon({
          html: renderMarkerHtml({
            variant: "destination",
            isActive: destination.id === focusedDestinationId,
            index,
            isPlanning,
            destinationId: destination.id,
          }),
        }),
      });
      marker.bindPopup(createPopupContent(destination));
      marker.on("click", () => {
        options.onDestinationClick(destination.id);
      });
      marker.addTo(destinationLayer);
      markerMap.set(destination.id, marker);
    });

    return markerMap;
  };

  return {
    sync: (state) => {
      if (state.start) {
        const nextLatLng: [number, number] = [state.start.lat, state.start.lon];
        if (!startMarker) {
          startMarker = L.marker(nextLatLng, {
            icon: createMarkerIcon({
              html: renderMarkerHtml({
                variant: "start",
                isActive: false,
              }),
            }),
          }).addTo(map);
        } else {
          startMarker.setLatLng(nextLatLng);
        }

        startMarker.bindPopup(createPopupContent(state.start));
      } else if (startMarker) {
        map.removeLayer(startMarker);
        startMarker = null;
      }

      const destinationMarkers = buildDestinationMarkerMap(
        deriveDisplayDestinations(state.destinations, state.itineraryOrder),
        state.focusedDestinationId,
        state.routeStatus === "planning",
      );

      if (state.routeCoords.length > 1) {
        const latLngs = state.routeCoords.map(
          ([lon, lat]) => [lat, lon] as [number, number],
        );
        if (!routeLine) {
          routeLine = L.polyline(latLngs, {
            color: "#2e6f73",
            weight: 5,
            opacity: 0.9,
          }).addTo(map);
        } else {
          routeLine.setLatLngs(latLngs);
        }

        const routeSignature = JSON.stringify(state.routeCoords);
        if (
          state.routeStatus === "ready" &&
          routeSignature !== lastRouteSignature
        ) {
          map.fitBounds(routeLine.getBounds(), {
            padding: [36, 36],
          });
        }
        lastRouteSignature = routeSignature;
      } else {
        lastRouteSignature = "";
        if (routeLine) {
          map.removeLayer(routeLine);
          routeLine = null;
        }
      }

      if (
        state.focusedDestinationId &&
        state.focusedDestinationId !== lastFocusedDestinationId
      ) {
        const marker = destinationMarkers.get(state.focusedDestinationId);
        if (marker) {
          marker.openPopup();
          map.panTo(marker.getLatLng(), { animate: true });
        }
      }
      lastFocusedDestinationId = state.focusedDestinationId;
    },
    destroy: () => {
      map.remove();
    },
  };
}

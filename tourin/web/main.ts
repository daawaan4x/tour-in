import "leaflet/dist/leaflet.css";

import { createRouteActions } from "./app/actions/route-actions";
import { createTripActions } from "./app/actions/trip-actions";
import {
  createGeoapifyControl,
  type GeoapifyControl,
} from "./app/integrations/geoapify";
import { createLeafletMapAdapter } from "./app/integrations/leaflet-map";
import { createMapStartPlace } from "./app/services/places";
import { createRouteApiClient } from "./app/services/route-api";
import { createStore } from "./app/state/store";
import type { AppState } from "./app/state/types";
import { createAppRenderer } from "./app/ui/render-app";
import "./styles/tokens.css";
import "./styles/tailwind.css";
import "./styles/base.css";
import "./styles/overrides.css";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:5000";
const TRACESTRACK_API_KEY = import.meta.env.VITE_TRACESTRACK_API_KEY;
const GEOAPIFY_API_KEY = import.meta.env.VITE_GEOAPIFY_API_KEY;

function requireElementById<T extends HTMLElement>(id: string): T {
  const node = document.getElementById(id);
  if (!node) {
    throw new Error(`Missing required DOM element: #${id}`);
  }

  return node as T;
}

const initialState: AppState = {
  start: null,
  destinations: [],
  itineraryOrder: [],
  routeCoords: [],
  routeDistanceKm: null,
  routeStatus: GEOAPIFY_API_KEY ? "missing-start" : "error",
  routeError: GEOAPIFY_API_KEY
    ? null
    : "Missing Geoapify API key. Search is disabled until VITE_GEOAPIFY_API_KEY is set.",
  isBootstrapping: false,
  isConfigMissing: !GEOAPIFY_API_KEY,
  focusedDestinationId: null,
};

const store = createStore(initialState);
const tripActions = createTripActions({ store });
const routeActions = createRouteActions({
  store,
  routeApiClient: createRouteApiClient({ apiUrl: API_URL }),
});

const renderer = createAppRenderer({
  mounts: {
    root: requireElementById("app"),
  },
  actions: {
    clearStart: tripActions.clearStart,
    removeDestination: tripActions.removeDestination,
    focusDestination: tripActions.focusDestination,
    retryRoute: () => {
      void routeActions.retryRoute();
    },
    clearTrip: tripActions.clearTrip,
  },
});

renderer.render(store.getState());

const mapAdapter = createLeafletMapAdapter({
  mapElementId: "map",
  traceStrackApiKey: TRACESTRACK_API_KEY,
  onMapClick: (lat, lon) => {
    tripActions.selectStartFromMap(createMapStartPlace(lat, lon));
  },
  onDestinationClick: (destinationId) => {
    tripActions.focusDestination(destinationId);
  },
});

let startSearchControl: GeoapifyControl | null = null;
let destinationSearchControl: GeoapifyControl | null = null;
const startSearchContainer = requireElementById<HTMLElement>(
  "start-search-control",
);
const destinationSearchContainer = requireElementById<HTMLElement>(
  "dest-search-control",
);

if (GEOAPIFY_API_KEY) {
  startSearchControl = createGeoapifyControl({
    container: startSearchContainer,
    apiKey: GEOAPIFY_API_KEY,
    placeholder: "Search starting point or click on the map",
    source: "search",
    inputId: "start-search-input",
    clearOnSelect: false,
    onSelect: (place) => {
      tripActions.selectStartFromSearch(place);
    },
  });

  destinationSearchControl = createGeoapifyControl({
    container: destinationSearchContainer,
    apiKey: GEOAPIFY_API_KEY,
    placeholder: "Search destination to add",
    source: "search",
    inputId: "dest-search-input",
    clearOnSelect: true,
    onSelect: (place) => tripActions.addDestinationFromSearch(place),
  });
}

function syncSearchControlState(state: AppState): void {
  const isPlanning = state.routeStatus === "planning";
  const disabled = isPlanning || state.isConfigMissing;
  startSearchControl?.setDisabled(disabled);
  destinationSearchControl?.setDisabled(disabled);
}

syncSearchControlState(store.getState());

const unsubscribeUi = store.subscribe((state) => {
  renderer.render(state);
  syncSearchControlState(state);
});

const unsubscribeMap = store.subscribe((state) => {
  mapAdapter.sync(state);
});

const unsubscribeAutoRoutePlan = store.subscribe((state, prevState) => {
  if (state.routeStatus === "planning") {
    return;
  }

  const startChanged = state.start?.id !== prevState.start?.id;
  const destinationsChanged =
    state.destinations.length !== prevState.destinations.length ||
    state.destinations.some(
      (destination, index) =>
        destination.id !== prevState.destinations[index]?.id,
    );
  if (!startChanged && !destinationsChanged) {
    return;
  }

  if (!state.start || state.destinations.length === 0) {
    return;
  }

  void routeActions.planRoute();
});

mapAdapter.sync(store.getState());

window.addEventListener("beforeunload", () => {
  unsubscribeUi();
  unsubscribeMap();
  unsubscribeAutoRoutePlan();
  mapAdapter.destroy();
  startSearchControl?.destroy();
  destinationSearchControl?.destroy();
});

export type RouteStatus =
  | "idle"
  | "missing-start"
  | "missing-destinations"
  | "planning"
  | "ready"
  | "error";

export type PlaceSource = "search" | "suggestion" | "map";

export interface PlaceRef {
  id: string;
  name: string;
  lat: number;
  lon: number;
  municipality?: string;
  source: PlaceSource;
}

export interface AppState {
  start: PlaceRef | null;
  destinations: PlaceRef[];
  routeCoords: [number, number][];
  routeDistanceKm: number | null;
  routeStatus: RouteStatus;
  routeError: string | null;
  isBootstrapping: boolean;
  isConfigMissing: boolean;
  focusedDestinationId: string | null;
}

export type StateUpdater = (prev: AppState) => AppState;
export type Listener = (state: AppState, prevState: AppState) => void;

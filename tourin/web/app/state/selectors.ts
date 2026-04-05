import type { PlaceRef, RouteStatus } from "./types";

export function deriveRouteStatusFromTrip(
  start: PlaceRef | null,
  destinations: PlaceRef[],
): RouteStatus {
  if (!start) {
    return "missing-start";
  }

  if (destinations.length === 0) {
    return "missing-destinations";
  }

  return "idle";
}

export function canPlanRoute(
  start: PlaceRef | null,
  destinations: PlaceRef[],
  routeStatus: RouteStatus,
): boolean {
  return Boolean(start) && destinations.length > 0 && routeStatus !== "planning";
}

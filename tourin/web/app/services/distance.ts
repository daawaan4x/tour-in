import { length, lineString } from "@turf/turf";

export function computeRouteDistanceKm(
  routeCoords: [number, number][],
): number | null {
  if (routeCoords.length < 2) {
    return null;
  }

  const routeLine = lineString(routeCoords);
  const routeDistanceKm = length(routeLine, { units: "kilometers" });
  return Number(routeDistanceKm.toFixed(1));
}

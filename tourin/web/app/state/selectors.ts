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

export function deriveDisplayDestinations(
  destinations: PlaceRef[],
  itineraryOrder: string[],
): PlaceRef[] {
  if (itineraryOrder.length === 0 || destinations.length === 0) {
    return destinations;
  }

  const destinationById = new Map(
    destinations.map((destination) => [destination.id, destination] as const),
  );
  const seenDestinationIds = new Set<string>();
  const orderedDestinations: PlaceRef[] = [];

  itineraryOrder.forEach((destinationId) => {
    const destination = destinationById.get(destinationId);
    if (!destination || seenDestinationIds.has(destinationId)) {
      return;
    }

    seenDestinationIds.add(destinationId);
    orderedDestinations.push(destination);
  });

  if (orderedDestinations.length === 0) {
    return destinations;
  }

  destinations.forEach((destination) => {
    if (!seenDestinationIds.has(destination.id)) {
      orderedDestinations.push(destination);
    }
  });

  return orderedDestinations;
}

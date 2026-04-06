import { deriveRouteStatusFromTrip } from "../state/selectors";
import type { Store } from "../state/store";
import type { PlaceRef } from "../state/types";

function destinationKey(place: PlaceRef): string {
  return `${place.lat.toFixed(6)}:${place.lon.toFixed(6)}`;
}

function isDuplicateDestination(
  destinations: PlaceRef[],
  candidate: PlaceRef,
): boolean {
  const candidateKey = destinationKey(candidate);
  return destinations.some(
    (destination) =>
      destination.id === candidate.id ||
      destinationKey(destination) === candidateKey,
  );
}

export interface TripActions {
  selectStartFromSearch(place: PlaceRef): void;
  selectStartFromMap(place: PlaceRef): void;
  clearStart(): void;
  addDestinationFromSearch(place: PlaceRef): boolean;
  addDestinationFromSuggestion(place: PlaceRef): boolean;
  removeDestination(destinationId: string): void;
  focusDestination(destinationId: string | null): void;
  clearTrip(): void;
}

interface CreateTripActionsOptions {
  store: Store;
}

export function createTripActions(
  options: CreateTripActionsOptions,
): TripActions {
  const { store } = options;

  const applyStartSelection = (place: PlaceRef): void => {
    store.setState((prev) => {
      if (prev.routeStatus === "planning") {
        return prev;
      }

      return {
        ...prev,
        start: place,
        itineraryOrder: [],
        routeCoords: [],
        routeDistanceKm: null,
        routeStatus: deriveRouteStatusFromTrip(place, prev.destinations),
        routeError: null,
        focusedDestinationId: null,
      };
    });
  };

  const addDestination = (place: PlaceRef): boolean => {
    let didAdd = false;
    store.setState((prev) => {
      if (prev.routeStatus === "planning") {
        return prev;
      }

      if (isDuplicateDestination(prev.destinations, place)) {
        return prev;
      }

      didAdd = true;
      const destinations = [...prev.destinations, place];
      return {
        ...prev,
        destinations,
        itineraryOrder: [],
        routeCoords: [],
        routeDistanceKm: null,
        routeStatus: deriveRouteStatusFromTrip(prev.start, destinations),
        routeError: null,
        focusedDestinationId: null,
      };
    });
    return didAdd;
  };

  return {
    selectStartFromSearch: applyStartSelection,
    selectStartFromMap: applyStartSelection,
    clearStart: () => {
      store.setState((prev) => {
        if (prev.routeStatus === "planning") {
          return prev;
        }

        return {
          ...prev,
          start: null,
          itineraryOrder: [],
          routeCoords: [],
          routeDistanceKm: null,
          routeStatus: "missing-start",
          routeError: null,
          focusedDestinationId: null,
        };
      });
    },
    addDestinationFromSearch: addDestination,
    addDestinationFromSuggestion: addDestination,
    removeDestination: (destinationId) => {
      store.setState((prev) => {
        if (prev.routeStatus === "planning") {
          return prev;
        }

        const destinations = prev.destinations.filter(
          (destination) => destination.id !== destinationId,
        );
        if (destinations.length === prev.destinations.length) {
          return prev;
        }

        const focusedDestinationId =
          prev.focusedDestinationId === destinationId
            ? null
            : prev.focusedDestinationId;

        return {
          ...prev,
          destinations,
          itineraryOrder: [],
          routeCoords: [],
          routeDistanceKm: null,
          routeStatus: deriveRouteStatusFromTrip(prev.start, destinations),
          routeError: null,
          focusedDestinationId,
        };
      });
    },
    focusDestination: (destinationId) => {
      store.setState((prev) => {
        if (!destinationId) {
          if (!prev.focusedDestinationId) {
            return prev;
          }

          return {
            ...prev,
            focusedDestinationId: null,
          };
        }

        const exists = prev.destinations.some(
          (destination) => destination.id === destinationId,
        );
        if (!exists) {
          return prev;
        }

        return {
          ...prev,
          focusedDestinationId: destinationId,
        };
      });
    },
    clearTrip: () => {
      store.setState((prev) => {
        if (prev.routeStatus === "planning") {
          return prev;
        }

        return {
          ...prev,
          start: null,
          destinations: [],
          itineraryOrder: [],
          routeCoords: [],
          routeDistanceKm: null,
          routeStatus: "missing-start",
          routeError: null,
          focusedDestinationId: null,
        };
      });
    },
  };
}

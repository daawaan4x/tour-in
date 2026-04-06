import { computeRouteDistanceKm } from "../services/distance";
import type { RouteApiClient } from "../services/route-api";
import { deriveRouteStatusFromTrip } from "../state/selectors";
import type { Store } from "../state/store";

export interface RouteActions {
  planRoute(): Promise<void>;
  retryRoute(): Promise<void>;
  clearRoute(): void;
}

interface CreateRouteActionsOptions {
  store: Store;
  routeApiClient: RouteApiClient;
}

export function createRouteActions(
  options: CreateRouteActionsOptions,
): RouteActions {
  const { routeApiClient, store } = options;
  let latestRequestId = 0;

  const planRoute = async (): Promise<void> => {
    const state = store.getState();
    if (!state.start || state.destinations.length === 0) {
      store.setState((prev) => ({
        ...prev,
        routeStatus: deriveRouteStatusFromTrip(prev.start, prev.destinations),
        routeError: null,
        itineraryOrder: [],
      }));
      return;
    }

    if (state.routeStatus === "planning") {
      return;
    }

    latestRequestId += 1;
    const requestId = latestRequestId;

    store.setState((prev) => ({
      ...prev,
      routeStatus: "planning",
      routeError: null,
      focusedDestinationId: null,
      itineraryOrder: [],
    }));

    try {
      const planResult = await routeApiClient.planRoute(
        state.start,
        state.destinations,
      );
      const routeDistanceKm = computeRouteDistanceKm(planResult.routeCoords);

      store.setState((prev) => {
        if (requestId !== latestRequestId) {
          return prev;
        }

        return {
          ...prev,
          routeCoords: planResult.routeCoords,
          routeDistanceKm,
          routeStatus: "ready",
          routeError: null,
          itineraryOrder: planResult.itineraryOrder,
        };
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Route unavailable right now. Please try again.";
      store.setState((prev) => {
        if (requestId !== latestRequestId) {
          return prev;
        }

        return {
          ...prev,
          routeCoords: [],
          routeDistanceKm: null,
          routeStatus: "error",
          routeError: message,
          itineraryOrder: [],
        };
      });
    }
  };

  return {
    planRoute,
    retryRoute: planRoute,
    clearRoute: () => {
      latestRequestId += 1;
      store.setState((prev) => {
        if (prev.routeStatus === "planning") {
          return prev;
        }

        return {
          ...prev,
          routeCoords: [],
          routeDistanceKm: null,
          routeStatus: deriveRouteStatusFromTrip(prev.start, prev.destinations),
          routeError: null,
          focusedDestinationId: null,
          itineraryOrder: [],
        };
      });
    },
  };
}

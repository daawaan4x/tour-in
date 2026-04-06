import type { PlaceRef } from "../state/types";

type RouteApiPayload = {
  start: { lat: number; lon: number };
  destinations: Array<{ id: string; lat: number; lon: number }>;
};

type RouteApiSuccess = {
  route: unknown;
  itinerary_order: unknown;
};

export interface RoutePlanResult {
  routeCoords: [number, number][];
  itineraryOrder: string[];
}

export interface RouteApiClient {
  planRoute(start: PlaceRef, destinations: PlaceRef[]): Promise<RoutePlanResult>;
}

interface CreateRouteApiClientOptions {
  apiUrl: string;
}

function normalizeApiUrl(apiUrl: string): string {
  return apiUrl.replace(/\/+$/, "");
}

function isRouteCoordinate(value: unknown): value is [number, number] {
  return (
    Array.isArray(value) &&
    value.length === 2 &&
    typeof value[0] === "number" &&
    Number.isFinite(value[0]) &&
    typeof value[1] === "number" &&
    Number.isFinite(value[1])
  );
}

function isDestinationId(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const body = (await response.json()) as Record<string, unknown>;
      const message = body.message ?? body.error;
      if (typeof message === "string" && message.trim().length > 0) {
        return message;
      }
    } else {
      const text = await response.text();
      if (text.trim().length > 0) {
        return text.trim();
      }
    }
  } catch {
    // no-op: use fallback message below
  }

  return "Route unavailable right now. Try again, remove a stop, or change the start point.";
}

export function createRouteApiClient(
  options: CreateRouteApiClientOptions,
): RouteApiClient {
  const baseUrl = normalizeApiUrl(options.apiUrl);

  return {
    async planRoute(start, destinations) {
      const payload: RouteApiPayload = {
        start: {
          lat: start.lat,
          lon: start.lon,
        },
        destinations: destinations.map((destination) => ({
          id: destination.id,
          lat: destination.lat,
          lon: destination.lon,
        })),
      };

      const response = await fetch(`${baseUrl}/api/route`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const message = await extractErrorMessage(response);
        throw new Error(message);
      }

      const body = (await response.json()) as RouteApiSuccess;
      if (!Array.isArray(body.route)) {
        throw new Error("Route response is invalid.");
      }
      if (!Array.isArray(body.itinerary_order)) {
        throw new Error("Route itinerary response is invalid.");
      }

      const route = body.route.filter(isRouteCoordinate);
      if (route.length < 2) {
        throw new Error(
          "Route result is empty. Try changing the start point or destinations.",
        );
      }

      const itineraryOrder = body.itinerary_order.filter(isDestinationId);
      if (itineraryOrder.length !== destinations.length) {
        throw new Error("Route itinerary response is invalid.");
      }
      if (new Set(itineraryOrder).size !== itineraryOrder.length) {
        throw new Error("Route itinerary response is invalid.");
      }

      return {
        routeCoords: route,
        itineraryOrder,
      };
    },
  };
}

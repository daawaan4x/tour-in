import type { PlaceRef, PlaceSource } from "../state/types";

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null;
}

function readString(record: UnknownRecord, key: string): string | null {
  const value = record[key];
  if (typeof value !== "string") {
    return null;
  }

  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function readNumber(record: UnknownRecord, key: string): number | null {
  const value = record[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

function buildFallbackId(name: string, lat: number, lon: number): string {
  return `place-${slugify(name)}-${lat.toFixed(6)}-${lon.toFixed(6)}`;
}

function readMunicipality(properties: UnknownRecord): string | undefined {
  const municipality =
    readString(properties, "city") ??
    readString(properties, "town") ??
    readString(properties, "village") ??
    readString(properties, "county");
  return municipality ?? undefined;
}

export function normalizeGeoapifyPlace(
  rawLocation: unknown,
  source: PlaceSource,
): PlaceRef | null {
  if (!isRecord(rawLocation) || !isRecord(rawLocation.properties)) {
    return null;
  }

  const properties = rawLocation.properties;
  const lat = readNumber(properties, "lat");
  const lon = readNumber(properties, "lon");
  if (lat === null || lon === null) {
    return null;
  }

  const name =
    readString(properties, "formatted") ??
    readString(properties, "address_line1") ??
    readString(properties, "name");
  if (!name) {
    return null;
  }

  const placeId = readString(properties, "place_id");
  const id = placeId ?? buildFallbackId(name, lat, lon);

  return {
    id,
    name,
    lat,
    lon,
    municipality: readMunicipality(properties),
    source,
  };
}

export function createMapStartPlace(lat: number, lon: number): PlaceRef {
  const latLabel = lat.toFixed(4);
  const lonLabel = lon.toFixed(4);
  return {
    id: `map-start-${lat.toFixed(6)}-${lon.toFixed(6)}`,
    name: `Pinned start (${latLabel}, ${lonLabel})`,
    lat,
    lon,
    source: "map",
  };
}

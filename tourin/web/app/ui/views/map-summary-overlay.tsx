import type { RouteStatus } from "../../state/types";

interface MapSummaryOverlayProps {
  status: RouteStatus;
  errorMessage: string | null;
  routeDistanceKm: number | null;
  canClear: boolean;
  isPlanning: boolean;
  onRetry(): void;
  onClearTrip(): void;
}

function statusTone(status: RouteStatus): "neutral" | "planning" | "error" {
  if (status === "planning") {
    return "planning";
  }

  if (status === "error") {
    return "error";
  }

  return "neutral";
}

export function MapSummaryOverlay(props: MapSummaryOverlayProps) {
  const routeDistanceLabel =
    props.routeDistanceKm === null
      ? "--"
      : props.routeDistanceKm.toFixed(1) + " km";
  const iconButtonClass =
    "inline-flex h-[30px] min-h-[30px] w-[30px] min-w-[30px] shrink-0 items-center justify-center rounded-full border border-[rgb(47_36_29_/_0.14)] bg-[var(--color-bg-card)] p-0 transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease-standard)] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-bg-canvas)] disabled:opacity-[0.52]";
  const retryButtonClass =
    "inline-flex min-h-[38px] items-center justify-center rounded-[var(--radius-pill)] border border-transparent bg-[var(--color-brand-primary)] px-3 text-[var(--font-size-small)] font-semibold text-[var(--color-text-inverse)] transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease-standard)] hover:bg-[var(--color-brand-primary-hover)] disabled:opacity-[0.52]";
  const tone = statusTone(props.status);
  const toneClass =
    tone === "planning"
      ? "border-[rgb(46_111_115_/_0.45)] bg-[rgb(215_232_230_/_0.95)]"
      : tone === "error"
        ? "border-[rgb(158_61_52_/_0.45)] bg-[rgb(158_61_52_/_0.10)]"
        : "border-[rgb(47_36_29_/_0.12)] bg-[rgb(251_247_241_/_0.95)]";

  return (
    <div
      id="map-summary-overlay"
      class="pointer-events-auto absolute right-4 top-4 z-600"
    >
      <div
        class={
          "inline-flex w-fit max-w-none items-center gap-3 rounded-md border p-3 shadow-(--shadow-md) " +
          toneClass
        }
      >
        <span class="whitespace-nowrap text-(--color-text-secondary)">
          Route
        </span>
        {props.status === "planning" ? (
          <>
            <span class="route-pending-spinner" aria-hidden="true" />
            <span class="sr-only">Updating route</span>
          </>
        ) : (
          <span class="whitespace-nowrap font-mono text-(--font-size-small) font-medium">
            {routeDistanceLabel}
          </span>
        )}
        <button
          class={iconButtonClass}
          type="button"
          title="Clear trip"
          aria-label="Clear trip"
          disabled={!props.canClear || props.isPlanning}
          onClick={props.onClearTrip}
        >
          <i
            class="bi bi-trash3 block text-[0.9rem] leading-none"
            aria-hidden="true"
          />
          <span class="sr-only">Clear trip</span>
        </button>

        {props.status === "error" && (
          <>
            <span class="whitespace-nowrap text-(--font-size-small)">
              {props.errorMessage ?? "Route unavailable."}
            </span>
            <button
              class={retryButtonClass}
              type="button"
              disabled={props.isPlanning}
              onClick={props.onRetry}
            >
              Retry
            </button>
          </>
        )}
      </div>
    </div>
  );
}

import type { AppState } from "../state/types";
import { MapSummaryOverlay } from "./views/map-summary-overlay";
import { StartSection } from "./views/start-section";
import { StopsAndItinerarySection } from "./views/stops-section";

interface AppShellActions {
  clearStart(): void;
  removeDestination(destinationId: string): void;
  focusDestination(destinationId: string): void;
  retryRoute(): void;
  clearTrip(): void;
}

interface AppShellProps {
  state: AppState;
  isPlanning: boolean;
  actions: AppShellActions;
}

export function AppShell(props: AppShellProps) {
  const { actions, isPlanning, state } = props;

  return (
    <div
      id="app-shell"
      class="grid min-h-screen grid-cols-1 min-[1080px]:h-screen min-[1080px]:min-h-0 min-[1080px]:grid-cols-[minmax(320px,400px)_1fr]"
      data-route-status={state.routeStatus}
    >
      <aside
        class="flex h-auto max-h-none flex-col gap-4 overflow-visible border-b border-[rgb(47_36_29/0.14)] bg-(--color-bg-panel) p-4 min-[1080px]:h-full min-[1080px]:min-h-0 min-[1080px]:overflow-y-auto min-[1080px]:border-b-0 min-[1080px]:border-r"
        aria-label="Trip planner panel"
      >
        <header class="grid gap-2">
          <p class="text-(--font-size-small) font-bold uppercase tracking-[0.08em]">
            Ilocos Norte Guide
          </p>
          <h1 class="inline-flex items-center gap-1 [font-family:var(--font-display)] text-[1.75rem] font-semibold leading-tight tracking-[0.01em]">
            TOUR-IN
            <span
              class="text-[0.78em] leading-none text-(--color-brand-primary)"
              aria-hidden="true"
            >
              ✿
            </span>
          </h1>
          <p class="text-(--font-size-small)">
            Plan a route even if you are new to the province.
          </p>
        </header>

        <section
          class="grid gap-3 rounded-lg border border-[rgb(47_36_29/0.12)] bg-(--color-bg-card) p-4 shadow-(--shadow-sm)"
          aria-labelledby="start-section-title"
        >
          <h2
            id="start-section-title"
            class="[font-family:var(--font-display)] text-(--font-size-h2) font-semibold"
          >
            Start your trip
          </h2>
          <label
            id="start-search-label"
            class="block text-(--font-size-small) font-semibold"
            for="start-search-input"
            hidden={Boolean(state.start)}
          >
            Search start location
          </label>
          <div
            id="start-search-control"
            class="search-control"
            data-role="start-search"
            hidden={Boolean(state.start)}
          />
          <StartSection
            start={state.start}
            isPlanning={isPlanning}
            onClearStart={actions.clearStart}
          />
        </section>

        <section
          class="grid gap-3 rounded-lg border border-[rgb(47_36_29/0.12)] bg-(--color-bg-card) p-4 shadow-(--shadow-sm)"
          aria-labelledby="stops-section-title"
        >
          <h2
            id="stops-section-title"
            class="[font-family:var(--font-display)] text-(--font-size-h2) font-semibold"
          >
            Add destinations
          </h2>
          <div id="dest-search-control" class="search-control" />
          <StopsAndItinerarySection
            destinations={state.destinations}
            focusedDestinationId={state.focusedDestinationId}
            isPlanning={isPlanning}
            onRemove={actions.removeDestination}
            onFocus={actions.focusDestination}
          />
        </section>
      </aside>

      <main
        class="relative min-h-0 bg-(--color-bg-card-muted)"
        aria-label="Map region"
      >
        <MapSummaryOverlay
          status={state.routeStatus}
          errorMessage={state.routeError}
          routeDistanceKm={state.routeDistanceKm}
          canClear={
            Boolean(state.start) ||
            state.destinations.length > 0 ||
            state.routeCoords.length > 0
          }
          isPlanning={isPlanning}
          onRetry={actions.retryRoute}
          onClearTrip={actions.clearTrip}
        />
        <div
          id="map"
          class="h-[62vh] w-full min-[1080px]:h-full"
          role="application"
          aria-label="Route map"
        />
      </main>
    </div>
  );
}

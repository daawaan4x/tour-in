import type { PlaceRef } from "../../state/types";

interface StopsAndItinerarySectionProps {
  destinations: PlaceRef[];
  focusedDestinationId: string | null;
  isPlanning: boolean;
  onRemove(destinationId: string): void;
  onFocus(destinationId: string): void;
}

export function StopsAndItinerarySection(props: StopsAndItinerarySectionProps) {
  if (props.destinations.length === 0) {
    return null;
  }

  const iconButtonClass =
    "inline-flex h-[30px] min-h-[30px] w-[30px] min-w-[30px] shrink-0 items-center justify-center rounded-full border border-[rgb(47_36_29_/_0.14)] bg-[var(--color-bg-card)] p-0 transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease-standard)] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-bg-canvas)] disabled:opacity-[0.52]";

  return (
    <ol class="m-0 grid list-none gap-3 p-0">
      {props.destinations.map((destination, index) => {
        const isFocused = destination.id === props.focusedDestinationId;
        const handleFocus = () => {
          if (props.isPlanning) {
            return;
          }

          props.onFocus(destination.id);
        };

        return (
          <li
            key={destination.id}
            class={
              "flex items-start gap-3 rounded-[var(--radius-md)] border bg-[var(--color-bg-canvas)] p-3 transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease-standard)] " +
              (isFocused
                ? "border-[var(--color-accent-route)] shadow-[var(--shadow-focus)]"
                : "border-[rgb(47_36_29_/_0.14)]")
            }
            tabIndex={0}
            role="button"
            aria-label={"Focus stop " + (index + 1) + ": " + destination.name}
            aria-disabled={props.isPlanning ? "true" : undefined}
            onClick={handleFocus}
            onKeyDown={(event) => {
              if (event.key !== "Enter" && event.key !== " ") {
                return;
              }

              event.preventDefault();
              handleFocus();
            }}
          >
            <span class="inline-flex h-6 min-w-6 items-center justify-center rounded-[var(--radius-pill)] bg-[var(--color-bg-card-muted)] px-1 [font-family:var(--font-mono)] text-[var(--font-size-small)] font-medium text-[var(--color-text-primary)]">
              {props.isPlanning ? (
                <>
                  <span
                    class="route-pending-spinner route-pending-spinner--compact"
                    aria-hidden="true"
                  />
                  <span class="sr-only">Updating stop order</span>
                </>
              ) : (
                index + 1
              )}
            </span>
            <div class="grid flex-1 gap-0.5">
              <p class="text-[var(--font-size-small)] font-normal">{destination.name}</p>
            </div>
            <div class="flex items-center gap-1">
              <button
                class={iconButtonClass}
                type="button"
                disabled={props.isPlanning}
                onClick={(event) => {
                  event.stopPropagation();
                  props.onRemove(destination.id);
                }}
              >
                <i class="bi bi-trash3 block text-[0.9rem] leading-none" aria-hidden="true" />
                <span class="sr-only">Remove stop</span>
              </button>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

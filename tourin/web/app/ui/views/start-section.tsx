import type { PlaceRef } from "../../state/types";

interface StartSectionProps {
  start: PlaceRef | null;
  isPlanning: boolean;
  onClearStart(): void;
}

export function StartSection(props: StartSectionProps) {
  if (!props.start) {
    return null;
  }

  const iconButtonClass =
    "inline-flex h-[30px] min-h-[30px] w-[30px] min-w-[30px] shrink-0 items-center justify-center rounded-full border border-[rgb(47_36_29_/_0.14)] bg-[var(--color-bg-card)] p-0 transition-colors duration-[var(--motion-fast)] ease-[var(--motion-ease-standard)] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-bg-canvas)] disabled:opacity-[0.52]";

  return (
    <div class="grid gap-2 rounded-[var(--radius-md)] border border-[rgb(47_36_29_/_0.14)] bg-[var(--color-bg-canvas)] p-3">
      <div class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2">
        <p class="min-w-0 break-words text-[var(--font-size-small)] font-normal">
          {props.start.name}
        </p>
        <button
          class={iconButtonClass}
          type="button"
          title="Clear start"
          aria-label="Clear start"
          disabled={props.isPlanning}
          onClick={props.onClearStart}
        >
          <i class="bi bi-trash3 block text-[0.9rem] leading-none" aria-hidden="true" />
          <span class="sr-only">Clear start</span>
        </button>
      </div>
    </div>
  );
}

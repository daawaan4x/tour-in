import { GeocoderAutocomplete } from "@geoapify/geocoder-autocomplete";
import "@geoapify/geocoder-autocomplete/styles/minimal.css";

import type { PlaceRef, PlaceSource } from "../state/types";
import { normalizeGeoapifyPlace } from "../services/places";

const ILOCOS_NORTE_FILTER =
  "51b65426295a295e405923591868d23d3240f00101f901e8f516000000000092030c496c6f636f73204e6f727465";

export interface GeoapifyControl {
  setDisabled(disabled: boolean): void;
  clear(): void;
  destroy(): void;
}

interface CreateGeoapifyControlOptions {
  container: HTMLElement;
  apiKey: string;
  placeholder: string;
  source: PlaceSource;
  inputId: string;
  describedById?: string;
  clearOnSelect?: boolean;
  onSelect(place: PlaceRef): boolean | void;
}

function findInput(container: HTMLElement): HTMLInputElement | null {
  return container.querySelector("input");
}

export function createGeoapifyControl(
  options: CreateGeoapifyControlOptions,
): GeoapifyControl {
  const autocomplete = new GeocoderAutocomplete(
    options.container,
    options.apiKey,
    {
      placeholder: options.placeholder,
      lang: "en",
      limit: 5,
      filter: { place: ILOCOS_NORTE_FILTER },
    },
  );

  const applyInputAttributes = (): void => {
    const input = findInput(options.container);
    if (!input) {
      return;
    }

    input.id = options.inputId;
    input.setAttribute("autocomplete", "off");
    if (options.describedById) {
      input.setAttribute("aria-describedby", options.describedById);
    }
  };

  const clearInput = (): void => {
    const input = findInput(options.container);
    if (!input) {
      return;
    }

    input.value = "";
    input.dispatchEvent(new Event("input", { bubbles: true }));
  };

  autocomplete.on("select", (rawLocation: unknown) => {
    const place = normalizeGeoapifyPlace(rawLocation, options.source);
    if (!place) {
      return;
    }

    const shouldClear = options.onSelect(place);
    if (options.clearOnSelect && shouldClear !== false) {
      clearInput();
    }
  });

  window.setTimeout(applyInputAttributes, 0);

  return {
    setDisabled: (disabled: boolean) => {
      const input = findInput(options.container);
      if (!input) {
        return;
      }

      input.disabled = disabled;
      input.setAttribute("aria-disabled", String(disabled));
    },
    clear: clearInput,
    destroy: () => {
      options.container.replaceChildren();
    },
  };
}

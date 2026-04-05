import { render } from "preact";

import type { AppState } from "../state/types";
import { AppShell } from "./app-shell";

interface RendererMounts {
  root: HTMLElement;
}

interface RendererActions {
  clearStart(): void;
  removeDestination(destinationId: string): void;
  focusDestination(destinationId: string): void;
  retryRoute(): void;
  clearTrip(): void;
}

interface CreateAppRendererOptions {
  mounts: RendererMounts;
  actions: RendererActions;
}

export interface AppRenderer {
  render(state: AppState): void;
}

export function createAppRenderer(options: CreateAppRendererOptions): AppRenderer {
  return {
    render: (state) => {
      render(
        <AppShell
          state={state}
          actions={options.actions}
          isPlanning={state.routeStatus === "planning"}
        />,
        options.mounts.root,
      );
    },
  };
}

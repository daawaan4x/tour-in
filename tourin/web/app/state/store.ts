import type { AppState, Listener, StateUpdater } from "./types";

export interface Store {
  getState(): AppState;
  setState(updater: StateUpdater): void;
  subscribe(listener: Listener): () => void;
}

export function createStore(initialState: AppState): Store {
  let state = initialState;
  const listeners = new Set<Listener>();

  return {
    getState: () => state,
    setState: (updater) => {
      const nextState = updater(state);
      if (nextState === state) {
        return;
      }

      const previousState = state;
      state = nextState;
      listeners.forEach((listener) => listener(state, previousState));
    },
    subscribe: (listener) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
}

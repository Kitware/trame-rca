// Shared Vitest setup. The controllers under test use ResizeObserver, which is
// not available in the node test environment.
class StubResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver ??= StubResizeObserver;

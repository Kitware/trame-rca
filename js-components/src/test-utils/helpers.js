import { vi } from 'vitest';

/**
 * Minimal trame source/session pair so controllers can mount without a real
 * client. `emit` dispatches one stream packet to the subscription callback.
 */
export function fakeSession() {
  let onPacket;
  const session = {
    call: vi.fn(() => Promise.resolve()),
    subscribe: vi.fn((_topic, callback) => {
      onPacket = callback;
      return 'subscription';
    }),
    unsubscribe: vi.fn(),
  };
  return { session, emit: (packet) => onPacket([packet]) };
}

export function trameSource(session) {
  return {
    trame: {
      client: { getConnection: () => ({ getSession: () => session }) },
    },
  };
}

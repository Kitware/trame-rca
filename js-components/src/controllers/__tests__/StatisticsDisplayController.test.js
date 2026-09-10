import { afterEach, describe, expect, it, vi } from 'vitest';

import { fakeSession, trameSource } from '../../test-utils/helpers.js';

import { StatisticsDisplayController } from '../StatisticsDisplayController.js';

describe('StatisticsDisplayController', () => {
  afterEach(() => vi.useRealTimers());

  it('applies resetMsThreshold when mounted', () => {
    vi.useFakeTimers();
    vi.setSystemTime(0);
    const { session, emit } = fakeSession();
    const onStats = vi.fn();
    const controller = new StatisticsDisplayController({
      source: trameSource(session),
      resetMsThreshold: 100,
      onStats,
    });
    controller.mount({ root: {}, canvas: null });

    emit({ name: 'default', meta: { st: 0 }, content: new Uint8Array([1]) });
    vi.advanceTimersByTime(200);
    emit({ name: 'default', meta: { st: 200 }, content: new Uint8Array([1]) });

    // 200ms exceeds the threshold, so the stat window resets and no stats are emitted.
    expect(onStats).not.toHaveBeenCalled();
    controller.unmount();
  });

  it('keeps the default 1000ms reset window', () => {
    vi.useFakeTimers();
    vi.setSystemTime(0);
    const { session, emit } = fakeSession();
    const onStats = vi.fn();
    const controller = new StatisticsDisplayController({
      source: trameSource(session),
      onStats,
    });
    controller.mount({ root: {}, canvas: null });

    emit({ name: 'default', meta: { st: 0 }, content: new Uint8Array([1]) });
    vi.advanceTimersByTime(500);
    emit({ name: 'default', meta: { st: 500 }, content: new Uint8Array([1]) });

    // 500ms is below the default threshold, so the stat window is preserved.
    expect(onStats).toHaveBeenCalledTimes(1);
    controller.unmount();
  });
});

import { afterEach, describe, expect, it, vi } from 'vitest';

import { fakeSession, trameSource } from '../../test-utils/helpers.js';

import { RemoteControlledAreaController } from '../RemoteControlledAreaController.js';

describe('RemoteControlledAreaController', () => {
  afterEach(() => vi.useRealTimers());

  it('pushes size requests before mount', () => {
    vi.useFakeTimers();
    const { session } = fakeSession();
    const controller = new RemoteControlledAreaController({
      source: trameSource(session),
      name: 'slider-test',
      origin: 'anonymous',
    });

    // Descendants request the video header during their own mount, which runs
    // before the parent's; the throttle must already be usable.
    controller.pushSize({ videoHeader: 1 });

    expect(session.call).toHaveBeenCalledWith('trame.rca.size', [
      'slider-test',
      'anonymous',
      { w: 10, h: 10, p: 1, videoHeader: 1 },
    ]);
  });
});

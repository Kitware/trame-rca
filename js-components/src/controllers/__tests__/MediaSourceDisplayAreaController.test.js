import { describe, expect, it, vi } from 'vitest';

import { fakeSession, trameSource } from '../../test-utils/helpers.js';

import { MediaSourceDisplayAreaController } from '../MediaSourceDisplayAreaController.js';

describe('MediaSourceDisplayAreaController', () => {
  it('does not throw on a video chunk received before the decoder exists', async () => {
    const { session, emit } = fakeSession();
    const onPushSize = vi.fn();
    const controller = new MediaSourceDisplayAreaController({
      source: trameSource(session),
      onPushSize,
    });
    controller.mount(null);
    expect(onPushSize).toHaveBeenCalledWith({ videoHeader: 1 });

    await expect(
      emit({
        name: 'default',
        meta: { type: 'video/webm' },
        content: new Uint8Array([0, 0, 0, 0]),
      }),
    ).resolves.toBeUndefined();
    expect(onPushSize).toHaveBeenCalledTimes(1);
    controller.unmount();
  });
});

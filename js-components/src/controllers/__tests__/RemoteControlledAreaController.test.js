import { afterEach, describe, expect, it, vi } from 'vitest';
import vtkRenderWindowInteractor from '@kitware/vtk.js/Rendering/Core/RenderWindowInteractor';

vi.mock('@kitware/vtk.js/Rendering/Core/RenderWindowInteractor', () => ({
  default: {
    newInstance: vi.fn(() => ({
      setInteractorStyle: vi.fn(),
      initialize: vi.fn(),
      bindEvents: vi.fn(),
      unbindEvents: vi.fn(),
    })),
  },
}));

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

  it('uses the current position after moving without resizing', () => {
    const { session } = fakeSession();
    const controller = new RemoteControlledAreaController({
      source: trameSource(session),
    });
    let rect = { left: 100, top: 50, width: 400, height: 300 };
    const root = { getBoundingClientRect: () => rect };
    controller.mount(root);
    try {
      // Start with the same size and offset a ResizeObserver would record.
      controller.currentSizeUpdateEvent = { w: 400, h: 300, p: 1 };
      controller.currentOffset = [100, 50];
      const position =
        vtkRenderWindowInteractor.newInstance.mock.lastCall[0]
          ._getScreenEventPositionFor;
      expect(position({ clientX: 125, clientY: 90 })).toEqual({
        x: 25,
        y: 260,
        z: 0,
      });

      // Dock the area elsewhere without delivering a resize notification.
      rect = { ...rect, left: 500, top: 200 };
      expect(position({ clientX: 525, clientY: 240 })).toEqual({
        x: 25,
        y: 260,
        z: 0,
      });

      // Scrolling also changes viewport-relative coordinates without a resize.
      rect = { ...rect, left: 460, top: 120 };
      expect(position({ clientX: 485, clientY: 160 })).toEqual({
        x: 25,
        y: 260,
        z: 0,
      });
      expect(session.call).not.toHaveBeenCalled();
    } finally {
      controller.unmount();
    }
  });
});

import { describe, expect, it, vi } from 'vitest';
import { EventThrottle } from '../EventThrottle'; // adjust path as needed

describe('throttle.compressEvents', () => {
  const throttle = new EventThrottle(null, 50);

  it('can compress mouse move events', () => {
    const mouseMoveEvents = [
      { w: 1364, h: 638, type: 'MouseMove', action: 'up', x: 50, y: 268 },
      { w: 1364, h: 638, type: 'MouseMove', action: 'up', x: 60, y: 264 },
      { w: 1364, h: 638, type: 'MouseMove', action: 'up', x: 74, y: 266 },
    ];

    const result = throttle.compressEvents(mouseMoveEvents);
    expect(result).toEqual([mouseMoveEvents[2]]);
  });

  it("doesn't compress start/stop events", () => {
    const events = [
      { type: 'StartInteractionEvent' },
      { type: 'EndInteractionEvent' },
    ];
    expect(throttle.compressEvents(events)).toEqual(events);
  });

  it('returns empty when input is empty', () => {
    expect(throttle.compressEvents([])).toEqual([]);
  });

  it('returns single event when input has one', () => {
    const event = { type: 'StartInteractionEvent' };
    expect(throttle.compressEvents([event])).toEqual([event]);
  });

  it('compresses duplicated messages', () => {
    const events = [
      { type: 'StartInteractionEvent' },
      { type: 'EndInteractionEvent' },
      { type: 'EndInteractionEvent' },
      { type: 'EndInteractionEvent' },
      { type: 'EndInteractionEvent' },
    ];
    const expected = [
      { type: 'StartInteractionEvent' },
      { type: 'EndInteractionEvent' },
    ];
    expect(throttle.compressEvents(events)).toEqual(expected);
  });

  it("doesn't compress wheel events", () => {
    const events = [
      { w: 1364, h: 638, type: 'StartMouseWheel' },
      { w: 1364, h: 638, type: 'StartMouseWheel' },
      { w: 1364, h: 638, type: 'MouseWheel' },
      { w: 1364, h: 638, type: 'MouseWheel' },
      { w: 1364, h: 638, type: 'MouseWheel' },
      { w: 1364, h: 638, type: 'MouseWheel' },
      { w: 1364, h: 638, type: 'EndMouseWheel' },
      { w: 1364, h: 638, type: 'EndMouseWheel' },
    ];

    const expected = [
      { w: 1364, h: 638, type: 'StartMouseWheel' },
      { w: 1364, h: 638, type: 'MouseWheel' },
      { w: 1364, h: 638, type: 'MouseWheel' },
      { w: 1364, h: 638, type: 'MouseWheel' },
      { w: 1364, h: 638, type: 'MouseWheel' },
      { w: 1364, h: 638, type: 'EndMouseWheel' },
    ];

    expect(throttle.compressEvents(events)).toEqual(expected);
  });
});

describe('EventThrottle async processing', () => {
  it('triggers process with compressed events', async () => {
    const mock = vi.fn();
    const throttle = new EventThrottle(mock, 50);

    const events = Array(10).fill({ type: 'EndInteractionEvent' });
    events.forEach((event) => throttle.sendEvent(event));

    await new Promise((resolve) => setTimeout(resolve, 100));

    // Expect 2 Calls, one for the first event, second for the compressed following events.
    expect(mock).toHaveBeenCalledTimes(2);
    expect(mock).toHaveBeenCalledWith({ type: 'EndInteractionEvent' });
  });

  it('clears event queue when processing following batch of events', async () => {
    const mock = vi.fn();
    const throttle = new EventThrottle(mock, 50);

    // Send first event to start event processing loop
    let events = Array(1).fill({ type: 'Event1' });
    events.forEach((event) => throttle.sendEvent(event));

    // Wait less than throttle time out and reset mock
    await new Promise((resolve) => setTimeout(resolve, 25));
    mock.mockReset();

    // Send second batch of events
    events = Array(10).fill({ type: 'Event2' });
    events.forEach((event) => throttle.sendEvent(event));
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Expect 1 event call corresponding to last compressed batch of events
    expect(mock).toHaveBeenCalledTimes(1);
    expect(mock).toHaveBeenCalledWith({ type: 'Event2' });
  });
});

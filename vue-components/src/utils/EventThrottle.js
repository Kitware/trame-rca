function yieldAsync() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

async function sleep(timeMS) {
  if (timeMS < 0) {
    return;
  }
  return new Promise((resolve) => setTimeout(resolve, timeMS));
}

/**
 * Class responsible for throttling and compressing the interaction events before they are handled by the server.
 * The class creates a queue of events to be processed and before sending the events compress identical events
 * with different screen coordinates.
 */
export class EventThrottle {
  constructor(processCallback, throttleTimeMs = 100) {
    this.eventQueue = [];
    this.processing = false;
    this.throttleTimeMs = throttleTimeMs;
    this.processCallback = processCallback;
    this.eventKeysToIgnore = new Set(['x', 'y']);
  }

  /**
   * Compress the input events if they are the same (same object keys) with different X, Y screen coordinates.
   * The MouseWheel event type is never compressed.
   *
   * @param events the list of events to compress
   * @returns {*|*[]} the compressed list of events to send to the server
   */
  compressEvents(events) {
    if (events.length < 2) return [...events];

    const compressed = [];
    for (let i = 0; i < events.length; i++) {
      const current = events[i];
      const next = events[i + 1];

      if (next && this.canCompressEvents(current, next)) {
        continue;
      }
      compressed.push(current);
    }
    return compressed;
  }

  canCompressEvents(prev, next) {
    if (prev.type === 'MouseWheel' || next.type === 'MouseWheel') return false;
    if (Object.keys(prev).length !== Object.keys(next).length) return false;

    for (let key in prev) {
      if (this.eventKeysToIgnore.has(key)) continue;
      if (prev[key] !== next[key]) return false;
    }
    return true;
  }

  /**
   * Push the input event to the processing queue.
   * If the queue is empty, the event is directly sent to the server for processing.
   *
   * If the queue is not empty and events are being processed, the event is pushed to queue for later processing.
   */
  sendEvent(event) {
    this.eventQueue.push(event);
    if (!this.processing) {
      this.processing = true;
      this._processEventQueue().catch((err) => {
        console.error('Error in _processEventQueue:', err);
        this.processing = false;
      });
    }
  }

  async _processEventQueue() {
    const compressedEvents = this.compressEvents(this.eventQueue);
    this.eventQueue.length = 0;

    const t0 = Date.now();

    for (const event of compressedEvents) {
      await this.processCallback(event);
      await yieldAsync();
    }

    await sleep(this.throttleTimeMs - Date.now() + t0);

    if (this.eventQueue.length > 0) {
      await this._processEventQueue();
    } else {
      this.processing = false;
    }
  }
}

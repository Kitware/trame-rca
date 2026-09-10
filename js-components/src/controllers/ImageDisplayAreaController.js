import { FPSMonitor } from '../utils/FPSMonitor.js';
import { ImageFrame } from '../utils/ImageFrame.js';
import { getSession, subscribe, unsubscribe } from '../session.js';

const SUPPORTED_IMAGE_TYPES = {
  'image/apng': 1,
  'image/avif': 1,
  'image/gif': 1,
  'image/jpeg': 1,
  'image/png': 1,
  'image/svg+xml': 1,
  'image/webp': 1,
};

/**
 * Logic for the image display area: frame pool, stream
 * subscription and optional fps/bandwidth monitoring.
 */
export class ImageDisplayAreaController {
  constructor({
    source,
    name = 'default',
    poolSize = 4,
    monitor = 0,
    onStats,
    onDisplayUrl,
    onHasContent,
  } = {}) {
    this.source = source;
    this.name = name;
    this.poolSize = poolSize;
    this.monitor = monitor;
    this.onStats = onStats;
    this.onDisplayUrl = onDisplayUrl;
    this.onHasContent = onHasContent;

    this.fpsMonitor = new FPSMonitor(10, 10);
    this.frames = [];
    this.nextFrameIndex = 0;
    this.session = null;
    this.subscription = null;
    this.handler = null;

    this.updatePoolSize();
    this.updateMonitorWindow();
  }

  updatePoolSize() {
    while (this.frames.length < this.poolSize) {
      this.frames.push(
        new ImageFrame((img, url) => {
          this.onDisplayUrl?.(url);
          this.onHasContent?.(true);
        })
      );
    }
    while (this.frames.length > this.poolSize) {
      this.frames.pop();
    }
  }

  updateMonitorWindow() {
    const bufferSize = Math.max(10, this.monitor);
    this.fpsMonitor.windowSize = bufferSize;
    this.fpsMonitor.windowStatSize = bufferSize;
  }

  resetContent() {
    this.onHasContent?.(false);
  }

  setName(value) {
    this.name = value;
  }

  mount() {
    this.session = getSession(this.source);
    this.handler = ([{ name, meta, content }]) => {
      if (this.name !== name) {
        return;
      }
      if (SUPPORTED_IMAGE_TYPES[meta.type]) {
        const nextIdx = (this.nextFrameIndex + 1) % this.frames.length;
        const frame = this.frames[nextIdx];
        if (frame.update(meta.type, content)) {
          this.nextFrameIndex = nextIdx;
          if (this.monitor) {
            const serverTime = meta.st;
            const contentSize = content.length;
            const stats = this.fpsMonitor.addEntry(serverTime, contentSize);
            if (stats) {
              const { avgFps, totalSize } = stats;
              this.onStats?.({
                fps: Math.round(avgFps),
                bps: Math.floor(totalSize),
                st: serverTime,
              });
            }
          }
        }
      } else {
        this.onHasContent?.(false);
      }
    };
    this.subscription = subscribe(
      this.session,
      'trame.rca.topic.stream',
      this.handler
    );
  }

  unmount() {
    unsubscribe(this.session, this.subscription);
    this.subscription = null;
  }
}

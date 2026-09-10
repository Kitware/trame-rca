import { ImageFrame } from '../utils/ImageFrame.js';
import { getSession, subscribe, unsubscribe } from '../session.js';

/**
 * Frame pool and stream subscription for `ImageStream`.
 * The owner provides an `onImage` callback used to publish the latest decoded
 * image to consumers (e.g. `ImageRegion`).
 */
export class ImageStreamController {
  constructor({ source, name = 'default', poolSize = 4, onImage } = {}) {
    this.source = source;
    this.name = name;
    this.poolSize = poolSize;
    this.onImage = onImage;

    this.frames = [];
    this.nextFrameIndex = 0;
    this.session = null;
    this.subscription = null;
    this.handler = null;

    this.updatePoolSize();
  }

  setName(value) {
    this.name = value;
  }

  updatePoolSize() {
    while (this.frames.length < this.poolSize) {
      this.frames.push(new ImageFrame((img) => this.onImage?.(img)));
    }
    while (this.frames.length > this.poolSize) {
      this.frames.pop();
    }
  }

  nextFrame() {
    this.nextFrameIndex = (this.nextFrameIndex + 1) % this.frames.length;
    return this.frames[this.nextFrameIndex];
  }

  mount() {
    this.session = getSession(this.source);
    this.handler = ([{ name, meta, content }]) => {
      if (this.name === name) {
        this.nextFrame().update(meta.type, content);
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

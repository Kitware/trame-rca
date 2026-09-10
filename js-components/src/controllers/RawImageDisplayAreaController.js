import { drawRawImage } from '../media/rawImage.js';
import { getSession, subscribe, unsubscribe } from '../session.js';

/**
 * Logic for the raw RGB24 / RGBA32 display area.
 */
export class RawImageDisplayAreaController {
  constructor({ source, name = 'default', onHasContent } = {}) {
    this.source = source;
    this.name = name;
    this.onHasContent = onHasContent;

    this.canvas = null;
    this.session = null;
    this.subscription = null;
    this.handler = null;
  }

  setName(value) {
    this.name = value;
  }

  mount(canvas) {
    this.canvas = canvas;
    this.session = getSession(this.source);
    this.handler = async ([{ name, meta, content }]) => {
      if (this.name !== name) {
        return;
      }
      const handled = await drawRawImage(this.canvas, meta, content);
      this.onHasContent?.(handled);
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
    this.canvas = null;
  }
}

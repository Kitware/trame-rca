import { DecoderWorker } from '../utils/decoder.js';
import { getSession, subscribe, unsubscribe } from '../session.js';

/**
 * Logic for the WebCodecs video decoder display area.
 */
export class VideoDecoderDisplayAreaController {
  constructor({ source, name = 'default', onSupported } = {}) {
    this.source = source;
    this.name = name;
    this.onSupported = onSupported;

    this.isSupported =
      typeof window !== 'undefined' && 'VideoFrame' in window;
    this.worker = null;
    this.session = null;
    this.subscription = null;
    this.handler = null;
  }

  setName(value) {
    this.name = value;
  }

  mount(canvas) {
    this.worker = new DecoderWorker();
    if (!this.isSupported) {
      this.onSupported?.(false);
      return;
    }
    this.onSupported?.(true);
    this.worker.bindCanvas(canvas);

    this.handler = async ([{ name, meta, content }]) => {
      // when we do not get octet-stream or valid codec, terminate worker.
      if (
        !meta.type.includes('application/octet-stream') ||
        !meta.codec.length ||
        meta.codec.includes('unknown')
      ) {
        return;
      }

      if (this.name === name && meta.codec.length) {
        this.worker.setContentType(meta.codec, meta.w, meta.h);
        const data = content.buffer
          ? content
          : new Uint8Array(await content.arrayBuffer());
        this.worker.pushChunk(meta.st, meta.key, data);
      }
    };

    this.session = getSession(this.source);
    if (this.session) {
      this.session.call('trame.rca.reset', [this.name]);
      this.subscription = subscribe(
        this.session,
        'trame.rca.topic.stream',
        this.handler
      );
    }
  }

  unmount() {
    if (this.worker) {
      this.worker.terminate();
      this.worker = null;
    }
    unsubscribe(this.session, this.subscription);
    this.subscription = null;
  }
}

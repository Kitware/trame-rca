import { DecoderWorker } from '../utils/decoder.js';
import { codecFamily, negotiateCodec } from '../utils/negotiate.js';
import { getSession, subscribe, unsubscribe } from '../session.js';

/**
 * Logic for the WebCodecs video decoder display area.
 */
export class VideoDecoderDisplayAreaController {
  constructor({ source, name = 'default', onSupported, onError } = {}) {
    this.source = source;
    this.name = name;
    this.onSupported = onSupported;
    this.onError = onError;
    this.rejected = [];

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

  async negotiate() {
    if (!this.session) {
      return;
    }
    const info = await negotiateCodec(this.session, this.name, this.rejected);
    this.onError?.(info.error ? `No common video codec (${info.error})` : null);
  }

  // browser rejected what the server emits: retry without that codec family
  onDecoderError() {
    const family = codecFamily(this.worker?.codec);
    if (family && !this.rejected.includes(family)) {
      this.rejected.push(family);
      this.worker.codec = '';
      this.negotiate();
    }
  }

  mount(canvas) {
    this.worker = new DecoderWorker(() => this.onDecoderError());
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
      this.subscription = subscribe(
        this.session,
        'trame.rca.topic.stream',
        this.handler
      );
      this.negotiate();
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

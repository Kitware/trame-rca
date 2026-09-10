import { MseVideoDecoder } from '../media/MseVideoDecoder.js';
import { getSession, subscribe, unsubscribe } from '../session.js';

/**
 * Logic for the Media Source video display area.
 */
export class MediaSourceDisplayAreaController {
  constructor({ source, name = 'default', onHasContent, onPushSize } = {}) {
    this.source = source;
    this.name = name;
    this.onHasContent = onHasContent;
    this.onPushSize = onPushSize;

    this.videoElement = null;
    this.decoder = null;
    this.session = null;
    this.subscription = null;
    this.received = 0;
  }

  mount(videoElement) {
    this.videoElement = videoElement;
    this.session = getSession(this.source);

    this.pushChunk = (bytes, mime) => {
      const fourcc = Array.from(new Uint8Array(bytes).slice(0, 4))
        .map((byte) => byte.toString(16))
        .join('');
      if (fourcc == '1a45dfa3' && mime.includes('webm')) {
        console.log('detected ebml fourcc');
        if (this.decoder) {
          this.decoder.exit();
        }
        // create a video decoder with that video tag
        this.decoder = new MseVideoDecoder(this.videoElement);
        this.decoder.initSegment = new Uint8Array(bytes);
      } else if (this.decoder && this.decoder.mime !== mime) {
        console.log('detected mime change');
        this.requestInitializationSegment();
      } else if (this.decoder) {
        this.decoder.queueChunk(bytes);
        this.onHasContent?.(true);
      }
    };

    this.onChunkAvailable = async ([{ name, meta, content }]) => {
      if (!meta.type.includes('video/')) {
        this.onHasContent?.(false);
        return;
      }
      if (this.name === name) {
        this.received += 1;
        const v = content.buffer
          ? content
          : new Uint8Array(await content.arrayBuffer());
        this.pushChunk(v, meta.type);
        this.onHasContent?.(true);
      }
    };

    if (this.session) {
      this.subscription = subscribe(
        this.session,
        'trame.rca.topic.stream',
        this.onChunkAvailable
      );
      this.requestInitializationSegment();
    }
  }

  setName(value) {
    this.name = value;
  }

  requestInitializationSegment() {
    this.onPushSize?.({ videoHeader: 1 });
  }

  unmount() {
    unsubscribe(this.session, this.subscription);
    this.subscription = null;
    if (this.decoder) {
      this.decoder.exit();
    }
  }
}

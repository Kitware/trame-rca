/**
 * Media Source Extensions based video decoder.
 *
 * Buffers media segments until the SourceBuffer can accept them and plays the
 * result through a <video> element.
 */
export class MseVideoDecoder {
  constructor(videoElement, mime = 'video/webm; codecs=vp09.00.10.08') {
    this.videoElement = videoElement;
    this.mime = mime;
    this.sourceBuffer = null;
    this.mediaSource = null;
    this.initSegment = null;
    this.mediaSegments = [];
    this.loaded = 0;

    if ('MediaSource' in window) {
      this.mediaSource = new MediaSource();
      this.videoElement.src = URL.createObjectURL(this.mediaSource);
      // sourceopen -> append initSegment -> listen to updateend of source buffer.
      this.mediaSource.addEventListener('sourceopen', () => {
        if (MediaSource.isTypeSupported(this.mime)) {
          this.initSourceBuffer();
        } else {
          console.error(`Unsupported MIME type or codec: ${this.mime}`);
        }
      });
    } else {
      console.error('The Media Source Extensions API is not supported.');
    }
  }

  initSourceBuffer() {
    this.sourceBuffer = this.mediaSource.addSourceBuffer(this.mime);
    this.sourceBuffer.mode = 'sequence';
    if (this.initSegment) {
      this.sourceBuffer.appendBuffer(this.initSegment);
    } else {
      console.error('Need initialization segment');
    }
    this.sourceBuffer.onupdateend = () => {
      if (!this.mediaSegments.length) {
        return;
      } else if (this.sourceBuffer.updating === false) {
        this.sourceBuffer.appendBuffer(this.mediaSegments.shift());
        this.loaded += 1;
      }
    };
  }

  queueChunk(data) {
    if (
      this.mediaSource.readyState === 'open' &&
      this.sourceBuffer &&
      this.sourceBuffer.updating === false
    ) {
      this.sourceBuffer.appendBuffer(data);
      this.loaded += 1;
    } else {
      this.mediaSegments.push(data);
    }
  }

  exit() {
    this.sourceBuffer?.abort();
    this.mediaSource?.endOfStream();
    this.videoElement.play();
    URL.revokeObjectURL(this.videoElement.src);
  }
}

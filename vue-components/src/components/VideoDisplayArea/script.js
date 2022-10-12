class VideoDecoder {
  constructor(videoElement) {
    this.videoElement = videoElement;
    // TODO: when we add other codecs, the media source and source buffer should reinitialize when mime changes.
    this.mime = 'video/webm; codecs=vp09.00.10.08';
    this.sourceBuffer = null;
    this.mediaSource = null;
    this.queue = [];
    this.loaded = 0;
    // redefine push such that it appends only when it is safe to do so.
    // if it is not safe to append the source buffer, push the buffer into queue.
    this.queue.push = (chunk) => {
      if (
        this.mediaSource.readyState === 'open' &&
        this.sourceBuffer &&
        this.sourceBuffer.updating === false
      ) {
        this.sourceBuffer.appendBuffer(chunk);
        this.loaded += 1;
      } else {
        Array.prototype.push.call(this, chunk);
      }
    };
    if ('MediaSource' in window) {
      this.mediaSource = new MediaSource();
      this.videoElement.src = URL.createObjectURL(this.mediaSource);
      this.mediaSource.addEventListener('sourceopen', () => {
        URL.revokeObjectURL(this.videoElement.src);
        console.log(`media-source readyState=${this.mediaSource.readyState}`);
        this.initBuffer();
      });
    } else {
      console.error('The Media Source Extensions API is not supported.');
    }
  }

  initBuffer() {
    if (MediaSource.isTypeSupported(this.mime)) {
      console.log(`addSourceBuffer: ${this.mime}`);
      this.sourceBuffer = this.mediaSource.addSourceBuffer(this.mime);
      this.sourceBuffer.mode = 'sequence';
    } else {
      console.error(`Unsupported MIME type or codec: ${this.mime}`);
    }
  }

  reset() {
    if (this.videoElement.src) {
      URL.revokeObjectURL(this.videoElement.src);
    }
    this.sourceBuffer = null;
    this.mediaSource = null;
    this.queue.length = 0;
  }

  queueChunk(content) {
    console.log(`q-add length=${this.queue.length}`);
    this.queue.push(content);
  }

  exit() {
    URL.revokeObjectURL(this.videoElement.src);
  }
}

export default {
  name: 'VideoDisplayArea',
  props: {
    name: {
      type: String,
      default: 'default',
    },
    origin: {
      type: String,
      default: 'anonymous',
    },
  },
  data() {
    return {
      loaded: 0,
      received: 0,
    };
  },
  created() {
    this.pushChunk = (bytes) => {
      console.log(`pushChunk l=${this.loaded} r=${this.received} d=${this.received - this.loaded}`);
      this.decoder.queueChunk(bytes);
      this.loaded = this.decoder.loaded;
    };
  },
  mounted() {
    // grab reference to <video></video> tag
    this.videoElement = this.$el.querySelector('video');
    // create a video decoder with that video tag
    this.decoder = new VideoDecoder(this.videoElement);

    this.onChunkAvailable = ([{ name, meta, content }]) => {
      // TODO: get mime type from meta and handle that mimetype
      if (this.name === name) {
        this.received += 1;
        console.log(`onChunkAvailable type=${meta.type}`);
        content.arrayBuffer().then((v) => this.pushChunk(v));
      }
    };
    if (this.trame) {
      this.wslinkSubscription = this.trame.client
        .getConnection()
        .getSession()
        .subscribe('trame.rca.topic.stream', this.onChunkAvailable);
    }
  },
  beforeUnmount() {
    // unsub trame.rca.topic.stream
    if (this.wslinkSubscription) {
      if (this.trame) {
        this.trame.client
          .getConnection()
          .getSession()
          .unsubscribe(this.wslinkSubscription);
        this.wslinkSubscription = null;
        // shutdown decoder
        this.decoder.exit();
      }
    }
  },
  inject: ['trame'],
};

class VideoDecoder {
  constructor(videoElement, mime = 'video/webm; codecs=vp09.00.10.08') {
    this.videoElement = videoElement;
    this.mime = mime;
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
      hasContent: false,
      loaded: 0,
      received: 0,
    };
  },
  methods: {
    requestKeyframeHeader() {
      console.log('requestKeyframeHeader');
      if (this.rcaPushSize) {
        console.log('push size with video header');
        this.rcaPushSize({ videoHeader: 1 });
      }
    },
  },
  created() {
    console.log('created video vue component');
    this.pushChunk = (bytes, mime) => {
      console.log(
        `pushChunk l=${this.loaded} r=${this.received} d=${this.received -
          this.loaded}`
      );
      if (this.decoder.mime !== mime) {
        this.decoder.reset();
        this.decoder = new VideoDecoder(this.$el, mime);
        this.requestKeyframeHeader();
      }
      this.decoder.queueChunk(bytes);
      this.loaded = this.decoder.loaded;
      this.hasContent = true;
    };
  },
  mounted() {
    console.log('mounted video vue component');
    // create a video decoder with that video tag
    this.decoder = new VideoDecoder(this.$el);

    this.onChunkAvailable = ([{ name, meta, content }]) => {
      // TODO: get mime type from meta and handle that mimetype
      if (this.name === name && meta.type.includes('video/')) {
        this.received += 1;
        console.log(`onChunkAvailable type=${meta.type}`);
        content.arrayBuffer().then((v) => this.pushChunk(v, meta.type));
      }
    };
    if (this.trame) {
      this.wslinkSubscription = this.trame.client
        .getConnection()
        .getSession()
        .subscribe('trame.rca.topic.stream', this.onChunkAvailable);

      this.requestKeyframeHeader();
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
  inject: ['trame', 'rcaPushSize'],
};

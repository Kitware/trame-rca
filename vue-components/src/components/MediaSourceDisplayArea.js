class VideoDecoder {
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
      // sourceopen -> append initSegemnt -> listen to updateend of source buffer.
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
    this.sourceBuffer.abort();
    this.mediaSource.endOfStream();
    this.videoElement.play();
    URL.revokeObjectURL(this.videoElement.src);
  }
}

export default {
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
  expose: ['requestInitializationSegment'],
  methods: {
    requestInitializationSegment() {
      if (this.rcaPushSize) {
        this.rcaPushSize({ videoHeader: 1 });
      }
    },
    cleanup() {
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
  },
  created() {
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
        this.decoder = new VideoDecoder(this.$el);
        this.decoder.initSegment = new Uint8Array(bytes);
      } else if (this.decoder.mime !== mime) {
        console.log('detected mime change');
        this.requestInitializationSegment();
      } else {
        this.decoder.queueChunk(bytes);
        this.loaded = this.decoder.loaded;
        this.hasContent = true;
      }
    };
  },
  mounted() {
    this.onChunkAvailable = ([{ name, meta, content }]) => {
      if (!meta.type.includes('video/')) {
        this.hasContent = false;
        return;
      }
      if (this.name === name) {
        this.received += 1;
        content.arrayBuffer().then((v) => this.pushChunk(v, meta.type));
        this.hasContent = true;
      }
    };
    if (this.trame) {
      this.wslinkSubscription = this.trame.client
        .getConnection()
        .getSession()
        .subscribe('trame.rca.topic.stream', this.onChunkAvailable);
      this.requestInitializationSegment();
    }
  },
  beforeUnmount() {
    this.cleanup();
  },
  beforeDestroy() {
    this.cleanup();
  },
  inject: ['trame', 'rcaPushSize'],
  template: `
    <video autoplay="autoplay" muted="muted" v-show="hasContent">
      Your browser does not support the video tag.
    </video>
  `,
};

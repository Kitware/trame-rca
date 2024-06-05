import { DecoderWorker } from '../utils/decoder';

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
      isSupported: 'VideoFrame' in window,
    };
  },
  expose: [''],
  methods: {
    cleanup() {
      if (this.worker) {
        this.worker.terminate();
        this.worker = null;
      }

      // unsub trame.rca.topic.stream
      if (this.wslinkSubscription) {
        if (this.trame) {
          this.trame.client
            .getConnection()
            .getSession()
            .unsubscribe(this.wslinkSubscription);
          this.wslinkSubscription = null;
        }
      }
    },
  },
  mounted() {
    this.worker = new DecoderWorker();
    if (this.isSupported) {
      const canvas = this.$el.querySelector('.js-canvas');
      this.worker.bindCanvas(canvas);

      this.onChunkAvailable = ([{ name, meta, content }]) => {
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
          content.arrayBuffer().then((data) => {
            this.worker.pushChunk(meta.st, meta.key, data);
          });
        }
      };

      if (this.trame) {
        this.wslinkSubscription = this.trame.client
          .getConnection()
          .getSession()
          .subscribe('trame.rca.topic.stream', this.onChunkAvailable);
      }
    }
  },
  // support both vue2 and vue3 unmount callbacks
  beforeUnmount() {
    this.cleanup();
  },
  beforeDestroy() {
    this.cleanup();
  },
  inject: ['trame', 'rcaPushSize'],
  template: `
    <div>
      <h1 v-if="!isSupported">WebCodecs API is not supported.</h1>
      <canvas class="js-canvas"></canvas>
    </div>
  `,
};

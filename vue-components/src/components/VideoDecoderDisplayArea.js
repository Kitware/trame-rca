import { VideoDecoderDisplayAreaController } from 'trame-rca-js';

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
  watch: {
    name(v) {
      this.controller?.setName(v);
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
      this.controller?.unmount();
    },
  },
  mounted() {
    this.controller = new VideoDecoderDisplayAreaController({
      source: this,
      name: this.name,
      onSupported: (value) => {
        this.isSupported = value;
      },
    });
    const canvas = this.$el.querySelector('.js-canvas');
    this.controller.mount(canvas);
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
    <div class="video-decoder-display-area">
      <h1 v-if="!isSupported">WebCodecs API is not supported.</h1>
      <canvas class="js-canvas"></canvas>
    </div>
  `,
};

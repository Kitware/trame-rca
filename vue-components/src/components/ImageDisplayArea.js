import { ImageDisplayAreaController } from 'trame-rca-js';

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
    poolSize: {
      type: Number,
      default: 4,
    },
    imageStyle: {
      type: Object,
      default: () => ({ width: '100%' }),
    },
    monitor: {
      type: Number,
      default: 0,
    },
  },
  watch: {
    name(v) {
      this.controller?.setName(v);
    },
    poolSize(v) {
      this.controller.poolSize = v;
      this.controller.updatePoolSize();
    },
    monitor(v) {
      this.controller.monitor = v;
      this.controller.updateMonitorWindow();
    },
  },
  data() {
    return {
      hasContent: false,
      displayURL: '',
    };
  },
  expose: ['resetContent', 'updatePoolSize'],
  methods: {
    resetContent() {
      this.controller?.resetContent();
    },
    updatePoolSize() {
      this.controller?.updatePoolSize();
    },
    cleanup() {
      this.controller?.unmount();
    },
  },
  created() {
    this.controller = new ImageDisplayAreaController({
      source: this,
      name: this.name,
      poolSize: this.poolSize,
      monitor: this.monitor,
      onStats: (stats) => this.$emit('stats', stats),
      onDisplayUrl: (url) => {
        this.displayURL = url;
      },
      onHasContent: (value) => {
        this.hasContent = value;
      },
    });
    this.controller.mount();
  },
  // support both vue2 and vue3 cleanup functions
  beforeDestroy() {
    this.cleanup();
  },
  beforeUnmount() {
    this.cleanup();
  },
  inject: ['trame'],
  template: `<slot><img class="image-display-area" :style="imageStyle" :src="displayURL" v-show="hasContent" draggable="false" /></slot>`,
};

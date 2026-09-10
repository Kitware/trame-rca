import { RawImageDisplayAreaController } from 'trame-rca-js';

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
    imageStyle: {
      type: Object,
      default: () => ({ width: '100%' }),
    },
  },
  watch: {
    name(v) {
      this.controller?.setName(v);
    },
  },
  data() {
    return {
      hasContent: false,
    };
  },
  methods: {
    cleanup() {
      this.controller?.unmount();
    },
  },
  mounted() {
    this.controller = new RawImageDisplayAreaController({
      source: this,
      name: this.name,
      onHasContent: (value) => {
        this.hasContent = value;
      },
    });
    this.controller.mount(this.$el);
  },
  // support both vue2 and vue3 unmount callbacks
  beforeDestroy() {
    this.cleanup();
  },
  beforeUnmount() {
    this.cleanup();
  },
  inject: ['trame'],
  template: `
    <canvas class="raw-image-display-area js-canvas" :style="imageStyle" v-show="hasContent"></canvas>
  `,
};

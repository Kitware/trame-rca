import { MediaSourceDisplayAreaController } from 'trame-rca-js';

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
      hasContent: false,
    };
  },
  expose: ['requestInitializationSegment'],
  methods: {
    requestInitializationSegment() {
      this.controller?.requestInitializationSegment();
    },
    cleanup() {
      this.controller?.unmount();
    },
  },
  mounted() {
    this.controller = new MediaSourceDisplayAreaController({
      source: this,
      name: this.name,
      onHasContent: (value) => {
        this.hasContent = value;
      },
      onPushSize: (addOn) => this.rcaPushSize?.(addOn),
    });
    this.controller.mount(this.$el);
  },
  beforeUnmount() {
    this.cleanup();
  },
  beforeDestroy() {
    this.cleanup();
  },
  inject: ['trame', 'rcaPushSize'],
  template: `
    <video class="media-source-display-area" autoplay="autoplay" muted="muted" v-show="hasContent">
      Your browser does not support the video tag.
    </video>
  `,
};

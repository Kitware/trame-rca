import { FPSMonitor } from '../utils/FPSMonitor';

class ImageFrame {
  constructor(vueComponent) {
    this.vueComponent = vueComponent;
    this.img = new Image();
    this.url = '';
    this.blob = null;

    this.img.addEventListener('load', () => {
      this.vueComponent.displayURL = this.url;
      this.vueComponent.hasContent = true;
    });
  }

  update(type, content) {
    window.URL.revokeObjectURL(this.url);
    this.blob = new Blob([content], { type });
    this.url = URL.createObjectURL(this.blob);
    this.img.src = this.url;
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
    poolSize() {
      this.updatePoolSize();
    },
    monitor() {
      this.updateMonitorWindow();
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
      this.hasContent = false;
    },
    updatePoolSize() {
      while (this.frames.length < this.poolSize) {
        this.frames.push(new ImageFrame(this));
      }
      while (this.frames.length > this.poolSize) {
        this.frames.pop();
      }
    },
    cleanup() {
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
  updateMonitorWindow() {
    const bufferSize = Math.max(10, this.monitor);
    this.fpsMonitor.windowSize = bufferSize;
    this.fpsMonitor.windowStatSize = bufferSize;
  },
  created() {
    // Monitoring
    this.fpsMonitor = new FPSMonitor(10, 10);
    // Image decoding
    this.frames = [];
    this.nextFrameIndex = 0;
    this.updatePoolSize();

    // Display stream
    this.wslinkSubscription = null;
    this.onImage = ([{ name, meta, content }]) => {
      const supportedImageTypes = [
        'image/apng',
        'image/avif',
        'image/gif',
        'image/jpeg',
        'image/png',
        'image/svg+xml',
        'image/webp',
      ];
      if (this.name === name) {
        if (supportedImageTypes.includes(meta.type)) {
          this.nextFrameIndex = (this.nextFrameIndex + 1) % this.frames.length;
          const frame = this.frames[this.nextFrameIndex];
          frame.update(meta.type, content);
          if (this.monitor) {
            const serverTime = meta.st;
            const contentSize = content.length;
            const stats = this.fpsMonitor.addEntry(serverTime, contentSize);
            if (stats) {
              const { avgFps, totalSize } = stats;
              this.$emit('stats', {
                fps: Math.round(avgFps),
                bps: Math.floor(totalSize),
                st: serverTime,
              });
            }
          }
        } else {
          this.hasContent = false;
        }
      }
    };
    if (this.trame) {
      this.wslinkSubscription = this.trame.client
        .getConnection()
        .getSession()
        .subscribe('trame.rca.topic.stream', this.onImage);
    }
  },
  // support both vue2 and vue3 cleanup functions
  beforeDestroy() {
    this.cleanup();
  },
  beforeUnmount() {
    this.cleanup();
  },
  inject: ['trame'],
  template: `<slot><img :style="imageStyle" :src="displayURL" v-show="hasContent" draggable="false" /></slot>`,
};

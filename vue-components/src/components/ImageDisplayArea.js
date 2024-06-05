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
  },
  watch: {
    poolSize() {
      this.updatePoolSize();
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
  created() {
    // Image decoding
    this.frames = [];
    this.nextFrameIndex = 0;
    this.updatePoolSize();

    // Display stream
    this.wslinkSubscription = null;
    this.onImage = ([{ name, meta, content }]) => {
      if (this.name === name) {
        if (meta.type === 'image/jpeg') {
          this.nextFrameIndex = (this.nextFrameIndex + 1) % this.frames.length;
          const frame = this.frames[this.nextFrameIndex];
          frame.update(meta.type, content);
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
  template: `<img :src="displayURL" v-show="hasContent" />`,
};

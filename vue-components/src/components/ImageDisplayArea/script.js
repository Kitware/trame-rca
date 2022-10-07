const RESOLVED_PROMISED = Promise.resolve(true);

class ImageFrame {
  constructor(vueComponent) {
    this.vueComponent = vueComponent;
    this.img = new Image();
    this.url = '';
    this.blob = null;

    this.img.onload(() => {
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
  name: 'ImageDisplayArea',
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
    pushSize() {
      if (this.trame) {
        if (this.readySizeUpdate) {
          this.readySizeUpdate = false;
          this.pendingSizeUpdatePromise = this.trame.client
            .getConnection()
            .getSession()
            .call('trame.rca.size', [
              this.name,
              this.origin,
              this.currentSizeUpdateEvent,
            ]);
          this.pendingSizeUpdatePromise.finally(this.finallySizeUpdate);
        } else {
          this.pendingSizeUpdateCount++;
        }
      }
    },
  },
  created() {
    // Image decoding
    this.frames = [];
    this.nextFrameIndex = 0;
    this.updatePoolSize();

    // Size management
    this.currentSizeUpdateEvent = { w: 10, h: 10, p: window.devicePixelRatio };
    this.readySizeUpdate = true;
    this.pendingSizeUpdatePromise = RESOLVED_PROMISED;
    this.pendingSizeUpdateCount = 0;

    this.finallySizeUpdate = () => {
      this.readySizeUpdate = true;
      if (this.pendingSizeUpdateCount) {
        this.pendingSizeUpdateCount = 0;
        this.pushSize();
      }
    };

    this.observer = new ResizeObserver(() => {
      if (!this.$el) {
        return;
      }
      const rect = this.$el.getBoundingClientRect();
      this.currentSizeUpdateEvent.w = rect.width;
      this.currentSizeUpdateEvent.h = rect.height;
      this.currentSizeUpdateEvent.p = window.devicePixelRatio;

      this.pushSize();
    });

    // Display stream
    this.wslinkSubscription = null;
    this.onImage = ([{ name, meta, content }]) => {
      if (this.name === name && meta.type.include('image')) {
        this.nextFrameIndex = (this.nextFrameIndex + 1) % this.frames.length;
        const frame = this.frames[this.nextFrameIndex];
        frame.update(meta.type, content);
      }
    };
    if (this.trame) {
      this.wslinkSubscription = this.trame.client
        .getConnection()
        .getSession()
        .subscribe('trame.rca.topic.stream', this.onImage);
    }
  },
  mounted() {
    this.observer.observe(this.$el);
  },
  beforeUnmount() {
    this.observer.unobserve(this.$el);
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
  inject: ['trame'],
};

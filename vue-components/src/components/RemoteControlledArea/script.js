const RESOLVED_PROMISED = Promise.resolve(true);

export default {
  name: 'RemoteControlledArea',
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
  methods: {
    pushSize() {
      console.log('push size');
      if (this.trame) {
        if (this.readySizeUpdate) {
          console.log(
            'this.currentSizeUpdateEvent',
            this.currentSizeUpdateEvent
          );
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

    const updateSize = () => {
      if (!this.$el) {
        return;
      }
      const rect = this.$el.getBoundingClientRect();
      this.currentSizeUpdateEvent.w = rect.width;
      this.currentSizeUpdateEvent.h = rect.height;
      this.currentSizeUpdateEvent.p = window.devicePixelRatio;

      this.pushSize();
    };

    this.observer = new ResizeObserver(updateSize);
  },
  mounted() {
    this.observer.observe(this.$el);
  },
  beforeUnmount() {
    this.observer.unobserve(this.$el);
  },
  inject: ['trame'],
};

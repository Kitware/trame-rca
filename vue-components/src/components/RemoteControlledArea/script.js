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
    pushSize(addOn) {
      if (this.trame) {
        if (this.readySizeUpdate) {
          this.readySizeUpdate = false;
          if (addOn) {
            this.pendingSizeUpdatePromise = this.trame.client
              .getConnection()
              .getSession()
              .call('trame.rca.size', [
                this.name,
                this.origin,
                { ...this.currentSizeUpdateEvent, ...addOn },
              ]);
          } else {
            this.pendingSizeUpdatePromise = this.trame.client
              .getConnection()
              .getSession()
              .call('trame.rca.size', [
                this.name,
                this.origin,
                this.currentSizeUpdateEvent,
              ]);
          }
          this.pendingSizeUpdatePromise.finally(this.finallySizeUpdate);
        } else {
          this.pendingSizeUpdateCount++;
        }
      }
    },
    onMouseDown(e) {
      this.dragging = true;
      e.preventDefault();
      this.sendEvent(this.toEvent('mouse-down', e));
      document.addEventListener('mousemove', this.onMouseMove);
      document.addEventListener('mouseup', this.onMouseUp);
    },
    toEvent(t, e) {
      const { altKey, button, ctrlKey, shiftKey, x, y } = e;
      const p = [x - this.currentOffset[0], y - this.currentOffset[1]];
      return { t, p, b: button, alt: altKey, ctrl: ctrlKey, shift: shiftKey };
    },
    sendEvent(event) {
      if (this.trame) {
        if (this.readyMouseUpdate) {
          this.readyMouseUpdate = false;
          this.lastEvent = event;
          this.pendingMouseUpdatePromise = this.trame.client
            .getConnection()
            .getSession()
            .call('trame.rca.event', [this.name, this.origin, this.lastEvent]);
          this.pendingSizeUpdatePromise.finally(this.finallyEventUpdate);
        } else if (this.lastEvent.type !== event.type) {
          this.pendingEventUpdateCount = 0;
          this.trame.client
            .getConnection()
            .getSession()
            .call('trame.rca.event', [this.name, this.origin, this.lastEvent]);
          this.trame.client
            .getConnection()
            .getSession()
            .call('trame.rca.event', [this.name, this.origin, event]);
          this.lastEvent = event;
        }
      }
    },
  },
  created() {
    // Mouse management
    this.dragging = false;
    this.readyMouseUpdate = true;
    this.lastEvent = null;
    this.pendingMouseUpdatePromise = RESOLVED_PROMISED;
    this.pendingMouseUpdateCount = 0;
    this.onMouseMove = (e) => {
      e.preventDefault();
      this.sendEvent(this.toEvent('mouse-move', e));
    };
    this.onMouseUp = (e) => {
      e.preventDefault();
      this.dragging = false;
      this.sendEvent(this.toEvent('mouse-up', e));
      document.removeEventListener('mousemove', this.onMouseMove);
      document.removeEventListener('mouseup', this.onMouseUp);
    };

    this.finallyEventUpdate = () => {
      this.readyMouseUpdate = true;
      if (this.pendingEventUpdateCount) {
        this.pendingEventUpdateCount = 0;
        this.sendEvent(this.lastEvent);
      }
    };

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
      const { top, left } = rect;
      this.currentSizeUpdateEvent.w = rect.width;
      this.currentSizeUpdateEvent.h = rect.height;
      this.currentSizeUpdateEvent.p = window.devicePixelRatio;
      this.currentOffset = [left, top];

      this.pushSize();
    });
  },
  mounted() {
    this.observer.observe(this.$el);
  },
  beforeUnmount() {
    this.observer.unobserve(this.$el);
  },
  inject: ['trame'],
  provide() {
    return {
      rcaPushSize: (addOn) => this.pushSize(addOn),
    };
  },
};

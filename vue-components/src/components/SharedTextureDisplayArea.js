// Shows the frames the trame-rca-electron preload draws from the texture VTK shares with
// Electron. Only works in a page loaded by trame-rca-electron: the preload defines the bridge.
export default {
  emits: ['stats'],
  methods: {
    cleanup() {
      window.trameRcaSharedTexture?.detach(this.$el);
    },
  },
  mounted() {
    if (!window.trameRcaSharedTexture) {
      console.warn(
        'shared-texture-display-area: no trameRcaSharedTexture bridge, not running in trame-rca-electron?'
      );
      return;
    }
    // { fps, frames, info } once a second.
    window.trameRcaSharedTexture.attach(this.$el, (stats) =>
      this.$emit('stats', stats)
    );
  },
  // support both vue2 and vue3 unmount callbacks
  beforeDestroy() {
    this.cleanup();
  },
  beforeUnmount() {
    this.cleanup();
  },
  template: `
    <canvas class="shared-texture-display-area" @contextmenu.prevent></canvas>
  `,
};

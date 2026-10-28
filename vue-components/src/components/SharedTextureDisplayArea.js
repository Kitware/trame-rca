// Shows the frames the trame-rca-electron preload draws from the texture VTK shares with
// Electron, for the view `name`. Only works in a page loaded by trame-rca-electron: the preload
// defines the bridge.
export default {
  props: {
    name: {
      type: String,
      default: 'default',
    },
  },
  emits: ['stats'],
  methods: {
    attach() {
      if (!window.trameRcaSharedTexture) {
        console.warn(
          'shared-texture-display-area: no trameRcaSharedTexture bridge, not running in trame-rca-electron?'
        );
        return;
      }
      this.attachedName = this.name;
      // { fps, frames, info } once a second.
      window.trameRcaSharedTexture.attach(this.name, this.$el, (stats) =>
        this.$emit('stats', stats)
      );
    },
    cleanup() {
      window.trameRcaSharedTexture?.detach(this.attachedName, this.$el);
    },
  },
  watch: {
    name() {
      this.cleanup();
      this.attach();
    },
  },
  mounted() {
    this.attach();
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

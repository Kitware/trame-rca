const { ref, onBeforeUnmount, watchEffect } = window.Vue;

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
  setup(props, { emit }) {
    const el = ref(null);
    const attached = [];

    function detachAll() {
      while (attached.length) {
        const [n, c] = attached.pop();
        window.trameRcaSharedTexture.detach(n, c);
      }
    }
    onBeforeUnmount(detachAll);

    if (!window.trameRcaSharedTexture) {
      console.warn(
        'shared-texture-display-area: no trameRcaSharedTexture bridge, not running in trame-rca-electron?'
      );
    }

    function emitStats(stats) {
      emit('stats', stats);
    }

    watchEffect(() => {
      const name = props.name;
      const container = el.value;
      detachAll();
      if (!container || !window.trameRcaSharedTexture) return;
      attached.push([name, container]);
      window.trameRcaSharedTexture.attach(name, container, emitStats);
    });

    return { el };
  },
  template: `
    <canvas ref="el" class="shared-texture-display-area" @contextmenu.prevent></canvas>
  `,
};

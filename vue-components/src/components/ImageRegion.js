import { watchEffect, inject, ref, onMounted, onBeforeUnmount } from 'vue';
import { ImageRegionController } from 'trame-rca-js';

export default {
  props: {
    bounds: {
      type: Array,
    },
    enableInteraction: {
      type: Boolean,
      default: false,
    },
    sendMouseMove: {
      type: Boolean,
      default: false,
    },
    sendMouseClick: {
      type: Boolean,
      default: false,
    },
    eventThrottleMs: {
      type: Number,
      default: 25,
    },
  },
  events: ['size'],
  setup(props, { emit }) {
    const trame = inject('trame');
    const rootElem = ref(null);
    const canvas = ref(null);
    const name = inject('rcaImageStreamName');
    const rcaImageStream = inject('rcaImageStream');

    const controller = new ImageRegionController({
      source: { trame },
      name,
      bounds: props.bounds,
      enableInteraction: props.enableInteraction,
      sendMouseMove: props.sendMouseMove,
      sendMouseClick: props.sendMouseClick,
      eventThrottleMs: props.eventThrottleMs,
      getImage: () => rcaImageStream?.value,
      onSize: (event) => emit('size', event),
    });

    // redraw when a new frame arrives or the bounds change
    watchEffect(() => {
      controller.bounds = props.bounds;
      // track the stream so a new frame triggers a redraw
      void rcaImageStream?.value;
      controller.draw();
    });

    watchEffect(() => {
      controller.setSendMouseMove(props.sendMouseMove);
    });
    watchEffect(() => {
      controller.setEventThrottleMs(props.eventThrottleMs);
    });
    watchEffect(() => {
      controller.setEnableInteraction(props.enableInteraction);
    });
    watchEffect(() => {
      controller.setSendMouseClick(props.sendMouseClick);
    });

    onMounted(() => {
      controller.mount({ root: rootElem.value, canvas: canvas.value });
    });

    onBeforeUnmount(() => {
      controller.unmount();
    });

    return {
      rootElem,
      canvas,
    };
  },
  template: `
    <div class="image-region" ref="rootElem" >
      <canvas class="image-region-canvas" ref="canvas"/>
    </div>
  `,
};

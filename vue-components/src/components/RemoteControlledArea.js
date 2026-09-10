import { RemoteControlledAreaController } from 'trame-rca-js';

const {
  inject,
  provide,
  ref,
  toRefs,
  onMounted,
  onBeforeUnmount,
  watchEffect,
} = window.Vue;

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
    display: {
      type: String,
      default: 'image',
    },
    sendMouseMove: {
      type: Boolean,
      default: false,
    },
    eventThrottleMs: {
      type: Number,
      default: 25,
    },
    resizeThrottleMs: {
      type: Number,
      default: 100,
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
  setup(props) {
    const rootElem = ref(null);
    const trame = inject('trame');

    const controller = new RemoteControlledAreaController({
      source: { trame },
      name: props.name,
      origin: props.origin,
      sendMouseMove: props.sendMouseMove,
      eventThrottleMs: props.eventThrottleMs,
      resizeThrottleMs: props.resizeThrottleMs,
    });

    watchEffect(() => {
      controller.setResizeThrottleMs(props.resizeThrottleMs);
    });
    watchEffect(() => {
      controller.setEventThrottleMs(props.eventThrottleMs);
    });
    watchEffect(() => {
      controller.setSendMouseMove(props.sendMouseMove);
    });
    watchEffect(() => {
      controller.setName(props.name);
    });
    watchEffect(() => {
      controller.setOrigin(props.origin);
    });

    provide('rcaPushSize', (addOn) => controller.pushSize(addOn));

    onMounted(() => {
      controller.mount(rootElem.value);
    });

    onBeforeUnmount(() => {
      controller.unmount();
    });

    return { rootElem, ...toRefs(props) };
  },
  template: `
    <div class="remote-controlled-area" ref="rootElem">
      <div class="remote-controlled-area-content">
        <display-area :display="display" :imageStyle="imageStyle" :name="name" :origin="origin" :monitor="monitor" @stats="$emit('stats', $event)" />
        <slot></slot>
      </div>
    </div>
  `,
};

import vtkRenderWindowInteractor from '@kitware/vtk.js/Rendering/Core/RenderWindowInteractor';
import vtkInteractorStyleRemoteMouse from '../utils/interactorStyle';
import { watchEffect, inject, ref, onMounted, onBeforeUnmount } from 'vue';
import { EventThrottle } from '../utils/EventThrottle';

class EventTranslator {
  constructor() {
    this.fullWidth = 300;
    this.fullheight = 300;
    this.xOffset = 0;
    this.yOffset = 0;
    this.xSize = 300;
    this.ySize = 300;
  }

  translate(event) {
    const out = { ...event };
    if (event.x !== undefined) {
      out.x = Math.round(this.xOffset + this.xSize * (event.x / event.w));
      out.y = Math.round(this.yOffset + this.ySize * (event.y / event.h));
      out.w = this.fullWidth;
      out.h = this.fullheight;
    }
    return out;
  }
}

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
    eventThrottleMs: {
      type: Number,
      default: 25,
    },
  },
  events: ['size'],
  setup(props, { emit }) {
    const eventTranslator = new EventTranslator();
    const trame = inject('trame');
    const rootElem = ref(null);
    const canvas = ref(null);
    const name = inject('rcaImageStreamName');
    const rcaImageStream = inject('rcaImageStream');

    watchEffect(() => {
      const fullImg = rcaImageStream.value;
      const domCanvas = canvas.value;
      const [xMin, yMin, xMax, yMax] = props.bounds;
      if (!fullImg || !domCanvas) {
        return;
      }
      const { width, height } = fullImg;
      const canvasWidth = Math.floor((xMax - xMin) * width);
      const canvasHeight = Math.floor((yMax - yMin) * height);
      const sx = Math.floor(xMin * width);
      const sy = Math.floor((1 - yMax) * height);
      const sw = Math.floor((xMax - xMin) * width);
      const sh = Math.floor((yMax - yMin) * height);
      domCanvas.width = canvasWidth;
      domCanvas.height = canvasHeight;
      const ctx = domCanvas.getContext('2d');
      ctx.drawImage(fullImg, sx, sy, sw, sh, 0, 0, canvasWidth, canvasHeight);

      // Update event translator
      eventTranslator.fullWidth = width;
      eventTranslator.fullheight = height;
      eventTranslator.xOffset = sx;
      eventTranslator.xSize = sw;
      eventTranslator.yOffset = Math.floor(yMin * height);
      eventTranslator.ySize = sh;
    });

    // -----------------------------------------------------------------------
    // VTK input handling
    // -----------------------------------------------------------------------
    // Mouse management
    let currentOffset = [0, 0];
    let currentSizeUpdateEvent = { w: 10, h: 10, p: window.devicePixelRatio };

    function onScroll() {
      if (!rootElem.value) {
        return;
      }
      const rect = rootElem.value.getBoundingClientRect();
      const { top, left } = rect;
      currentOffset = [left, top];
    }

    const throttle = new EventThrottle((event) => {
      const et = eventTranslator.translate(event);
      return trame.client
        .getConnection()
        .getSession()
        .call('trame.rca.event', [name, 'region', et]);
    }, props.eventThrottleMs);

    function _getScreenEventPositionFor(source) {
      return {
        x: source.clientX - currentOffset[0],
        y: currentSizeUpdateEvent.h - source.clientY + currentOffset[1],
        z: 0,
      };
    }

    const windowInteractor = vtkRenderWindowInteractor.newInstance({
      _getScreenEventPositionFor,
      currentRenderer: 1,
    });
    const interactorStyle = vtkInteractorStyleRemoteMouse.newInstance();
    windowInteractor.setInteractorStyle(interactorStyle);

    // Mouse
    interactorStyle.onRemoteMouseEvent((e) => {
      sendEvent(
        Object.assign(
          { w: currentSizeUpdateEvent.w, h: currentSizeUpdateEvent.h },
          e
        )
      );
    });
    // Wheel
    interactorStyle.onRemoteWheelEvent((e) => {
      sendEvent(
        Object.assign(
          { w: currentSizeUpdateEvent.w, h: currentSizeUpdateEvent.h },
          e
        )
      );
    });
    // Gesture
    interactorStyle.onRemoteGestureEvent((e) => {
      sendEvent(
        Object.assign(
          { w: currentSizeUpdateEvent.w, h: currentSizeUpdateEvent.h },
          e
        )
      );
    });
    // Keyboard
    interactorStyle.onRemoteKeyEvent((e) => {
      sendEvent(
        Object.assign(
          { w: currentSizeUpdateEvent.w, h: currentSizeUpdateEvent.h },
          e
        )
      );
    });
    // Interaction Events
    interactorStyle.onStartInteractionEvent((e) => {
      sendEvent(e);
    });
    interactorStyle.onEndInteractionEvent((e) => {
      sendEvent(e);
    });

    // -----------------------------------------------------------------------

    function sendEvent(event) {
      if (trame && props.enableInteraction) {
        throttle.sendEvent(event);
      }
    }

    const observer = new ResizeObserver(() => {
      if (!rootElem.value) {
        return;
      }
      const rect = rootElem.value.getBoundingClientRect();
      const { top, left } = rect;
      currentSizeUpdateEvent.w = rect.width;
      currentSizeUpdateEvent.h = rect.height;
      currentSizeUpdateEvent.p = window.devicePixelRatio;
      currentOffset = [left, top];
      emit('size', currentSizeUpdateEvent);
    });

    onMounted(() => {
      observer.observe(rootElem.value);
      windowInteractor.initialize();
      windowInteractor.bindEvents(rootElem.value);
      window.addEventListener('scroll', onScroll);
    });

    onBeforeUnmount(() => {
      observer.unobserve(rootElem.value);
      windowInteractor.unbindEvents(rootElem.value);
      window.removeEventListener('scroll', onScroll);
    });

    watchEffect(() => {
      interactorStyle.setSendMouseMove(props.sendMouseMove);
    });

    return {
      rootElem,
      canvas,
    };
  },
  template: `<div ref="rootElem" style="margin: 0; padding: 0; position: relative; width: 100%; height: 100%;"><canvas ref="canvas" style="position:absolute;width:100%;height:auto;" /></div>`,
};

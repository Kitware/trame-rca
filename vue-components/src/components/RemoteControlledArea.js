import vtkRenderWindowInteractor from '@kitware/vtk.js/Rendering/Core/RenderWindowInteractor';
import vtkInteractorStyleRemoteMouse from '../utils/interactorStyle';
const { inject, provide, ref, toRefs, onMounted, onBeforeUnmount } = window.Vue;

const RESOLVED_PROMISED = Promise.resolve(true);

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
  },
  setup(props) {
    const rootElem = ref(null);
    const pendingEventPromise = ref(RESOLVED_PROMISED);
    const trame = inject('trame');

    // Mouse management
    let readyEventUpdate = true;
    let lastEvent = null;
    let pendingEventUpdateCount = 0;
    let currentOffset = [0, 0];

    // Size management
    let currentSizeUpdateEvent = { w: 10, h: 10, p: window.devicePixelRatio };
    let readySizeUpdate = true;
    let pendingSizeUpdatePromise = RESOLVED_PROMISED;
    let pendingSizeUpdateCount = 0;

    // -----------------------------------------------------------------------
    // VTK input handling
    // -----------------------------------------------------------------------
    function _getScreenEventPositionFor(source) {
      source.preventDefault(); // Do we need that?
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
    interactorStyle.setSendMouseMove(props.sendMouseMove);
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
      if (trame) {
        if (readyEventUpdate) {
          readyEventUpdate = false;
          lastEvent = event;
          pendingEventPromise.value = trame.client
            .getConnection()
            .getSession()
            .call('trame.rca.event', [props.name, props.origin, lastEvent]);
          pendingSizeUpdatePromise.finally(finallyEventUpdate);
        } else if (lastEvent.type !== event.type) {
          pendingEventUpdateCount = 0;
          trame.client
            .getConnection()
            .getSession()
            .call('trame.rca.event', [props.name, props.origin, lastEvent]);
          trame.client
            .getConnection()
            .getSession()
            .call('trame.rca.event', [props.name, props.origin, event]);
          lastEvent = event;
        }
      }
    }

    function finallyEventUpdate() {
      readyEventUpdate = true;
      if (pendingEventUpdateCount) {
        pendingEventUpdateCount = 0;
        sendEvent(lastEvent);
      }
    }

    function finallySizeUpdate() {
      readySizeUpdate = true;
      if (pendingSizeUpdateCount) {
        pendingSizeUpdateCount = 0;
        pushSize();
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
      pushSize();
    });

    function pushSize(addOn) {
      if (trame) {
        if (readySizeUpdate) {
          readySizeUpdate = false;
          if (addOn) {
            pendingSizeUpdatePromise = trame.client
              .getConnection()
              .getSession()
              .call('trame.rca.size', [
                props.name,
                props.origin,
                { ...currentSizeUpdateEvent, ...addOn },
              ]);
          } else {
            pendingSizeUpdatePromise = trame.client
              .getConnection()
              .getSession()
              .call('trame.rca.size', [
                props.name,
                props.origin,
                currentSizeUpdateEvent,
              ]);
          }
          pendingSizeUpdatePromise.finally(finallySizeUpdate);
        } else {
          pendingSizeUpdateCount++;
        }
      }
    }

    provide('rcaPushSize', pushSize);

    onMounted(() => {
      observer.observe(rootElem.value);
      windowInteractor.initialize();
      windowInteractor.bindEvents(rootElem.value);
    });

    onBeforeUnmount(() => {
      observer.unobserve(rootElem.value);
      windowInteractor.unbindEvents(rootElem.value);
    });

    return { rootElem, ...toRefs(props) };
  },
  template: `
    <div ref="rootElem" style="margin: 0; padding: 0; position: relative; width: 100%; height: 100%;">
      <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">
        <display-area :display="display" :name="name" :origin="origin" />
        <slot></slot>
      </div>
    </div>
  `,
};

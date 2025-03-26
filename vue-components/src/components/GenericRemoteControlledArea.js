const { inject, ref, provide, toRefs, onMounted, onBeforeUnmount } = window.Vue;

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
  },
  setup(props) {
    const rootElem = ref(null);
    const trame = inject('trame');

    // Size management
    let currentSizeUpdateEvent = { w: 10, h: 10, p: window.devicePixelRatio };
    let readySizeUpdate = true;
    let pendingSizeUpdatePromise = RESOLVED_PROMISED;
    let pendingSizeUpdateCount = 0;

    function sendEvent(eventType, event) {
      if (trame) {
        const eventData = {
          type: eventType,
          key: event.key || null,
          code: event.code || null,
          button: event.button || null,
          buttons: event.buttons || null,
          clientX: event.clientX || null,
          clientY: event.clientY || null,
          deltaX: event.deltaX || null,
          deltaY: event.deltaY || null,
          ctrlKey: event.ctrlKey,
          shiftKey: event.shiftKey,
          altKey: event.altKey,
          metaKey: event.metaKey,
        };
        trame.client
          .getConnection()
          .getSession()
          .call('trame.rca.event', [props.name, props.origin, eventData]);
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
      currentSizeUpdateEvent.w = rect.width;
      currentSizeUpdateEvent.h = rect.height;
      currentSizeUpdateEvent.p = window.devicePixelRatio;
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
      if (rootElem.value) {
        rootElem.value.focus();
        observer.observe(rootElem.value);
        rootElem.value.addEventListener('click', (event) =>
          sendEvent('click', event)
        );
        rootElem.value.addEventListener('wheel', (event) =>
          sendEvent('wheel', event)
        );
        rootElem.value.addEventListener('keydown', (event) =>
          sendEvent('keydown', event)
        );
      }
    });

    onBeforeUnmount(() => {
      if (rootElem.value) {
        observer.unobserve(rootElem.value);
        rootElem.value.removeEventListener('click', (event) =>
          sendEvent('click', event)
        );
        rootElem.value.removeEventListener('wheel', (event) =>
          sendEvent('wheel', event)
        );
        rootElem.value.removeEventListener('keydown', (event) =>
          sendEvent('keydown', event)
        );
      }
    });

    return { rootElem, ...toRefs(props) };
  },
  template: `
    <div ref="rootElem" style="margin: 0; padding: 0; position: relative; width: 100%; height: 100%; outline: none; display: flex; justify-content: center; align-items: center;">
      <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">
        <display-area :display="display" :name="name" :origin="origin" style="width: 100%; height: 100%; display: flex; justify-content: center; align-items: center;" />
        <slot></slot>
      </div>
    </div>
  `,
};

import macro from '@kitware/vtk.js/macro';
import vtkRenderWindowInteractor from '@kitware/vtk.js/Rendering/Core/RenderWindowInteractor';

import vtkInteractorStyleRemoteMouse from '../utils/interactorStyle.js';
import { EventThrottle } from '../utils/EventThrottle.js';
import { EventTranslator } from '../utils/EventTranslator.js';
import { getDevicePixelRatio } from '../utils/devicePixelRatio.js';
import { getSession } from '../session.js';

const CLICK_TYPE = { LeftButtonRelease: true, LeftButtonPress: true };

/**
 * Logic for an interactive sub-region of an image stream.
 * The owner decides when to redraw (new frame / bounds change) by calling
 * `draw()`, and forwards size events through `onSize`.
 */
export class ImageRegionController {
  constructor({
    source,
    name,
    bounds,
    enableInteraction = false,
    sendMouseMove = false,
    sendMouseClick = false,
    eventThrottleMs = 25,
    getImage,
    onSize,
  } = {}) {
    this.source = source;
    this.name = name;
    this.bounds = bounds;
    this.enableInteraction = enableInteraction;
    this.sendMouseMove = sendMouseMove;
    this.sendMouseClick = sendMouseClick;
    this.eventThrottleMs = eventThrottleMs;
    this.getImage = getImage;
    this.onSize = onSize;

    this.rootElement = null;
    this.canvas = null;
    this.session = null;
    this.throttle = null;
    this.windowInteractor = null;
    this.interactorStyle = null;
    this.observer = null;
    this.onScroll = null;

    this.eventTranslator = new EventTranslator();
    this.currentOffset = [0, 0];
    this.currentSizeUpdateEvent = {
      w: 10,
      h: 10,
      p: getDevicePixelRatio(),
    };
  }

  mount({ root, canvas }) {
    this.rootElement = root;
    this.canvas = canvas;
    this.session = getSession(this.source);

    this.onScroll = () => {
      if (!this.rootElement) {
        return;
      }
      const rect = this.rootElement.getBoundingClientRect();
      this.currentOffset = [rect.left, rect.top];
    };

    this.throttle = new EventThrottle((event) => {
      const et = this.eventTranslator.translate(event);
      return this.session.call('trame.rca.event', [this.name, 'region', et]);
    }, this.eventThrottleMs);

    const getScreenEventPositionFor = (source) => ({
      x: source.clientX - this.currentOffset[0],
      y: this.currentSizeUpdateEvent.h - source.clientY + this.currentOffset[1],
      z: 0,
    });

    this.windowInteractor = vtkRenderWindowInteractor.newInstance({
      _getScreenEventPositionFor: getScreenEventPositionFor,
      currentRenderer: 1,
    });
    this.interactorStyle = vtkInteractorStyleRemoteMouse.newInstance();
    this.windowInteractor.setInteractorStyle(this.interactorStyle);

    const withSize = (e) =>
      this.sendEvent({
        w: this.currentSizeUpdateEvent.w,
        h: this.currentSizeUpdateEvent.h,
        ...e,
      });

    this.interactorStyle.onRemoteMouseEvent(withSize);
    this.interactorStyle.onRemoteWheelEvent(withSize);
    this.interactorStyle.onRemoteGestureEvent(withSize);
    this.interactorStyle.onRemoteKeyEvent(withSize);
    this.interactorStyle.onRemoteTapEvent(withSize);
    this.interactorStyle.onRemoteLongTapEvent(withSize);
    this.interactorStyle.onStartInteractionEvent((e) => this.sendEvent(e));
    this.interactorStyle.onEndInteractionEvent((e) => this.sendEvent(e));
    this.interactorStyle.setSendMouseMove(this.sendMouseMove);

    this.observer = new ResizeObserver(
      macro.debounce(() => {
        if (!this.rootElement) {
          return;
        }
        const rect = this.rootElement.getBoundingClientRect();
        this.currentSizeUpdateEvent.w = rect.width;
        this.currentSizeUpdateEvent.h = rect.height;
        this.currentSizeUpdateEvent.p = getDevicePixelRatio();
        this.currentOffset = [rect.left, rect.top];
        this.onSize?.(this.currentSizeUpdateEvent);
      }, 100)
    );

    this.windowInteractor.initialize();
    this.windowInteractor.bindEvents(this.rootElement);
    window.addEventListener('scroll', this.onScroll);
    this.observer.observe(this.rootElement);

    this.draw();
  }

  sendEvent(event) {
    if (!this.session) {
      return;
    }
    if (
      this.enableInteraction ||
      (this.sendMouseMove &&
        event.type === 'MouseMove' &&
        event.action === 'up')
    ) {
      this.throttle.sendEvent(event);
    } else if (this.sendMouseClick && CLICK_TYPE[event.type]) {
      this.throttle.sendEvent(event);
    }
  }

  draw() {
    const fullImg = this.getImage?.();
    const domCanvas = this.canvas;
    if (!fullImg || !domCanvas || !this.bounds) {
      return;
    }
    const [xMin, yMin, xMax, yMax] = this.bounds;
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
    this.eventTranslator.fullWidth = width;
    this.eventTranslator.fullHeight = height;
    this.eventTranslator.xOffset = sx;
    this.eventTranslator.xSize = sw;
    this.eventTranslator.yOffset = Math.floor(yMin * height);
    this.eventTranslator.ySize = sh;
  }

  setBounds(bounds) {
    this.bounds = bounds;
    this.draw();
  }

  setEnableInteraction(value) {
    this.enableInteraction = value;
  }

  setSendMouseClick(value) {
    this.sendMouseClick = value;
  }

  setSendMouseMove(value) {
    this.sendMouseMove = value;
    this.interactorStyle?.setSendMouseMove(value);
  }

  setEventThrottleMs(value) {
    this.eventThrottleMs = Number(value);
    if (this.throttle) {
      this.throttle.throttleTimeMs = Number(value);
    }
  }

  unmount() {
    if (this.observer && this.rootElement) {
      this.observer.unobserve(this.rootElement);
    }
    if (this.windowInteractor && this.rootElement) {
      this.windowInteractor.unbindEvents(this.rootElement);
    }
    window.removeEventListener('scroll', this.onScroll);
    this.rootElement = null;
    this.canvas = null;
  }
}

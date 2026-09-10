import macro from '@kitware/vtk.js/macro';
import vtkRenderWindowInteractor from '@kitware/vtk.js/Rendering/Core/RenderWindowInteractor';

import vtkInteractorStyleRemoteMouse from '../utils/interactorStyle.js';
import { EventThrottle, FunctionThrottle } from '../utils/EventThrottle.js';
import { getDevicePixelRatio } from '../utils/devicePixelRatio.js';
import { getSession, getTrame } from '../session.js';

const RESOLVED_PROMISE = Promise.resolve(true);

/**
 * Logic for the remote controlled area: size updates with
 * back-pressure, input capture and throttling.
 */
export class RemoteControlledAreaController {
  constructor({
    source,
    name = 'default',
    origin = 'anonymous',
    sendMouseMove = false,
    eventThrottleMs = 25,
    resizeThrottleMs = 100,
  } = {}) {
    this.source = source;
    this.name = name;
    this.origin = origin;
    this.sendMouseMove = sendMouseMove;
    this.eventThrottleMs = eventThrottleMs;
    this.resizeThrottleMs = resizeThrottleMs;

    this.rootElement = null;
    this.trame = getTrame(this.source);
    this.session = getSession(this.source);
    this.windowInteractor = null;
    this.interactorStyle = null;
    this.observer = null;
    this.currentOffset = [0, 0];
    this.currentSizeUpdateEvent = {
      w: 10,
      h: 10,
      p: getDevicePixelRatio(),
    };
    this.readySizeUpdate = true;
    this.pendingSizeUpdatePromise = RESOLVED_PROMISE;
    this.pendingSizeUpdateCount = 0;

    this.finallySizeUpdate = this.finallySizeUpdate.bind(this);
    this._pushSize = this._pushSize.bind(this);

    // The size/event throttles are ready before `mount` so descendants (e.g.
    // MediaSourceDisplayArea) can request a size during their own mount.
    this.throttleSize = new FunctionThrottle(
      this._pushSize,
      this.resizeThrottleMs
    );
    this.throttle = new EventThrottle((event) => {
      return this.session?.call('trame.rca.event', [
        this.name,
        this.origin,
        event,
      ]);
    }, this.eventThrottleMs);
  }

  mount(root) {
    this.rootElement = root;

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
    this.interactorStyle.setSendMouseMove(this.sendMouseMove);

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
        this.pushSize();
      }, 100)
    );

    this.observer.observe(this.rootElement);
    this.windowInteractor.initialize();
    this.windowInteractor.bindEvents(this.rootElement);
  }

  sendEvent(event) {
    if (this.trame) {
      this.throttle.sendEvent(event);
    }
  }

  pushSize(addOn) {
    this.throttleSize?.run(addOn);
  }

  finallySizeUpdate() {
    this.readySizeUpdate = true;
    if (this.pendingSizeUpdateCount) {
      this.pendingSizeUpdateCount = 0;
      this.pushSize();
    }
  }

  _pushSize(addOn) {
    if (!this.trame || !this.session) {
      return;
    }
    if (this.readySizeUpdate) {
      this.readySizeUpdate = false;
      this.pendingSizeUpdatePromise = this.session.call('trame.rca.size', [
        this.name,
        this.origin,
        addOn
          ? { ...this.currentSizeUpdateEvent, ...addOn }
          : this.currentSizeUpdateEvent,
      ]);
      this.pendingSizeUpdatePromise.finally(this.finallySizeUpdate);
    } else {
      this.pendingSizeUpdateCount++;
    }
  }

  setEventThrottleMs(value) {
    this.eventThrottleMs = Number(value);
    if (this.throttle) {
      this.throttle.throttleTimeMs = Number(value);
    }
  }

  setName(value) {
    this.name = value;
  }

  setOrigin(value) {
    this.origin = value;
  }

  setResizeThrottleMs(value) {
    this.resizeThrottleMs = value;
    if (this.throttleSize) {
      this.throttleSize.delay = value;
    }
  }

  setSendMouseMove(value) {
    this.sendMouseMove = value;
    this.interactorStyle?.setSendMouseMove(value);
  }

  unmount() {
    if (this.observer && this.rootElement) {
      this.observer.unobserve(this.rootElement);
    }
    if (this.windowInteractor && this.rootElement) {
      this.windowInteractor.unbindEvents(this.rootElement);
    }
    this.rootElement = null;
  }
}

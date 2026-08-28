import { useEffect, useRef } from "react";

import macro from "@kitware/vtk.js/macro";
import vtkRenderWindowInteractor from "@kitware/vtk.js/Rendering/Core/RenderWindowInteractor";

import {
  type AnyProps,
  getSession,
  getTrame,
  type PushSizeFn,
  RcaPushSizeContext,
} from "../context";
import { EventThrottle, FunctionThrottle } from "../utils/EventThrottle";
import vtkInteractorStyleRemoteMouse from "../utils/interactorStyle";

import DisplayArea from "./DisplayArea";

const RESOLVED_PROMISED = Promise.resolve(true);

export default function RemoteControlledArea(props: AnyProps) {
  const {
    name = "default",
    origin = "anonymous",
    display = "image",
    sendMouseMove = false,
    eventThrottleMs = 25,
    resizeThrottleMs = 100,
    imageStyle = { width: "100%" },
    monitor = 0,
    onStats,
    slot,
  } = props;
  const propsRef = useRef<AnyProps>(props);
  propsRef.current = props;
  const rootElem = useRef<HTMLDivElement | null>(null);
  const ctx = useRef<any>(null);

  useEffect(() => {
    const trame = getTrame(propsRef.current);
    const session = getSession(propsRef.current);
    const context: any = {};
    ctx.current = context;

    // Mouse management
    let currentOffset = [0, 0];

    // Size management
    const currentSizeUpdateEvent = {
      w: 10,
      h: 10,
      p: Math.max(1, window.devicePixelRatio),
    };
    let readySizeUpdate = true;
    let pendingSizeUpdatePromise = RESOLVED_PROMISED;
    let pendingSizeUpdateCount = 0;

    function finallySizeUpdate() {
      readySizeUpdate = true;
      if (pendingSizeUpdateCount) {
        pendingSizeUpdateCount = 0;
        pushSize();
      }
    }

    function _pushSize(addOn?: Record<string, unknown>) {
      if (!trame) return;
      if (readySizeUpdate) {
        readySizeUpdate = false;
        pendingSizeUpdatePromise = session.call("trame.rca.size", [
          propsRef.current.name,
          propsRef.current.origin ?? "anonymous",
          addOn
            ? { ...currentSizeUpdateEvent, ...addOn }
            : currentSizeUpdateEvent,
        ]);
        pendingSizeUpdatePromise.finally(finallySizeUpdate);
      } else {
        pendingSizeUpdateCount++;
      }
    }

    // Resizing throttle
    const throttleSize = new FunctionThrottle(
      _pushSize,
      propsRef.current.resizeThrottleMs ?? 100,
    );
    context.throttleSize = throttleSize;

    function pushSize(addOn?: Record<string, unknown>) {
      throttleSize.run(addOn);
    }
    context.pushSize = pushSize as PushSizeFn;

    // Event throttle
    const throttle = new EventThrottle((event: unknown) => {
      return session.call("trame.rca.event", [
        propsRef.current.name,
        propsRef.current.origin ?? "anonymous",
        event,
      ]);
    }, propsRef.current.eventThrottleMs ?? 25);
    context.throttle = throttle;

    function sendEvent(event: Record<string, unknown>) {
      if (trame) {
        throttle.sendEvent(event);
      }
    }

    // -----------------------------------------------------------------------
    // VTK input handling
    // -----------------------------------------------------------------------
    function _getScreenEventPositionFor(source: {
      clientX: number;
      clientY: number;
    }) {
      return {
        x: source.clientX - currentOffset[0],
        y: currentSizeUpdateEvent.h - source.clientY + currentOffset[1],
        z: 0,
      };
    }

    const windowInteractor = vtkRenderWindowInteractor.newInstance({
      _getScreenEventPositionFor,
      currentRenderer: 1,
    } as any);
    const interactorStyle = vtkInteractorStyleRemoteMouse.newInstance();
    windowInteractor.setInteractorStyle(interactorStyle);
    context.interactorStyle = interactorStyle;
    interactorStyle.setSendMouseMove(propsRef.current.sendMouseMove ?? false);

    const withSize = (e: Record<string, unknown>) =>
      sendEvent({
        w: currentSizeUpdateEvent.w,
        h: currentSizeUpdateEvent.h,
        ...e,
      });
    interactorStyle.onRemoteMouseEvent(withSize);
    interactorStyle.onRemoteWheelEvent(withSize);
    interactorStyle.onRemoteGestureEvent(withSize);
    interactorStyle.onRemoteKeyEvent(withSize);
    interactorStyle.onRemoteTapEvent(withSize);
    interactorStyle.onRemoteLongTapEvent(withSize);
    interactorStyle.onStartInteractionEvent((e: any) => sendEvent(e));
    interactorStyle.onEndInteractionEvent((e: any) => sendEvent(e));

    // -----------------------------------------------------------------------

    const observer = new ResizeObserver(
      macro.debounce(() => {
        if (!rootElem.current) {
          return;
        }
        const rect = rootElem.current.getBoundingClientRect();
        const { top, left } = rect;
        currentSizeUpdateEvent.w = rect.width;
        currentSizeUpdateEvent.h = rect.height;
        currentSizeUpdateEvent.p = Math.max(1, window.devicePixelRatio);
        currentOffset = [left, top];
        pushSize();
      }, 100),
    );

    const el = rootElem.current as HTMLDivElement;
    observer.observe(el);
    windowInteractor.initialize();
    windowInteractor.bindEvents(el);

    return () => {
      observer.unobserve(el);
      windowInteractor.unbindEvents();
      ctx.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name]);

  // prop-driven updates
  useEffect(() => {
    if (ctx.current) ctx.current.throttleSize.delay = resizeThrottleMs;
  }, [resizeThrottleMs]);
  useEffect(() => {
    if (ctx.current)
      ctx.current.throttle.throttleTimeMs = Number(eventThrottleMs);
  }, [eventThrottleMs]);
  useEffect(() => {
    ctx.current?.interactorStyle.setSendMouseMove(sendMouseMove);
  }, [sendMouseMove]);

  return (
    <div className="remote-controlled-area" ref={rootElem}>
      <div className="remote-controlled-area-content">
        <RcaPushSizeContext.Provider
          value={(addOn) => ctx.current?.pushSize?.(addOn)}
        >
          <DisplayArea
            display={display}
            imageStyle={imageStyle}
            name={name}
            origin={origin}
            monitor={monitor}
            onStats={onStats}
            trame={props.trame}
          />
          {slot ? slot() : null}
        </RcaPushSizeContext.Provider>
      </div>
    </div>
  );
}

import { useContext, useEffect, useRef } from "react";

import macro from "@kitware/vtk.js/macro";
import vtkRenderWindowInteractor from "@kitware/vtk.js/Rendering/Core/RenderWindowInteractor";

import {
  type AnyProps,
  getSession,
  getTrame,
  RcaImageStreamContext,
} from "../context";
import { EventThrottle } from "../utils/EventThrottle";
import vtkInteractorStyleRemoteMouse from "../utils/interactorStyle";

class EventTranslator {
  fullWidth = 300;
  fullheight = 300;
  xOffset = 0;
  yOffset = 0;
  xSize = 300;
  ySize = 300;

  translate(event: any) {
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

const CLICK_TYPE: Record<string, boolean> = {
  LeftButtonRelease: true,
  LeftButtonPress: true,
};

export default function ImageRegion(props: AnyProps) {
  const {
    bounds,
    sendMouseMove = false,
    eventThrottleMs = 25,
  } = props;
  const propsRef = useRef<AnyProps>(props);
  propsRef.current = props;
  const rootElem = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const stream = useContext(RcaImageStreamContext);
  const streamRef = useRef(stream);
  streamRef.current = stream;
  const ctx = useRef<any>(null);

  // one-time construction
  useEffect(() => {
    const trame = getTrame(propsRef.current);
    const session = getSession(propsRef.current);
    const eventTranslator = new EventTranslator();
    const context: any = { eventTranslator };
    ctx.current = context;

    // Mouse management
    let currentOffset = [0, 0];
    const currentSizeUpdateEvent = {
      w: 10,
      h: 10,
      p: Math.max(1, window.devicePixelRatio),
    };

    function onScroll() {
      if (!rootElem.current) return;
      const rect = rootElem.current.getBoundingClientRect();
      const { top, left } = rect;
      currentOffset = [left, top];
    }

    const throttle = new EventThrottle((event: unknown) => {
      const et = eventTranslator.translate(event);
      return session.call("trame.rca.event", [
        streamRef.current?.name,
        "region",
        et,
      ]);
    }, propsRef.current.eventThrottleMs ?? 25);
    context.throttle = throttle;

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

    function sendEvent(event: any) {
      if (!trame) return;
      const p = propsRef.current;
      if (
        p.enableInteraction ||
        (p.sendMouseMove && event.type === "MouseMove" && event.action === "up")
      ) {
        throttle.sendEvent(event);
      } else if (p.sendMouseClick && CLICK_TYPE[event.type]) {
        throttle.sendEvent(event);
      }
    }

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

    const observer = new ResizeObserver(
      macro.debounce(() => {
        if (!rootElem.current) return;
        const rect = rootElem.current.getBoundingClientRect();
        const { top, left } = rect;
        currentSizeUpdateEvent.w = rect.width;
        currentSizeUpdateEvent.h = rect.height;
        currentSizeUpdateEvent.p = Math.max(1, window.devicePixelRatio);
        currentOffset = [left, top];
        propsRef.current.onSize?.(currentSizeUpdateEvent);
      }, 100),
    );

    const el = rootElem.current as HTMLDivElement;
    windowInteractor.initialize();
    windowInteractor.bindEvents(el);
    window.addEventListener("scroll", onScroll);
    observer.observe(el);

    return () => {
      observer.unobserve(el);
      windowInteractor.unbindEvents();
      window.removeEventListener("scroll", onScroll);
      ctx.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // redraw the region when a new frame arrives or bounds change
  useEffect(() => {
    if (!stream) return undefined;

    const draw = () => {
      const fullImg = stream.getImage();
      const domCanvas = canvasRef.current;
      const b = propsRef.current.bounds;
      if (!fullImg || !domCanvas || !b) return;
      const [xMin, yMin, xMax, yMax] = b;
      const { width, height } = fullImg;
      const canvasWidth = Math.floor((xMax - xMin) * width);
      const canvasHeight = Math.floor((yMax - yMin) * height);
      const sx = Math.floor(xMin * width);
      const sy = Math.floor((1 - yMax) * height);
      const sw = Math.floor((xMax - xMin) * width);
      const sh = Math.floor((yMax - yMin) * height);
      domCanvas.width = canvasWidth;
      domCanvas.height = canvasHeight;
      const context2d = domCanvas.getContext("2d") as CanvasRenderingContext2D;
      context2d.drawImage(
        fullImg,
        sx,
        sy,
        sw,
        sh,
        0,
        0,
        canvasWidth,
        canvasHeight,
      );

      // Update event translator
      const eventTranslator = ctx.current?.eventTranslator;
      if (eventTranslator) {
        eventTranslator.fullWidth = width;
        eventTranslator.fullheight = height;
        eventTranslator.xOffset = sx;
        eventTranslator.xSize = sw;
        eventTranslator.yOffset = Math.floor(yMin * height);
        eventTranslator.ySize = sh;
      }
    };

    draw();
    return stream.subscribe(draw);
  }, [stream, bounds]);

  // prop-driven updates
  useEffect(() => {
    if (ctx.current)
      ctx.current.throttle.throttleTimeMs = Number(eventThrottleMs);
  }, [eventThrottleMs]);
  useEffect(() => {
    ctx.current?.interactorStyle.setSendMouseMove(sendMouseMove);
  }, [sendMouseMove]);

  return (
    <div className="image-region" ref={rootElem}>
      <canvas className="image-region-canvas" ref={canvasRef} />
    </div>
  );
}
